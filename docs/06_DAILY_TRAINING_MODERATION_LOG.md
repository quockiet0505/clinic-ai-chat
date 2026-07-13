# NHẬT KÝ HOẠT ĐỘNG: HUẤN LUYỆN MÔ HÌNH V2 & KIỂM DUYỆT BÌNH LUẬN (13/07/2026)

Tài liệu này ghi lại chi tiết các đầu việc đã thực hiện trong ngày, kiến trúc hệ thống hiện tại và định hướng các công việc tiếp theo để chuẩn bị báo cáo đồ án.

---

## 1. Kết Quả Huấn Luyện Mô Hình AI (Phiên Bản V2)

### Lý do thực hiện huấn luyện V2:
*   Khắc phục hiện tượng rò rỉ dữ liệu (Data Leakage) của phiên bản V1.
*   Cơ cấu lại tỷ lệ chia dữ liệu chuẩn mực khoa học: **80% Train / 10% Validation / 10% Test** (thay vì tỷ lệ cũ là 90/10).

### Kết quả Loss thấp nhất (tại Step 690 / 702):
1.  **SeaLLM v2.5 (7B):** `1.1142` (Mô hình hội tụ nhanh nhất, chỉ số lỗi thấp nhất).
2.  **Qwen 2.5 (7B):** `1.2210` (Hội tụ tốt, bám rất sát SeaLLM).
3.  **VinaLlama (7B):** `1.4552` (Chỉ số lỗi cao nhất trong ba mô hình nhưng vẫn đạt mức ổn định).

### Backup & Đồng bộ hóa lên Hugging Face:
*   Viết lại và thực thi thành công script `train/push_all_to_hf.py` trên Modal.
*   Sao lưu toàn bộ kết quả lên tài khoản Hugging Face (`quockietdev/`):
    *   **Thư mục gốc (`/`):** Chứa các file Merged Model (`model.safetensors`, `config.json`, `tokenizer.json`...) để sau này gọi trực tiếp qua thư viện `transformers` không bị lỗi.
    *   **Thư mục `/checkpoints`:** Lưu trữ toàn bộ lịch sử checkpoint (bao gồm file logs `trainer_state.json`).
    *   **Thư mục `/lora_adapter`:** Lưu trữ các file cấu hình LoRA thích ứng.

---

## 2. Hệ Thống Kiểm Duyệt Bình Luận (AI Moderation)

### Những gì đã làm được:
1.  **Cấu trúc dữ liệu Database (Backend):** Bảng `Feedback` và `DoctorReview` đã có cột `aiStatus` (chứa 3 trạng thái: `PENDING`, `APPROVED`, `REJECTED`) và `aiModerationNote` (lưu lý do duyệt/chặn).
2.  **Logic xử lý ngầm (Backend):** Spring Boot bắt sự kiện gửi bình luận, lưu trạng thái mặc định là `PENDING` (chưa hiển thị công khai) và gọi bất đồng bộ (`@Async`) sang AI Server thông qua lớp `AiModerationService.java`.
3.  **Hạ tầng AI Server (FastAPI):** Có sẵn endpoint `POST /api/v1/moderation/check` thiết lập bộ lọc 2 lớp cực kỳ chặt chẽ:
    *   *Lớp 1 (Quick Filter - Lọc Heuristics không tốn GPU):*
        *   **Chặn rating thấp:** Tự động từ chối (`approved = false`) đối với mọi đánh giá **1 và 2 sao** để bảo vệ uy tín phòng khám.
        *   **Chặn từ cấm mở rộng:** Quét từ điển cấm tuyệt đối bao gồm từ tục tĩu thuần túy (`địt`, `đụ`, `cặc`, `lồn`, `vcl`...) và các từ khóa phá hoại, đe dọa do người dùng yêu cầu (`lừa đảo`, `scam`, `vô dụng`, `khởi kiện`, `tống tiền`, `báo cáo`, `tố cáo sai`...).
        *   **Chặn chửi thề cách điệu:** Dùng Regex bắt các ký tự viết chèn khoảng trắng/dấu chấm ở giữa (VD: `đ.ị.t`, `đ_é_o`, `v.c.l`).
        *   **Chặn quảng cáo spam:** Quét link liên kết rút gọn (`shopee.vn`, `t.me/`, `zalo.me/`) và SĐT Việt Nam (bỏ qua khoảng trắng/dấu chấm).
    *   *Lớp 2 (LLM Contextual - Phân tích ngữ cảnh):*
        *   Các đánh giá từ **3 đến 5 sao** lọt qua Lớp 1 sẽ được đưa vào LLM Qwen để đọc hiểu ngữ cảnh sâu. 
        *   Nếu là đánh giá **3 sao** nhưng góp ý lịch sự, văn minh (không dùng từ cấm ở Lớp 1) -> AI cho phép duyệt (`approved = true`) để hiển thị khách quan trên trang chi tiết dịch vụ/bác sĩ.
        *   Tuy nhiên, Backend Java luôn truy vấn `rating >= 4` để hiển thị trên Landing Page nhằm **ưu tiên quảng bá các đánh giá 4-5 sao xuất sắc nhất**.
4.  **Giao diện Bệnh nhân (Patient Web):** Component `MyReviews.tsx` đã hoàn tất, cho phép hiển thị các bình luận cá nhân, chỉnh sửa trong 24 giờ và hiển thị phản hồi từ ban quản trị phòng khám.
5.  **Tập dữ liệu kiểm thử (Ground Truth Dataset):** Tạo thành công file `data/moderation_test_cases.json` chứa đúng **100 câu test tiếng Việt** cực khó bao gồm cả những câu dài và câu ngắn thực tế. Chi tiết phân loại như sau:

    *   **Thống kê chi tiết theo 12 Kịch Bản (Scenarios) để thử thách AI:**
        *   *Chuẩn mực - Tích cực (Approved):* **25 câu** (Bình luận khen ngợi thông thường).
        *   *Góp ý chân thành - 3 sao nhưng lịch sự (Approved):* **5 câu** (Chê phòng khám nóng, chờ lâu, giá đắt nhưng nói năng lịch sự, văn minh).
        *   *Bẫy Từ khóa - Chứa từ nhạy cảm nhưng nghĩa tốt (Approved):* **5 câu** (Câu có chứa từ "lừa đảo", "tệ" nhưng là câu phủ định: "Không hề có chuyện lừa đảo...").
        *   *Căm phẫn - Swearing/Insults (Rejected):* **15 câu** (Bình luận thô tục, chửi bới bác sĩ trực tiếp).
        *   *Bẫy Spam quảng cáo (Rejected):* **15 câu** (Chứa số điện thoại mua thuốc, link Shopee, link Telegram kiếm tiền...).
        *   *Bẫy Phá rối - 5 sao kèm Chửi thề (Rejected):* **5 câu** (Đánh giá 5 sao nhưng nội dung vô văn hóa để lừa AI).
        *   *Ngoại lệ - Không liên quan y tế (Rejected):* **5 câu** (Bàn chuyện thời tiết, giá vàng, phim ảnh rạp).
        *   *Ngoại lệ - Gõ chữ vô nghĩa (Rejected):* **5 câu** (Gõ phím bừa, spam icon dấu chấm...).
        *   *Kỳ thị / Phân biệt đối xử (Hate Speech) (Rejected):* **5 câu** (Kỳ thị vùng miền, giới tính, tuổi tác).
        *   *Đe dọa / Tống tiền / Phá hoại (Threats) (Rejected):* **5 câu** (Đe dọa đập phá phòng khám, bôi nhọ bác sĩ).
        *   *Bôi nhọ / Chơi xấu từ đối thủ (Competitor Defamation) (Rejected):* **5 câu** (Chê bai bôi nhọ và lôi kéo bệnh nhân qua cơ sở khác).
        *   *Tin đồn y tế thất thiệt / Ác ý (Misinformation) (Rejected):* **5 câu** (Lan truyền tin giả ác ý như dùng kim tiêm cũ, lấy nội tạng, bán thuốc giả...).
        *   *Tổng cộng:* **100 câu**.

    *   **Phân nhóm theo tính chất (Cảm xúc bình luận):**
        *   *Nhóm TỐT (Khen ngợi, tích cực - APPROVED):* **30 câu** (Gồm: 25 câu Chuẩn mực tích cực + 5 câu Khen có chứa từ khóa bẫy).
        *   *Nhóm TRUNG TÍNH (Chê lịch sự, góp ý xây dựng - APPROVED):* **5 câu** (Gồm: 5 câu Góp ý chân thành, tuy chê nhưng không vi phạm thuần phong mỹ tục nên vẫn được Duyệt).
        *   *Nhóm KHÔNG TỐT (Vi phạm quy định - REJECTED):* **65 câu** (Gồm: 15 câu Chửi bới + 15 câu Spam quảng cáo + 5 câu 5 sao phá rối + 5 câu lạc đề + 5 câu gõ vô nghĩa + 5 câu kỳ thị + 5 câu đe dọa + 5 câu đối thủ chơi xấu + 5 câu tin đồn ác ý).


### Định hướng kiểm thử tính năng Lọc bình luận:
*   Viết Script chạy kiểm thử tự động đọc file 100 câu trên, gửi liên tiếp lên API của AI Server và tổng hợp kết quả (Xuất ra các chỉ số Precision, Recall, Accuracy % và vẽ Ma trận nhầm lẫn - Confusion Matrix).

---

## 3. Các Phần Chưa Hoàn Thành (Kế Hoạch Cho Ngày Mai)

1.  **Chấm điểm Đánh giá (Evaluation):**
    *   Chạy script `modal run train/modal_evaluate.py` trên tập test độc lập `test_100_v2.json` để đo lường điểm số chính xác của 3 mô hình V2 (Qwen, SeaLLM, VinaLlama).
2.  **Lựa chọn & Triển khai Mô hình Tốt nhất:**
    *   So sánh điểm số test của 3 mô hình, lựa chọn con tốt nhất tích hợp vào Chatbot chính của phòng khám (`modal_clinic_app.py`).
3.  **Chạy Đánh giá Auto-Test 100 câu bình luận:**
    *   Khởi động FastAPI Server và mô hình LLM được chọn.
    *   Chạy script tự động quét 100 câu bình luận trong tập test và xuất báo cáo độ chính xác (Accuracy %) để phục vụ slide thuyết trình đồ án.
