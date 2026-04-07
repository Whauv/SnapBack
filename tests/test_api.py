from __future__ import annotations

import importlib
import inspect
import os
import sys
import types
import unittest
from pathlib import Path


def install_framework_stubs():
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

        def middleware(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

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
            self.status_code = 200

    class RedirectResponse(Response):
        def __init__(self, url: str, status_code: int = 307):
            super().__init__(headers={"location": url})
            self.status_code = status_code

    class Request:
        def __init__(self, headers=None, path="/", client_host="127.0.0.1"):
            self.headers = headers or {}
            self.url = types.SimpleNamespace(path=path)
            self.client = types.SimpleNamespace(host=client_host)
            self.state = types.SimpleNamespace()
            self.method = "GET"

    fastapi_module = types.ModuleType("fastapi")
    fastapi_module.FastAPI = FastAPI
    fastapi_module.HTTPException = HTTPException
    fastapi_module.Request = Request
    fastapi_module.Response = Response

    cors_module = types.ModuleType("fastapi.middleware.cors")
    cors_module.CORSMiddleware = object
    trusted_host_module = types.ModuleType("fastapi.middleware.trustedhost")
    trusted_host_module.TrustedHostMiddleware = object

    responses_module = types.ModuleType("fastapi.responses")
    responses_module.RedirectResponse = RedirectResponse
    responses_module.Response = Response

    sys.modules["fastapi"] = fastapi_module
    sys.modules["fastapi.middleware"] = types.ModuleType("fastapi.middleware")
    sys.modules["fastapi.middleware.cors"] = cors_module
    sys.modules["fastapi.middleware.trustedhost"] = trusted_host_module
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
            for value in cls.__dict__.values():
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
                    except Exception as error:  # pragma: no cover - test stub behavior
                        raise ValidationError(str(error)) from error
                setattr(self, field_name, value)

    pydantic_module = types.ModuleType("pydantic")
    pydantic_module.BaseModel = BaseModel
    pydantic_module.ConfigDict = dict
    pydantic_module.Field = Field
    pydantic_module.ValidationError = ValidationError
    pydantic_module.field_validator = field_validator
    sys.modules["pydantic"] = pydantic_module

    return HTTPException, Request


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


class ApiSecurityAndServiceTests(unittest.TestCase):
    def setUp(self):
        self.http_exception_class, self.request_class = install_framework_stubs()
        self.temp_dir = Path(__file__).resolve().parent / "_tmp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / f"{self._testMethodName}.db"
        self.db_path.unlink(missing_ok=True)
        os.environ["SNAPBACK_DB_PATH"] = str(self.db_path)
        os.environ["APP_ENV"] = "development"
        os.environ["SNAPBACK_API_TOKENS"] = "alice:token-alice,bob:token-bob"
        os.environ["RATE_LIMIT_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"

        self.settings_module = importlib.reload(importlib.import_module("services.api.settings"))
        self.contracts_module = importlib.reload(importlib.import_module("services.api.contracts"))
        self.database_module = importlib.reload(importlib.import_module("services.storage.database"))
        self.auth_module = importlib.reload(importlib.import_module("services.api.auth"))
        self.rate_limit_module = importlib.reload(importlib.import_module("services.api.rate_limit"))
        self.service_module = importlib.reload(importlib.import_module("services.api.session_service"))
        self.main_module = importlib.reload(importlib.import_module("apps.api.main"))

        self.database_module.init_db()
        settings = self.settings_module.AppSettings.from_env()
        self.service = self.service_module.SessionService(
            root_dir=self.settings_module.ROOT_DIR,
            settings=settings,
            summarizer=StubSummarizer(),
        )
        self.auth_manager = self.auth_module.AuthManager(settings)
        self.rate_limiter = self.rate_limit_module.InMemoryRateLimiter(limit=2, window_seconds=60)
        self.alice = self.auth_module.AuthenticatedPrincipal(principal_id="principal:alice", token_name="alice")
        self.bob = self.auth_module.AuthenticatedPrincipal(principal_id="principal:bob", token_name="bob")

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)
        for key in [
            "SNAPBACK_DB_PATH",
            "APP_ENV",
            "SNAPBACK_API_TOKENS",
            "RATE_LIMIT_REQUESTS",
            "RATE_LIMIT_WINDOW_SECONDS",
        ]:
            os.environ.pop(key, None)

    def test_root_redirects_to_docs(self):
        response = self.main_module.root_redirect()
        self.assertEqual(response.headers["location"], "/docs")

    def test_auth_manager_reads_bearer_token(self):
        request = self.request_class(headers={"authorization": "Bearer token-alice"})
        principal = self.auth_manager.authenticate(request)
        self.assertEqual(principal.principal_id, "principal:alice")

    def test_rate_limiter_blocks_after_limit(self):
        self.rate_limiter.enforce("principal:alice:/session/start")
        self.rate_limiter.enforce("principal:alice:/session/start")
        with self.assertRaises(self.http_exception_class) as context:
            self.rate_limiter.enforce("principal:alice:/session/start")
        self.assertEqual(context.exception.status_code, 429)

    def test_session_service_enforces_owner_scope(self):
        session = self.service.start_session(
            principal=self.alice,
            mode="cloud",
            language="English",
            recap_length="standard",
        )
        self.service.ingest_transcript(
            principal=self.alice,
            session_id=session["session_id"],
            text="We are introducing gradient descent and discussing the cost function.",
            timestamp="2026-04-07T10:00:00+00:00",
        )

        with self.assertRaises(self.http_exception_class) as context:
            self.service.get_session_transcript(principal=self.bob, session_id=session["session_id"])
        self.assertEqual(context.exception.status_code, 404)

    def test_session_service_generates_recap_and_study_pack(self):
        session = self.service.start_session(
            principal=self.alice,
            mode="cloud",
            language="English",
            recap_length="standard",
        )
        self.service.ingest_transcript(
            principal=self.alice,
            session_id=session["session_id"],
            text="We are introducing gradient descent and discussing the cost function.",
            timestamp="2026-04-07T10:00:00+00:00",
        )
        self.service.ingest_transcript(
            principal=self.alice,
            session_id=session["session_id"],
            text="This will be on the exam, so remember the update rule and learning rate tradeoff.",
            timestamp="2026-04-07T10:01:00+00:00",
        )

        recap = self.service.generate_recap(
            principal=self.alice,
            session_id=session["session_id"],
            from_timestamp="2026-04-07T09:59:00+00:00",
            to_timestamp="2026-04-07T10:02:00+00:00",
        )
        self.assertTrue(recap["summary"])
        self.assertTrue(recap["missed_alerts"])

        study_pack = self.service.generate_study_pack(principal=self.alice, session_id=session["session_id"])
        self.assertTrue(study_pack["study_pack"]["flashcards"])

    def test_invalid_audio_payload_is_rejected(self):
        session = self.service.start_session(
            principal=self.alice,
            mode="cloud",
            language="English",
            recap_length="standard",
        )
        with self.assertRaises(self.http_exception_class) as context:
            self.service.ingest_audio_chunk(
                principal=self.alice,
                session_id=session["session_id"],
                chunk_index=0,
                mime_type="audio/webm",
                audio_base64="%%%not-valid-base64%%%",
                timestamp="2026-04-07T10:00:00+00:00",
                source="chrome-extension",
            )
        self.assertEqual(context.exception.status_code, 400)

    def test_contract_timestamp_validation(self):
        with self.assertRaises(Exception) as context:
            self.contracts_module.parse_timestamp("not-a-timestamp")
        self.assertIn("Timestamps must be valid ISO-8601 strings", str(context.exception))


if __name__ == "__main__":
    unittest.main()
