# Hướng dẫn Cài đặt & Triển khai (Deployment)

## 1. Yêu cầu hệ thống
- **CPU:** Tối thiểu 4 cores (khuyến nghị 8 cores)
- **RAM:** Tối thiểu 8GB (khuyến nghị 16GB cho Llama 3.2 3B)
- **GPU:** Tùy chọn, giúp phản hồi nhanh hơn
- **Ổ cứng:** SSD trống ít nhất 20GB

## 2. Cài đặt Ollama & Model
```bash
# Tải Ollama: https://ollama.com/
ollama pull llama3.2:3b
```
Ollama chạy mặc định tại `http://localhost:11434`.

## 3. Chạy toàn bộ hệ thống (Development)

Mở **4 terminal** theo thứ tự:

### Terminal 1 — Clinic Backend (Spring Boot)
```bash
cd clinic-backend/backend
mvn spring-boot:run
```
→ Chạy tại `http://localhost:8080`

### Terminal 2 — AI Chat Microservice
```bash
cd clinic-ai-chat
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
→ Chạy tại `http://localhost:8000`

Kiểm tra:
```bash
curl http://localhost:8000/health
```

### Terminal 3 — Patient Web (React)
```bash
cd clinic-frontend/patient-web
copy .env.example .env
npm install
npm run dev
```
→ Mở web, bấm icon chat góc phải để test AI.

Cấu hình `.env`:
```env
VITE_AI_CHAT_URL=http://localhost:8000
```

### Terminal 4 — Mobile App (Flutter)
```bash
cd clinic-frontend/mobile-app
copy .env.example .env
flutter pub get
flutter run
```
→ Vào tab **Chat** để test AI.

Cấu hình `.env` (Android Emulator):
```env
API_BASE_URL=http://10.0.2.2:8080/api/v1
AI_CHAT_URL=http://10.0.2.2:8000
```

> **Lưu ý:** `10.0.2.2` là localhost của máy host khi chạy Android Emulator.

## 4. Sơ đồ kết nối

```
Patient Web (:5173)  ──POST /api/v1/chat/send──►  AI Chat (:8000) ──► Ollama
Mobile App           ──POST /api/v1/chat/send──►       │
                                                       └──► Backend (:8080)
```

## 5. Troubleshooting

| Lỗi | Cách xử lý |
|-----|------------|
| Web/Mobile báo không kết nối AI | Kiểm tra `curl http://localhost:8000/health` |
| Mobile không gọi được AI | Dùng `10.0.2.2:8000` (emulator), không dùng `localhost` |
| AI trả lời chậm | Bình thường với LLM local; đợi 10–60 giây |
| Tool không lấy được bác sĩ/dịch vụ | Kiểm tra backend `:8080` đang chạy |
| Ollama lỗi | Chạy `ollama list` xem model `llama3.2:3b` đã pull chưa |

## 6. Docker (Production - tùy chọn)
Chưa bắt buộc cho môi trường dev. Ollama nên chạy trực tiếp trên host để tận dụng GPU.
