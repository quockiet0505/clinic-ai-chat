@echo off
echo ==================================================
echo [CLINIC AI CHAT] KHOI DONG SERVER LOCAL
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

echo Buoc 2: Bat moi truong ao (virtual environment)...
call venv\Scripts\activate.bat

echo Buoc 3: Khoi chay FastAPI Server tai cong 8000...
uvicorn app.main:app --host 0.0.0.0 --reload --port 8000

pause
