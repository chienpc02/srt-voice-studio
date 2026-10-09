"""SRT Voice Studio: đọc văn bản, đọc phụ đề và quản lý thư viện giọng nói đã nhân bản."""
from __future__ import annotations

import os
import sys
import threading
import time

import gradio as gr

from srtvoice.audioutil import save_audio
from srtvoice.engines import EDGE_VOICES, XTTS_LANGS, EdgeEngine, XTTSEngine
from srtvoice.library import VoiceLibrary
from srtvoice.parser import Cue, read_subtitle_file
from srtvoice.textsplit import split_text
from srtvoice.timeline import build_track

_BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)
LIB = VoiceLibrary(os.path.join(_BASE, "voices"))
SR = 24000
_stop = threading.Event()

ENGINE_CLONE = "Giọng nhân bản (XTTS, chạy trên máy)"
ENGINE_EDGE = "Giọng có sẵn (Edge, cần internet)"
CONSENT_TEXT = ("Tôi xác nhận giọng mẫu là giọng của tôi hoặc tôi được chủ giọng đồng ý, "
                "và tôi đồng ý giấy phép mô hình XTTS-v2 (CPML, chỉ dùng phi thương mại).")


# ---------------------------------------------------------------- thư viện giọng

def lib_choices():
    return [(f"{v.name} ({v.lang}, {v.duration:.0f} giây)", v.id) for v in LIB.list()]


def lib_rows():
    return [[v.name, v.lang, f"{v.duration:.0f} giây", v.created_text] for v in LIB.list()]


def sync(select: str | None = None):
    """Cập nhật danh sách giọng ở mọi nơi: ô chọn ở hai tab đọc, ô chọn và bảng ở tab thư viện."""
    ch = lib_choices()
    val = select if select in [c[1] for c in ch] else None
    pick = gr.update(choices=ch, value=val)
    return pick, pick, pick, lib_rows()


def save_voice(audio, name, lang_name, consent):
    try:
        v = LIB.save(name, audio, XTTS_LANGS[lang_name], consent)
    except (ValueError, OSError, RuntimeError) as e:
        gr.Warning(str(e))
        return (*sync(), "")
    gr.Info(f"Đã lưu giọng \"{v.name}\" vào thư viện.")
    return (*sync(v.id), "")


def show_voice(voice_id):
    v = LIB.get(voice_id)
    if not v:
        return None, "", ""
    info = f"{v.name}\nNgôn ngữ: {v.lang}   Thời lượng mẫu: {v.duration:.0f} giây   Lưu lúc: {v.created_text}"
    return LIB.ref_path(v.id), info, v.name


def rename_voice(voice_id, new_name):
    try:
        LIB.rename(voice_id, new_name)
    except (ValueError, FileNotFoundError) as e:
        gr.Warning(str(e))
        return sync(voice_id)
    gr.Info("Đã đổi tên.")
    return sync(voice_id)


def delete_voice(voice_id, sure):
    if not voice_id:
        gr.Warning("Hãy chọn một giọng để xóa.")
        return (*sync(), False)
    if not sure:
        gr.Warning("Tick ô xác nhận xóa trước.")
        return (*sync(voice_id), False)
    LIB.delete(voice_id)
    gr.Info("Đã xóa giọng.")
    return (*sync(), False)


# ---------------------------------------------------------------- chọn engine

def make_synth(engine_name, ref_audio, voice_id, lang_name, consent, edge_voice, edge_rate, progress):
    if engine_name == ENGINE_EDGE:
        return EdgeEngine(EDGE_VOICES[edge_voice], int(edge_rate))
    if ref_audio:                       # mẫu mới tải lên: cần xác nhận quyền dùng giọng
        if not consent:
            raise gr.Error("Hãy tick xác nhận quyền dùng giọng mẫu.")
        ref = ref_audio
    elif voice_id:                      # giọng đã lưu: đã xác nhận lúc lưu
        try:
            ref = LIB.ref_path(voice_id)
        except FileNotFoundError as e:
            raise gr.Error(str(e))
    else:
        raise gr.Error("Hãy chọn một giọng đã lưu, hoặc tải lên/ghi âm giọng mẫu 6 đến 30 giây.")
    progress(0, desc="Đang nạp mô hình XTTS (lần đầu sẽ tải khoảng 2 GB)...")
    return XTTSEngine(ref, XTTS_LANGS[lang_name])


def finish(track, name, fmt):
    if len(track) <= 1:
        raise gr.Error("Không tạo được âm thanh.")
    out = os.path.join(OUT_DIR, f"{name}_{int(time.time())}.{fmt}")
    save_audio(track, SR, out)
    return out


# ---------------------------------------------------------------- đọc văn bản

def load_text_file(path):
    if not path:
        return gr.update()
    for enc in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeError, OSError):
            continue
    return gr.update()


def convert_text(text, engine_name, ref_audio, voice_id, lang_name, consent, edge_voice, edge_rate,
                 gap_ms, fmt, progress=gr.Progress()):
    _stop.clear()
    chunks = split_text(text or "")
    if not chunks:
        raise gr.Error("Hãy nhập hoặc dán văn bản cần đọc.")
    synth = make_synth(engine_name, ref_audio, voice_id, lang_name, consent, edge_voice, edge_rate, progress)
    cues = [Cue(i, 0, 0, t) for i, t in enumerate(chunks, 1)]
    t0 = time.time()
    track, _ = build_track(
        cues, synth, sr=SR, mode="sequential", gap_ms=int(gap_ms),
        on_progress=lambda i, n: progress(i / n, desc=f"Đang đọc đoạn {i}/{n}"),
        should_stop=_stop.is_set,
    )
    out = finish(track, "van-ban", fmt)
    return out, out, f"Xong sau {time.time() - t0:.0f} giây. {len(chunks)} đoạn, dài {len(track) / SR:.1f} giây.\nFile: {out}"


# ---------------------------------------------------------------- đọc phụ đề

def preview_subtitles(sub_file):
    if not sub_file:
        return "Chưa chọn file phụ đề."
    cues = read_subtitle_file(sub_file)
    if not cues:
        return "Không đọc được câu thoại nào. Kiểm tra lại định dạng SRT/VTT."
    chars = sum(len(c.text) for c in cues)
    head = "\n".join(f"{c.index:>3}. {c.text}" for c in cues[:8])
    more = f"\n... và {len(cues) - 8} câu nữa" if len(cues) > 8 else ""
    return f"{len(cues)} câu thoại, {chars} ký tự, dài khoảng {cues[-1].end / 60000:.1f} phút.\n\n{head}{more}"


def convert_srt(sub_file, engine_name, ref_audio, voice_id, lang_name, consent, edge_voice, edge_rate,
                mode, fit, max_speedup, gap_ms, fmt, progress=gr.Progress()):
    _stop.clear()
    if not sub_file:
        raise gr.Error("Hãy chọn file phụ đề (.srt hoặc .vtt).")
    cues = read_subtitle_file(sub_file)
    if not cues:
        raise gr.Error("Không đọc được câu thoại nào trong file phụ đề.")
    synth = make_synth(engine_name, ref_audio, voice_id, lang_name, consent, edge_voice, edge_rate, progress)
    t0 = time.time()
    track, report = build_track(
        cues, synth, sr=SR, mode="timed" if mode.startswith("Theo") else "sequential",
        fit=fit, max_speedup=float(max_speedup), gap_ms=int(gap_ms),
        on_progress=lambda i, n: progress(i / n, desc=f"Đang đọc câu {i}/{n}"),
        should_stop=_stop.is_set,
    )
    out = finish(track, os.path.splitext(os.path.basename(sub_file))[0], fmt)
    late = [r for r in report if r["late"] > 0.3]
    fast = [r for r in report if r["speedup"] > 1.0]
    log = (f"Xong sau {time.time() - t0:.0f} giây. {len(report)}/{len(cues)} câu, dài {len(track) / SR:.1f} giây.\n"
           f"{len(fast)} câu được tăng tốc để kịp thời gian, {len(late)} câu bị trễ hơn 0,3 giây "
           f"vì câu trước chưa đọc xong.\nFile: {out}")
    return out, out, log


def stop():
    _stop.set()
    return "Đã yêu cầu dừng, app sẽ lưu phần đã đọc."


def test_voice(voice_id, lang_name, sample_text, progress=gr.Progress()):
    if not voice_id:
        raise gr.Error("Hãy chọn một giọng trong thư viện.")
    text = (sample_text or "").strip() or "Xin chào, đây là giọng nói đã được lưu."
    synth = XTTSEngine(LIB.ref_path(voice_id), XTTS_LANGS[lang_name])
    audio, sr = synth(text[:300])
    out = os.path.join(OUT_DIR, f"nghe-thu_{int(time.time())}.wav")
    save_audio(audio, sr, out)
    return out


# ---------------------------------------------------------------- giao diện

def voice_controls(tag):
    """Khối chọn giọng dùng chung cho hai tab đọc."""
    engine = gr.Radio([ENGINE_CLONE, ENGINE_EDGE], value=ENGINE_CLONE, label="Giọng đọc")
    with gr.Group(visible=True) as clone_box:
        pick = gr.Dropdown(choices=[], value=None, label="Giọng đã lưu trong thư viện")
        ref = gr.Audio(label="Hoặc giọng mẫu mới: tải lên / ghi âm 6 đến 30 giây (ưu tiên hơn giọng đã lưu)",
                       sources=["upload", "microphone"], type="filepath")
        lang = gr.Dropdown(list(XTTS_LANGS), value="Tiếng Việt", label="Ngôn ngữ của nội dung")
        consent = gr.Checkbox(label=CONSENT_TEXT)
        with gr.Accordion("Lưu giọng mẫu này vào thư viện", open=False):
            name = gr.Textbox(label="Tên giọng", placeholder="Ví dụ: Giọng của tôi")
            save = gr.Button("Lưu giọng")
    with gr.Group(visible=False) as edge_box:
        edge_voice = gr.Dropdown(list(EDGE_VOICES), value="Hoài My (nữ, Việt)", label="Giọng")
        edge_rate = gr.Slider(-50, 50, value=0, step=5, label="Tốc độ (%)")
    engine.change(lambda e: (gr.update(visible=e == ENGINE_CLONE), gr.update(visible=e != ENGINE_CLONE)),
                  engine, [clone_box, edge_box])
    return engine, pick, ref, lang, consent, name, save, edge_voice, edge_rate


with gr.Blocks(title="SRT Voice Studio") as demo:
    gr.Markdown("# SRT Voice Studio\nĐọc văn bản và phụ đề thành giọng nói. Lưu giọng đã nhân bản để dùng lại.")

    with gr.Tabs():
        # ---------------- Tab: đọc văn bản
        with gr.Tab("Đọc văn bản"):
            with gr.Row():
                with gr.Column():
                    t_text = gr.Textbox(label="Văn bản cần đọc", lines=12,
                                        placeholder="Dán hoặc gõ văn bản vào đây. Văn bản dài sẽ được tự chia thành các đoạn.")
                    t_file = gr.File(label="Hoặc mở file .txt", file_types=[".txt"], type="filepath")
                    (t_engine, t_pick, t_ref, t_lang, t_consent, t_name, t_save,
                     t_edge_voice, t_edge_rate) = voice_controls("t")
                with gr.Column():
                    t_gap = gr.Slider(0, 1500, value=350, step=50, label="Khoảng nghỉ giữa các đoạn (ms)")
                    t_fmt = gr.Radio(["wav", "mp3"], value="mp3", label="Định dạng xuất")
                    with gr.Row():
                        t_go = gr.Button("Tạo giọng nói", variant="primary")
                        t_halt = gr.Button("Dừng")
                    t_player = gr.Audio(label="Kết quả", type="filepath", interactive=False)
                    t_dl = gr.File(label="Tải file về")
                    t_log = gr.Textbox(label="Nhật ký", lines=5, interactive=False)

        # ---------------- Tab: đọc phụ đề
        with gr.Tab("Đọc phụ đề"):
            with gr.Row():
                with gr.Column():
                    s_sub = gr.File(label="File phụ đề (.srt, .vtt)", file_types=[".srt", ".vtt", ".txt"], type="filepath")
                    s_info = gr.Textbox(label="Xem nhanh", lines=7, interactive=False)
                    (s_engine, s_pick, s_ref, s_lang, s_consent, s_name, s_save,
                     s_edge_voice, s_edge_rate) = voice_controls("s")
                with gr.Column():
                    s_mode = gr.Radio(["Theo mốc thời gian", "Nối tiếp"], value="Theo mốc thời gian", label="Cách ghép")
                    s_fit = gr.Checkbox(value=True, label="Tăng tốc câu dài hơn khoảng thời gian cho phép")
                    s_speed = gr.Slider(1.0, 2.0, value=1.5, step=0.05, label="Tăng tốc tối đa (lần)")
                    s_gap = gr.Slider(0, 1500, value=250, step=50, label="Khoảng nghỉ giữa câu khi nối tiếp (ms)")
                    s_fmt = gr.Radio(["wav", "mp3"], value="mp3", label="Định dạng xuất")
                    with gr.Row():
                        s_go = gr.Button("Tạo giọng nói", variant="primary")
                        s_halt = gr.Button("Dừng")
                    s_player = gr.Audio(label="Kết quả", type="filepath", interactive=False)
                    s_dl = gr.File(label="Tải file về")
                    s_log = gr.Textbox(label="Nhật ký", lines=5, interactive=False)

        # ---------------- Tab: thư viện giọng nói
        with gr.Tab("Thư viện giọng nói"):
            with gr.Row():
                with gr.Column():
                    l_table = gr.Dataframe(headers=["Tên", "Ngôn ngữ", "Thời lượng", "Lưu lúc"],
                                           value=[], interactive=False, label="Giọng đã lưu")
                    l_sel = gr.Dropdown(choices=[], value=None, label="Chọn giọng để xem, nghe thử, đổi tên hoặc xóa")
                    l_preview = gr.Audio(label="Mẫu gốc", type="filepath", interactive=False)
                    l_info = gr.Textbox(label="Thông tin", lines=3, interactive=False)
                    with gr.Row():
                        l_newname = gr.Textbox(label="Tên mới", scale=3)
                        l_rename = gr.Button("Đổi tên", scale=1)
                    with gr.Row():
                        l_sure = gr.Checkbox(label="Tôi muốn xóa giọng này", scale=3)
                        l_del = gr.Button("Xóa giọng", variant="stop", scale=1)
                    l_test_text = gr.Textbox(label="Câu nghe thử", value="Xin chào, đây là giọng nói đã được lưu.")
                    l_test_lang = gr.Dropdown(list(XTTS_LANGS), value="Tiếng Việt", label="Ngôn ngữ nghe thử")
                    l_test = gr.Button("Nghe thử giọng này")
                    l_test_out = gr.Audio(label="Kết quả nghe thử", type="filepath", interactive=False)
                with gr.Column():
                    gr.Markdown("### Thêm giọng mới\nTải lên hoặc ghi âm 6 đến 30 giây giọng nói rõ, không nhạc nền, "
                                "rồi lưu để dùng lại ở các tab đọc.")
                    n_audio = gr.Audio(label="Giọng mẫu", sources=["upload", "microphone"], type="filepath")
                    n_name = gr.Textbox(label="Tên giọng")
                    n_lang = gr.Dropdown(list(XTTS_LANGS), value="Tiếng Việt", label="Ngôn ngữ của giọng")
                    n_consent = gr.Checkbox(label=CONSENT_TEXT)
                    n_save = gr.Button("Lưu giọng", variant="primary")

    # ---- cập nhật danh sách giọng mọi nơi
    sync_out = [t_pick, s_pick, l_sel, l_table]
    demo.load(sync, None, sync_out)

    # ---- lưu giọng từ hai tab đọc
    t_save.click(save_voice, [t_ref, t_name, t_lang, t_consent], sync_out + [t_name])
    s_save.click(save_voice, [s_ref, s_name, s_lang, s_consent], sync_out + [s_name])
    # ---- tab thư viện
    n_save.click(save_voice, [n_audio, n_name, n_lang, n_consent], sync_out + [n_name])
    l_sel.change(show_voice, l_sel, [l_preview, l_info, l_newname])
    l_rename.click(rename_voice, [l_sel, l_newname], sync_out)
    l_del.click(delete_voice, [l_sel, l_sure], sync_out + [l_sure])
    l_test.click(test_voice, [l_sel, l_test_lang, l_test_text], l_test_out)

    # ---- đọc văn bản
    t_file.change(load_text_file, t_file, t_text)
    t_go.click(convert_text,
               [t_text, t_engine, t_ref, t_pick, t_lang, t_consent, t_edge_voice, t_edge_rate, t_gap, t_fmt],
               [t_player, t_dl, t_log])
    t_halt.click(stop, None, t_log)

    # ---- đọc phụ đề
    s_sub.change(preview_subtitles, s_sub, s_info)
    s_go.click(convert_srt,
               [s_sub, s_engine, s_ref, s_pick, s_lang, s_consent, s_edge_voice, s_edge_rate,
                s_mode, s_fit, s_speed, s_gap, s_fmt],
               [s_player, s_dl, s_log])
    s_halt.click(stop, None, s_log)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    demo.queue().launch(inbrowser=True)
