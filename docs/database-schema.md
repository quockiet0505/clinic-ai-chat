# 🗄️ Cấu trúc Cơ sở dữ liệu (Database Schema)

Dự án sử dụng cơ sở dữ liệu quan hệ (PostgreSQL/MySQL) để lưu trữ State và History, độc lập với Database của Spring Boot (hoặc chung CSDL nhưng khác Schema).

## Bảng `chat_session`
Lưu trữ phiên chat của người dùng.
- `id` (UUID, PK)
- `patient_id` (BIGINT, Nullable - Nếu khách vãng lai)
- `title` (VARCHAR 255) - Tự động tạo tóm tắt từ tin nhắn đầu tiên.
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## Bảng `chat_message`
Lưu từng bong bóng chat trong session.
- `id` (BIGINT, PK, Auto Increment)
- `session_id` (UUID, FK -> chat_session)
- `role` (ENUM: 'user', 'assistant', 'system', 'tool')
- `content` (TEXT)
- `tool_calls` (JSONB) - Lưu dữ liệu log nếu có gọi hàm.
- `created_at` (TIMESTAMP)

## Bảng `chat_feedback`
Thu thập phản hồi để fine-tune mô hình sau này.
- `id` (BIGINT, PK)
- `message_id` (BIGINT, FK -> chat_message)
- `rating` (ENUM: 'thumbs_up', 'thumbs_down')
- `reason` (TEXT)
- `created_at` (TIMESTAMP)
