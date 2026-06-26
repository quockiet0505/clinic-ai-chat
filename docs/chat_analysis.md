# Phân tích hệ thống AI Chat (Clinic AI)

Hệ thống Clinic AI Chat là một microservice độc lập (FastAPI) đóng vai trò trợ lý y tế ảo cho phòng khám ClinicPro. Nó sử dụng mô hình LLM Llama 3.2 3B (thông qua Ollama) kết hợp với công nghệ RAG (Retrieval-Augmented Generation) và Function Calling.

---

## 1. Kiến trúc tổng quan
- **Framework:** FastAPI
- **LLM Engine:** ChatOllama (Llama 3.2 3B)
- **Prompt & History:** Quản lý bối cảnh qua `LangChain` (`HumanMessage`, `AIMessage`, `SystemMessage`).
- **Tích hợp Backend:** Gọi API trực tiếp tới `clinic-backend` qua class `BackendClient`.

---

## 2. Luồng xử lý tin nhắn (Chat Flow)
Mỗi khi bệnh nhân gửi tin nhắn:
1. **Lấy lịch sử chat:** Hệ thống map `session_id` để lấy 20 tin nhắn gần nhất.
2. **RAG (Knowledge Retrieval):** Nội dung tin nhắn được so khớp với các file markdown trong thư mục `knowledge/` (như `faq.md`, `booking_guide.md`, `symptom_guide.md`...) để trích xuất ngữ cảnh.
3. **Gọi LLM:** LLM nhận tin nhắn, lịch sử và ngữ cảnh RAG.
4. **Kích hoạt Tool (Function Calling):** 
   - Nếu LLM nhận thấy cần dữ liệu thời gian thực (hỏi giờ trống, hỏi bác sĩ), nó sẽ kích hoạt Tools (xem mục 3).
   - Hệ thống thực thi hàm Python tương ứng, gọi API backend và trả kết quả về cho LLM.
5. **Phản hồi:** LLM tự tổng hợp câu trả lời cuối cùng và stream/trả thẳng về client.

---

## 3. Các công cụ (Tools) mà AI hỗ trợ
AI được cung cấp các function calling để giao tiếp với hệ thống:

| Tên Tool | Chức năng | Liên kết Backend API |
| Tên Tool | Chức năng | Liên kết Backend API |
|----------|-----------|----------------------|
| `get_specialties_tool` | Lấy danh sách chuyên khoa | `GET /expertise/all` |
| `get_doctors_tool` | Lấy danh sách bác sĩ (có thể lọc) | `GET /staffs/filter` hoặc `/staffs/doctors` |
| `get_services_tool` | Lấy danh sách dịch vụ (giá, loại) | `GET /services/all` |
| `get_clinic_info_tool` | Lấy thông tin hotline, địa chỉ | Không gọi API (trả fix) |
| `get_available_slots_tool`| Tra cứu giờ khám trống | `GET /appointments/slots` |
| `suggest_expertise_tool` | Gợi ý khoa từ mô tả triệu chứng | Dùng RAG (`symptom_guide.md`) |
| `book_appointment_tool` | Đặt lịch tự động | `POST /appointments` |
| `register_patient_tool` | Đăng ký người dùng mới | Trả hướng dẫn hoặc form link |
| `get_my_appointments_tool` | Xem danh sách lịch hẹn của bệnh nhân | `GET /appointments/my` |
| `cancel_appointment_tool` | Hủy lịch hẹn (trước 3 tiếng) | `PATCH /appointments/{id}/cancel` |

---

## 4. Chi tiết luồng đặt lịch bằng AI (AI Booking Flow)
Tính năng này hỗ trợ 4 chế độ (`booking_mode`) tương tự hệ thống backend, đảm bảo xử lý chặt chẽ các logic nghiệp vụ (gán bác sĩ, loại dịch vụ):

1. **Nhận dạng nhu cầu & Phân loại Mode:**
   - **DOCTOR:** Khách chọn cụ thể bác sĩ (AI truyền `mainDoctorId`, `expertiseId` tự gán theo bác sĩ).
   - **EXPERTISE:** Khách chọn khoa (AI truyền `expertiseId`, `mainDoctorId` có thể bỏ trống để backend tự động xếp bác sĩ).
   - **SERVICE:** Khách chọn dịch vụ xét nghiệm/chụp chiếu (AI truyền `serviceId`, bỏ qua chọn bác sĩ và chuyên khoa).
   - **DIRECT:** Khách chỉ cung cấp ngày giờ, hệ thống sẽ chờ nhân viên xác nhận. (Thường AI sẽ gợi ý và lái về EXPERTISE).
2. **AI phân tích triệu chứng (Tùy chọn):** Gọi `suggest_expertise_tool` để nhận gợi ý chuyên khoa và truyền vào `suggested_expertise_name`.
3. **Kiểm tra slot trống:** Gọi `get_available_slots_tool` truyền vào tương ứng `doctor_name`, `expertise_name` hoặc `service_name` để lấy lịch trống khớp với điều kiện.
4. **Hỏi xác nhận:** AI đưa ra danh sách giờ trống (VD: "Có giờ 08:30, 09:00... Bạn chọn giờ nào?").
5. **Thực hiện đặt lịch:** Gọi `book_appointment_tool` (cần `access_token` JWT). AI tự map các biến số thành payload chuẩn đẩy sang backend. Lịch tạo thành công có trạng thái PENDING.

## 5. Quản lý lịch hẹn (Xem / Hủy)
- **Xem lịch:** AI gọi `get_my_appointments_tool` qua token JWT để lấy các lịch sắp tới của bệnh nhân (trạng thái PENDING, CONFIRMED).
- **Hủy lịch:** Khi bệnh nhân yêu cầu hủy, AI phải kiểm tra lý do và xác nhận mã lịch. Nếu hợp lệ, gọi `cancel_appointment_tool` bắn PATCH request. Đảm bảo tuân thủ quy tắc nghiệp vụ: *Chỉ được hủy trước giờ khám ≥ 3 tiếng.*
