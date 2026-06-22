# Clinic AI Chat Microservice

## Tổng quan dự án

Clinic AI Chat là một microservice chạy hoàn toàn trên máy chủ local (on-premise) nhằm cung cấp trợ lý ảo AI thông minh cho bệnh nhân của hệ thống phòng khám. Sử dụng công nghệ Local LLM thông qua Ollama (Llama 3.2 3B / Mistral / Qwen), hệ thống đảm bảo tính bảo mật dữ liệu tuyệt đối cho bệnh nhân mà không phát sinh chi phí API (zero token cost).

## Mục tiêu

Cung cấp trải nghiệm tương tác tự nhiên, liên tục (24/7) cho bệnh nhân để giải quyết các nhu cầu thường gặp mà không cần sự can thiệp của nhân sự trực tổng đài.

## Các tính năng chính (đã triển khai)

1. **Tra cứu FAQ / quy trình:** Light RAG từ `knowledge/*.md` (giờ làm việc, đặt lịch, gợi ý triệu chứng).
2. **Tra cứu dữ liệu live:** Tool calling → clinic-backend (bác sĩ, dịch vụ, giá, giờ trống, đăng ký guest).
3. **Hội thoại có ngữ cảnh:** Session in-memory (tối đa ~10 lượt), REST API cho web + mobile.

## Roadmap (chưa triển khai)

- Đặt lịch tự động (cần JWT bệnh nhân)
- Tra cứu lịch hẹn của bệnh nhân đã đăng nhập
- Vector RAG, lưu chat vào DB, WebSocket streaming thật

## Công nghệ sử dụng

- **AI Engine:** Ollama chạy local (Llama 3.2 3B mặc định).
- **Backend Framework:** Python FastAPI (AI) + Java Spring Boot (clinic-backend).
- **Kiến thức tĩnh:** Markdown chunk + keyword search (`app/rag/retriever.py`).
- **Dữ liệu live:** LangChain tools → HTTP REST clinic-backend.
- **Giao tiếp:** REST API (`POST /api/v1/chat/send`, `/stream` chunk sau khi xử lý xong).
- **Session:** In-memory (không dùng PostgreSQL/MongoDB cho chat ở giai đoạn này).

## Cấu trúc mã nguồn (Code)

```
app/
├── main.py, config.py
├── api/v1/endpoints/chat.py
├── core/prompts.py, exceptions.py
├── schemas/chat.py
├── services/llm_service.py, chat_service.py
├── rag/retriever.py
├── tools/clinic_tools.py, patient_tools.py, appointment_tools.py
└── clients/backend_client.py
knowledge/          # FAQ markdown
prompts/system.txt
```

## Đã tích hợp Frontend

- **Patient Web:** Floating chatbot gọi `POST /api/v1/chat/send`
- **Mobile App:** Tab Chat gọi `POST /api/v1/chat/send`

Xem hướng dẫn chạy đầy đủ: [deployment.md](deployment.md) | [integration-guide.md](integration-guide.md)

## Cấu trúc tài liệu (Docs)

- [Kiến trúc & Luồng xử lý (Architecture)](architecture.md)
- [Knowledge Base — Bảo trì FAQ cho AI (Knowledge Base)](knowledge-base.md)
- **Luồng đặt lịch / khám bệnh (backend):** `clinic-backend/docs/business-flows.md` — nguồn sự thật cho schema và business rules
- [Thiết kế API & WebSocket (API Design)](api-design.md)
- [Cấu trúc Database (Database Schema)](database-schema.md)
- [Kỹ thuật Prompt & Intents (Prompt Engineering)](prompt-engineering.md)
- [Hướng dẫn Tích hợp Microservices (Integration Guide)](integration-guide.md)
- [Kế hoạch Phát triển (Development Plan)](development-plan.md)
- [Hướng dẫn Cài đặt & Triển khai (Deployment)](deployment.md)
