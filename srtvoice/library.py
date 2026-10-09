"""Thư viện giọng nói: lưu các giọng mẫu đã dùng để nhân bản, dùng lại cho lần sau.

Mỗi giọng là một thư mục `voices/<id>/` gồm `ref.wav` (mẫu đã chuẩn hóa 24 kHz, mono)
và `meta.json`. XTTS nhân bản giọng trực tiếp từ mẫu này nên không cần lưu gì thêm.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass

from .audioutil import decode_to_array, write_wav

SR = 24000
MIN_SEC = 3.0
MAX_SEC = 30.0


@dataclass
class Voice:
    id: str
    name: str
    lang: str
    created: float
    duration: float
    consent: bool

    @property
    def created_text(self) -> str:
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(self.created))


def _slug(name: str) -> str:
    s = name.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:30] or "voice"


class VoiceLibrary:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _dir(self, voice_id: str) -> str:
        # chống đường dẫn lạ: id chỉ gồm chữ, số và gạch ngang
        if not re.fullmatch(r"[a-z0-9-]+", voice_id or ""):
            raise ValueError("Mã giọng không hợp lệ.")
        return os.path.join(self.root, voice_id)

    def list(self) -> list[Voice]:
        out: list[Voice] = []
        for d in os.listdir(self.root):
            meta = os.path.join(self.root, d, "meta.json")
            if os.path.isfile(meta):
                try:
                    with open(meta, encoding="utf-8") as f:
                        out.append(Voice(**json.load(f)))
                except (OSError, ValueError, TypeError):
                    continue
        return sorted(out, key=lambda v: v.created, reverse=True)

    def get(self, voice_id: str | None) -> Voice | None:
        if not voice_id:
            return None
        return next((v for v in self.list() if v.id == voice_id), None)

    def ref_path(self, voice_id: str) -> str:
        p = os.path.join(self._dir(voice_id), "ref.wav")
        if not os.path.isfile(p):
            raise FileNotFoundError("Không tìm thấy giọng đã lưu.")
        return p

    def save(self, name: str, audio_path: str, lang: str, consent: bool) -> Voice:
        name = (name or "").strip()
        if not name:
            raise ValueError("Hãy đặt tên cho giọng.")
        if not audio_path:
            raise ValueError("Chưa có giọng mẫu để lưu.")
        if not consent:
            raise ValueError("Hãy xác nhận bạn có quyền dùng giọng này.")
        audio = decode_to_array(audio_path, SR)
        dur = len(audio) / SR
        if dur < MIN_SEC:
            raise ValueError(f"Giọng mẫu quá ngắn ({dur:.1f} giây). Cần tối thiểu {MIN_SEC:.0f} giây.")
        audio = audio[: int(MAX_SEC * SR)]
        peak = float(abs(audio).max())
        if peak > 0:
            audio = audio * (0.9 / peak)
        voice = Voice(
            id=f"{_slug(name)}-{uuid.uuid4().hex[:6]}",
            name=name, lang=lang, created=time.time(),
            duration=round(len(audio) / SR, 1), consent=True,
        )
        d = self._dir(voice.id)
        os.makedirs(d)
        write_wav(os.path.join(d, "ref.wav"), audio, SR)
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(voice), f, ensure_ascii=False, indent=2)
        return voice

    def rename(self, voice_id: str, new_name: str) -> Voice:
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Tên mới không được để trống.")
        v = self.get(voice_id)
        if not v:
            raise FileNotFoundError("Không tìm thấy giọng đã lưu.")
        v.name = new_name
        with open(os.path.join(self._dir(voice_id), "meta.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(v), f, ensure_ascii=False, indent=2)
        return v

    def delete(self, voice_id: str) -> None:
        d = self._dir(voice_id)
        if os.path.isdir(d):
            shutil.rmtree(d)
