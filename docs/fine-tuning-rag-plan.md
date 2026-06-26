# Kế Hoạch Triển Khai AI: Semantic Routing + RAG + Fine-Tuning

Tài liệu này vạch ra lộ trình nâng cấp hệ thống Clinic AI Chat theo kiến trúc Agentic Workflow, kết hợp việc tìm kiếm thông tin động (RAG) và trả lời chuyên sâu y khoa (Fine-tuned LLM).

## 1. Tổng quan Kiến Trúc Đề Xuất

```text
                   User Request
                        │
            [ Semantic Router / Intent Classifier ]
           (Phân loại ý định của câu hỏi)
                        │
      ┌─────────────────┴─────────────────┐
      │                                   │
[ Ý định: Hỏi Phòng Khám ]        [ Ý định: Hỏi Bệnh Học ]
(Giá, Giờ khám, Đặt lịch)         (Triệu chứng, Đau đầu, Thuốc)
      │                                   │
[ RAG + Tool Calling ]             [ Fine-Tuned Llama / Qwen ]
(Tìm kiếm Vector DB, gọi API)      (Suy luận dựa trên y khoa)
      │                                   │
      └─────────────────┬─────────────────┘
                        │
                 [ Final Answer ]
           (Câu trả lời trả về cho User)
```

## 2. Kế Hoạch Triển Khai

### Giai đoạn 1: Xây dựng Semantic Router
- Sử dụng thư viện `semantic-router` (Python) hoặc dùng LLM prompt để phân loại câu hỏi thành 2 nhóm chính: `CLINIC_INFO` và `MEDICAL_ADVICE`.
- Code này sẽ nằm ở file `services/llm_service.py`, đóng vai trò như một người điều phối giao thông.

### Giai đoạn 2: Xây dựng RAG (Vector Database) cho Nhánh Phòng Khám
- Chuyển các thông tin tĩnh của phòng khám (Chính sách, Bảng giá, Quy định) thành file PDF/TXT.
- Dùng **ChromaDB** hoặc **FAISS** để nhúng (embed) các tài liệu này.
- Kết hợp với các API lấy danh sách bác sĩ, lịch trống (Langchain Tools) đã có sẵn.

### Giai đoạn 3: Fine-Tuning Nhánh Y Tế (Train Text)
- Huấn luyện một model riêng để chuyên xử lý các câu hỏi khám bệnh.
- Tích hợp model này vào Ollama để phục vụ nhánh `MEDICAL_ADVICE`.

---

## 3. Hướng Dẫn Tự Train (Fine-Tune) Model LLM

Việc "Train Text" (Fine-tuning) cho LLM hiện nay không cần phải train từ con số 0. Chúng ta sẽ sử dụng kỹ thuật **PEFT (Parameter-Efficient Fine-Tuning)**, cụ thể là **QLoRA** để tinh chỉnh một mô hình mã nguồn mở (ví dụ: `Qwen2.5-7B` hoặc `Llama-3-8B`) cho rẻ và nhanh.

### Bước 3.1: Chuẩn bị Dữ liệu (Dataset)
- Bạn tải tập dữ liệu `vietnamese-medical-qa` từ Hugging Face.
- Chuyển dữ liệu về định dạng JSON/JSONL chuẩn của Instruction Tuning:
```json
[
  {
    "instruction": "Đóng vai một bác sĩ tư vấn y tế.",
    "input": "Tôi hay bị đau đầu dữ dội nửa bên trái, thỉnh thoảng buồn nôn. Cho hỏi tôi bị gì?",
    "output": "Chào bạn, với các triệu chứng đau đầu dữ dội nửa đầu kèm buồn nôn, rất có thể bạn đang mắc hội chứng Migraine (đau nửa đầu)..."
  }
]
```

### Bước 3.2: Công cụ Training (Khuyên dùng: Unsloth)
Cách dễ nhất và nhanh nhất để train model hiện nay là dùng thư viện **Unsloth**. Unsloth giúp tăng tốc độ train lên gấp 2-5 lần và giảm 70% VRAM (chỉ cần GPU khoảng 16GB VRAM là train được model 8B).

1. Bạn có thể thuê máy ảo trên **RunPod** (GPU RTX 4090 24GB giá khoảng 0.4$/giờ) hoặc dùng Google Colab Pro.
2. Viết script Python dùng `Unsloth` để load model gốc (ví dụ `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`).
3. Load Dataset ở bước 3.1.
4. Chạy hàm Trainer (của thư viện `trl`).

### Bước 3.3: Xuất file GGUF
Sau khi train xong, dùng Unsloth xuất thẳng model ra định dạng `.gguf`. Bạn copy file này về máy tính cá nhân, đưa vào **Ollama** và chạy như bình thường.

---

## 4. Train Model Mất Bao Lâu?

Thời gian huấn luyện phụ thuộc vào 2 yếu tố: **Số lượng dữ liệu** và **Sức mạnh Card màn hình (GPU)**.

**Giả sử bạn có:**
- Dataset: 9,000 cặp câu hỏi y tế (tương đương khoảng 3-5 MB text).
- Model: Llama-3 (8B) hoặc Qwen2.5 (7B).
- Thuật toán: QLoRA (thông qua Unsloth).
- Epochs: 3 vòng (lặp lại việc học 3 lần).

**Ước tính thời gian:**
1. **Dùng GPU RTX 3090 / 4090 (24GB VRAM):** Mất khoảng **2 đến 4 tiếng**.
2. **Dùng GPU T4 (16GB VRAM - Google Colab miễn phí):** Mất khoảng **8 đến 12 tiếng** (có thể bị ngắt giữa chừng vì quá giờ của Google).
3. **Dùng GPU A100 (80GB VRAM - Thuê khoảng 1.5$/giờ):** Mất khoảng **30 - 45 phút**.

**Kết luận:** 
Việc train không quá lâu nếu dữ liệu chỉ khoảng 10,000 câu. Chi phí thuê máy trên RunPod để vọc vạch train model này chỉ tốn của bạn khoảng **$2 - $5 (50k - 120k VNĐ)** cho một lần thử nghiệm. Bạn hoàn toàn có thể tự làm nghiệm thu dự án!
