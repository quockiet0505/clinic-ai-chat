# Kế hoạch Phát triển (Development Plan)

Dự án được chia làm 6 giai đoạn (Phases) để đảm bảo tiến độ và giảm thiểu rủi ro.

## Giai đoạn 1: Khởi tạo và Setup Cơ sở hạ tầng (Tuần 1)
- Thiết lập thư mục dự án `clinic-ai-chat` (Sử dụng Spring Boot + Java 17).
- Viết Dockerfile và Docker Compose (nếu cần).
- Cài đặt Ollama local và tải các models (`llama3.2`, `qwen2.5-coder`).
- Setup Database Schema (PostgreSQL/MongoDB).

## Giai đoạn 2: Tích hợp Local LLM (Tuần 1 - 2)
- Cấu hình thư viện Langchain / LlamaIndex để giao tiếp với Ollama qua REST API.
- Viết các function cơ bản để truyền prompt và nhận response.
- Thử nghiệm system prompt cơ bản để đóng vai "Clinic AI".

## Giai đoạn 3: Phát triển REST API & Database (Tuần 2)
- Viết các API CRUD cho Chat Sessions và Chat Messages.
- Lưu trữ lịch sử tin nhắn.
- Áp dụng kỹ thuật nhớ (Memory/Context Window) để gởi kèm lịch sử chat vào mỗi prompt.

## Giai đoạn 4: Tích hợp Microservices (Tool Calling) (Tuần 3)
- Định nghĩa các "Tools" cho LLM (ví dụ: `check_appointments`, `get_doctors`).
- Triển khai code gọi API sang `Appointment Service`, `Staff Service`, v.v.
- Parse yêu cầu từ người dùng -> gọi Tool -> lấy kết quả -> đưa lại cho LLM để sinh câu trả lời tự nhiên.

## Giai đoạn 5: Phát triển WebSocket & Streaming (Tuần 4)
- Setup WebSocket Server.
- Chuyển đổi luồng sinh text từ LLM thành dạng stream qua WebSocket.
- Thiết kế cơ chế gửi `UI_ACTION` qua WebSocket để Client render UI tương ứng (ví dụ form đặt lịch).

## Giai đoạn 6: Kiểm thử, Tối ưu và Triển khai (Tuần 5)
- Viết Unit Test cho các function chính.
- Tối ưu hóa prompt để tránh LLM bị hallucination.
- Xử lý các edge cases (ví dụ: người dùng chửi bậy, hỏi ngoài lề).
- Viết tài liệu hướng dẫn triển khai cuối cùng.
