#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
python --version
python - <<'PY' || echo "CẢNH BÁO: cần Python 3.10 đến 3.12, PyTorch có thể không cài được với phiên bản khác."
import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)
PY
if ! python -c "import torch, torchaudio, TTS, gradio" 2>/dev/null; then
  echo "Đang cài thư viện, có thể mất 10 phút và vài GB..."
  python -m pip install --upgrade pip
  pip install -r requirements.txt || { echo "Cài thư viện bị lỗi."; exit 1; }
fi
python app.py
