# Chính sách và Quy định khắt khe của Phòng khám (Q&A)

Tài liệu này liệt kê các chính sách vận hành được lập trình "cứng" vào hệ thống Backend. Mọi ngoại lệ đều phải thông qua Quản lý phòng khám.

## Chính sách Hủy lịch và Hạn chế (Anti-Spam)
**Câu hỏi:** Tôi có thể hủy lịch bất cứ lúc nào phải không?
**Trả lời:** Không. Theo lập trình của hệ thống, bạn **chỉ được phép hủy lịch trước giờ hẹn ít nhất 3 tiếng**. Nếu thời gian còn lại dưới 3 tiếng, nút Hủy trên Web/App sẽ bị vô hiệu hóa.

**Câu hỏi:** Phòng khám có phạt nếu tôi hay hủy lịch không?
**Trả lời:** Có. Hệ thống có cơ chế Anti-Spam. Nếu bạn hủy lịch quá nhiều lần (từ 3 lần trở lên) và các lần hủy này bị hệ thống đánh dấu là `[SPAM]`, tài khoản của bạn sẽ bị tước quyền đặt lịch online vĩnh viễn (cho đến khi Admin gỡ phạt). Cảnh cáo tương tự áp dụng cho việc đặt lịch mà Không đến khám (`NO_SHOW`).

## Chính sách Đặt lịch Online
**Câu hỏi:** Tại sao tôi không thể đặt lịch khám cho sáng ngày mai ngay bây giờ (tối nay)?
**Trả lời:** Nhằm đảm bảo phòng khám sắp xếp đủ nhân sự, hệ thống quy định: Mọi lịch hẹn đặt trực tuyến (Online) phải cách thời điểm đặt **ít nhất 24 giờ**. Nếu bạn cần khám gấp vào ngày mai, vui lòng gọi Hotline 1900 2115 hoặc đến lấy số trực tiếp (Walk-in).

**Câu hỏi:** Tôi có thể đặt lịch khám vào ngày lễ không?
**Trả lời:** Không. Thuật toán của hệ thống sẽ tự động đối chiếu ngày bạn chọn với Lịch nghỉ Lễ quốc gia và Lịch nghỉ thứ Bảy, Chủ Nhật. Nếu rơi vào các ngày này, hệ thống sẽ chặn không cho tạo lịch hẹn.

## Chính sách Bảo mật Thông tin Bệnh án
**Câu hỏi:** Ai có quyền sửa đổi bệnh án của tôi?
**Trả lời:** Bệnh án (`MedicalRecord`) chỉ có thể được xem và cập nhật bởi bác sĩ trực tiếp khám cho bạn. Mọi sửa đổi sau khi bệnh án đã hoàn tất (`DONE`) đều bị hệ thống lưu lại lịch sử người sửa (`updated_by_doctor`) và bắt buộc phải kèm theo Lý do sửa chữa (`edit_reason`). Bệnh nhân chỉ có quyền Đọc (Read-only) đối với bệnh án của mình.
