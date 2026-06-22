# Cấu trúc Database (Database Schema)

Dự án có thể sử dụng PostgreSQL (Relational) hoặc MongoDB (NoSQL). Dưới đây là thiết kế theo hướng Relational (PostgreSQL) - phù hợp với kiến trúc phòng khám chung.

## 1. Table `chat_sessions`
Lưu trữ thông tin về một phiên chat của người dùng.

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | Primary Key | ID của phiên chat |
| `patient_id` | UUID | Nullable, FK | Liên kết đến Patient Service nếu user đã đăng nhập |
| `device_id` | VARCHAR | Nullable | ID thiết bị cho guest user |
| `status` | VARCHAR | Default 'active' | Trạng thái (`active`, `closed`) |
| `summary` | TEXT | Nullable | Tóm tắt nội dung phiên chat (dùng cho analytics) |
| `created_at` | TIMESTAMP | Default NOW() | |
| `updated_at` | TIMESTAMP | Default NOW() | |

## 2. Table `chat_messages`
Lưu trữ từng tin nhắn trong phiên.

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | Primary Key | |
| `session_id` | UUID | Foreign Key | Thuộc phiên chat nào |
| `sender_type` | VARCHAR | Not Null | `user` (Bệnh nhân), `ai` (Bot), `system` (Hệ thống) |
| `content` | TEXT | Not Null | Nội dung tin nhắn |
| `intent` | VARCHAR | Nullable | Ý định được phân loại (VD: `book_appt`) |
| `action_payload` | JSONB | Nullable | Dữ liệu dạng JSON nếu tin nhắn kích hoạt UI Action |
| `created_at` | TIMESTAMP | Default NOW() | |

## 3. Table `chat_feedbacks`
Lưu trữ đánh giá của người dùng về câu trả lời của AI (Thumbs up / Thumbs down).

| Cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | UUID | Primary Key | |
| `message_id` | UUID | Foreign Key | Đánh giá cho tin nhắn AI nào |
| `rating` | INT | Not Null | 1 (Up), -1 (Down) |
| `comment` | TEXT | Nullable | Lý do đánh giá |
| `created_at` | TIMESTAMP | Default NOW() | |

## 4. Bảng liên quan (Tham khảo từ các Microservice khác)
- **Appointments:** `Appointment Service` quản lý, Chat Service chỉ gọi qua API, không lưu trực tiếp vào database này.
- **Patients/Users:** `Patient Service` quản lý.
