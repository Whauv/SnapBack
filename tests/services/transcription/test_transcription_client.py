"""Import-safety and configuration tests for the transcription client.

The realtime capture paths (AssemblyAI websocket, whisper.cpp, PyAudio) require
live audio hardware and network access, so they are not exercised here. These
tests confirm the module imports cleanly and parses its configuration from the
environment as expected.
"""

from __future__ import annotations

import importlib
import os
import unittest


class TranscriptionConfigTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("services.transcription.transcription_client")
        self._saved = {
            key: os.environ.get(key)
            for key in ("BACKEND_PORT", "TRANSCRIPTION_MODE", "LOCAL_SEGMENT_SECONDS", "WHISPER_THREADS")
        }

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_module_exposes_config_and_client(self):
        self.assertTrue(hasattr(self.module, "TranscriptionConfig"))
        self.assertTrue(hasattr(self.module, "SnapBackTranscriptionClient"))

    def test_from_env_defaults(self):
        for key in ("BACKEND_PORT", "TRANSCRIPTION_MODE", "LOCAL_SEGMENT_SECONDS"):
            os.environ.pop(key, None)
        config = self.module.TranscriptionConfig.from_env()
        self.assertTrue(config.backend_base_url.startswith("http://localhost:"))
        self.assertEqual(config.mode, "cloud")
        self.assertGreaterEqual(config.whisper_threads, 1)

    def test_from_env_overrides(self):
        os.environ["BACKEND_PORT"] = "9001"
        os.environ["TRANSCRIPTION_MODE"] = "LOCAL"
        os.environ["LOCAL_SEGMENT_SECONDS"] = "1"  # clamped up to the minimum of 5
        config = self.module.TranscriptionConfig.from_env()
        self.assertEqual(config.backend_base_url, "http://localhost:9001")
        self.assertEqual(config.mode, "local")
        self.assertEqual(config.local_segment_seconds, 5)


if __name__ == "__main__":
    unittest.main()
