import logging
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm import get_llm
from app.config import settings

logger = logging.getLogger(__name__)

class RouterService:
    """
    Phân loại ý định người dùng (Intent Routing) để điều hướng Pipeline.
    Các Intent: EMERGENCY, BOOKING, CLINIC_SYMPTOM, DOCTOR_INFO, CLINIC_INFO, MEDICAL_QA, GENERAL
    """
    
    def __init__(self):
        self.llm = get_llm(temperature=0.0, max_tokens=15)
        
        self.system_prompt = """Bạn là Router của phòng khám. 
Phân loại tin nhắn thành MỘT TRONG 7 Intent sau (chỉ in ra đúng 1 từ khóa):

1. EMERGENCY: Khẩn cấp (đột quỵ, khó thở nặng, co giật, chảy máu).
2. BOOKING: Yêu cầu đặt lịch, hẹn ngày, xem lịch trống.
3. CLINIC_SYMPTOM: Hỏi phòng khám có khoa nào để khám bệnh của họ.
4. DOCTOR_INFO: Hỏi danh sách bác sĩ, tìm bác sĩ cụ thể.
5. CLINIC_INFO: Hỏi dịch vụ, bảng giá, giờ làm việc, địa chỉ phòng khám.
6. MEDICAL_QA: Hỏi tư vấn bệnh lý, sức khỏe, thuốc (Không liên quan đến đặt lịch/chọn khoa).
7. GENERAL: Chào hỏi thông thường, CÂU HỎI NGOÀI LỀ, KHÔNG LIÊN QUAN ĐẾN Y TẾ HOẶC PHÒNG KHÁM.

Hãy in ra 1 từ khóa:"""

    def get_intent(self, user_message: str) -> str:
        intent = self.get_rule_based_intent(user_message)
        if intent:
            return intent
            
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

    def get_rule_based_intent(self, user_message: str) -> str | None:
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
        doctor_info_keywords = [
            "danh sách bác sĩ", "tìm bác sĩ", "đội ngũ bác sĩ", "bác sĩ của phòng khám", 
            "bác sĩ nào tốt", "bác sĩ điều trị", "bác sĩ trực", "danh sach bac si", "tim bac si",
            "thông tin bác sĩ", "bác sĩ chuyên khoa"
        ]
        if any(kw in msg_lower for kw in doctor_info_keywords) or (msg_lower.startswith("bác sĩ") and len(msg_lower.split()) < 4):
            return "DOCTOR_INFO"
            
        # CLINIC_SYMPTOM / danh sách chuyên khoa rules
        specialty_keywords = [
            "chuyên khoa", "chuyen khoa", "các chuyên khoa", "danh sách chuyên khoa",
            "phòng khám có khoa", "có khoa nào", "khoa gì", "khoa nào",
            "ở khoa", "bác sĩ nào", "khám chuyên khoa"
        ]
        if any(kw in msg_lower for kw in specialty_keywords):
            return "CLINIC_SYMPTOM"
            
        # PERSONAL_RECORD rules
        record_keywords = ["hồ sơ bệnh án", "kết quả khám", "lịch sử khám", "bệnh án của tôi", "kết quả xét nghiệm"]
        if any(kw in msg_lower for kw in record_keywords):
            return "PERSONAL_RECORD"

        # CLINIC_INFO rules
        clinic_info_keywords = [
            "giờ làm việc", "lịch làm việc", "mấy giờ", "mở cửa", "đóng cửa",
            "khám giờ nào", "làm việc giờ nào", "bao nhiêu tiền", "chi phí",
            "gói khám", "dịch vụ", "địa chỉ", "ở đâu", "đường nào",
            "thanh toán", "hotline", "số điện thoại",
            "giá khám", "học phí", "phí khám",
        ]
        if any(kw in msg_lower for kw in clinic_info_keywords):
            if "bác sĩ" in msg_lower or "bac si" in msg_lower:
                return "DOCTOR_INFO"
            return "CLINIC_INFO"

        # Medical QA rules - chỉ bắt khi có nội dung y tế mang tính triệu chứng rõ ràng
        medical_keywords = [
            "đau đầu", "đau bụng", "đau ngực", "đau lưng", "đau họng", "đau tai",
            "nhức đầu", "nhức mỏi", "buốt", "sốt cao", "sốt li bì",
            "ho khan", "ho có đờm", "ho ra máu", "ho kéo dài",
            "bệnh lý", "thuốc uống", "uống gì", "chóng mặt",
            "buồn nôn", "nguyên nhân gây", "ung thư", "viêm nhiễm",
            "nghẹt mũi", "ù tai", "ngứa da", "dị ứng da", "phát ban", "nổi mụn",
            "táo bón", "tiêu chảy", "khó tiêu", "đầy hơi",
            "triệu chứng", "chảy máu mũi", "chảy máu", "sưng hạch",
            "em bị", "tôi bị", "mình bị", "con bị", "cháu bị",
        ]
        if any(kw in msg_lower for kw in medical_keywords):
            return "MEDICAL_QA"

        # General rules
        general_keywords = ["xin chào", "hello", "hi", "cảm ơn", "tạm biệt", "bye", "ok", "dạ", "vâng"]
        if any(kw in msg_lower for kw in general_keywords) and len(msg_lower.split()) <= 5:
            return "GENERAL"

        return None
