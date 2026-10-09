"""Các engine tổng hợp giọng nói.

- XTTSEngine: nhân bản giọng từ một đoạn âm thanh mẫu (chạy hoàn toàn trên máy).
"""
from __future__ import annotations

import os

import numpy as np

XTTS_LANGS = {
    "Tiếng Việt": "vi", "English": "en", "Español": "es", "Français": "fr",
    "Deutsch": "de", "Italiano": "it", "Português": "pt", "Polski": "pl",
    "Türkçe": "tr", "Русский": "ru", "Nederlands": "nl", "Čeština": "cs",
    "العربية": "ar", "中文": "zh-cn", "日本語": "ja", "한국어": "ko", "Magyar": "hu",
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
        try:
            import torch  # noqa: F401
            from TTS.api import TTS  # nạp muộn vì rất nặng
        except ImportError as e:
            raise RuntimeError(
                "Chưa cài PyTorch hoặc Coqui TTS. Mở PowerShell trong thư mục app và chạy: "
                ".venv\\Scripts\\activate  rồi  pip install -r requirements.txt  "
                "(cần Python 3.10 đến 3.12)."
            ) from e

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
