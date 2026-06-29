# Kiến trúc Hệ thống Bot AI (Langchain & FastAPI)

## 1. Thành phần Cốt lõi
- **Framework:** FastAPI cho Server, Langchain cho luồng AI.
- **LLM:** Sử dụng Local Model (ví dụ: Qwen2.5 3B, Llama3.2 3B) thông qua Ollama.
- **Vector Database (RAG):** Sử dụng ChromaDB để chứa 9400 cặp câu hỏi y tế `hungnm/vietnamese-medical-qa`. 
  - *Embedding Model:* `nomic-embed-text`.
  - *Cross-encoder (Re-ranker):* `ms-marco-MiniLM-L-6-v2` để chấm điểm lại độ chính xác của câu trả lời Y khoa.

## 2. Hệ thống Tool Calling (10 Tools)
Bot đóng vai trò như một AI Agent có khả năng gọi các "Hàm" (Tools) để thao tác với Backend của phòng khám:
1. `get_specialties_tool`: Liệt kê chuyên khoa.
2. `get_doctors_tool`: Tìm kiếm bác sĩ.
3. `get_services_tool`: Xem bảng giá dịch vụ.
4. `get_clinic_info_tool`: Xem thông tin phòng khám.
5. `get_available_slots_tool`: Quét giờ trống của bác sĩ.
6. `suggest_expertise_tool`: AI gợi ý chuyên khoa dựa vào triệu chứng.
7. `book_appointment_tool`: Đặt lịch (Có check điều kiện chặn Chủ Nhật và phải đặt trước 24h).
8. `get_my_appointments_tool`: Xem lịch sử đặt lịch.
9. `cancel_appointment_tool`: Hủy lịch.
10. `register_patient_tool`: Đăng ký tài khoản mới.

## 3. Tương tác với Backend Java & Mobile App
- API `/api/v1/chat/send` của Python sẽ nhận tin nhắn và **JWT Token** từ App/Web.
- Token này được Python nhúng thẳng vào Header khi gọi sang các API của Spring Boot Backend, đảm bảo mọi thao tác đặt lịch/hủy lịch đều được xác thực đúng danh tính bệnh nhân.

*(Tài liệu này đã được gộp từ các file phân tích lẻ tẻ trước đây nhằm dễ theo dõi hơn).*
