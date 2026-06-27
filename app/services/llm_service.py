import logging
from typing import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.core.prompts import load_system_prompt

logger = logging.getLogger(__name__)


class LLMService:
    """
    Dịch vụ giao tiếp với LLM (Ollama).
    Hệ thống này chỉ chịu trách nhiệm sinh ngôn ngữ tự nhiên (NLP) dựa trên Context.
    Mọi logic lấy dữ liệu (Tool Calling) đều đã được xử lý bằng code Python ở vòng ngoài.
    """

    def __init__(self):
        try:
            self.llm = ChatOllama(
                model=settings.MODEL_NAME,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=settings.LLM_TEMPERATURE,
            )
        except Exception as exc:
            logger.error(f"Lỗi khởi tạo Ollama: {exc}")
            raise LLMServiceError("Không thể kết nối đến AI Service") from exc

    def _build_system_message(self, intent: str = "GENERAL") -> SystemMessage:
        content = f"HỆ THỐNG PHÂN LOẠI INTENT HIỆN TẠI: {intent}\n\n"
        
        # QUY TẮC TRẢ LỜI THEO INTENT
        intent_guidelines = {
            "CLINIC_INFO": "Chỉ trả lời THÔNG TIN ĐƯỢC HỎI. KHÔNG lặp lại toàn bộ thông tin phòng khám. Ví dụ: hỏi 'giờ làm việc' thì CHỈ trả lời giờ làm việc.",
            "TOOL_CALLING": "KHÔNG lặp lại thông tin phòng khám. Tập trung vào câu hỏi của người dùng.",
            "CLINIC_FAQ": "Trả lời ngắn gọn, đúng trọng tâm.",
        }
        
        if intent in intent_guidelines:
            content += f"⚠️ QUY TẮC CHO INTENT '{intent}': {intent_guidelines[intent]}\n\n"
        
        if intent == "EMERGENCY":
            content += """LƯU Ý ĐẶC BIỆT (EMERGENCY INTENT):
- Người dùng đang gặp tình trạng khẩn cấp.
- HÃY KHUYÊN HỌ GỌI CẤP CỨU 115 HOẶC ĐẾN BỆNH VIỆN GẦN NHẤT NGAY LẬP TỨC.
"""
        elif intent == "MEDICAL_QA":
            content += """LƯU Ý ĐẶC BIỆT (MEDICAL_QA INTENT):
- Người dùng đang hỏi về vấn đề y khoa, bệnh lý, triệu chứng.
- BẠN LÀ TRỢ LÝ Y TẾ, KHÔNG PHẢI BÁC SĨ. TUYỆT ĐỐI KHÔNG CHẨN ĐOÁN HAY KÊ ĐƠN.
- Chỉ chia sẻ thông tin y khoa mang tính chất THAM KHẢO dựa trên CONTEXT.
- BẮT BUỘC khuyên bệnh nhân đến phòng khám để bác sĩ chuyên khoa khám trực tiếp.
"""
        elif intent in ["DOCTOR_INFO", "CLINIC_INFO", "CLINIC_SYMPTOM", "BOOKING"]:
            content += """LƯU Ý ĐẶC BIỆT (PIPELINE INTENT):
- Hệ thống đã tự động chạy Code Python để trích xuất dữ liệu từ Backend và nạp vào phần CONTEXT bên dưới.
- Nhiệm vụ của bạn LÀ ĐỌC CONTEXT VÀ TRẢ LỜI NGƯỜI DÙNG BẰNG NGÔN NGỮ TỰ NHIÊN. LUÔN LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT.
- TUYỆT ĐỐI KHÔNG TỰ BỊA RA (HALLUCINATE) BÁC SĨ, GIÁ TIỀN, HAY LỊCH TRỐNG. Chỉ nói những gì có trong CONTEXT.
- Nếu CONTEXT có chứa chỉ thị "CHỈ THỊ CHO AI:", hãy làm theo chỉ thị đó một cách tự nhiên (Ví dụ: hỏi thêm thông tin ngày giờ, triệu chứng).
- Bạn KHÔNG ĐƯỢC gọi Tool nào cả, chỉ cần nói chuyện với người dùng.
"""

        content += "\n" + load_system_prompt()
        return SystemMessage(content=content)

    def chat(self, user_message: str, history: list | None = None, knowledge_context: str = "", access_token: str | None = None, intent: str = "GENERAL") -> str:
        messages = [self._build_system_message(intent=intent)]
        if history:
            messages.extend(history)
            
        if knowledge_context.strip():
            if intent == "MEDICAL_QA":
                prompt = f"""===== TÀI LIỆU Y KHOA THAM KHẢO =====
Dưới đây là các câu hỏi/đáp y khoa để bạn tham khảo. KHÔNG PHẢI là hồ sơ của người dùng.
Hãy dùng kiến thức này để khuyên họ:
{knowledge_context.strip()}
=================================="""
            else:
                prompt = f"""===== CONTEXT TỪ HỆ THỐNG =====
Đọc kỹ dữ liệu và các CHỈ THỊ CHO AI (nếu có) dưới đây để trả lời người dùng:
{knowledge_context.strip()}
==============================="""
            messages.append(HumanMessage(content=prompt))
            
        messages.append(HumanMessage(content=user_message))

        try:
            # Bỏ Agent Loop, gọi thẳng 1 lần duy nhất!
            ai_msg = self.llm.invoke(messages)
            content = str(ai_msg.content)
            
            import re
            # Fix lỗi Qwen 3B không chịu xuống dòng cho danh sách: chỉ bẻ dòng nếu phía trước là khoảng trắng và phía sau là ** (danh sách in đậm)
            content = re.sub(r'(?<!\n)( - \*\*)', r'\n\1', content)
            
            return content
        except Exception as exc:
            raise LLMServiceError(f"Không gọi được Ollama: {exc}") from exc

    def stream_chat(self, user_message: str, history: list | None = None, knowledge_context: str = "", access_token: str | None = None, intent: str = "GENERAL") -> Iterator[str]:
        messages = [self._build_system_message(intent=intent)]
        if history:
            messages.extend(history)
            
        if knowledge_context.strip():
            if intent == "MEDICAL_QA":
                prompt = f"""===== TÀI LIỆU Y KHOA THAM KHẢO =====
Dưới đây là các câu hỏi/đáp y khoa để bạn tham khảo. KHÔNG PHẢI là hồ sơ của người dùng.
Hãy dùng kiến thức này để khuyên họ:
{knowledge_context.strip()}
=================================="""
            else:
                prompt = f"""===== CONTEXT TỪ HỆ THỐNG =====
Đọc kỹ dữ liệu và các CHỈ THỊ CHO AI (nếu có) dưới đây để trả lời người dùng:
{knowledge_context.strip()}
==============================="""
            messages.append(HumanMessage(content=prompt))
            
        messages.append(HumanMessage(content=user_message))

        try:
            for chunk in self.llm.stream(messages):
                yield chunk.content
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            raise LLMServiceError(f"Stream thất bại: {exc}") from exc
