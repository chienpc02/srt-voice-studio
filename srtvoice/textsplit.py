"""Tách văn bản dài thành các đoạn ngắn để mô hình đọc ổn định."""
from __future__ import annotations

import re

_SENT = re.compile(r"(?<=[.!?…。！？])\s+")


def _hard_split(s: str, n: int) -> list[str]:
    out: list[str] = []
    while len(s) > n:
        cut = s.rfind(", ", 0, n)
        if cut < n // 3:
            cut = s.rfind(" ", 0, n)
        if cut <= 0:
            cut = n - 1
        out.append(s[: cut + 1].strip())
        s = s[cut + 1:].strip()
    if s:
        out.append(s)
    return out


def split_text(text: str, max_chars: int = 220) -> list[str]:
    """Mỗi đoạn xuống dòng được tách riêng, câu ngắn gộp lại tới `max_chars` ký tự."""
    chunks: list[str] = []
    for para in re.split(r"\n+", text.replace("\r", "")):
        para = re.sub(r"\s+", " ", para).strip()
        if not para:
            continue
        cur = ""
        for sent in _SENT.split(para):
            for piece in _hard_split(sent, max_chars):
                if cur and len(cur) + 1 + len(piece) > max_chars:
                    chunks.append(cur)
                    cur = piece
                else:
                    cur = f"{cur} {piece}".strip()
        if cur:
            chunks.append(cur)
    return chunks
