# Tiến độ Dự án & Những việc đang làm

Tài liệu này ghi lại những gì hệ thống đã hoàn thiện, các bug lớn đã được sửa và định hướng tiếp theo.

## 1. Các hạng mục đã hoàn thiện
- **Ổn định hệ thống Core LLM:** Cấu hình Langchain kết nối thành công với Ollama (Qwen2.5 / Llama3.2).
- **Phát triển bộ công cụ (Tools):** Tích hợp hoàn chỉnh các API từ Backend (Spring Boot) thành các tool cho AI (tra cứu bác sĩ, dịch vụ, đặt lịch, hủy lịch).
- **Tối ưu Knowledge Base:** Đập đi xây lại toàn bộ thư mục `knowledge/` (khoảng 12 file) thành định dạng chuẩn Q&A để tối đa hóa hiệu suất cho thuật toán RAG.
- **Sửa bug RAG và Prompt:** Tách biệt Context ra khỏi System Message để LLM không bị rối. Đã cấu hình "CRITICAL RULES" để cấm AI in ra file JSON cho người dùng.
- **Fix lỗi tìm kiếm Bác sĩ:** Nâng cấp `get_doctors_tool` hỗ trợ tìm kiếm bằng tham số `doctor_name` và tăng giới hạn số lượng trả về lên 50, xử lý triệt để lỗi "không tìm thấy Bác sĩ Tuấn".

## 2. Trạng thái hiện tại
Hiện tại, AI đã có khả năng:
- Giao tiếp mượt mà bằng tiếng Việt, không quăng lỗi JSON.
- Đóng vai trò là một tiếp tân ảo xuất sắc, biết hướng dẫn khách hàng, tra cứu giá tiền và lịch trống.
- Có khả năng tự động đặt lịch / hủy lịch nếu người dùng đã đăng nhập (cung cấp Token).

## 3. Các bước tiếp theo (Roadmap)
1. **Hoàn thiện Medical RAG:** Nhúng (embed) toàn bộ bộ dataset 9.400 câu hỏi y tế (`hungnm/vietnamese-medical-qa`) vào hệ thống Vector Database.
2. **Train LoRA (Tùy chọn):** Nếu AI còn trả lời lan man hoặc quên cảnh báo y tế, sẽ tiến hành Fine-tune LoRA một phần nhỏ để ép mô hình tuân thủ quy tắc xưng hô và khước từ chẩn đoán bệnh.
3. **Mở rộng giao diện UI/UX:** Cải tiến khung chat trên Website (React/Next.js) để render các câu trả lời dạng Markdown, in đậm tên bác sĩ và tạo các nút Quick Reply.
