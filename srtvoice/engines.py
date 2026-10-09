"""Các engine tổng hợp giọng nói.

- XTTSEngine: nhân bản giọng từ một đoạn âm thanh mẫu (chạy hoàn toàn trên máy).
- EdgeEngine: giọng có sẵn (cần internet, không nhân bản giọng, nhẹ và nhanh).
"""
from __future__ import annotations

import asyncio
import os
import tempfile

import numpy as np

from .audioutil import decode_to_array

XTTS_LANGS = {
    "Tiếng Việt": "vi", "English": "en", "Español": "es", "Français": "fr",
    "Deutsch": "de", "Italiano": "it", "Português": "pt", "Polski": "pl",
    "Türkçe": "tr", "Русский": "ru", "Nederlands": "nl", "Čeština": "cs",
    "العربية": "ar", "中文": "zh-cn", "日本語": "ja", "한국어": "ko", "Magyar": "hu",
}

EDGE_VOICES = {
    "Hoài My (nữ, Việt)": "vi-VN-HoaiMyNeural",
    "Nam Minh (nam, Việt)": "vi-VN-NamMinhNeural",
    "Jenny (nữ, Anh-Mỹ)": "en-US-JennyNeural",
    "Guy (nam, Anh-Mỹ)": "en-US-GuyNeural",
}

_xtts_cache: dict = {}


def pick_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


class XTTSEngine:
    MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(self, reference_wav: str, language: str = "vi"):
        # Người dùng đã đồng ý giấy phép CPML trong giao diện trước khi tới đây.
        os.environ["COQUI_TOS_AGREED"] = "1"
        from TTS.api import TTS  # nạp muộn vì rất nặng

        device = pick_device()
        key = (self.MODEL, device)
        if key not in _xtts_cache:
            _xtts_cache[key] = TTS(self.MODEL).to(device)
        self.tts = _xtts_cache[key]
        self.ref = reference_wav
        self.lang = language
        self.sr = int(getattr(self.tts.synthesizer, "output_sample_rate", 24000))

    def __call__(self, text: str) -> tuple[np.ndarray, int]:
        wav = self.tts.tts(text=text, speaker_wav=self.ref, language=self.lang)
        return np.asarray(wav, dtype=np.float32), self.sr


class EdgeEngine:
    def __init__(self, voice: str, rate_percent: int = 0):
        self.voice = voice
        self.rate = f"{rate_percent:+d}%"
        self.sr = 24000

    async def _save(self, text: str, path: str) -> None:
        import edge_tts
        await edge_tts.Communicate(text, self.voice, rate=self.rate).save(path)

    def __call__(self, text: str) -> tuple[np.ndarray, int]:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.mp3")
            asyncio.run(self._save(text, p))
            return decode_to_array(p, self.sr), self.sr
