@echo off
cd /d "%~dp0"

call env\Scripts\activate.bat

echo Menjalankan File Compressor...
echo (Jendela ini boleh diminimize, jangan ditutup selama app dipakai)

python -m streamlit run app.py --server.port 8501

echo Exit code: %errorlevel%
pause
