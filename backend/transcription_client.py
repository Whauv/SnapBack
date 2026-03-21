from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyaudio
import requests
import websocket


ASSEMBLYAI_WS_URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
DEFAULT_WHISPER_MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TranscriptionConfig:
    backend_base_url: str
    assemblyai_api_key: str | None = None
    whisper_binary_path: str = "whisper-cli"
    whisper_model_path: str = "models/ggml-base.en.bin"
    mode: str = "cloud"


class LectureLensTranscriptionClient:
    def __init__(self, config: TranscriptionConfig) -> None:
        self.config = config
        self._ws: websocket.WebSocketApp | None = None
        self._audio_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None
        self._local_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._session_id: str | None = None

    def start_transcription(self, session_id: str) -> None:
        self.stop_transcription()
        self._stop_event.clear()
        self._session_id = session_id

        if self.config.mode == "local":
            self._ensure_whisper_model()
            self._local_thread = threading.Thread(target=self._run_local_whisper_loop, daemon=True)
            self._local_thread.start()
            return

        self._ws = websocket.WebSocketApp(
            ASSEMBLYAI_WS_URL,
            header={"Authorization": self.config.assemblyai_api_key or ""},
            on_open=self._on_open,
            on_message=self._on_message,
            on_close=self._on_close,
            on_error=self._on_error,
        )
        self._audio_thread = threading.Thread(target=self._capture_microphone_stream, daemon=True)
        self._worker_thread = threading.Thread(target=self._ws.run_forever, kwargs={"ping_interval": 5}, daemon=True)
        self._audio_thread.start()
        self._worker_thread.start()

    def stop_transcription(self) -> None:
        self._stop_event.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None

    def _capture_microphone_stream(self) -> None:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1600,
        )
        try:
            while not self._stop_event.is_set():
                chunk = stream.read(1600, exception_on_overflow=False)
                if self._ws and self._ws.sock and self._ws.sock.connected:
                    audio_data = base64.b64encode(chunk).decode("utf-8")
                    self._ws.send(json.dumps({"audio_data": audio_data}))
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        return None

    def _on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        payload = json.loads(message)
        if payload.get("message_type") == "FinalTranscript" and payload.get("text"):
            self._post_transcript(payload["text"])

    def _on_close(self, ws: websocket.WebSocketApp, status_code: Any, close_msg: Any) -> None:
        if not self._stop_event.is_set():
            time.sleep(2)
            if self._session_id:
                self.start_transcription(self._session_id)

    def _on_error(self, ws: websocket.WebSocketApp, error: Any) -> None:
        print(f"AssemblyAI WebSocket error: {error}")

    def _post_transcript(self, text: str) -> None:
        if not self._session_id:
            return
        requests.post(
            f"{self.config.backend_base_url}/session/transcript",
            json={
                "session_id": self._session_id,
                "text": text,
                "timestamp": utc_now_iso(),
            },
            timeout=15,
        )

    def _run_local_whisper_loop(self) -> None:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1600,
        )
        try:
            while not self._stop_event.is_set():
                frames: list[bytes] = []
                start_time = time.time()
                while time.time() - start_time < 30 and not self._stop_event.is_set():
                    frames.append(stream.read(1600, exception_on_overflow=False))
                if not frames:
                    continue
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    wav_path = Path(temp_wav.name)
                self._write_wav(wav_path, frames)
                text = self._transcribe_with_whisper(wav_path)
                if text:
                    self._post_transcript(text)
                wav_path.unlink(missing_ok=True)
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def _write_wav(self, wav_path: Path, frames: list[bytes]) -> None:
        with wave.open(str(wav_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(b"".join(frames))

    def _ensure_whisper_model(self) -> None:
        model_path = Path(self.config.whisper_model_path)
        if model_path.exists():
            return
        model_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(DEFAULT_WHISPER_MODEL_URL, timeout=120)
        response.raise_for_status()
        model_path.write_bytes(response.content)

    def _transcribe_with_whisper(self, wav_path: Path) -> str:
        command = [
            self.config.whisper_binary_path,
            "-m",
            self.config.whisper_model_path,
            "-f",
            str(wav_path),
            "-nt",
            "-otxt",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"whisper.cpp failed: {result.stderr}")
            return ""
        txt_path = wav_path.with_suffix(".txt")
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8").strip()
            txt_path.unlink(missing_ok=True)
            return text
        return result.stdout.strip()


_client: LectureLensTranscriptionClient | None = None


def configure_transcription_client(config: TranscriptionConfig) -> LectureLensTranscriptionClient:
    global _client
    _client = LectureLensTranscriptionClient(config)
    return _client


def start_transcription(session_id: str) -> None:
    if _client is None:
        raise RuntimeError("Transcription client is not configured.")
    _client.start_transcription(session_id)


def stop_transcription() -> None:
    if _client is None:
        return
    _client.stop_transcription()
