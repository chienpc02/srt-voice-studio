"""Ghép từng câu đã tổng hợp thành một bản âm thanh duy nhất."""
from __future__ import annotations

from typing import Callable

import numpy as np

from .audioutil import resample, stretch
from .parser import Cue

Synth = Callable[[str], tuple[np.ndarray, int]]


def build_track(
    cues: list[Cue],
    synth: Synth,
    sr: int = 24000,
    mode: str = "timed",          # "timed": đúng mốc thời gian | "sequential": nối tiếp
    fit: bool = True,             # tăng tốc câu dài hơn khoảng thời gian cho phép
    max_speedup: float = 1.6,
    gap_ms: int = 250,            # khoảng nghỉ giữa các câu (chế độ nối tiếp)
    on_progress: Callable[[int, int], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[np.ndarray, list[dict]]:
    placed: list[tuple[float, np.ndarray]] = []
    report: list[dict] = []
    cursor = 0.0
    for n, c in enumerate(cues):
        if should_stop and should_stop():
            break
        audio, asr = synth(c.text)
        audio = resample(np.asarray(audio, dtype=np.float32), asr, sr)
        dur = len(audio) / sr
        factor = 1.0
        if mode == "timed":
            slot = (c.end - c.start) / 1000
            if fit and slot > 0 and dur > slot * 1.02:
                factor = min(dur / slot, max_speedup)
                if factor > 1.02:
                    audio = stretch(audio, sr, factor)
                    dur = len(audio) / sr
                else:
                    factor = 1.0
            wanted = c.start / 1000
            pos = max(wanted, cursor)
            cursor = pos + dur + 0.05
        else:
            wanted = cursor
            pos = cursor
            cursor = pos + dur + gap_ms / 1000
        placed.append((pos, audio))
        report.append({"index": c.index, "start": round(pos, 3), "dur": round(dur, 3),
                       "speedup": round(factor, 2), "late": round(pos - wanted, 3)})
        if on_progress:
            on_progress(n + 1, len(cues))

    total = max((p + len(a) / sr for p, a in placed), default=0.0)
    out = np.zeros(int(total * sr) + 1, dtype=np.float32)
    for pos, a in placed:
        s = int(round(pos * sr))
        out[s:s + len(a)] += a
    return out, report
