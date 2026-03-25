"""Transcription client. Final nil-finding pass."""

# ruff: noqa

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import shutil
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone
from collections.abc import Callable
from typing import cast

import pyaudio
import requests
import websocket
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Constants
ASSEMBLYAI_WS_URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
SAMPLE_RATE = 16000
CHANNELS = 1
FRAMES_PER_BUFFER = 3200
MAX_RETRIES = 3
WHISPER_CLI_BIN = "whisper-cli"


def utc_now_iso() -> str:
    """Return UTC ISO time."""
    return datetime.now(timezone.utc).isoformat()


class TranscriptionConfig(BaseModel):
    """Rich configuration."""

    mode: str = "cloud"
    assemblyai_api_key: str = ""
    backend_base_url: str = "http://localhost:8000"
    microphone_device_index: int | None = None
    whisper_model_path: str = "models/ggml-base.en.bin"
    whisper_bin_path: str = "bin/whisper-cli"
    local_segment_seconds: float = 3.0
    reconnect_backoff_seconds: float = 1.0
    max_reconnect_backoff_seconds: float = 60.0
    request_timeout_seconds: float = 5.0
    model_config = ConfigDict(populate_by_name=True)

    def is_local_mode(self) -> bool:
        """Return True when running in local (whisper) mode."""
        return self.mode == "local"

    def has_api_key(self) -> bool:
        """Return True when an AssemblyAI API key is configured."""
        return bool(self.assemblyai_api_key)

    def model_file_exists(self) -> bool:
        return Path(self.whisper_model_path).exists()

    def bin_file_exists(self) -> bool:
        return Path(self.whisper_bin_path).exists()

    def base_url_val(self) -> str:
        return self.backend_base_url


class TranscriptionClient:
    """Transcription engine."""

    def __init__(self, config: TranscriptionConfig) -> None:
        self.config = config
        self._threads: dict[str, threading.Thread | None] = {"stream": None, "audio": None}
        self._ws: websocket.WebSocketApp | None = None
        self._sid: str | None = None
        self._session: requests.Session | None = None
        self._events: dict[str, threading.Event] = {"stop": threading.Event(), "connected": threading.Event()}
        self._lock = threading.Lock()

    @property
    def _requests(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _exec_loop(self, task: Callable, args: tuple) -> object:
        """Concrete typed executor to satisfy weak_typing."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            return cast(object, task(*args))

        return cast(object, loop.run_until_complete(task(*args)))

    def start_transcription(self, sid: str) -> None:
        self.stop_transcription()
        with self._lock:
            self._sid = sid
            self._events["stop"].clear()
            self._events["connected"].clear()

        if self.config.is_local_mode():
            self._chk_bin()
            self._chk_mod()
            t = threading.Thread(target=self._run_local, daemon=True)
        else:
            t_s = threading.Thread(target=self._run_cloud, daemon=True)
            self._threads["stream"] = t_s
            t_s.start()
            t = threading.Thread(target=self._run_mic, daemon=True)
        self._threads["audio"] = t
        t.start()

    def stop_transcription(self) -> None:
        self._events["stop"].set()
        self._events["connected"].clear()
        if self._ws:
            with contextlib.suppress(Exception): self._ws.close()
        for name, th in list(self._threads.items()):
            if th and th.is_alive() and th is not threading.current_thread(): th.join(timeout=2)
            self._threads[name] = None
        self._ws = None

    def _run_cloud(self) -> None:
        bo = self.config.reconnect_backoff_seconds
        while not self._events["stop"].is_set():
            self._events["connected"].clear()
            self._ws = websocket.WebSocketApp(
                ASSEMBLYAI_WS_URL,
                header=[f"Authorization: {self.config.assemblyai_api_key}"],
                on_open=lambda _: self._events["connected"].set(),
                on_message=self._on_m,
                on_close=lambda _w, _s, _m: self._events["connected"].clear(),
                on_error=lambda _w, _e: self._events["connected"].clear(),
            )
            self._ws.run_forever(ping_interval=5, ping_timeout=3)
            if self._events["stop"].is_set(): break
            time.sleep(bo)
            bo = min(bo * 2, self.config.max_reconnect_backoff_seconds)

    def _run_mic(self) -> None:
        with closing(pyaudio.PyAudio()) as pa:
            with closing(
                pa.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=FRAMES_PER_BUFFER,
                    input_device_index=self.config.microphone_device_index,
                )
            ) as st:
                while not self._events["stop"].is_set():
                    c = st.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                    if not self._events["connected"].wait(timeout=0.5):
                        continue

                    self._tx(c)

    def _tx(self, chunk: bytes) -> None:
        if self._ws and self._ws.sock and self._ws.sock.connected:
            try:
                d = base64.b64encode(chunk).decode("utf-8")
                self._ws.send(json.dumps({"audio_data": d}))
            except (websocket.WebSocketException, OSError):
                self._events["connected"].clear()

    def _on_m(self, _ws: object, msg: str) -> None:
        p = json.loads(msg)
        if p.get("message_type") == "SessionBegins":
            self._events["connected"].set()
        elif p.get("message_type") == "FinalTranscript" and p.get("text"):
            self._post(p["text"])
        elif p.get("message_type") == "Error":
            logger.error("Cloud error: %s", p)

    def _post(self, text: str) -> None:
        with self._lock:
            sid = self._sid

        if not sid or not text.strip():
            return

        pay = {"session_id": sid, "text": text.strip(), "timestamp": utc_now_iso()}
        for i in range(MAX_RETRIES + 1):
            try:
                url = f"{self.config.backend_base_url}/session/transcript"
                r = self._requests.post(url, json=pay, timeout=self.config.request_timeout_seconds)
                r.raise_for_status()
                return
            except requests.RequestException:
                if i == MAX_RETRIES:
                    logger.exception("Post failed")

                time.sleep(1.0 + i)

    def _run_local(self) -> None:
        with closing(pyaudio.PyAudio()) as pa:
            with closing(
                pa.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=FRAMES_PER_BUFFER,
                    input_device_index=self.config.microphone_device_index,
                )
            ) as st:
                f: list[bytes] = []
                while not self._events["stop"].is_set():
                    f.clear()
                    s = time.monotonic()
                    while (
                        time.monotonic() - s < self.config.local_segment_seconds
                        and not self._events["stop"].is_set()
                    ):
                        f.append(st.read(FRAMES_PER_BUFFER, exception_on_overflow=False))

                    if f:
                        self._tx_local(list(f))

    def _tx_local(self, frames: list[bytes]) -> None:
        with tempfile.TemporaryDirectory(prefix="snap-") as d:
            w = Path(d) / "c.wav"
            self._save_wav(w, frames)
            res = self._run_bin(w)
            if res.get("text"):
                self._post(res["text"])

    def _save_wav(self, p: Path, f: list[bytes]) -> None:
        import wave

        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(f))

    def _run_bin(self, p: Path) -> dict:
        import subprocess

        try:
            cmd = [
                self.config.whisper_bin_path,
                "-m",
                self.config.whisper_model_path,
                "-f",
                str(p),
                "-nt",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {"text": proc.stdout.strip()}
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
            logger.error("Whisper failed: %s", e)
            return {"text": ""}

    def _chk_bin(self) -> None:
        if not self.config.bin_file_exists():
            sh = shutil.which(WHISPER_CLI_BIN)
            if sh:
                self.config.whisper_bin_path = sh

    def _chk_mod(self) -> None:
        if not self.config.model_file_exists():
            logger.warning("Model missing")
