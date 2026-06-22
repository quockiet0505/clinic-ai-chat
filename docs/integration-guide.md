# Hướng dẫn Tích hợp

## 1. Tích hợp Frontend (Patient Web & Mobile)

### Patient Web
- File: `patient-web/src/features/chatbot/api/chatbotApi.ts`
- Config: `VITE_AI_CHAT_URL` trong `.env`
- Endpoint: `POST {AI_URL}/api/v1/chat/send`
- **Đã đăng nhập:** gửi kèm `access_token` từ `localStorage.token` để AI có thể đặt lịch hộ

```env
VITE_AI_CHAT_URL=http://localhost:8000
```

### Mobile App (Flutter)
- File: `mobile-app/lib/services/ai_chat_service.dart`
- Provider: `mobile-app/lib/providers/chat_provider.dart`
- Config: `AI_CHAT_URL` trong `.env`
- **Đã đăng nhập:** service tự đọc `jwt_token` từ SecureStorage, gửi `access_token`

```env
# Android Emulator
AI_CHAT_URL=http://10.0.2.2:8000
```

### Request / Response

```json
// Request (đã login — có thể đặt lịch qua AI)
POST /api/v1/chat/send
{
  "message": "Tôi đau bụng, đặt lịch thứ 5 được không?",
  "session_id": "web-uuid-hoac-mobile-id",
  "access_token": "eyJhbGciOiJIUzI1NiIs..."
}

// Response
{
  "reply": "...",
  "session_id": "web-uuid-hoac-mobile-id"
}
```

## 2. Tích hợp Backend (Spring Boot)

AI Chat gọi các API sau từ `clinic-backend`:

| Mục đích | API |
|----------|-----|
| Đăng ký guest | `POST /api/v1/auth/patient/register` |
| Danh sách chuyên khoa | `GET /api/v1/expertise/all` |
| Danh sách bác sĩ | `GET /api/v1/staffs/filter?staffType=DOCTOR` |
| Danh sách dịch vụ | `GET /api/v1/services/all` |
| Giờ trống | `GET /api/v1/appointments/slots?date=&doctorId=&expertiseId=&serviceId=` |
| Đặt lịch (JWT) | `POST /api/v1/appointments` + `Authorization: Bearer` |
| Thông tin phòng khám | `GET /api/v1/settings` |

Cấu hình `clinic-ai-chat/.env`:

```env
CLINIC_BACKEND_URL=http://localhost:8080
```

## 3. LangChain Tools

| Tool | Mô tả |
|------|-------|
| `get_specialties_tool` | Lấy chuyên khoa |
| `get_doctors_tool` | Lấy bác sĩ (lọc theo chuyên khoa) |
| `get_services_tool` | Lấy dịch vụ |
| `get_clinic_info_tool` | Hotline, địa chỉ, giờ làm việc |
| `suggest_expertise_tool` | Gợi ý khoa từ triệu chứng (RAG + danh sách khoa) |
| `get_available_slots_tool` | Giờ trống theo bác sĩ / chuyên khoa / dịch vụ |
| `book_appointment_tool` | Tạo lịch PENDING (cần JWT — inject từ request) |
| `register_patient_tool` | Đăng ký tài khoản guest |

## 4. Luồng AI đặt lịch

1. `suggest_expertise_tool(symptoms)` → gợi ý khoa tham khảo
2. `get_available_slots_tool(date, expertise_name=...)` → khung giờ
3. Khách xác nhận → `book_appointment_tool` với `suggested_expertise_name` + `expertise_name`
4. Chưa login → AI hướng dẫn đăng nhập hoặc đặt thủ công trên web/app

## 5. Xử lý lỗi

- Frontend hiển thị thông báo thân thiện khi AI service không chạy.
- AI service trả `503` khi Ollama không phản hồi.
- Tools trả text lỗi cho LLM khi backend timeout.
