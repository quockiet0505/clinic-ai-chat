# Tổng Quan Kiến Trúc Hệ Thống AI Chatbot

Tài liệu này mô tả kiến trúc cốt lõi của trợ lý AI ClinicPro sau khi được tối ưu hóa. Hệ thống sử dụng mô hình ngôn ngữ lớn (Qwen2.5:3B) kết hợp với các kỹ thuật Intent Routing, RAG, Data Pipeline và Tool Calling để giải quyết các truy vấn y tế phức tạp một cách an toàn.

## 1. Hybrid Intent Routing (Bộ định tuyến lai)
Khi người dùng gửi tin nhắn, hệ thống sẽ sử dụng cơ chế **Hybrid Router** (Kết hợp Rule-based và LLM) được viết tại `app/services/router_service.py` để phân loại ý định (Intent) cực nhanh vào 4 nhánh:
- **Clinic FAQ:** Hỏi giờ làm việc, địa chỉ, thanh toán, quy định. (Sẽ đi qua `Clinic RAG`).
- **Medical Question:** Xin tư vấn triệu chứng, bệnh lý. (Sẽ đi qua `Medical RAG`).
- **Tool Calling:** Yêu cầu tìm bác sĩ, xem giá, đặt lịch. (Sẽ gọi API backend).
- **General:** Chào hỏi, khen ngợi thông thường.

## 2. Hệ thống Dual RAG (Retrieval-Augmented Generation)
Hệ thống sử dụng Vector Database (ChromaDB) để lưu trữ và truy xuất:
- **Clinic RAG (`app/rag/retriever.py`):** Dữ liệu nguồn là thư mục `knowledge/`. Chunk size = 350.
- **Medical RAG (`app/rag/medical_retriever.py`):** Lấy 9.335 câu hỏi từ tập dataset `hungnm/vietnamese-medical-qa`. Mỗi cặp Question/Answer được cấu hình thành đúng 1 Document (Không dùng chunking bừa bãi để giữ toàn vẹn ngữ cảnh y tế).

## 3. Data Pipeline (Đường ống xử lý dữ liệu cho Tool Calling)
Để chống hiện tượng Hallucination và ngăn AI hiển thị mã JSON rác cho người dùng, toàn bộ Tool được kiến trúc qua 3 lớp chặt chẽ:
1. **BackendClient:** Gọi API Spring Boot lấy dữ liệu thô (Raw JSON).
2. **ResponseValidator (`app/services/response_validator.py`):** Bắt lỗi mảng rỗng `[]`, `null`, lỗi 500 và trả về thông báo Tiếng Việt chuẩn mực.
3. **Mapper (`app/schemas/domain_models.py`):** Dùng Pydantic đúc JSON thành các Object `Doctor`, `Service`, `Specialty` rõ ràng.
4. **ResponseFormatter (`app/services/response_formatter.py`):** Nặn Object thành Markdown Text (VD: 1206834 -> 1.206.834 VNĐ). Cuối cùng mới chuyển cho LLM.

## 4. Hệ thống Đánh giá Tự động (Evaluation Script)
Được đặt tại `scripts/evaluate_architecture.py`. Đây là Script quan trọng phục vụ cho việc đo lường số liệu Luận văn:
- Tự động chạy bộ **100 test cases** (FAQ, Medical, Tool, General, Edge Cases).
- Ghi log cực chi tiết ra file **`evaluation_results.csv`**:
  - Tính Latency bóc tách cho: Router (ms), RAG (ms), Tool (ms), LLM (ms).
  - Thống kê Token: Prompt, Completion, Total.
  - Ma trận nhầm lẫn của Router: Expected Intent vs Predicted Intent.
  - Phân tích Retrieval: File nào được bốc lên, Similarity Score là bao nhiêu.
  - Đánh giá Correctness và Hallucination dựa trên Ground Truth.

## 5. Mô hình và Fine-Tuning (LoRA)
Hệ thống sử dụng mô hình **Qwen2.5:3B** cài đặt local. 
Thay vì dùng LoRA để nhồi nhét kiến thức (việc này do RAG đảm nhiệm), LoRA được sử dụng để "dạy" mô hình **phong cách trả lời chuẩn y khoa**:
- Biết cảnh báo các trường hợp cấp cứu (gọi 115).
- Khước từ việc chẩn đoán thay bác sĩ thật.
