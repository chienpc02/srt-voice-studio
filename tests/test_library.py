import os
import tempfile

import numpy as np

from srtvoice.audioutil import write_wav
from srtvoice.library import VoiceLibrary
from srtvoice.textsplit import split_text


def _wav(path, sec, sr=16000):
    t = np.linspace(0, sec, int(sec * sr), endpoint=False)
    write_wav(path, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr)


def test_library_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        lib = VoiceLibrary(os.path.join(d, "voices"))
        src = os.path.join(d, "mau.wav")
        _wav(src, 5)
        v = lib.save("Giọng Đẹp của tôi", src, "vi", True)
        assert v.id.startswith("giong-dep-cua-toi-")
        assert os.path.isfile(lib.ref_path(v.id))
        assert [x.name for x in lib.list()] == ["Giọng Đẹp của tôi"]
        lib.rename(v.id, "Giọng B")
        assert lib.get(v.id).name == "Giọng B"
        lib.delete(v.id)
        assert lib.list() == []


def test_library_validation():
    with tempfile.TemporaryDirectory() as d:
        lib = VoiceLibrary(d)
        src = os.path.join(d, "s.wav")
        _wav(src, 1)
        for args, msg in [(("A", src, "vi", True), "quá ngắn"), (("", src, "vi", True), "tên"),
                          (("A", src, "vi", False), "quyền")]:
            try:
                lib.save(*args)
            except ValueError as e:
                assert msg in str(e), e
            else:
                raise AssertionError("phải báo lỗi")
        try:
            lib.ref_path("../etc")
        except ValueError:
            pass
        else:
            raise AssertionError("phải chặn đường dẫn lạ")


def test_library_trims_to_30s():
    with tempfile.TemporaryDirectory() as d:
        lib = VoiceLibrary(d)
        src = os.path.join(d, "long.wav")
        _wav(src, 45)
        assert lib.save("Dài", src, "vi", True).duration == 30.0


def test_split_text():
    text = "Câu một. Câu hai ngắn.\n\nĐoạn mới bắt đầu ở đây! " + ("từ " * 150).strip() + "."
    chunks = split_text(text, 100)
    assert all(len(c) <= 100 for c in chunks)
    assert chunks[0] == "Câu một. Câu hai ngắn."      # xuống dòng thì tách đoạn
    assert chunks[1].startswith("Đoạn mới")
    assert split_text("   \n  ") == []
