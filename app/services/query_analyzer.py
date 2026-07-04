import json
import logging
import re
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from app.config import settings

logger = logging.getLogger(__name__)

class QueryAnalyzerService:
    """
    Dịch vụ hợp nhất (Unified) để Viết lại câu hỏi, Phân loại Intent và Trích xuất tham số 
    chỉ trong 1 lần gọi LLM duy nhất (One-Shot JSON), giúp giảm thiểu độ trễ (TTFT).
    """
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.0,
            format="json",
        )

    def analyze(self, query: str, chat_history: list) -> dict:
        dialogue = ""
        if chat_history:
            for msg in chat_history[-6:]:
                role = "User" if isinstance(msg, HumanMessage) else "AI"
                dialogue += f"{role}: {msg.content}\n"
        dialogue += f"User: {query}\n"

        today = datetime.now().strftime("%Y-%m-%d")

        system_prompt = f"""Bạn là bộ phân tích truy vấn AI. Nhiệm vụ của bạn là đọc hội thoại và xuất ra 1 JSON duy nhất.
Hôm nay là {today}.

Các Intent hợp lệ:
1. EMERGENCY: Khẩn cấp, nguy hiểm tính mạng.
2. BOOKING: Yêu cầu đặt lịch khám, hẹn ngày giờ, xem lịch trống.
3. CLINIC_SYMPTOM: Hỏi phòng khám có khoa nào khám bệnh abc.
4. DOCTOR_INFO: Hỏi thông tin về bác sĩ, chuyên khoa.
5. CLINIC_INFO: Hỏi thông tin phòng khám, giá tiền, giờ làm việc.
6. MEDICAL_QA: Xin tư vấn y khoa, thuốc men, bệnh lý.
7. GENERAL: Chào hỏi thông thường, CÂU HỎI NGOÀI LỀ, KHÔNG LIÊN QUAN ĐẾN Y TẾ HOẶC PHÒNG KHÁM, KHÔNG RÕ NGHĨA.

Yêu cầu JSON có cấu trúc sau:
{{
    "rewritten_query": "Câu hỏi viết lại đầy đủ ngữ cảnh (nếu câu gốc bị thiếu chủ ngữ/vị ngữ, nếu đã rõ thì giữ nguyên câu gốc)",
    "intent": "MỘT_TRONG_7_INTENT",
    "parameters": {{
        "doctor_name": "Tên bác sĩ (nếu có)",
        "expertise_name": "Tên chuyên khoa (nếu có)",
        "service_name": "Tên dịch vụ (nếu có)",
        "target_type": "DOCTOR hoặc SERVICE (dành cho BOOKING)",
        "date": "Ngày hẹn YYYY-MM-DD (dành cho BOOKING)",
        "time_slot": "Giờ hẹn (dành cho BOOKING)",
        "symptoms": "Triệu chứng (dành cho BOOKING)"
    }}
}}

Chỉ xuất 1 khối JSON hợp lệ. Không giải thích."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Đoạn hội thoại:\n{dialogue}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = (response.content or "").strip()
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = {}
                    
            return {
                "rewritten_query": data.get("rewritten_query", query),
                "intent": data.get("intent", "GENERAL"),
                "parameters": data.get("parameters", {})
            }
        except Exception as e:
            logger.error(f"Unified Analyzer Error: {e}")
            return {
                "rewritten_query": query,
                "intent": "GENERAL",
                "parameters": {}
            }
