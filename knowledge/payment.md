# Hướng dẫn chi tiết Thanh toán & Viện phí (Q&A)

## Thời điểm tính tiền và Thanh toán
**Câu hỏi:** Tiền khám bệnh của tôi được tính như thế nào?
**Trả lời:** Khác với nhiều nơi thu tiền trước, hệ thống của ClinicPro tính tiền **sau khi khám xong**. Cụ thể, ngay khi bác sĩ hoàn tất quá trình khám và ấn nút "Hoàn thành" (DONE) trên phần mềm, hệ thống backend sẽ tự động tính tổng viện phí của bạn.

**Câu hỏi:** Viện phí của tôi bao gồm những khoản nào?
**Trả lời:** Tổng viện phí của bạn được hệ thống tự động cộng dồn từ 2 khoản:
1. **Tiền công khám (Consultation Fee):** Mức giá này phụ thuộc vào Bác sĩ bạn chọn (lấy từ bảng `doctor_service_price`). Nếu bác sĩ chưa được cấu hình giá riêng, hệ thống sẽ tự động áp dụng mức giá mặc định là **300.000 VNĐ**.
2. **Tiền xét nghiệm/chụp chiếu (Service Fee):** Hệ thống sẽ rà soát tất cả các Phiếu chỉ định (Service Order) mà bác sĩ yêu cầu bạn làm trong buổi hôm đó. Nó sẽ cộng tổng tiền của những dịch vụ mà bạn ĐÃ LÀM (loại trừ những dịch vụ bị CANCELLED).

Sau khi có tổng cộng, bạn sẽ cầm biên lai ra quầy thu ngân để thanh toán.

## Khuyến mãi và Giảm giá
**Câu hỏi:** Tôi thấy dịch vụ có giá gốc và giá khuyến mãi, hệ thống thu theo giá nào?
**Trả lời:** Hệ thống luôn ưu tiên lấy giá Khuyến mãi (Discount Price) làm mức thu thực tế nếu dịch vụ đó đang được cài đặt khuyến mãi trên hệ thống. Nếu không, hệ thống sẽ thu theo giá Gốc (Original Price).

## Hóa đơn
**Câu hỏi:** Tôi có thể lấy hóa đơn VAT không?
**Trả lời:** Có. Sau khi thanh toán viện phí tại quầy, bạn cung cấp Mã số Thuế và thông tin Công ty cho Thu ngân để xuất hóa đơn VAT điện tử.
