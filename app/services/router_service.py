import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from app.config import settings

logger = logging.getLogger(__name__)

class RouterService:
    """
    Phân loại ý định người dùng (Intent Routing) để điều hướng Pipeline.
    Các Intent: EMERGENCY, BOOKING, CLINIC_SYMPTOM, DOCTOR_INFO, CLINIC_INFO, MEDICAL_QA, GENERAL
    """
    
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.0, 
            num_predict=15,
        )
        
        self.system_prompt = """Bạn là Router của phòng khám. 
Phân loại tin nhắn thành MỘT TRONG 7 Intent sau (chỉ in ra đúng 1 từ khóa):

1. EMERGENCY: Khẩn cấp (đột quỵ, khó thở nặng, co giật, chảy máu).
2. BOOKING: Yêu cầu đặt lịch, hẹn ngày, xem lịch trống.
3. CLINIC_SYMPTOM: Hỏi phòng khám có khoa nào để khám bệnh của họ.
4. DOCTOR_INFO: Hỏi danh sách bác sĩ, tìm bác sĩ cụ thể.
5. CLINIC_INFO: Hỏi dịch vụ, bảng giá, giờ làm việc, địa chỉ phòng khám.
6. MEDICAL_QA: Hỏi tư vấn bệnh lý, sức khỏe, thuốc (Không liên quan đến đặt lịch/chọn khoa).
7. GENERAL: Chào hỏi thông thường.

Hãy in ra 1 từ khóa:"""

    def get_intent(self, user_message: str) -> str:
        msg_lower = user_message.lower()
        
        # EMERGENCY rules
        emergency_keywords = ["khó thở", "đột quỵ", "co giật", "ngất", "chảy máu nhiều", "đau thắt ngực", "cấp cứu", "mất nhận thức"]
        if any(kw in msg_lower for kw in emergency_keywords):
            return "EMERGENCY"
            
        # BOOKING rules
        booking_keywords = ["đặt lịch", "đặt khám", "hẹn lịch", "lịch trống", "đặt chỗ", "book lịch", "lấy số", "hẹn ngày"]
        if any(kw in msg_lower for kw in booking_keywords):
            return "BOOKING"
            
        # DOCTOR_INFO rules
        doctor_info_keywords = ["bác sĩ", "bs ", "bs.", "chuyên khoa", "khoa gia đình", "khoa nhi", "khoa sản", "khám khoa", "khoa răng", "khoa mắt", "khoa tai"]
        if any(kw in msg_lower for kw in doctor_info_keywords) or msg_lower.startswith("khoa "):
            return "DOCTOR_INFO"
            
        # CLINIC_SYMPTOM rules
        if any(kw in msg_lower for kw in ["khoa nào", "khoa gì", "ở khoa", "bác sĩ nào"]):
            return "CLINIC_SYMPTOM"
            
        # CLINIC_INFO rules
        clinic_info_keywords = ["giá", "bao nhiêu tiền", "xét nghiệm", "gói khám", "dịch vụ", "giờ làm việc", "lịch làm việc", "mấy giờ", "mở cửa", "đóng cửa", "khám giờ nào", "làm việc giờ nào", "địa chỉ", "ở đâu", "đường nào", "thanh toán", "hotline", "số điện thoại", "phòng khám có"]
        if any(kw in msg_lower for kw in clinic_info_keywords):
            return "CLINIC_INFO"
            
        # Medical QA rules
        medical_keywords = ["đau", "nhức", "mỏi", "buốt", "sốt", "ho", "bệnh", "thuốc", "triệu chứng", "uống gì", "chóng mặt", "buồn nôn", "nguyên nhân"]
        if any(kw in msg_lower for kw in medical_keywords):
            return "MEDICAL_QA"
            
        # General rules
        general_keywords = ["xin chào", "hello", "hi", "cảm ơn", "tạm biệt", "bye", "ok", "dạ", "vâng"]
        if any(kw in msg_lower for kw in general_keywords) and len(msg_lower.split()) <= 5:
            return "GENERAL"
            
        # Fallback to LLM
        logger.info(f"Rules didn't match for '{user_message}', falling back to LLM Router...")
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message)
        ]
        try:
            response = self.llm.invoke(messages)
            intent = (response.content or "").strip().upper()
            
            for valid_intent in ["EMERGENCY", "BOOKING", "CLINIC_SYMPTOM", "DOCTOR_INFO", "CLINIC_INFO", "MEDICAL_QA", "GENERAL"]:
                if valid_intent in intent:
                    return valid_intent
                    
            return "GENERAL"
        except Exception as e:
            logger.error(f"Router error: {e}")
            return "GENERAL"
