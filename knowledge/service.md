# Hướng dẫn chi tiết Các Loại Dịch vụ (Q&A)

## Phân loại 3 nhóm dịch vụ
**Câu hỏi:** Hệ thống ClinicPro quản lý các loại dịch vụ như thế nào?
**Trả lời:** Theo hệ thống dữ liệu, mọi dịch vụ (Service) được chia thành 3 nhóm (`ServiceType`) với quy trình xử lý hoàn toàn khác nhau:
1. **Khám bệnh (EXAM):** Đây là các dịch vụ như Khám Nội, Khám Tim mạch, Khám Tổng quát. **Bắt buộc** phải do một Bác sĩ (StaffType: DOCTOR) trực tiếp thực hiện.
2. **Xét nghiệm (LAB_TEST):** Gồm xét nghiệm máu, nước tiểu, sinh hóa. Không cần bác sĩ trực tiếp làm, mà sẽ được phân công cho Kỹ thuật viên (StaffType: LAB_TECH) hoặc Nhân viên (STAFF) lấy mẫu và chạy máy.
3. **Chụp chiếu (IMAGING):** Gồm Siêu âm, X-Quang, MRI, CT. Tương tự như Xét nghiệm, phần này do Kỹ thuật viên hình ảnh phụ trách.

## Lưu ý khi đặt lịch Dịch vụ
**Câu hỏi:** Tôi muốn đặt lịch trực tuyến chỉ để xét nghiệm máu (LAB_TEST) thì có cần chọn Bác sĩ không?
**Trả lời:** Về nguyên tắc, Xét nghiệm không cần Bác sĩ. Tuy nhiên, hệ thống đặt lịch tự động hiện tại phân bổ khung giờ (Time slot) dựa trên lịch làm việc của Bác sĩ. Đối với LAB_TEST và IMAGING, hệ thống sẽ tìm khung giờ trống của nhóm nhân viên Kỹ thuật (LAB_TECH) để xếp lịch cho bạn. Nếu bạn gặp khó khăn khi đặt lịch Xét nghiệm trực tuyến, hãy gọi Hotline 1900 2115.

**Câu hỏi:** Dịch vụ nổi bật (Featured) là gì?
**Trả lời:** Trên hệ thống có đánh dấu một số dịch vụ là "Nổi bật" (`is_featured = true`) và được sắp xếp theo mức độ ưu tiên (`featured_priority`). Đây thường là các gói khám tầm soát ung thư, tổng quát toàn diện đang có khuyến mãi. Bạn có thể hỏi AI về các dịch vụ nổi bật này để biết thêm chi tiết.
