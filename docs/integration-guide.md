# 🔗 Hướng dẫn Tích hợp (Integration with Spring Boot)

FastAPI (AI Chat) đóng vai trò là Client đi gọi API của Spring Boot Backend để lấy dữ liệu thực tế.

## 1. Cấu hình Gọi API
Bên trong FastAPI, ta sử dụng thư viện `httpx` (async) để gọi REST API sang Spring Boot.
- **Base URL Backend:** `http://localhost:8080/api/v1`
- Cần tạo một `Service Account Token` (JWT nội bộ) để FastAPI có quyền bypass Security của Spring Boot khi gọi các API hệ thống.

## 2. Các API cần tương tác
### Lấy danh sách Bác sĩ / Chuyên khoa
Khi user hỏi "Phòng khám có bác sĩ tim mạch nào giỏi không?".
- FastAPI gọi: `GET /api/v1/doctors?specialty=tim_mach&sort=rating,desc`
- Parse kết quả, đưa vào Context cho Llama sinh câu trả lời.

### Lấy thông tin Lịch hẹn
Khi user hỏi "Tôi có lịch khám nào ngày mai không?".
- FastAPI phải trích xuất `patient_id` (từ token Web/Mobile truyền vào WebSocket).
- Gọi Backend: `GET /api/v1/appointments?patientId=123&status=PENDING`
- Trả về câu trả lời: "Dạ, ngày mai bạn có lịch khám Tiêu hóa lúc 09:00 với BS. Nguyễn Văn A."

### Thực thi Đặt lịch
- Llama trích xuất xong Entity -> Gọi hàm Python `book_appointment_tool()`.
- Hàm này thực thi: `POST /api/v1/appointments` tới Backend.
