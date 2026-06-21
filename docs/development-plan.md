# 📅 Kế hoạch Phát triển (Development Roadmap)

Việc phát triển Microservice AI Chat sẽ được chia làm 6 giai đoạn (Phù hợp cho Luận văn/Đồ án).

## Phase 1: Setup Infrastructure (Tuần 1)
- Cài đặt Ollama local, pull model `llama3.2:3b`.
- Khởi tạo project FastAPI. Cấu hình CORS, Database (SQLAlchemy/Alembic).

## Phase 2: Core Chat & WebSockets (Tuần 2)
- Xây dựng API `/ws/chat` cho phép streaming text từ Ollama về Client.
- Lưu trữ lịch sử tin nhắn vào Database.
- Tích hợp UI Chat bên Patient Web / Mobile App để test streaming.

## Phase 3: Intent Classification & RAG (Tuần 3)
- Cài đặt ChromaDB hoặc FAISS lưu trữ vector thông tin phòng khám (Giờ mở cửa, Bảng giá, Quy định).
- Xây dựng Router phân loại câu hỏi (Hỏi thông tin tĩnh -> vào RAG).

## Phase 4: Function Calling & Tích hợp Backend (Tuần 4)
- Viết các Tool Functions trong Python (gọi `httpx` sang Spring Boot).
- Áp dụng logic trích xuất Entity (NER) từ câu chat của bệnh nhân để tự động điền form đặt lịch.

## Phase 5: Testing & Tuning (Tuần 5)
- Thử nghiệm các ca sử dụng dị biệt (Edge cases).
- Tinh chỉnh (Tune) System Prompts để giọng điệu thân thiện, tiếng Việt chuẩn xác hơn.
- Xử lý lỗi khi Spring Boot Backend die.

## Phase 6: Deployment (Tuần 6)
- Dockerize FastAPI app.
- Viết script `docker-compose.yml` chạy song song Backend, Frontend, FastAPI, Database và Ollama.
