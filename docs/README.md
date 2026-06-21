# 🤖 Clinic AI Chat Microservice

Microservice xử lý trí tuệ nhân tạo (AI Chat) cục bộ dành riêng cho hệ sinh thái Clinic Management.
Hệ thống sử dụng LLM Local (Llama 3.2 3B) thông qua Ollama để đóng vai trò là Trợ lý Ảo Y tế, giúp bệnh nhân đặt lịch, tra cứu thông tin và nhận tư vấn sức khỏe cơ bản mà không tốn chi phí API (Zero API Token Cost) và bảo mật tuyệt đối dữ liệu y tế (Privacy-first).

## 💡 Tech Stack
- **Ngôn ngữ:** Python 3.11+
- **Framework:** FastAPI (Cực nhanh, hỗ trợ WebSockets native).
- **AI Core:** Ollama (Local LLM Server).
- **Model:** Llama 3.2 3B (Phiên bản tối ưu hóa cho tốc độ và suy luận cục bộ).
- **Orchestration:** LangChain / LlamaIndex (Quản lý Prompt, RAG, Memory).
- **Database:** PostgreSQL / MySQL (Lưu trữ lịch sử Chat, Feedback).

## 🚀 Các Tính Năng Chính
1. **Tư vấn chuyên khoa:** Phân tích triệu chứng của bệnh nhân và gợi ý khám đúng chuyên khoa.
2. **Hỗ trợ đặt lịch hẹn:** Trích xuất Entity (Thời gian, Bác sĩ, Dịch vụ) để gọi API Backend tự động đặt lịch.
3. **Tra cứu lịch sử:** Kiểm tra lịch hẹn sắp tới, kết quả khám bệnh cũ thông qua Retrieval-Augmented Generation (RAG).
4. **Hỏi đáp phòng khám:** Cung cấp thông tin giờ mở cửa, địa chỉ, bảng giá dịch vụ ưu đãi.
