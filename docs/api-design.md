# Thiết kế API (REST + WebSocket)

## 1. REST API

### 1.1. Khởi tạo phiên Chat (Start Chat Session)
- **URL:** `/api/v1/chat/sessions`
- **Method:** `POST`
- **Auth:** Bearer Token (nếu đã đăng nhập) / Tùy chọn (Guest)
- **Request Body:**
  ```json
  {
    "patient_id": "optional_id",
    "device_id": "uuid-for-guest"
  }
  ```
- **Response:**
  ```json
  {
    "session_id": "sess-12345",
    "status": "active",
    "created_at": "2024-01-01T10:00:00Z"
  }
  ```

### 1.2. Lấy lịch sử chat (Get Chat History)
- **URL:** `/api/v1/chat/sessions/:session_id/messages`
- **Method:** `GET`
- **Response:**
  ```json
  {
    "messages": [
      {
        "id": "msg-1",
        "sender": "user",
        "content": "Tôi muốn đặt lịch khám",
        "created_at": "2024-01-01T10:01:00Z"
      },
      {
        "id": "msg-2",
        "sender": "ai",
        "content": "Dạ, bạn muốn khám chuyên khoa nào ạ?",
        "created_at": "2024-01-01T10:01:05Z"
      }
    ]
  }
  ```

## 2. WebSocket (Real-time Streaming)

### 2.1. Kết nối (Connection)
- **Endpoint:** `ws://localhost:PORT/ws/chat/:session_id`

### 2.2. Gửi tin nhắn từ Client (Client -> Server)
- **Format (JSON):**
  ```json
  {
    "type": "USER_MESSAGE",
    "content": "Tôi bị đau đầu từ hôm qua"
  }
  ```

### 2.3. Nhận phản hồi Streaming (Server -> Client)
Server sẽ trả về nhiều event liên tục theo từng token/chunk của LLM.
- **Format (JSON):**
  ```json
  {
    "type": "AI_STREAM_CHUNK",
    "content": "Dạ, "
  }
  ```
  ```json
  {
    "type": "AI_STREAM_CHUNK",
    "content": "với "
  }
  ```
  ```json
  {
    "type": "AI_STREAM_CHUNK",
    "content": "triệu chứng "
  }
  ```

### 2.4. Kết thúc Streaming (Server -> Client)
- **Format (JSON):**
  ```json
  {
    "type": "AI_STREAM_END",
    "full_message": "Dạ, với triệu chứng đau đầu...",
    "action_required": null
  }
  ```

### 2.5. Yêu cầu Client thực hiện hành động (UI Tool Calling)
Nếu LLM xác định cần hiển thị một Card (như danh sách bác sĩ, form đặt lịch), Server sẽ gửi:
- **Format (JSON):**
  ```json
  {
    "type": "UI_ACTION",
    "action": "SHOW_DOCTOR_LIST",
    "payload": {
      "doctors": [
        {"id": "doc1", "name": "Nguyễn Văn A", "specialty": "Nội thần kinh"}
      ]
    }
  }
  ```
