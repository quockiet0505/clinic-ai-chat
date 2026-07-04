@echo off
echo =========================================
echo    Khởi động Clinic AI Chat Service
echo =========================================

echo.
echo [1] Đang khởi động Ollama (llama3.2) ở cửa sổ mới...
start "Ollama - llama3.2" cmd /c "ollama run llama3.2"

echo.
echo [2] Đang kích hoạt môi trường ảo (venv)...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [CẢNH BÁO] Không tìm thấy venv\Scripts\activate.bat
    echo Vui lòng đảm bảo bạn đang ở đúng thư mục dự án và đã cài đặt venv.
    pause
    exit /b 1
)

echo.
echo [3] Đang khởi chạy Uvicorn Server...
uvicorn app.main:app --reload --port 8000

pause
