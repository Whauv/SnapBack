from __future__ import annotations

import importlib
import inspect
import os
import sys
import types
import unittest
from pathlib import Path

from services.exporters.export import build_markdown_export


class StubSummarizer:
    def generate_summary(self, transcript_text: str, language: str = "English", recap_length: str = "standard") -> str:
        return f"Summary for {language}: {transcript_text[:60]}".strip()

    def extract_keywords(self, transcript_text: str) -> list[str]:
        return ["gradient descent", "learning rate"]

    def summarize_full_session(self, transcript_text: str, language: str = "English") -> str:
        return f"Full summary for {language}"

    def generate_study_pack(self, transcript_text: str, language: str = "English") -> dict:
        return {
            "outline": ["Optimization basics"],
            "flashcards": [{"question": "What is gradient descent?", "answer": "An optimization method."}],
            "quiz_questions": [
                {
                    "question": "Why does learning rate matter?",
                    "answer": "It affects convergence.",
                    "explanation": "Too small is slow and too large can diverge.",
                }
            ],
            "review_priorities": ["Update rule"],
        }


class ApiFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(__file__).resolve().parent / "_tmp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / f"{self._testMethodName}.db"
        self.db_path.unlink(missing_ok=True)
        os.environ["SNAPBACK_DB_PATH"] = str(self.db_path)
        os.environ["AUTO_DELETE_AFTER_HOURS"] = "24"
        os.environ["CORS_ALLOW_ORIGINS"] = "http://localhost:5173"
        self._install_dependency_stubs()
        self.api_module = importlib.import_module("apps.api.main")
        self.api_module = importlib.reload(self.api_module)
        self.api_module.summarizer = StubSummarizer()
        self.api_module.init_db()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)
        os.environ.pop("SNAPBACK_DB_PATH", None)

    def _install_dependency_stubs(self):
        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class FastAPI:
            def __init__(self, *args, **kwargs):
                self.routes = []

            def add_middleware(self, *args, **kwargs):
                return None

            def get(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

            def post(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

        class Response:
            def __init__(self, content=None, media_type=None, headers=None):
                self.content = content
                self.media_type = media_type
                self.headers = headers or {}

        class RedirectResponse(Response):
            def __init__(self, url: str, status_code: int = 307):
                super().__init__(headers={"location": url})
                self.status_code = status_code

        fastapi_module = types.ModuleType("fastapi")
        fastapi_module.FastAPI = FastAPI
        fastapi_module.HTTPException = HTTPException

        cors_module = types.ModuleType("fastapi.middleware.cors")
        cors_module.CORSMiddleware = object

        responses_module = types.ModuleType("fastapi.responses")
        responses_module.RedirectResponse = RedirectResponse
        responses_module.Response = Response

        sys.modules["fastapi"] = fastapi_module
        sys.modules["fastapi.middleware"] = types.ModuleType("fastapi.middleware")
        sys.modules["fastapi.middleware.cors"] = cors_module
        sys.modules["fastapi.responses"] = responses_module

        class ValidationError(Exception):
            pass

        def Field(default=..., **kwargs):
            return default

        def field_validator(*field_names):
            def decorator(func):
                func.__field_names__ = field_names
                return func

            return decorator

        class BaseModel:
            __validators__ = {}

            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__(**kwargs)
                validators = {}
                for name, value in cls.__dict__.items():
                    target = value.__func__ if isinstance(value, classmethod) else value
                    field_names = getattr(target, "__field_names__", ())
                    for field_name in field_names:
                        validators.setdefault(field_name, []).append(target)
                cls.__validators__ = validators

            def __init__(self, **kwargs):
                for field_name in getattr(self, "__annotations__", {}):
                    if field_name in kwargs:
                        value = kwargs[field_name]
                    elif hasattr(type(self), field_name):
                        value = getattr(type(self), field_name)
                    else:
                        raise ValidationError(f"{field_name} is required")

                    for validator in type(self).__validators__.get(field_name, []):
                        params = inspect.signature(validator).parameters
                        try:
                            if len(params) >= 3:
                                value = validator(type(self), value, types.SimpleNamespace(field_name=field_name))
                            else:
                                value = validator(type(self), value)
                        except Exception as error:
                            raise ValidationError(str(error)) from error
                    setattr(self, field_name, value)

        pydantic_module = types.ModuleType("pydantic")
        pydantic_module.BaseModel = BaseModel
        pydantic_module.Field = Field
        pydantic_module.ValidationError = ValidationError
        pydantic_module.field_validator = field_validator
        sys.modules["pydantic"] = pydantic_module

    def test_root_redirects_to_docs(self):
        response = self.api_module.root_redirect()
        self.assertEqual(response.headers["location"], "/docs")

    def test_session_recap_and_study_pack_flow(self):
        session_payload = self.api_module.SessionStartRequest(mode="cloud", language="English", recap_length="standard")
        session_response = self.api_module.start_session(session_payload)
        session_id = session_response["session_id"]

        transcript_payloads = [
            self.api_module.TranscriptChunkRequest(
                session_id=session_id,
                text="We are introducing gradient descent and discussing the cost function.",
                timestamp="2026-04-07T10:00:00+00:00",
            ),
            self.api_module.TranscriptChunkRequest(
                session_id=session_id,
                text="This will be on the exam, so remember the update rule and learning rate tradeoff.",
                timestamp="2026-04-07T10:01:00+00:00",
            ),
        ]
        for payload in transcript_payloads:
            self.api_module.ingest_transcript(payload)

        recap_response = self.api_module.generate_recap(
            self.api_module.RecapRequest(
                session_id=session_id,
                from_timestamp="2026-04-07T09:59:00+00:00",
                to_timestamp="2026-04-07T10:02:00+00:00",
            )
        )
        self.assertTrue(recap_response["summary"])
        self.assertTrue(recap_response["missed_alerts"])

        study_pack_response = self.api_module.generate_study_pack(self.api_module.StudyPackRequest(session_id=session_id))
        self.assertTrue(study_pack_response["study_pack"]["flashcards"])

        session_end_response = self.api_module.complete_session(self.api_module.SessionEndRequest(session_id=session_id))
        self.assertTrue(session_end_response["full_summary"])

        transcript_response = self.api_module.get_session_transcript(session_id)
        markdown_export = build_markdown_export(transcript_response)
        self.assertIn("SnapBack Session", markdown_export)

    def test_invalid_timestamp_is_rejected(self):
        with self.assertRaises(Exception) as context:
            self.api_module._parse_timestamp("not-a-timestamp")
        self.assertIn("Timestamps must be valid ISO-8601 strings", str(context.exception))

    def test_invalid_audio_payload_is_rejected(self):
        session_response = self.api_module.start_session(
            self.api_module.SessionStartRequest(mode="cloud", language="English", recap_length="standard")
        )
        session_id = session_response["session_id"]
        with self.assertRaises(self.api_module.HTTPException) as context:
            self.api_module.ingest_audio_chunk(
                self.api_module.AudioChunkRequest(
                    session_id=session_id,
                    chunk_index=0,
                    mime_type="audio/webm",
                    audio_base64="%%%not-valid-base64%%%",
                    timestamp="2026-04-07T10:00:00+00:00",
                    source="chrome-extension",
                )
            )
        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
