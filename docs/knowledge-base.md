# Knowledge Base — Hướng dẫn bảo trì FAQ cho AI Chat

Tài liệu này mô tả cách quản lý nội dung FAQ tĩnh (`knowledge/*.md`) dùng cho **Light RAG** trong microservice `clinic-ai-chat`.

Mỗi lần bổ sung hoặc sửa FAQ, **cập nhật file tương ứng** và ghi vào [Changelog](#changelog) ở cuối tài liệu.

---

## 1. Vai trò trong kiến trúc

| Nguồn | Dùng khi | Ví dụ |
|-------|----------|-------|
| `knowledge/*.md` | FAQ tĩnh, quy trình, gợi ý triệu chứng | Hủy lịch 3 tiếng, cách đăng ký, thanh toán QR |
| LangChain tools → backend | Dữ liệu **live**, thay đổi theo DB | Tên bác sĩ, giá dịch vụ, giờ trống, hotline admin cập nhật |
| `prompts/system.txt` | Quy tắc hành vi AI | Không chẩn đoán, bắt buộc gọi tool cho số liệu live |

Chi tiết kiến trúc: [architecture.md](architecture.md)

---

## 2. Cấu trúc thư mục `knowledge/`

**Luồng đặt lịch chi tiết (As-Is / To-Be, schema):** `clinic-backend/docs/business-flows.md` (repo backend).

| File | Nội dung | Gợi ý từ khóa |
|------|----------|---------------|
| `ai_booking_guide.md` | **Quy tắc cho AI** — suggest/book, JWT, suggested_expertise | đặt lịch AI, book_appointment_tool, access_token |
| `faq.md` | FAQ tổng hợp, chính sách, giới thiệu | hotline, giờ làm việc, hủy lịch, BHYT, bảo mật |
| `booking_guide.md` | Quy trình đặt lịch web/app/hotline | đặt lịch, walk-in, slot, 24 giờ, trạng thái lịch |
| `payment_guide.md` | Thanh toán, hóa đơn, hoàn tiền | tiền mặt, thẻ, Momo, VNPay, VAT |
| `account_guide.md` | Đăng ký, đăng nhập, quên MK | tài khoản, email, mật khẩu, khóa đặt lịch |
| `symptom_guide.md` | Gợi ý chuyên khoa (tham khảo) | đau đầu, ho sốt, tim mạch, da liễu |
| `medical_records_guide.md` | Hồ sơ, xét nghiệm, đơn thuốc, đánh giá | kết quả xét nghiệm, lịch sử khám, đánh giá bác sĩ |

Thêm file mới: đặt tên `snake_case.md`, load tự động qua `KnowledgeRetriever` (glob `*.md`).

---

## 3. Quy tắc viết nội dung

### 3.1. Heading `##` = một chunk RAG

Retriever tách file theo dòng `## Tiêu đề`. **Mỗi section nên tập trung một chủ đề** để câu hỏi match đúng chunk.

```markdown
# Tên file (intro — chunk "Tổng quan")

## Một câu hỏi hoặc một chủ đề
Nội dung trả lời ngắn gọn, đủ ý...

## Chủ đề khác
...
```

### 3.2. Plain text, không HTML

Viết markdown đơn giản. **Không** dùng `<ul>`, `<strong>` kiểu FAQPage web — RAG đọc plain text.

Dùng `-` hoặc số thứ tự cho danh sách. In đậm bằng `**text**`.

### 3.3. Từ khóa cho retrieval

Mỗi section nên chứa từ khóa người dùng hay hỏi (tiếng Việt có dấu). Ví dụ section hủy lịch nên có: *hủy lịch*, *thay đổi lịch*, *3 tiếng*, *miễn phí*.

Retriever dùng **keyword overlap** (không embedding) — section càng rõ từ khóa càng dễ được chọn.

### 3.4. Static vs live

| Ghi trong FAQ | Ghi chú |
|---------------|---------|
| Quy trình, chính sách ổn định | OK — ví dụ hủy trước 3 tiếng (backend enforce) |
| Hotline, địa chỉ mặc định | Ghi giá trị tham khảo + ghi chú admin có thể đổi |
| Giá dịch vụ, tên bác sĩ, giờ trống | **Không** ghi số cố định — AI phải gọi tool |
| Giờ làm việc từ admin settings | FAQ ghi mặc định; ưu tiên `get_clinic_info_tool` khi hỏi chính xác |

### 3.5. Đồng bộ với frontend

Khi sửa FAQ trên AI, nên kiểm tra đồng bộ với:

- `patient-web/src/features/home/pages/FAQPage.tsx`
- `mobile-app/lib/screens/profile/faq_screen.dart`
- `patient-web/src/features/contact/pages/ContactPage.tsx`

**Quy tắc ưu tiên:** Backend logic > FAQ AI > text marketing trên UI.  
Ví dụ: backend hủy lịch **3 tiếng** — FAQ AI dùng 3 tiếng; nếu FAQPage web vẫn ghi 2 giờ thì nên sửa web sau.

---

## 4. Cấu hình RAG

File `.env`:

```env
RAG_ENABLED=true
RAG_TOP_K=3
RAG_MIN_SCORE=0.15
```

| Biến | Ý nghĩa |
|------|---------|
| `RAG_TOP_K` | Số chunk tối đa inject vào prompt |
| `RAG_MIN_SCORE` | Ngưỡng overlap tối thiểu (0–1). Tăng nếu AI hay lấy nhầm chunk |

Sau khi sửa `knowledge/*.md`: **restart uvicorn** (hoặc `--reload` tự load lại khi file đổi).

---

## 5. Kiểm tra sau khi cập nhật

### 5.1. Đếm chunk

```bash
cd clinic-ai-chat
python -c "from app.rag.retriever import KnowledgeRetriever; r=KnowledgeRetriever(); print(len(r.chunks), 'chunks')"
```

### 5.2. Test retrieve thủ công

```bash
python -c "
from app.rag.retriever import KnowledgeRetriever
r = KnowledgeRetriever()
for q in ['hủy lịch bao lâu', 'thanh toán momo', 'đau đầu khám gì']:
    print('---', q)
    print(r.retrieve(q)[:300] or '(empty)')
"
```

### 5.3. Test tích hợp (cần Ollama + backend)

```bash
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hủy lịch trước bao lâu?\", \"session_id\": \"test\"}"
```

Câu trả lời nên nhắc **3 tiếng**, không bịa số khác.

---

## 6. Quy trình cập nhật (checklist)

1. Xác định chủ đề thuộc file nào (bảng mục 2).
2. Thêm/sửa section `## ...` — một chủ đề một section.
3. Tránh ghi giá/bác sĩ cố định; tham chiếu tra cứu hệ thống nếu cần.
4. Restart / reload AI service.
5. Chạy test retrieve (mục 5).
6. (Tuỳ chọn) Đồng bộ FAQPage mobile/web.
7. Ghi dòng vào **Changelog** bên dưới.

---

## 7. Roadmap mở rộng

- Vector RAG (embedding) khi số lượng tài liệu > ~100 chunk
- Script sync FAQ từ admin CMS → `knowledge/`
- i18n (en/vi) nếu cần đa ngôn ngữ

---

## Changelog

| Ngày | Người cập nhật | Thay đổi |
|------|----------------|----------|
| 2026-06-22 | — | AI book qua JWT: `book_appointment_tool`, `suggested_expertise_id`; web/mobile gửi `access_token`; cập nhật integration-guide |
| 2026-06-22 | — | Thêm `ai_booking_guide.md`; sửa `booking_guide.md`, `faq.md`, `system.txt` theo thực tế backend (24h/3h, slot theo BS, AI không tự book). Migration: `add_appointment_booking_fields.sql` |
| 2026-06-22 | — | Đồng bộ booking_guide với 4 mode đặt lịch + luồng dịch vụ Lab/Imaging. Tham chiếu backend business-flows.md |
| 2026-06-22 | — | Khởi tạo bộ knowledge 6 file: faq, booking, payment, account, symptom, medical_records. Chuẩn hóa hủy lịch 3 tiếng, đặt online 24h, hotline 1900 2115. |

*Thêm dòng mới lên đầu bảng mỗi lần cập nhật FAQ.*
