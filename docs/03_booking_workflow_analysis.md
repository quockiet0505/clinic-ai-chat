# Phân Tích Luồng Đặt Lịch Thông Minh (Booking Workflow)

Tài liệu này phân tích chi tiết quy trình Đặt lịch khám bệnh tự động qua AI Chatbot, đảm bảo bám sát các nghiệp vụ (Business Logic) thực tế của hệ thống ClinicPro.

## 1. Các Trường Hợp Đặt Lịch (Booking Modes)
Dựa theo tài liệu nghiệp vụ, hệ thống AI cần xử lý 3 luồng đặt lịch trực tuyến (Online Booking) chính:
- **Đặt theo Bác sĩ (Doctor):** Người dùng yêu cầu đích danh bác sĩ (VD: "Tôi muốn đặt lịch bác sĩ Lê Tuấn").
- **Đặt theo Chuyên khoa (Expertise):** Người dùng yêu cầu khám chuyên khoa (VD: "Tôi muốn khám Răng Hàm Mặt").
- **Đặt theo Dịch vụ (Service):** Người dùng yêu cầu gói khám/xét nghiệm (VD: "Tôi muốn đặt gói khám tổng quát").

## 2. Các Trường Thông Tin Bắt Buộc (Required Fields)
Để chốt được một lịch hẹn, AI **bắt buộc phải thu thập đủ 4 trường thông tin sau** từ người dùng:
1. **Đối tượng khám (Target):** ID của Bác sĩ (`doctor_id`), Khoa (`expertise_id`), hoặc Dịch vụ (`service_id`).
2. **Ngày khám (Date):** Định dạng `YYYY-MM-DD`.
3. **Khung giờ (Time Slot):** Định dạng `HH:mm`. Phải nằm trong khung giờ làm việc (Sáng: 07:30 - 11:30, Chiều: 13:30 - 17:00).
4. **Triệu chứng (Symptoms/Reason):** Lý do đi khám để bác sĩ chuẩn bị.

## 3. Các Ràng Buộc Nghiệp Vụ (Business Constraints)
AI không được phép đặt lịch bừa bãi mà phải tuân thủ các quy tắc sau (Code Python sẽ chặn):
- **Luật 24 Giờ:** Phải đặt trước ít nhất 24 giờ. AI không được cho phép đặt lịch "ngay hôm nay".
- **Luật Cuối Tuần:** Phòng khám không làm việc Thứ 7 và Chủ Nhật.
- **Xác thực (Authentication):** Người dùng bắt buộc phải có `access_token` (đã đăng nhập) mới được gọi API `create_appointment`.

## 4. Giải Pháp Kiến Trúc: State-based Extractor

Việc đặt lịch là một quá trình **Multi-turn (Hội thoại nhiều bước)**. Chúng ta sẽ dùng Deterministic Pipeline kết hợp với State Memory để ép AI hỏi người dùng cho đến khi đủ thông tin:

### Vòng lặp thu thập thông tin:
- **Bước 1:** `BookingExtractor` đọc lịch sử chat, xuất ra JSON chứa các trường hiện có.
  ```json
  {
    "target_type": "EXPERTISE",
    "target_name": "Tai Mũi Họng",
    "date": null,
    "time_slot": null,
    "symptoms": "Đau rát họng"
  }
  ```
- **Bước 2 (Code Python kiểm tra):**
  - **Thiếu Date?** -> Dừng vòng lặp, ra lệnh cho Chat LLM: *"Hãy hỏi người dùng ngày họ muốn đến khám (nhắc họ phòng khám không làm việc cuối tuần)."*
  - **Đủ Date nhưng thiếu Time Slot?** -> Code gọi API `get_available_slots` -> Nạp list giờ trống vào Prompt -> Yêu cầu Chat LLM: *"Hãy liệt kê các giờ trống sau (08:00, 08:30...) và bảo người dùng chọn."*
  - **Thiếu Symptoms?** -> Ra lệnh Chat LLM hỏi: *"Bạn có thể mô tả triệu chứng hiện tại không?"*
- **Bước 3 (Chốt đơn):** Khi JSON đã đầy đủ tất cả các trường. Code Python kiểm tra `access_token`.
  - Bị thiếu Token: AI trả lời *"Vui lòng đăng nhập để hoàn tất đặt lịch."*
  - Đã có Token: Code Python gọi API POST `/api/v1/appointments` -> Trả về mã vé -> AI báo đặt thành công.

## 5. Tổng Kết
Với kiến trúc Pipeline phân tách rạch ròi: LLM chỉ dùng để trích xuất JSON (Extractor) và giao tiếp NLP (Chat). Mọi logic nghiệp vụ khó (Check thứ 7 chủ nhật, Check 24h, Check slot trống) sẽ do **Spring Boot Backend và Python code** đảm nhiệm. Điều này đảm bảo AI của ClinicPro không bao giờ bị "ảo giác" trong quá trình tư vấn lịch khám!
