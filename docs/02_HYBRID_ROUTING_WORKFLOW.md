# Kiến trúc Phân luồng Mô hình Kép (Hybrid Dual-Model Routing)

> **[CẢNH BÁO] TÍNH NĂNG NÀY HIỆN TẠI ĐANG TẠM NGƯNG.**
> Nhằm tối ưu tốc độ cho các hệ thống máy cá nhân (như RTX 3050), code hiện tại đã được Revert về kiến trúc **Pure RAG (Dùng chung 1 model siêu nhẹ cho mọi tác vụ)**. Tài liệu dưới đây chỉ đóng vai trò tham khảo cho các lần nâng cấp sau này.

Tài liệu này mô tả chi tiết cách hệ thống phân luồng yêu cầu (Intent Routing) và chọn mô hình AI (Model Selection) để đạt được sự cân bằng hoàn hảo giữa **Tốc độ (Speed)**, **Định dạng (Formatting)** và **Chuyên môn Y khoa (Medical Expertise)**.

---

## 1. Vấn đề của mô hình Fine-tuned (Học vẹt & Quên thảm khốc)

Mô hình `clinic-ai:latest` (6.2GB) được huấn luyện (Fine-tune) trên tập dữ liệu 9400 câu hỏi y khoa. Mặc dù nó rất giỏi trong việc đóng vai Bác sĩ, nhưng nó mắc phải 2 nhược điểm chết người khi xử lý các nghiệp vụ khác:
1. **Quá nặng (6.2GB):** Trên các dòng GPU phổ thông như RTX 3050 (4GB/8GB VRAM), mô hình này bị tràn bộ nhớ, đẩy tải sang RAM CPU khiến tốc độ sinh Text rớt thê thảm (mất 40 giây cho một câu trả lời).
2. **Quên cách định dạng (Catastrophic Forgetting):** Do quá tập trung học kiến thức Y khoa, mô hình quên mất cách định dạng Markdown chuẩn, dẫn đến lỗi dính chữ hoặc sai format khi in Bảng giá hay Lịch làm việc.

---

## 2. Giải pháp: Kiến trúc Hybrid (Lễ Tân & Bác Sĩ)

Để giải quyết, hệ thống triển khai cơ chế **Luân chuyển Mô hình tự động** ngay bên trong `LLMService`.

### A. Mô hình "Lễ Tân" (`qwen2.5:3b`)
- **Nhiệm vụ:** Xử lý các Intent liên quan đến `CLINIC_INFO`, `DOCTOR_INFO`, `BOOKING` (Hỏi giá, giờ làm, tìm bác sĩ, đặt lịch).
- **Đặc điểm:** Nhẹ (1.9GB), phản hồi siêu tốc (< 4 giây), định dạng Markdown cực chuẩn.
- **Quy trình:**
  1. Router xác định Intent là Đặt lịch / Hỏi giá.
  2. Lấy dữ liệu từ Backend API (Tools).
  3. Đánh thức `qwen2.5:3b` trả lời khách hàng.

### B. Mô hình "Bác Sĩ" (`clinic-ai:latest`)
- **Nhiệm vụ:** Trả lời các Intent về `MEDICAL_QA` (Bệnh lý, triệu chứng, tư vấn y khoa).
- **Đặc điểm:** Chuyên môn y khoa cao, văn phong chuẩn y khoa.
- **Quy trình:**
  1. Router xác định Intent là Hỏi bệnh.
  2. Hệ thống bới tìm 3 tài liệu sát nhất trong ChromaDB (RAG 9400 câu).
  3. Ollama **tự động Swap (đổi) mô hình**, đẩy mô hình Lễ tân ra khỏi VRAM và đưa mô hình Bác sĩ vào để xử lý câu hỏi.

---

## 3. Tối ưu Cache (Truy xuất tức thì < 0.5s)

Để khắc phục độ trễ dư thừa cho các câu hỏi mang tính "văn mẫu" và bất biến (như hỏi giờ làm việc, hỏi bảng giá), hệ thống tích hợp thêm lớp **Semantic Cache (Tối ưu 2)** ở cấp độ cao nhất trong `chat_service.py`.

- Khi người dùng nhắn các câu như: `"lịch làm việc"`, `"chi phí khám"`, `"bảng giá"`,... 
- Hàm `stream_message` sẽ **chặn đứng** truy vấn ngay lập tức, không thèm ném qua Router hay LLM.
- **Kết quả:** Trả về văn bản đã chuẩn bị sẵn (Cached Response) chỉ trong vòng `~0.005 giây`. 
- **Lợi ích:** Tiết kiệm hàng ngàn lệnh gọi LLM vô ích, giải phóng hoàn toàn tài nguyên GPU để phục vụ cho các câu hỏi phức tạp hơn.
