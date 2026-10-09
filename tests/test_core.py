import numpy as np

from srtvoice.parser import parse_subtitles
from srtvoice.timeline import build_track

SRT = """﻿1
00:00:01,000 --> 00:00:03,000
<i>Xin chào</i> các bạn.

2
00:00:04,000 --> 00:00:05,000
- Câu này rất dài so với khoảng thời gian cho phép.
- Dòng hai.

WEBVTT-NOTE bỏ qua

00:00:10.500 --> 00:00:12.000 align:start
{\\an8}Câu VTT.
"""

SR = 24000


def fake_synth(text):
    # 0,05 giây cho mỗi ký tự
    n = int(0.05 * len(text) * SR)
    return (0.3 * np.sin(np.linspace(0, 440 * 2 * np.pi, n))).astype(np.float32), SR


def test_parse():
    cues = parse_subtitles(SRT)
    assert [c.start for c in cues] == [1000, 4000, 10500]
    assert cues[0].text == "Xin chào các bạn."
    assert cues[1].text.startswith("Câu này") and "Dòng hai" in cues[1].text
    assert cues[2].text == "Câu VTT."


def test_timed_positions_and_speedup():
    cues = parse_subtitles(SRT)
    track, rep = build_track(cues, fake_synth, SR, mode="timed", fit=True, max_speedup=1.5)
    assert abs(rep[0]["start"] - 1.0) < 1e-6
    assert rep[1]["speedup"] == 1.5          # câu 2 dài hơn 1 giây nên bị chặn ở 1.5
    assert abs(rep[2]["start"] - 10.5) < 1e-6
    assert abs(len(track) / SR - (10.5 + rep[2]["dur"])) < 0.01


def test_sequential_no_overlap():
    cues = parse_subtitles(SRT)
    _, rep = build_track(cues, fake_synth, SR, mode="sequential", gap_ms=200)
    for a, b in zip(rep, rep[1:]):
        assert b["start"] >= a["start"] + a["dur"] + 0.19
