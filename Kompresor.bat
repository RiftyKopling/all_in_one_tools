@echo off
cd /d "%~dp0"
echo Menjalankan File Compressor...
echo (Jendela ini boleh diminimize, jangan ditutup selama app dipakai)
streamlit run app.py
pause
