# Chiến lược Huấn luyện và Kiểm thử (Testing) Đa Mô hình AI Y tế

Tài liệu này trình bày chi tiết về phương pháp luận, lý do lựa chọn mô hình, và cách thức đảm bảo tính công bằng trong quá trình huấn luyện và đánh giá hệ thống AI y tế của ClinicPro.

## 1. Tại sao phải huấn luyện cùng lúc 3 mô hình (Qwen, VinaLlama, SeaLLM)?

Trong nghiên cứu khoa học và phát triển phần mềm AI, việc chỉ đưa ra kết quả của một mô hình duy nhất (ví dụ: Qwen-7B) thiếu đi tính thuyết phục. Người dùng hoặc hội đồng đánh giá sẽ đặt câu hỏi: *"Tại sao lại chọn mô hình này? Liệu nó có thực sự tốt nhất cho bài toán y tế tiếng Việt không?"*

Do đó, việc huấn luyện và so sánh cùng lúc 3 mô hình mang lại các lợi ích cốt lõi sau:
- **Tạo ra đối trọng (Baseline Comparison):** Việc có các đối thủ cùng hạng cân (7 Tỷ tham số - 7B) giúp làm nổi bật ưu/nhược điểm của từng cấu trúc (Architecture).
- **Tối ưu ngôn ngữ:** 
  - `Qwen2.5-7B-Instruct`: Kiến trúc từ Alibaba, mạnh về đa ngôn ngữ và suy luận logic.
  - `VinaLlama-7B-chat`: Dựa trên nền tảng Llama 2, được cộng đồng AI Việt Nam fine-tune cực kỳ sâu sát cho văn phong Tiếng Việt.
  - `SeaLLM-7B-v2.5`: Tối ưu hóa đặc biệt cho các ngôn ngữ Đông Nam Á, hiệu suất sinh từ vựng Tiếng Việt cực kỳ tiết kiệm token.
- **Tránh sự cố về bản quyền (Gated Repo):** Việc tránh dùng nguyên bản Meta Llama-3 giúp hệ thống dễ dàng triển khai ở môi trường production mà không vướng rào cản bản quyền khắt khe.

## 2. Nội dung Huấn luyện (Training Content) là gì?

Quá trình huấn luyện sử dụng kỹ thuật **QLoRA (Quantized Low-Rank Adaptation)**, giúp dạy mô hình kiến thức mới mà không cần siêu máy tính.

- **Tập dữ liệu (Dataset):** `hungnm/vietnamese-medical-qa` (hơn 9000 cặp câu hỏi - đáp y tế).
- **Mục tiêu:** Chuyển đổi một mô hình ngôn ngữ chung chung thành một "Bác sĩ ảo ClinicPro". Mô hình học cách:
  - Trả lời đúng chuyên môn y khoa (dựa vào đáp án chuẩn).
  - Giữ thái độ chuyên nghiệp, từ chối trả lời những câu hỏi không thuộc phạm vi y tế.
  - Không bịa đặt thông tin (Hallucination) gây nguy hiểm cho tính mạng bệnh nhân.

## 3. Cách thức Kiểm thử (Testing Methodology)

Thay vì chỉ dùng điểm BLEU (so khớp mặt chữ) - vốn đã lỗi thời đối với Generative AI, hệ thống áp dụng chiến lược **Kiểm thử Đa Chiều (Multi-metric)**:

1. **Tốc độ phản hồi (Tokens per second):** Đo lường trải nghiệm thực tế. Mô hình nào chạy nhanh hơn trên cùng một phần cứng sẽ được ưu tiên cho ứng dụng di động.
2. **N-gram Overlap (BLEU & ROUGE):** 
   - Đo lường xem AI có sinh ra các từ khóa y khoa chính xác giống với bác sĩ thật hay không (ví dụ: dùng đúng cụm từ "Paracetamol", "huyết áp tâm thu").
3. **Semantic Similarity (BERTScore):** 
   - Đánh giá khả năng hiểu ý nghĩa. Mặc dù AI dùng cách hành văn khác bác sĩ, nhưng nếu lời khuyên y tế là tương đương, điểm BERTScore vẫn sẽ rất cao.
4. **LLM-as-a-Judge:** 
   - Dùng các mô hình tiên tiến nhất (GPT-4 / Claude) đóng vai trò giám khảo độc lập, đọc từng câu trả lời của 3 mô hình và chấm điểm dựa trên "Độ an toàn y khoa" và "Sự hữu ích".

## 4. Tính Công bằng (Fairness) trong Huấn luyện được Đảm bảo Thế nào?

Để báo cáo so sánh mang tính học thuật cao và không thiên vị, tính công bằng được thiết lập chặt chẽ:

- **100% Đồng nhất Siêu tham số (Hyperparameters):** Cả 3 mô hình đều được train trên cùng 1 con chip GPU H100, cùng cấu hình (Batch size = 4, Gradient Accumulation = 4, Epochs = 3, Learning Rate = 2e-4, Cosine Scheduler).
- **Random Seed Cố định (Seed=42):** Quá trình bốc ngẫu nhiên 10% dữ liệu để làm tập Validation trong lúc train được khóa cứng bằng `seed=42`. Nghĩa là cả 3 mô hình đều "nhìn thấy" đúng 940 câu Valid y hệt nhau, không có mô hình nào bị dính phải đề bài khó hơn.
- **Tập Test Hoàn Toàn Độc Lập:** Để tránh tình trạng "học vẹt", 100 câu hỏi dùng cho khâu Testing cuối cùng sẽ được trích xuất từ một bộ dữ liệu hoàn toàn khác trên HuggingFace. Không một mô hình nào được tiếp xúc với 100 câu hỏi này trong quá trình train. Điều này giúp kiểm tra khả năng "suy luận thực sự" của AI.
