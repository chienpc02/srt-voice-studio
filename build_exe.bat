@echo off
REM Tao SRT-Voice-Studio.exe (thu muc dist\SRT-Voice-Studio). Can Python 3.10-3.12 va internet.
cd /d "%~dp0"
python -m venv .buildenv || goto :err
call .buildenv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller || goto :err
pyinstaller --noconfirm --clean --onedir --name SRT-Voice-Studio ^
  --collect-all TTS --collect-all trainer --collect-all gradio --collect-all gradio_client ^
  --collect-all safehttpx --collect-all groovy --collect-all imageio_ffmpeg --collect-all edge_tts ^
  --collect-all gruut --collect-all jamo --collect-all inflect --collect-all spacy ^
  --collect-data coqpit --hidden-import=scipy.special._cdflib ^
  app.py || goto :err
echo.
echo Xong. Chay: dist\SRT-Voice-Studio\SRT-Voice-Studio.exe
echo Co the nen thu muc dist\SRT-Voice-Studio de gui cho may khac.
pause
exit /b 0
:err
echo Build loi. Xem thong bao phia tren.
pause
exit /b 1
