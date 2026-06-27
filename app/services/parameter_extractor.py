import json
import logging
import re
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from app.config import settings

logger = logging.getLogger(__name__)

class ParameterExtractorService:
    """
    Sử dụng LLM ở chế độ JSON Mode để trích xuất các tham số tất định.
    Tránh hiện tượng LLM luyên thuyên khi gọi Tool.
    """
    
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.0,
            format="json", # Ép cứng output ra JSON
        )

    def _parse_json(self, content: str) -> dict:
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    pass
        return {}

    def extract_clinic_params(self, query: str) -> dict:
        """Trích xuất doctor_name, expertise_name từ câu hỏi tra cứu"""
        system_prompt = """Trích xuất thông tin từ câu hỏi.
Trả về JSON đúng chuẩn với các key sau (nếu không có từ khóa nào thì để chuỗi rỗng ""):
- "doctor_name": Tên bác sĩ người dùng muốn tìm.
- "expertise_name": Tên chuyên khoa người dùng muốn tìm (ví dụ: "Tai Mũi Họng", "Răng Hàm Mặt", "Mắt").
- "service_name": Tên dịch vụ hoặc gói khám.

Chỉ trả về JSON, không giải thích gì thêm."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        
        try:
            response = self.llm.invoke(messages)
            data = self._parse_json(response.content or "")
            return {
                "doctor_name": data.get("doctor_name", ""),
                "expertise_name": data.get("expertise_name", ""),
                "service_name": data.get("service_name", ""),
            }
        except Exception as e:
            logger.error(f"Extractor error: {e}")
            return {"doctor_name": "", "expertise_name": "", "service_name": ""}

    def extract_booking_state(self, chat_history: list, current_query: str) -> dict:
        """Trích xuất toàn bộ trạng thái form đặt lịch từ lịch sử trò chuyện"""
        dialogue = ""
        if chat_history:
            # Chỉ lấy 6 turn gần nhất để tránh nhiễu
            for msg in chat_history[-6:]:
                if isinstance(msg, HumanMessage):
                    dialogue += f"User: {msg.content}\n"
                else:
                    dialogue += f"AI: {msg.content}\n"
        dialogue += f"User: {current_query}\n"

        today = datetime.now().strftime("%Y-%m-%d")
        
        system_prompt = f"""Đọc đoạn hội thoại và trích xuất thông tin Đặt Lịch vào định dạng JSON.
Hôm nay là {today}. Nếu người dùng nói "ngày mai", hãy tự cộng ngày.
Yêu cầu JSON bắt buộc phải có đúng 5 keys sau (nếu chưa rõ thông tin thì để chuỗi rỗng ""):
- "target_type": Loại đối tượng khám (chỉ chọn 1 trong 3 giá trị: "DOCTOR", "EXPERTISE", "SERVICE", hoặc để rỗng).
- "target_name": Tên của Bác sĩ / Chuyên khoa / Dịch vụ đó (VD: "Lê Tuấn", "Răng Hàm Mặt").
- "date": Ngày hẹn khám (định dạng YYYY-MM-DD).
- "time_slot": Khung giờ khám (định dạng HH:mm, ví dụ: "08:30").
- "symptoms": Triệu chứng bệnh hoặc lý do khám.

Chỉ trả về 1 khối JSON duy nhất, không kèm text."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Đoạn hội thoại:\n{dialogue}")
        ]
        
        try:
            response = self.llm.invoke(messages)
            data = self._parse_json(response.content or "")
            return {
                "target_type": data.get("target_type", ""),
                "target_name": data.get("target_name", ""),
                "date": data.get("date", ""),
                "time_slot": data.get("time_slot", ""),
                "symptoms": data.get("symptoms", ""),
            }
        except Exception as e:
            logger.error(f"Booking extractor error: {e}")
            return {"target_type": "", "target_name": "", "date": "", "time_slot": "", "symptoms": ""}
