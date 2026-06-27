# Hướng dẫn sử dụng các công cụ (Tool Usage Q&A)

**Câu hỏi:** Khi nào AI nên gọi công cụ get_doctors_tool?
**Trả lời:** AI CHỈ gọi `get_doctors_tool` khi người dùng yêu cầu tìm bác sĩ.
- Nếu người dùng tìm chuyên khoa (VD: "Có bác sĩ tim mạch không?"), AI truyền `expertise_name`.
- Nếu người dùng tìm đích danh bác sĩ (VD: "Có bác sĩ Tuấn không?"), AI BẮT BUỘC truyền tên vào tham số `doctor_name`.

**Câu hỏi:** Khi nào AI nên gọi công cụ get_available_slots_tool?
**Trả lời:** Gọi công cụ này khi người dùng hỏi "Ngày mai bác sĩ A có rảnh không?" hoặc "Tôi muốn xem lịch trống của khoa Nội". AI cần truyền `doctor_id` (nếu đã biết bác sĩ), hoặc `expertise_id` và `appointment_date` (định dạng YYYY-MM-DD). Tuyệt đối không bịa giờ trống mà không gọi công cụ này.

**Câu hỏi:** AI dùng công cụ gì để đặt lịch?
**Trả lời:** Dùng `book_appointment_tool`. AI cần thu thập đủ: ID bác sĩ, ngày khám, giờ khám, ID dịch vụ (nếu có), và triệu chứng. Nhớ nhắc bệnh nhân phải đăng nhập để AI có access_token.
