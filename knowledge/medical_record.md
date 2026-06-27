# Hướng dẫn chi tiết Hồ sơ Y tế & Quy trình khám (Q&A)

## Quy trình Khám và Chờ kết quả
**Câu hỏi:** Quá trình khám tại phòng khám diễn ra như thế nào?
**Trả lời:** Khi đến lượt, bác sĩ sẽ tiến hành khám cho bạn (Trạng thái hồ sơ: **IN_PROGRESS**). Nếu cần thiết, bác sĩ sẽ tạo Phiếu chỉ định xét nghiệm/chụp chiếu (Service Order). Lúc này, trạng thái hồ sơ của bạn chuyển sang **WAITING_RESULT** (Chờ kết quả). Bạn sẽ đi làm xét nghiệm. Khi Kỹ thuật viên nhập kết quả xong, bác sĩ sẽ gọi bạn lại để đọc kết quả và đưa ra Chẩn đoán, Hướng điều trị. Khi xong xuôi, trạng thái chuyển thành **DONE** (Hoàn thành).

## Ghi nhận Sinh hiệu (Triage)
**Câu hỏi:** Tại sao tôi lại bị đo mạch, huyết áp trước khi vào gặp bác sĩ?
**Trả lời:** Đây là bước Đo Sinh hiệu (Triage). Điều dưỡng sẽ ghi nhận chiều cao, cân nặng, nhịp tim, huyết áp của bạn và cập nhật vào Hồ sơ Sinh hiệu (PatientVitalProfile) trên hệ thống. Dữ liệu này giúp bác sĩ có cái nhìn tổng quan nhất về tình trạng thể chất của bạn ngay khi bắt đầu khám.

## Kê đơn thuốc và Tái khám
**Câu hỏi:** Làm sao để xem đơn thuốc của tôi?
**Trả lời:** Đơn thuốc (Prescription) sẽ được bác sĩ kê ngay trên hệ thống. Đơn thuốc bao gồm tên thuốc, số lượng lẻ (ví dụ 1.5 viên), đơn vị (vỉ/lọ) và cách dùng chi tiết. Bạn có thể xem trên app/web tại phần Chi tiết Hồ sơ khám.

**Câu hỏi:** Nếu bác sĩ dặn tái khám thì hệ thống xử lý thế nào?
**Trả lời:** Bác sĩ sẽ tạo một phiếu Hẹn Tái khám (Follow Up) đính kèm vào hồ sơ của bạn. Hệ thống sẽ hiển thị ngày tái khám và tự động gửi thông báo nhắc nhở (Email/Hệ thống) khi gần đến ngày.
