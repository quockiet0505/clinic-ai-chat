# Phân tích và Khắc phục các Lỗi Phổ biến của AI trong Luồng Đặt Lịch Khám

Tài liệu này ghi chú lại các lỗi phổ biến mà AI thường mắc phải trong quá trình thực hiện luồng đặt lịch khám, nguyên nhân cốt lõi và cách khắc phục đã được áp dụng trong mã nguồn.

## 1. Lỗi kẹt luồng ở bước điền triệu chứng (AI quên Intent BOOKING)
- **Mô tả:** Khi người dùng đang ở bước cuối cùng của luồng đặt lịch (điền triệu chứng hoặc lý do khám), ví dụ trả lời "Tôi bị đau bụng", AI đột ngột đổi ý định (Intent) từ `BOOKING` sang `MEDICAL_QA`. 
- **Hậu quả:** Thay vì chốt lịch khám, AI lại đóng vai bác sĩ để tư vấn bệnh lý (ví dụ: "Chào bạn, đau bụng có thể do nhiều nguyên nhân... Hãy đi khám nhé") và luồng đặt lịch bị huỷ bỏ, vòng lặp hỏi lại triệu chứng tiếp diễn.
- **Nguyên nhân:** Bộ định tuyến (Rule-based Router) thấy từ khoá "đau" nên phân loại thành `MEDICAL_QA`. LLM thì thấy câu trả lời ngắn không có ngữ cảnh đặt lịch nên cũng bị phân tâm.
- **Cách khắc phục:** 
  - Khóa luồng (State Lock): Nếu người dùng đang trong phiên đặt lịch (đã có `target_type`), hệ thống sẽ BẮT BUỘC ghi đè Intent hiện tại thành `BOOKING` bất kể câu trả lời là gì.
  - Sửa đổi hàm `stream_message` và `send_message` trong `chat_service.py` để sử dụng cờ `is_booking` làm điều kiện kích hoạt `QueryAnalyzerService`.

## 2. Lỗi LLM không trích xuất được `symptoms`
- **Mô tả:** Mặc dù Intent đã bị khóa cứng thành `BOOKING`, LLM (QueryAnalyzerService) vẫn trả về tham số `symptoms` rỗng khi người dùng chỉ nhập một câu trần thuật như "Tôi bị đau bụng âm ỉ".
- **Hậu quả:** Hệ thống thấy thiếu `symptoms` nên liên tục hỏi lại: "Để hoàn tất hồ sơ, xin bạn mô tả ngắn gọn triệu chứng...".
- **Nguyên nhân:** LLM đôi khi không nhận diện được một câu nói bâng quơ là một tham số (đặc biệt là khi prompt yêu cầu format JSON chặt chẽ).
- **Cách khắc phục:** 
  - Thêm logic Hardcode (Fallback): Nếu hệ thống đã gom đủ ngày (`date_str`), giờ (`time_slot`) mà đang bị thiếu `symptoms`, thì CÂU TRẢ LỜI NGAY SAU ĐÓ của người dùng sẽ MẶC ĐỊNH được gán thành giá trị cho `symptoms` mà không cần thông qua LLM trích xuất.

## 3. Lỗi thông báo thành công bị LLM viết lại thành tư vấn bệnh
- **Mô tả:** Hệ thống backend đã gọi API đặt lịch thành công và trả về chuỗi "Đặt lịch thành công! Mã vé là XYZ". Tuy nhiên, LLM lại "giấu" câu này đi và tự ý trả lời "Bạn nên đi khám tổng quát nhé".
- **Hậu quả:** Đặt lịch ở backend thì thành công nhưng người dùng không hề biết mã vé của mình.
- **Nguyên nhân:** Các kết quả được đưa vào mục `knowledge_context`. LLM đọc được `knowledge_context` nhưng do có thông tin về triệu chứng (đau bụng), nó ưu tiên chức năng Medical QA thay vì báo tin vui.
- **Cách khắc phục:**
  - Áp dụng cơ chế `[DIRECT_REPLY]`: Nếu chuỗi trả về từ `_execute_booking_flow` bắt đầu bằng `[DIRECT_REPLY]`, hệ thống sẽ cắt thẳng chuỗi này ra màn hình chat mà không gửi qua LLM để format lại.
  - Đồng thời thực hiện `self._session_params.pop(session_id)` để giải phóng trạng thái đặt lịch (clear state) sau khi đã thành công, cho phép người dùng bắt đầu câu chuyện mới.

## 4. Lỗi thiếu Chuyên khoa (expertiseId) khi đặt qua Bác sĩ
- **Mô tả:** Người dùng chọn đích danh Bác sĩ (VD: "Bác sĩ Lê Tuấn"). Khi chốt lịch, backend báo lỗi: "Vui lòng chọn chuyên khoa."
- **Hậu quả:** API `create_appointment` trả về lỗi và đặt lịch thất bại.
- **Nguyên nhân:** Hệ thống AI tra cứu thông tin Bác sĩ từ backend nhưng lấy nhầm field. Backend trả về ID chuyên khoa trực tiếp ở trường `expertiseId` tại root level (ví dụ: `{'staffId': 22, 'expertiseId': 22, ...}`), nhưng AI lại cố tìm trong một object lồng nhau là `d["expertise"]["expertiseId"]`.
- **Cách khắc phục:** 
  - Cập nhật logic tìm ID chuyên khoa trong `chat_service.py` để lấy `d.get("expertiseId")`.

---
*Tài liệu này được tạo ra để lưu trữ lại kinh nghiệm làm việc với hệ thống Agentic Chatbot khi kết hợp giữa luồng dựa trên trạng thái (State-machine) và LLM.*
