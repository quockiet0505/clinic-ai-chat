# 🔌 Thiết kế API (REST + WebSocket)

Microservice cung cấp 2 giao thức giao tiếp: WebSocket (cho trải nghiệm chat realtime, gõ từng chữ) và REST (lấy lịch sử, feedback).

## 1. WebSocket Endpoint (Chat Streaming)
**Endpoint:** `ws://localhost:8000/ws/chat/{session_id}`

**Luồng giao tiếp:**
- **Client gửi:**
  ```json
  {
    "action": "send_message",
    "content": "Tôi bị đau đầu và buồn nôn thì khám khoa nào?",
    "patient_id": 123
  }
  ```
- **Server trả về (Streaming từng token):**
  ```json
  {"type": "chunk", "content": "Dựa"}
  {"type": "chunk", "content": " vào"}
  {"type": "chunk", "content": " triệu chứng..."}
  {"type": "tool_call", "name": "get_specialty", "status": "searching"}
  {"type": "done", "content": ""}
  ```

## 2. REST Endpoints (Quản lý lịch sử)
### Lấy lịch sử đoạn chat
- **GET** `/api/v1/chat/sessions/{session_id}/messages`
- **Response:**
  ```json
  {
    "data": [
      {"role": "user", "content": "Hello", "timestamp": "2026-06-21T10:00:00Z"},
      {"role": "assistant", "content": "Chào bạn, tôi có thể giúp gì?", "timestamp": "2026-06-21T10:00:05Z"}
    ]
  }
  ```

### Gửi Feedback (Đánh giá câu trả lời của Bot)
- **POST** `/api/v1/chat/feedback`
- **Body:**
  ```json
  {
    "message_id": 456,
    "rating": "thumbs_down",
    "reason": "Trả lời sai thông tin phòng khám"
  }
  ```
