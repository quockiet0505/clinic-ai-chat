import logging
from typing import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.core.llm import get_llm

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
            self.ollama_llm = get_llm()
            logger.info("Khởi tạo LLM Service thành công.")
        except Exception as exc:
            logger.error(f"Lỗi khởi tạo LLM: {exc}")
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
            # Ghi đè toàn bộ content bằng System Prompt chuẩn được fine-tune
            content = "Bạn là một bác sĩ tư vấn y tế ảo của phòng khám ClinicPro. Nhiệm vụ của bạn là tư vấn sức khỏe, giải đáp triệu chứng và đưa ra lời khuyên y khoa an toàn dựa trên chuyên môn."
            return SystemMessage(content=content)
        elif intent == "BOOKING":
            content += """LƯU Ý ĐẶC BIỆT (BOOKING INTENT):
- Hệ thống đã xử lý logic và cung cấp chỉ thị dưới dạng CONTEXT.
- BẠN BẮT BUỘC PHẢI ĐỌC KỸ CONTEXT VÀ CHỈ HỎI/TRẢ LỜI ĐÚNG NHỮNG GÌ CONTEXT YÊU CẦU.
- TUYỆT ĐỐI KHÔNG TỰ Ý HỎI THÊM CÁC THÔNG TIN NHƯ "CHUYÊN KHOA", "GIỜ KHÁM", "BÁC SĨ" NẾU CONTEXT KHÔNG NHẮC TỚI.
- NGAY CẢ KHI NGƯỜI DÙNG CUNG CẤP TRIỆU CHỨNG, BẠN CŨNG KHÔNG ĐƯỢC PHÉP ĐÓNG VAI BÁC SĨ ĐỂ TƯ VẤN Y KHOA.
- VĂN PHONG: Trả lời tự nhiên, lịch sự, thân thiện nhưng vẫn phải ngắn gọn.
"""
        elif intent in ["DOCTOR_INFO", "CLINIC_INFO", "CLINIC_SYMPTOM", "PERSONAL_RECORD"]:
            content += """LƯU Ý ĐẶC BIỆT (PIPELINE INTENT):
- Hệ thống đã tự động chạy Code Python để trích xuất dữ liệu từ Backend và nạp vào phần CONTEXT bên dưới.
- Nhiệm vụ của bạn LÀ ĐỌC CONTEXT VÀ TRẢ LỜI NGƯỜI DÙNG BẰNG NGÔN NGỮ TỰ NHIÊN. LUÔN LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT.
- TUYỆT ĐỐI KHÔNG TỰ BỊA RA (HALLUCINATE) BÁC SĨ, GIÁ TIỀN, HAY LỊCH TRỐNG. Chỉ nói những gì có trong CONTEXT.
- Nếu CONTEXT có chứa chỉ thị "CHỈ THỊ CHO AI:", hãy làm theo chỉ thị đó một cách tự nhiên (Ví dụ: hỏi thêm thông tin ngày giờ, triệu chứng).
- Bạn KHÔNG ĐƯỢC gọi Tool nào cả, chỉ cần nói chuyện với người dùng.
- VĂN PHONG: Trả lời tự nhiên, lịch sự, thân thiện nhưng vẫn phải ngắn gọn.
- NGUYÊN TẮC XUỐNG DÒNG DÀNH CHO DANH SÁCH: Khi có danh sách (VD: bắt đầu bằng dấu gạch ngang), BẠN BẮT BUỘC PHẢI GIỮ NGUYÊN DẤU GẠCH NGANG VÀ NHẤN ENTER XUỐNG DÒNG cho từng mục. Tuyệt đối không được viết dính chùm tất cả các mục trên cùng một dòng.
"""

        content += "\n" + load_system_prompt()
        return SystemMessage(content=content)

    def chat(self, user_message: str, history: list | None = None, knowledge_context: str = "", access_token: str | None = None, intent: str = "GENERAL") -> str:
        messages = [self._build_system_message(intent=intent)]
        if history:
            messages.extend(history)
            
        if knowledge_context.strip():
            if intent == "MEDICAL_QA":
                user_content = f"Dựa vào kiến thức y khoa sau:\n{knowledge_context.strip()}\n\nHãy trả lời câu hỏi: {user_message}"
            else:
                user_content = f"Thông tin nội bộ (ẩn):\n{knowledge_context.strip()}\n\nCâu hỏi của tôi: {user_message}\n\nHãy trả lời tôi một cách tự nhiên (không nhắc đến việc bạn có thông tin nội bộ)."
            messages.append(HumanMessage(content=user_content))
        else:
            messages.append(HumanMessage(content=user_message))

        try:
            ai_msg = self.ollama_llm.invoke(messages)
            content = str(ai_msg.content)
            
            return content
        except Exception as exc:
            raise LLMServiceError(f"Không gọi được Ollama: {exc}") from exc

    def stream_chat(self, user_message: str, history: list | None = None, knowledge_context: str = "", access_token: str | None = None, intent: str = "GENERAL") -> Iterator[str]:
        messages = [self._build_system_message(intent=intent)]
        if history:
            messages.extend(history)
            
        if knowledge_context.strip():
            if intent == "MEDICAL_QA":
                user_content = f"Dựa vào kiến thức y khoa sau:\n{knowledge_context.strip()}\n\nHãy trả lời câu hỏi: {user_message}"
            else:
                user_content = f"Thông tin nội bộ (ẩn):\n{knowledge_context.strip()}\n\nCâu hỏi của tôi: {user_message}\n\nHãy trả lời tôi một cách tự nhiên (không nhắc đến việc bạn có thông tin nội bộ)."
            messages.append(HumanMessage(content=user_content))
        else:
            messages.append(HumanMessage(content=user_message))

        try:
            # Backend Modal hiện tại trả về cục JSON thay vì SSE, 
            # nên dùng invoke() rồi fake stream từng đoạn để tránh lỗi parse stream.
            response = self.ollama_llm.invoke(messages)
            content = response.content
            
            # Fake stream bằng cách chia nhỏ theo từ (word)
            words = content.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            raise LLMServiceError(f"Stream thất bại: {exc}") from exc
