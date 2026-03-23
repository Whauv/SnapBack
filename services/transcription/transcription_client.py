"""Transcription client for SnapBack using AssemblyAI or local Whisper."""

from __future__ import annotations

import base64
import contextlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pyaudio
import requests
import websocket
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]

CHUNK_MS = 100
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
FRAMES_PER_BUFFER = int(SAMPLE_RATE * CHUNK_MS / 1000)
LOCAL_SEGMENT_SECONDS = 30
ASSEMBLYAI_WS_URL = f"wss://api.assemblyai.com/v2/realtime/ws?sample_rate={SAMPLE_RATE}"
DEFAULT_WHISPER_MODEL_URL = (
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
)
MAX_RETRIES = 2


def utc_now_iso() -> str:
    """Return the current time in ISO 8601 format (UTC)."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TranscriptionConfig:
    """Configuration for SnapBack transcription."""

    backend_base_url: str
    assemblyai_api_key: str | None = None
    whisper_binary_path: str = "whisper-cli"
    whisper_model_path: str = str(ROOT_DIR / "models" / "ggml-base.en.bin")
    whisper_model_url: str = DEFAULT_WHISPER_MODEL_URL
    whisper_language: str = "en"
    whisper_threads: int = 4
    mode: str = "cloud"
    microphone_device_index: int | None = None
    local_segment_seconds: int = LOCAL_SEGMENT_SECONDS
    reconnect_backoff_seconds: float = 2.0
    max_reconnect_backoff_seconds: float = 15.0
    request_timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls) -> TranscriptionConfig:
        """Create a TranscriptionConfig instance from environment variables."""
        load_dotenv(ROOT_DIR / "config" / "env" / ".env")
        backend_port = os.getenv("BACKEND_PORT", "8000")
        model_path = str(ROOT_DIR / "models" / "ggml-base.en.bin")
        whisper_model_path = os.getenv("WHISPER_MODEL_PATH", model_path)
        mic_idx_str = os.getenv("MICROPHONE_DEVICE_INDEX", "")
        mic_idx = int(mic_idx_str) if mic_idx_str else None
        local_seg_str = os.getenv("LOCAL_SEGMENT_SECONDS", str(LOCAL_SEGMENT_SECONDS))
        local_seg = max(5, int(local_seg_str))

        return cls(
            backend_base_url=os.getenv(
                "BACKEND_BASE_URL",
                f"http://localhost:{backend_port}",
            ),
            assemblyai_api_key=os.getenv("ASSEMBLYAI_API_KEY"),
            whisper_binary_path=os.getenv("WHISPER_BINARY_PATH", "whisper-cli"),
            whisper_model_path=whisper_model_path,
            whisper_model_url=os.getenv("WHISPER_MODEL_URL", DEFAULT_WHISPER_MODEL_URL),
            whisper_language=os.getenv("WHISPER_LANGUAGE", "en"),
            whisper_threads=max(1, int(os.getenv("WHISPER_THREADS", "4"))),
            mode=os.getenv("TRANSCRIPTION_MODE", "cloud").lower(),
            microphone_device_index=mic_idx,
            local_segment_seconds=local_seg,
        )


class SnapBackTranscriptionClient:
    """Client for managing real-time and local transcription sessions."""

    def __init__(self, config: TranscriptionConfig) -> None:
        """Initialize the transcription client with the given configuration."""
        self.config = config
        self._ws: websocket.WebSocketApp | None = None
        self._stream_thread: threading.Thread | None = None
        self._audio_thread: threading.Thread | None = None
        self._local_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._session_lock = threading.Lock()
        self._session_id: str | None = None
        self._requests = requests.Session()

    def start_transcription(self, session_id: str) -> None:
        """Start a transcription session for the given ID."""
        self.stop_transcription()
        with self._session_lock:
            self._session_id = session_id
            self._stop_event.clear()
            self._connected_event.clear()

        if self.config.mode == "local":
            self._ensure_whisper_binary()
            self._ensure_whisper_model()
            self._local_thread = threading.Thread(
                target=self._run_local_whisper_loop,
                daemon=True,
            )
            self._local_thread.start()
            return

        if not self.config.assemblyai_api_key:
            msg = "ASSEMBLYAI_API_KEY is required for cloud transcription mode."
            raise RuntimeError(msg)

        self._stream_thread = threading.Thread(
            target=self._run_cloud_stream_loop,
            daemon=True,
        )
        self._audio_thread = threading.Thread(
            target=self._capture_microphone_stream,
            daemon=True,
        )
        self._stream_thread.start()
        self._audio_thread.start()

    def stop_transcription(self) -> None:
        """Stop the current transcription session and clean up resources."""
        self._stop_event.set()
        self._connected_event.clear()
        if self._ws:
            with contextlib.suppress(Exception):
                self._ws.close()
        self._join_thread(self._audio_thread)
        self._join_thread(self._stream_thread)
        self._join_thread(self._local_thread)
        self._audio_thread = None
        self._stream_thread = None
        self._local_thread = None
        self._ws = None

    def _join_thread(self, thread: threading.Thread | None) -> None:
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _run_cloud_stream_loop(self) -> None:
        backoff = self.config.reconnect_backoff_seconds
        while not self._stop_event.is_set():
            self._connected_event.clear()
            self._ws = websocket.WebSocketApp(
                ASSEMBLYAI_WS_URL,
                header=[f"Authorization: {self.config.assemblyai_api_key}"],
                on_open=self._on_open,
                on_message=self._on_message,
                on_close=self._on_close,
                on_error=self._on_error,
            )
            self._ws.run_forever(ping_interval=5, ping_timeout=3)
            if self._stop_event.is_set():
                break
            time.sleep(backoff)
            backoff = min(backoff * 2, self.config.max_reconnect_backoff_seconds)

    def _capture_microphone_stream(self) -> None:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            input_device_index=self.config.microphone_device_index,
        )
        try:
            while not self._stop_event.is_set():
                chunk = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                if not self._connected_event.wait(timeout=0.5):
                    continue
                if self._ws and self._ws.sock and self._ws.sock.connected:
                    try:
                        audio_data = base64.b64encode(chunk).decode("utf-8")
                        self._ws.send(json.dumps({"audio_data": audio_data}))
                    except Exception:
                        logger.exception("AssemblyAI send failed")
                        self._connected_event.clear()
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def _on_open(self, _ws: websocket.WebSocketApp) -> None:
        self._connected_event.set()

    def _on_message(self, _ws: websocket.WebSocketApp, message: str) -> None:
        payload = json.loads(message)
        message_type = payload.get("message_type")
        if message_type == "SessionBegins":
            self._connected_event.set()
            return
        if message_type == "FinalTranscript" and payload.get("text"):
            self._post_transcript(payload["text"])
            return
        if message_type == "Error":
            logger.exception("AssemblyAI error: %s", payload)

    def _on_close(
        self,
        _ws: websocket.WebSocketApp,
        status_code: int,
        close_msg: str,
    ) -> None:
        self._connected_event.clear()
        logger.info(
            "AssemblyAI socket closed: code=%s message=%s",
            status_code,
            close_msg,
        )

    def _on_error(self, _ws: websocket.WebSocketApp, error: object) -> None:
        self._connected_event.clear()
        logger.error("AssemblyAI WebSocket error: %s", error)

    def _post_transcript(self, text: str) -> None:
        with self._session_lock:
            session_id = self._session_id
        if not session_id:
            return

        payload = {
            "session_id": session_id,
            "text": text.strip(),
            "timestamp": utc_now_iso(),
        }
        if not payload["text"]:
            return

        for attempt in range(MAX_RETRIES + 1):
            # ruff: noqa: PERF203
            try:
                response = self._requests.post(
                    f"{self.config.backend_base_url}/session/transcript",
                    json=payload,
                    timeout=self.config.request_timeout_seconds,
                )
                response.raise_for_status()
            except requests.RequestException:
                if attempt == MAX_RETRIES:
                    logger.exception(
                        "Failed to post transcript chunk after retries",
                    )
                else:
                    time.sleep(1.0 + attempt)
            else:
                return

    def _run_local_whisper_loop(self) -> None:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            input_device_index=self.config.microphone_device_index,
        )
        try:
            while not self._stop_event.is_set():
                frames: list[bytes] = []
                started_at = time.monotonic()
                while (
                    time.monotonic() - started_at < self.config.local_segment_seconds
                    and not self._stop_event.is_set()
                ):
                    frames.append(
                        stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False),
                    )
                if frames:
                    self._transcribe_local_segment(frames)
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

    def _transcribe_local_segment(self, frames: list[bytes]) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="snapback-whisper-"))
        wav_path = temp_dir / "segment.wav"
        txt_path = temp_dir / "segment.wav.txt"
        try:
            self._write_wav(wav_path, frames)
            text = self._transcribe_with_whisper(wav_path, txt_path)
            if text:
                self._post_transcript(text)
        finally:
            for path in (txt_path, wav_path):
                path.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                temp_dir.rmdir()

    def _write_wav(self, wav_path: Path, frames: list[bytes]) -> None:
        with wave.open(str(wav_path), "wb") as handle:
            handle.setnchannels(CHANNELS)
            handle.setsampwidth(SAMPLE_WIDTH_BYTES)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes(b"".join(frames))

    def _ensure_whisper_binary(self) -> None:
        binary_path = self.config.whisper_binary_path
        if Path(binary_path).exists() or shutil.which(binary_path):
            return
        msg = (
            "whisper.cpp binary was not found. Set WHISPER_BINARY_PATH to "
            "whisper-cli or the full executable path."
        )
        raise RuntimeError(msg)

    def _ensure_whisper_model(self) -> None:
        model_path = Path(self.config.whisper_model_path)
        if model_path.exists():
            return
        model_path.parent.mkdir(parents=True, exist_ok=True)
        url = self.config.whisper_model_url
        with self._requests.get(
            url,
            timeout=120,
            stream=True,
        ) as response:
            response.raise_for_status()
            with model_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

    def _transcribe_with_whisper(self, wav_path: Path, txt_path: Path) -> str:
        command = [
            self.config.whisper_binary_path,
            "-m",
            self.config.whisper_model_path,
            "-f",
            str(wav_path),
            "-l",
            self.config.whisper_language,
            "-t",
            str(self.config.whisper_threads),
            "-nt",
            "-otxt",
            "-of",
            str(wav_path),
        ]
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error("whisper.cpp failed: %s", result.stderr or result.stdout)
            return ""
        if txt_path.exists():
            return txt_path.read_text(encoding="utf-8").strip()
        return result.stdout.strip()


_client: SnapBackTranscriptionClient | None = None


def configure_transcription_client(
    config: TranscriptionConfig,
) -> SnapBackTranscriptionClient:
    """Configure the global transcription client instance."""
    global _client  # noqa: PLW0603
    _client = SnapBackTranscriptionClient(config)
    return _client


def start_transcription(session_id: str) -> None:
    """Start the global transcription client for the given session."""
    if _client is None:
        configure_transcription_client(TranscriptionConfig.from_env())
    if _client:
        _client.start_transcription(session_id)


def stop_transcription() -> None:
    """Stop the global transcription client."""
    if _client is None:
        return
    _client.stop_transcription()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SnapBack live transcription client",
    )
    parser.add_argument(
        "session_id",
        help="Session ID returned by POST /session/start",
    )
    parser.add_argument(
        "--mode",
        choices=["cloud", "local"],
        default=None,
        help="Override transcription mode",
    )
    args = parser.parse_args()

    config = TranscriptionConfig.from_env()
    if args.mode:
        config.mode = args.mode

    client = configure_transcription_client(config)
    client.start_transcription(args.session_id)
    logger.info(
        "SnapBack transcription started in %s mode for session %s. "
        "Press Ctrl+C to stop.",
        config.mode,
        args.session_id,
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping transcription...")
        client.stop_transcription()
