"""SRT Voice Studio: chuyển file phụ đề thành giọng nói, có thể nhân bản giọng từ mẫu của bạn."""
from __future__ import annotations

import os
import tempfile
import threading
import time

import gradio as gr

from srtvoice.audioutil import save_audio
from srtvoice.engines import EDGE_VOICES, XTTS_LANGS, EdgeEngine, XTTSEngine
from srtvoice.parser import read_subtitle_file
from srtvoice.timeline import build_track

import sys

_BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)
SR = 24000
_stop = threading.Event()

ENGINE_CLONE = "Nhân bản giọng của tôi (XTTS, chạy trên máy)"
ENGINE_EDGE = "Giọng có sẵn (Edge, cần internet)"


def preview_subtitles(sub_file):
    if not sub_file:
        return "Chưa chọn file phụ đề."
    cues = read_subtitle_file(sub_file)
    if not cues:
        return "Không đọc được câu thoại nào. Kiểm tra lại định dạng SRT/VTT."
    chars = sum(len(c.text) for c in cues)
    last = cues[-1].end / 1000
    head = "\n".join(f"{c.index:>3}. {c.text}" for c in cues[:8])
    more = f"\n... và {len(cues) - 8} câu nữa" if len(cues) > 8 else ""
    return f"{len(cues)} câu thoại, {chars} ký tự, dài khoảng {last/60:.1f} phút.\n\n{head}{more}"


def convert(sub_file, engine_name, ref_audio, lang_name, edge_voice, edge_rate,
            consent, mode, fit, max_speedup, gap_ms, fmt, progress=gr.Progress()):
    _stop.clear()
    if not sub_file:
        raise gr.Error("Hãy chọn file phụ đề (.srt hoặc .vtt).")
    cues = read_subtitle_file(sub_file)
    if not cues:
        raise gr.Error("Không đọc được câu thoại nào trong file phụ đề.")

    if engine_name == ENGINE_CLONE:
        if not ref_audio:
            raise gr.Error("Hãy tải lên hoặc ghi âm một đoạn giọng mẫu (khoảng 6 đến 30 giây, ít tạp âm).")
        if not consent:
            raise gr.Error("Hãy xác nhận bạn có quyền dùng giọng mẫu và đồng ý giấy phép mô hình.")
        progress(0, desc="Đang nạp mô hình XTTS (lần đầu sẽ tải khoảng 2 GB)...")
        synth = XTTSEngine(ref_audio, XTTS_LANGS[lang_name])
    else:
        synth = EdgeEngine(EDGE_VOICES[edge_voice], int(edge_rate))

    t0 = time.time()

    def on_progress(i, n):
        progress(i / n, desc=f"Đang đọc câu {i}/{n}")

    track, report = build_track(
        cues, synth, sr=SR, mode="timed" if mode.startswith("Theo") else "sequential",
        fit=fit, max_speedup=float(max_speedup), gap_ms=int(gap_ms),
        on_progress=on_progress, should_stop=_stop.is_set,
    )
    if len(track) <= 1:
        raise gr.Error("Không tạo được âm thanh.")

    base = os.path.splitext(os.path.basename(sub_file))[0]
    out = os.path.join(OUT_DIR, f"{base}_{int(time.time())}.{fmt}")
    save_audio(track, SR, out)

    late = [r for r in report if r["late"] > 0.3]
    fast = [r for r in report if r["speedup"] > 1.0]
    log = (f"Xong sau {time.time() - t0:.0f} giây. {len(report)}/{len(cues)} câu, "
           f"dài {len(track) / SR:.1f} giây.\n"
           f"{len(fast)} câu được tăng tốc để kịp thời gian, {len(late)} câu bị trễ hơn 0,3 giây "
           f"vì câu trước chưa đọc xong.\nFile: {out}")
    return out, out, log


def stop():
    _stop.set()
    return "Đã yêu cầu dừng, app sẽ lưu phần đã đọc."


with gr.Blocks(title="SRT Voice Studio") as demo:
    gr.Markdown("# SRT Voice Studio\nChuyển file phụ đề thành giọng nói, có thể nhân bản giọng từ đoạn mẫu của bạn.")
    with gr.Row():
        with gr.Column():
            sub = gr.File(label="1. File phụ đề (.srt, .vtt)", file_types=[".srt", ".vtt", ".txt"], type="filepath")
            sub_info = gr.Textbox(label="Xem nhanh", lines=7, interactive=False)
            engine = gr.Radio([ENGINE_CLONE, ENGINE_EDGE], value=ENGINE_CLONE, label="2. Giọng đọc")
            with gr.Group(visible=True) as clone_box:
                ref = gr.Audio(label="Giọng mẫu: tải lên hoặc ghi âm 6 đến 30 giây",
                               sources=["upload", "microphone"], type="filepath")
                lang = gr.Dropdown(list(XTTS_LANGS), value="Tiếng Việt", label="Ngôn ngữ của phụ đề")
                consent = gr.Checkbox(label="Tôi xác nhận giọng mẫu là giọng của tôi hoặc tôi được chủ giọng đồng ý, "
                                            "và tôi đồng ý giấy phép mô hình XTTS-v2 (CPML, chỉ dùng phi thương mại).")
            with gr.Group(visible=False) as edge_box:
                edge_voice = gr.Dropdown(list(EDGE_VOICES), value="Hoài My (nữ, Việt)", label="Giọng")
                edge_rate = gr.Slider(-50, 50, value=0, step=5, label="Tốc độ (%)")
        with gr.Column():
            mode = gr.Radio(["Theo mốc thời gian", "Nối tiếp"], value="Theo mốc thời gian", label="3. Cách ghép")
            fit = gr.Checkbox(value=True, label="Tăng tốc câu dài hơn khoảng thời gian cho phép")
            max_speedup = gr.Slider(1.0, 2.0, value=1.5, step=0.05, label="Tăng tốc tối đa (lần)")
            gap = gr.Slider(0, 1500, value=250, step=50, label="Khoảng nghỉ giữa câu khi nối tiếp (ms)")
            fmt = gr.Radio(["wav", "mp3"], value="mp3", label="Định dạng xuất")
            with gr.Row():
                go = gr.Button("Tạo giọng nói", variant="primary")
                halt = gr.Button("Dừng")
            player = gr.Audio(label="Kết quả", type="filepath", interactive=False)
            dl = gr.File(label="Tải file về")
            log = gr.Textbox(label="Nhật ký", lines=5, interactive=False)

    sub.change(preview_subtitles, sub, sub_info)
    engine.change(lambda e: (gr.update(visible=e == ENGINE_CLONE), gr.update(visible=e != ENGINE_CLONE)),
                  engine, [clone_box, edge_box])
    go.click(convert, [sub, engine, ref, lang, edge_voice, edge_rate, consent, mode, fit, max_speedup, gap, fmt],
             [player, dl, log])
    halt.click(stop, None, log)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    demo.queue().launch(inbrowser=True)
