"""Đọc file phụ đề SRT / VTT thành danh sách câu thoại."""
from __future__ import annotations

import re
from dataclasses import dataclass

_TIME = re.compile(r"^(?:(\d+):)?(\d+):(\d+)(?:[.,](\d+))?$")


@dataclass
class Cue:
    index: int
    start: int  # mili giây
    end: int
    text: str


def _to_ms(s: str) -> int | None:
    m = _TIME.match(s.strip())
    if not m:
        return None
    h, mi, sec, frac = int(m.group(1) or 0), int(m.group(2)), int(m.group(3)), m.group(4)
    ms = int((frac + "000")[:3]) if frac else 0
    return ((h * 60 + mi) * 60 + sec) * 1000 + ms


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)          # thẻ HTML như <i>
    text = re.sub(r"\{\\[^}]*\}", "", text)      # thẻ ASS như {\an8}
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">"))
    text = re.sub(r"(?m)^\s*[-–]\s*", "", text)  # gạch đầu dòng hội thoại
    return re.sub(r"\s+", " ", text).strip()


def parse_subtitles(raw: str) -> list[Cue]:
    raw = raw.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    cues: list[Cue] = []
    for block in re.split(r"\n{2,}", raw):
        lines = [l for l in block.split("\n") if l.strip()]
        ti = next((i for i, l in enumerate(lines) if "-->" in l), -1)
        if ti < 0:
            continue
        left, right = lines[ti].split("-->", 1)
        start, end = _to_ms(left), _to_ms(right.strip().split()[0]) if right.strip() else None
        if start is None or end is None:
            continue
        text = _clean("\n".join(lines[ti + 1:]))
        if text:
            cues.append(Cue(0, start, end, text))
    cues.sort(key=lambda c: c.start)
    for i, c in enumerate(cues, 1):
        c.index = i
    return cues


def read_subtitle_file(path: str) -> list[Cue]:
    for enc in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return parse_subtitles(f.read())
        except (UnicodeError, OSError):
            continue
    return []
