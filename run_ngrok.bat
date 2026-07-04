@echo off
echo ==================================================
echo [CLINIC AI CHAT] KHOI DONG SERVER + NGROK
echo ==================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [LOI] Khong tim thay moi truong ao 'venv'. Vui long chay: python -m venv venv
    pause
    exit /b
)

echo Buoc 1: Bật FastAPI Server ở Terminal mới...
start "AI Server (FastAPI)" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

echo Đang chờ Server khởi động (3 giây)...
timeout /t 3 /nobreak >nul

echo Buoc 2: Khởi chạy Ngrok Tunnel...
echo Domain: judiciary-suitably-perpetual.ngrok-free.dev
echo.
ngrok http 8000 --domain=judiciary-suitably-perpetual.ngrok-free.dev

pause
