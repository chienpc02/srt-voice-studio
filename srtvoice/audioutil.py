"""Các hàm âm thanh dùng chung: ffmpeg, đổi tần số lấy mẫu, co giãn tốc độ, ghi file."""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile


def read_wav(path: str) -> tuple[np.ndarray, int]:
    sr, data = wavfile.read(path)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128.0) / 128.0
    else:
        data = data.astype(np.float32)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, int(sr)


def write_wav(path: str, audio: np.ndarray, sr: int) -> None:
    wavfile.write(path, sr, np.asarray(audio, dtype=np.float32))


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Không tìm thấy ffmpeg. Hãy chạy: pip install imageio-ffmpeg") from e


def _run(args: list[str]) -> None:
    p = subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi: {p.stderr.strip()}")


def resample(audio: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return audio.astype(np.float32)
    from scipy.signal import resample_poly
    g = math.gcd(sr_in, sr_out)
    return resample_poly(audio, sr_out // g, sr_in // g).astype(np.float32)


def stretch(audio: np.ndarray, sr: int, factor: float) -> np.ndarray:
    """Tăng tốc `factor` lần (>1 là nhanh hơn) mà giữ nguyên cao độ."""
    factor = float(min(2.0, max(0.5, factor)))
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "in.wav"), os.path.join(d, "out.wav")
        write_wav(a, audio, sr)
        _run(["-i", a, "-filter:a", f"atempo={factor:.4f}", b])
        out, _ = read_wav(b)
    return out


def decode_to_array(path: str, sr: int) -> np.ndarray:
    """Giải mã mp3/wav/... thành mảng mono float32 ở tần số `sr`."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.wav")
        _run(["-i", path, "-ac", "1", "-ar", str(sr), out])
        audio, _ = read_wav(out)
    return audio


def save_audio(audio: np.ndarray, sr: int, path: str) -> str:
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 0.99:
        audio = audio * (0.99 / peak)
    if path.lower().endswith(".mp3"):
        with tempfile.TemporaryDirectory() as d:
            tmp = os.path.join(d, "t.wav")
            write_wav(tmp, audio, sr)
            _run(["-i", tmp, "-codec:a", "libmp3lame", "-q:a", "2", path])
    else:
        write_wav(path, audio, sr)
    return path
