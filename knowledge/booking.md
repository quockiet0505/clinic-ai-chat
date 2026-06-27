# Hướng dẫn chi tiết Đặt Lịch Khám (Q&A)

## 4 Chế độ đặt lịch (Booking Modes)
**Câu hỏi:** Hệ thống ClinicPro có những phương thức đặt lịch nào?
**Trả lời:** Hệ thống cung cấp 4 chế độ đặt lịch chính, tương ứng với nhu cầu của bệnh nhân:
1. **Theo Bác sĩ (DOCTOR):** Bạn chỉ định đích danh một bác sĩ (ví dụ: Bác sĩ Tuấn). Bạn chọn ngày và xem khung giờ trống của bác sĩ này.
2. **Theo Chuyên khoa (EXPERTISE):** Bạn chọn chuyên khoa (ví dụ: Tim mạch), hệ thống sẽ hiển thị danh sách các bác sĩ thuộc khoa này để bạn lựa chọn và xem giờ trống.
3. **Theo Dịch vụ (SERVICE):** Dành cho việc đặt gói khám, xét nghiệm (LAB_TEST) hoặc chụp chiếu (IMAGING). Với gói khám, bạn vẫn cần chọn bác sĩ. Với xét nghiệm, hệ thống sẽ tự động gán nhân viên (LAB_TECH hoặc STAFF).
4. **Trực tiếp (DIRECT):** Dành cho bệnh nhân đến quầy lễ tân yêu cầu khám trực tiếp, nhân viên sẽ tự động gán bác sĩ có lịch trống gần nhất.

## Quy định về thời gian đặt lịch
**Câu hỏi:** Tôi có thể đặt lịch khám vào cuối tuần không?
**Trả lời:** Không, phòng khám hiện **không nhận lịch khám vào Thứ Bảy và Chủ Nhật**. Ngoài ra, hệ thống cũng khóa không cho phép đặt lịch vào các Ngày Lễ chính thức hoặc các ngày bác sĩ bạn chọn đang xin nghỉ phép.

**Câu hỏi:** Tôi phải đặt lịch trực tuyến trước bao nhiêu tiếng?
**Trả lời:** Theo quy định của phòng khám, mọi lịch hẹn đặt trực tuyến (Online) phải được đặt **trước ít nhất 24 giờ** so với thời điểm khám.

**Câu hỏi:** Mỗi lượt khám kéo dài bao lâu?
**Trả lời:** Trừ khi có cấu hình riêng, mặc định mỗi khung giờ khám (Slot) sẽ kéo dài **30 phút**. Khung giờ làm việc mặc định của bác sĩ nếu không có lịch đột xuất là **07:30 - 11:30** (sáng) và **13:30 - 17:00** (chiều).

## Vấn đề Khách vãng lai và Số thứ tự
**Câu hỏi:** Nếu tôi đến trực tiếp phòng khám mà không đặt trước (Walk-in) thì sao?
**Trả lời:** Lễ tân sẽ xếp bạn vào lịch trống hiện tại của bác sĩ. Lịch của bạn sẽ được chuyển ngay sang trạng thái CHECKED_IN. Hệ thống sẽ cấp cho bạn một **Số thứ tự (Queue Number)** dựa trên số lượng khách vãng lai trong ngày. Nếu bạn là ca Cấp cứu (Priority), bạn sẽ được xếp số thứ tự Ưu tiên số 0.
Lưu ý: Nếu bạn đến sau **16:45** (quá sát giờ nghỉ 17:00), hệ thống sẽ từ chối nhận thêm khách vãng lai.

## Các trạng thái của một Lịch hẹn
**Câu hỏi:** Lịch hẹn của tôi sẽ trải qua những trạng thái nào?
**Trả lời:** Lịch hẹn có các trạng thái theo thứ tự:
1. **PENDING:** Lịch vừa được đặt, đang chờ phòng khám xác nhận.
2. **CONFIRMED:** Phòng khám đã chấp nhận lịch của bạn.
3. **CHECKED_IN:** Bạn đã đến phòng khám và quét mã QR hoặc báo danh tại quầy.
4. **IN_PROGRESS:** Bạn đang trong phòng khám với bác sĩ.
5. **WAITING_RESULT:** Đang chờ kết quả xét nghiệm cận lâm sàng.
6. **COMPLETED:** Buổi khám đã hoàn tất.
7. **SKIPPED / NO_SHOW:** Bỏ qua lượt hoặc không đến khám.
8. **CANCELLED:** Lịch đã bị hủy bởi bạn hoặc phòng khám.
