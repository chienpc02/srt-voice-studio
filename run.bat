@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Dang tao moi truong Python, lan dau se mat vai phut...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python --version
python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,12) else 1)"
if errorlevel 1 (
  echo.
  echo CANH BAO: can Python 3.10, 3.11 hoac 3.12. Ban dang dung phien ban khac, PyTorch co the khong cai duoc.
  echo Hay cai Python 3.11 tu python.org, xoa thu muc .venv roi chay lai file nay.
  echo.
)
python -c "import torch, torchaudio, TTS, gradio" 2>nul
if errorlevel 1 (
  echo Dang cai thu vien, co the mat 10 phut va vai GB dung luong...
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo Cai thu vien bi loi. Xem thong bao phia tren.
    pause
    exit /b 1
  )
)
python app.py
pause
