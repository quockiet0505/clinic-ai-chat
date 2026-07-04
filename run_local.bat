@echo off
echo ==================================================
echo [CLINIC AI CHAT] KHOI DONG SERVER LOCAL
echo ==================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [LOI] Khong tim thay moi truong ao 'venv'. Vui long chay: python -m venv venv
    pause
    exit /b
)

echo Bật môi trường ảo (virtual environment)...
call venv\Scripts\activate.bat

echo Khởi chạy FastAPI Server tại cổng 8000...
uvicorn app.main:app --reload --port 8000

pause
