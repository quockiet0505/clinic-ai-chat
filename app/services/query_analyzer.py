import json
import logging
import re
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm import get_llm
from app.config import settings

logger = logging.getLogger(__name__)

class QueryAnalyzerService:
    """
    Dịch vụ hợp nhất (Unified) để Viết lại câu hỏi, Phân loại Intent và Trích xuất tham số 
    chỉ trong 1 lần gọi LLM duy nhất (One-Shot JSON), giúp giảm thiểu độ trễ (TTFT).
    """
    def __init__(self):
        self.llm = get_llm(
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
4. DOCTOR_INFO: Hỏi thông tin về bác sĩ, chuyên khoa, HỎI GIÁ KHÁM CỦA BÁC SĨ (chỉ khi HỎI THÔNG TIN, nếu đang trong luồng ĐẶT LỊCH mà cung cấp tên bác sĩ thì intent phải là BOOKING).
5. CLINIC_INFO: Hỏi thông tin phòng khám, giá DỊCH VỤ / XÉT NGHIỆM, giờ làm việc. (TUYỆT ĐỐI KHÔNG dùng nếu người dùng hỏi giá khám của Bác sĩ).
6. MEDICAL_QA: Xin tư vấn y khoa, thuốc men, bệnh lý.
7. PERSONAL_RECORD: Hỏi về hồ sơ bệnh án, kết quả khám của bản thân.
8. GENERAL: Chào hỏi thông thường, CÂU HỎI NGOÀI LỀ, KHÔNG LIÊN QUAN ĐẾN Y TẾ HOẶC PHÒNG KHÁM, KHÔNG RÕ NGHĨA.

QUAN TRỌNG: Nếu lịch sử hội thoại cho thấy người dùng ĐANG TRONG QUÁ TRÌNH ĐẶT LỊCH (ví dụ AI đang hỏi ngày giờ, chuyên khoa, tên bác sĩ) NHƯNG câu nói hiện tại của người dùng là một CÂU HỎI (ví dụ: "Có bác sĩ Lê Tuấn không?", "Giá khám bao nhiêu?"), thì BẮT BUỘC phải chuyển Intent sang DOCTOR_INFO hoặc CLINIC_INFO để AI trả lời câu hỏi đó. CHỈ GIỮ Intent là BOOKING nếu người dùng trực tiếp cung cấp thông tin để điền vào chỗ trống (ví dụ: "Tôi chọn Lê Tuấn", "Ngày mai", "Khám chuyên khoa nhi").

Yêu cầu JSON có cấu trúc sau:
{{
    "rewritten_query": "Câu hỏi viết lại đầy đủ ngữ cảnh (nếu câu gốc bị thiếu chủ ngữ/vị ngữ, nếu đã rõ thì giữ nguyên câu gốc)",
    "intent": "MỘT_TRONG_8_INTENT",
    "parameters": {{
        "doctor_name": "Tên bác sĩ (nếu có)",
        "expertise_name": "Tên chuyên khoa. NẾU USER CHỈ NÓI TRIỆU CHỨNG, BẮT BUỘC TỰ ĐỘNG SUY LUẬN CHUYÊN KHOA (VD: đau đầu -> Nội Thần Kinh, đau dạ dày -> Tiêu Hóa Gan Mật, gãy xương -> Chấn Thương Chỉnh Hình).",
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
