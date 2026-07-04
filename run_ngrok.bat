@echo off
echo ==================================================
echo [CLINIC AI CHAT] KHOI DONG SERVER + NGROK
echo ==================================================
echo.

echo Buoc 1: Kiem tra / Khoi dong Ollama Server...
start "Ollama Server" /min cmd /c "ollama serve"
timeout /t 2 /nobreak >nul
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [LOI] Khong tim thay moi truong ao 'venv'. Vui long chay: python -m venv venv
    pause
    exit /b
)

echo Buoc 2: Bat FastAPI Server o Terminal moi...
start "AI Server (FastAPI)" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Đang chờ Server khởi động (3 giây)...
timeout /t 3 /nobreak >nul

echo Buoc 3: Khoi chay Ngrok Tunnel...
echo Domain: judiciary-suitably-perpetual.ngrok-free.dev
echo.
ngrok http 8000 --domain=judiciary-suitably-perpetual.ngrok-free.dev

pause
