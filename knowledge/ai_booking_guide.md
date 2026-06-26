# Hướng dẫn đặt lịch — dành cho trợ lý AI (thực tế hệ thống)

Tài liệu này mô tả **những gì hệ thống làm được hôm nay**. AI phải trả lời theo nội dung này, không hứa tính năng chưa có.

## AI làm được gì

- Trả lời FAQ: giờ làm việc, hủy lịch, thanh toán, quy trình chung.
- Gợi ý **chuyên khoa tham khảo** từ triệu chứng (RAG `symptom_guide`) — không chẩn đoán.
- Tra **bác sĩ, chuyên khoa, dịch vụ, giá, hotline** qua tool → backend.
- Tra **giờ trống của một bác sĩ cụ thể** theo ngày (tool `get_available_slots_tool` — cần mã bác sĩ).
- Hỗ trợ **đăng ký tài khoản** guest (tool `register_patient_tool`).
- Hướng dẫn bệnh nhân **tự đặt lịch trên web/app** sau khi đăng nhập.

## AI đã làm được những gì (Cập nhật mới)

- **Tự động tạo lịch hẹn** thay bệnh nhân thông qua `book_appointment_tool` (đã hỗ trợ truyền JWT `access_token` từ Frontend).
- **Xem và hủy lịch hẹn** cá nhân (sử dụng `get_my_appointments_tool` và `cancel_appointment_tool`).
- **Tra giờ trống theo bác sĩ / chuyên khoa / dịch vụ** (đã tích hợp vào `get_available_slots_tool`).
- (Đang phát triển): Đặt gói khám nhiều dịch vụ một lần (đợi backend hoàn thiện bảng `appointment_service`).

Khi khách muốn đặt lịch mà chưa đăng nhập: AI sẽ yêu cầu khách đăng nhập trên website/app để lấy token, hoặc gọi hotline **1900 2115**.

## Quy tắc đặt lịch (backend đang enforce)

| Quy tắc | Giá trị |
|---------|---------|
| Đặt online (ONLINE) | Trước giờ khám **ít nhất 24 giờ** |
| Hủy lịch online | Trước giờ khám **ít nhất 3 tiếng** |
| Độ dài slot khám bác sĩ | **30 phút** |
| Trạng thái khi tạo online | **PENDING** (chờ phòng khám xác nhận) |
| Mô tả triệu chứng trên web | **Bắt buộc** — lưu vào `note` của lịch hẹn |
| Đăng nhập | **Bắt buộc** để đặt online |

## Ba cách đặt lịch khám — web/app (đang hoạt động)

### Cách A — Từ trang bác sĩ (`doctorId`)

Chọn bác sĩ → chuyên khoa tự khóa theo bác sĩ → chọn ngày → chọn slot 30 phút của bác sĩ đó → nhập triệu chứng → xác nhận.

### Cách B — Từ chuyên khoa (`expertiseId`)

Chọn chuyên khoa → **phải chọn bác sĩ** trên website để hiện khung giờ (API slot chỉ theo từng bác sĩ).

Nếu không chọn bác sĩ trên form, backend có thể tự xếp bác sĩ khi tạo lịch — nhưng **web hiện không hiện giờ trống** khi chưa chọn bác sĩ. AI nên khuyên: chọn bác sĩ trong danh sách, hoặc gọi hotline.

Tuỳ chọn "Sắp xếp bác sĩ ngẫu nhiên" trên web **chưa hiện slot** — nên chọn bác sĩ cụ thể.

### Cách C — Từ dịch vụ (`serviceId`, mode service)

Chọn dịch vụ (khám EXAM, xét nghiệm LAB_TEST, chụp IMAGING).

**Khám bệnh (EXAM):** tương tự chọn bác sĩ + slot.

**Xét nghiệm/chụp (LAB_TEST, IMAGING):** thiết kế không bắt buộc bác sĩ; **web/app chưa có slot Lab ổn định** — khuyên gọi **1900 2115** hoặc đến quầy.

## Direct booking (chỉ mô tả + ngày giờ)

Thiết kế tương lai: bệnh nhân mô tả triệu chứng → AI gợi ý khoa → đặt lịch.

**Hiện tại:** AI chỉ **gợi ý chuyên khoa** và liệt kê bác sĩ/dịch vụ; bệnh nhân tự hoàn tất trên web hoặc hotline.

## Sau khi đặt lịch

Xem lịch tại **Lịch hẹn của tôi**. Trạng thái thường gặp: PENDING → CONFIRMED → CHECKED_IN → COMPLETED.

Đến quầy **trước giờ hẹn 10–15 phút**, mang CMND/CCCD.

## Khi khách hỏi giờ trống

1. Hỏi **bác sĩ** (hoặc giúp chọn từ chuyên khoa bằng `get_doctors_tool`).
2. Hỏi **ngày** (định dạng YYYY-MM-DD).
3. Gọi `get_available_slots_tool` với `doctor_id` và `date`.
4. Nếu chưa chọn được bác sĩ → gợi ý danh sách bác sĩ theo chuyên khoa trước.

Không bịa giờ trống.

## Khi khách mô tả triệu chứng

1. Dùng kiến thức RAG gợi ý chuyên khoa (tham khảo).
2. Gọi `get_specialties_tool` / `get_doctors_tool` để đưa lựa chọn thật.
3. Nhắc: đây không phải chẩn đoán; triệu chứng nặng → 115.
4. Hướng dẫn đặt lịch trên web: chọn khoa/BS → ngày giờ → triệu chứng.

## Loại dịch vụ trên hệ thống

| service_type | Ý nghĩa |
|--------------|---------|
| EXAM | Khám bệnh / gói khám — thường có bác sĩ |
| LAB_TEST | Xét nghiệm (máu, nước tiểu, ...) |
| IMAGING | Chụp chiếu (X-quang, siêu âm, MRI, CT) |

Giá và tên dịch vụ: luôn gọi `get_services_tool`.
