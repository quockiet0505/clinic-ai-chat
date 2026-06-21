# 📦 Hướng dẫn Cài đặt & Chạy (Deployment)

## 1. Cài đặt Ollama (Model Server)
1. Tải và cài đặt [Ollama](https://ollama.com/).
2. Tải mô hình Llama 3.2 3B:
   ```bash
   ollama run llama3.2:3b
   ```
   *Lưu ý: Đảm bảo máy tính có RAM >= 8GB. Llama 3.2 3B chạy rất mượt trên CPU thông thường.*

## 2. Cài đặt FastAPI (Chat Server)
1. Tạo môi trường ảo Python:
   ```bash
   python -m venv venv
   source venv/bin/activate  # (Mac/Linux)
   venv\Scripts\activate     # (Windows)
   ```
2. Cài thư viện:
   ```bash
   pip install fastapi uvicorn langchain langchain-ollama sqlalchemy psycopg2-binary httpx
   ```
3. Khởi chạy Server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 3. Triển khai bằng Docker Compose (Production)
```yaml
version: '3.8'
services:
  ai-chat-api:
    build: ./clinic-ai-chat
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - SPRING_BOOT_URL=http://clinic-backend:8080/api/v1
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```
