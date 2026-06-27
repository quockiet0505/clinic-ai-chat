# Hướng dẫn chi tiết Tài khoản và Sinh hiệu Bệnh nhân (Q&A)

## Quản lý Tài khoản (Account)
**Câu hỏi:** Tài khoản của tôi bị khóa đặt lịch online, lý do vì sao?
**Trả lời:** Theo quy định của hệ thống backend, nếu một tài khoản bệnh nhân thực hiện thao tác **Hủy lịch khám sát giờ** với lý do chứa từ khóa `[SPAM]` từ 3 lần trở lên, hoặc liên tục **Không đến khám (NO_SHOW)**, hệ thống sẽ tự động khóa tính năng Đặt lịch trực tuyến. Lúc này, bệnh nhân chỉ có thể đến đăng ký khám trực tiếp tại quầy. (Bạn có thể gọi hotline để khiếu nại).

**Câu hỏi:** Tôi có thể thay đổi số điện thoại trên hồ sơ không?
**Trả lời:** Có. Bệnh nhân có thể đăng nhập vào Web/App để cập nhật các thông tin cơ bản trên bảng `Patient` như Họ tên, Giới tính, Ngày sinh, Số điện thoại và Địa chỉ. Xin lưu ý hệ thống có xác thực số điện thoại hợp lệ (phải từ 10 đến 15 chữ số). Ngày sinh không được lớn hơn ngày hiện tại (không được ở tương lai).

## Hồ sơ Sinh hiệu (Patient Vital Profile)
**Câu hỏi:** Bác sĩ có biết được nhóm máu hay các bệnh lý nền của tôi trước khi khám không?
**Trả lời:** Có. Hệ thống ClinicPro lưu trữ một Hồ sơ Sinh hiệu (Vital Profile) riêng biệt gắn liền với từng bệnh nhân. 
Bạn có thể cập nhật các thông tin sau vào hệ thống để bác sĩ tham khảo:
- Nhóm máu (Blood Type)
- Tiền sử dị ứng (Allergies) - Rất quan trọng khi kê đơn thuốc.
- Bệnh mãn tính (Chronic Diseases)
- Lịch sử phẫu thuật/bệnh tật (Medical History)

Mỗi lần bạn đến khám, y tá sẽ tiến hành đo lại Chiều cao, Cân nặng, Huyết áp, Nhịp tim và cập nhật đè lên hồ sơ sinh hiệu này. Việc lưu trữ xuyên suốt giúp bác sĩ cá nhân hóa quá trình điều trị cho bạn.
