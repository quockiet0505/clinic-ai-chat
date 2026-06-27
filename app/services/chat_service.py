from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.rag.retriever import KnowledgeRetriever
from app.rag.medical_retriever import MedicalRetriever
from app.services.llm_service import LLMService
from app.services.router_service import RouterService


class ChatService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        retriever: KnowledgeRetriever | None = None,
        medical_retriever: MedicalRetriever | None = None,
        router_service: RouterService | None = None,
    ):
        self.llm_service = llm_service or LLMService()
        self.retriever = retriever or KnowledgeRetriever()
        self.medical_retriever = medical_retriever or MedicalRetriever()
        self.router_service = router_service or RouterService()
        
        self._sessions: dict[str, list] = {}
        self._session_tokens: dict[str, str | None] = {}

    def _get_history(self, session_id: str) -> list:
        return self._sessions.get(session_id, [])

    def _append_history(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.append(HumanMessage(content=user_message))
        history.append(AIMessage(content=assistant_reply))
        if len(history) > 20:
            self._sessions[session_id] = history[-20:]

    def _build_knowledge_context(self, message: str, intent: str, history: list, access_token: str | None) -> str:
        """
        Dựa vào Intent để gọi RAG hoặc gọi trực tiếp Python Code (Pipeline tất định).
        """
        if intent == "CLINIC_FAQ":
            return self.retriever.retrieve(message)
            
        elif intent == "MEDICAL_QA":
            return self.medical_retriever.retrieve(message)
            
        elif intent in ["DOCTOR_INFO", "CLINIC_SYMPTOM"]:
            from app.services.parameter_extractor import ParameterExtractorService
            extractor = ParameterExtractorService()
            params = extractor.extract_clinic_params(message)
            
            from app.tools.clinic_tools import get_doctors_tool, get_specialties_tool
            # Nếu có tên bác sĩ hoặc khoa cụ thể
            if params.get("doctor_name") or params.get("expertise_name"):
                return get_doctors_tool.invoke(params)
                
            # Nếu không trích xuất được tham số nào
            if "bác sĩ" in message.lower() or "bs" in message.lower().split():
                return get_doctors_tool.invoke({})
            else:
                return get_specialties_tool.invoke({})
                
        elif intent == "CLINIC_INFO":
            from app.tools.clinic_tools import get_services_tool, get_clinic_info_tool
            if "giá" in message.lower() or "dịch vụ" in message.lower() or "xét nghiệm" in message.lower():
                return get_services_tool.invoke({"featured_only": False})
            else:
                return get_clinic_info_tool.invoke({})
                
        elif intent == "BOOKING":
            return self._handle_booking_flow(history, message, access_token)
            
        else:
            return ""

    def _handle_booking_flow(self, history: list, current_query: str, access_token: str | None) -> str:
        from app.services.parameter_extractor import ParameterExtractorService
        extractor = ParameterExtractorService()
        state = extractor.extract_booking_state(history, current_query)
        
        target_type = state.get("target_type")
        target_name = state.get("target_name")
        expertise_name = state.get("expertise_name")
        date_str = state.get("date")
        time_slot = state.get("time_slot")
        symptoms = state.get("symptoms")

        if not target_type or not target_name:
            return "CHỈ THỊ CHO AI: Hướng dẫn đặt lịch theo 2 luồng: (1) Khám bác sĩ — chọn chuyên khoa VÀ bác sĩ; (2) Xét nghiệm/chụp — chọn dịch vụ (không cần bác sĩ)."
            
        if not date_str:
            return "CHỈ THỊ CHO AI: Hãy hỏi người dùng chọn ngày đi khám (Lưu ý phòng khám nghỉ Chủ Nhật)."
            
        from app.clients.backend_client import BackendClient
        client = BackendClient()
        try:
            expertise_id = None
            doctor_id = None
            service_id = None
            
            target_t = (target_type or "").upper()

            if target_t == "DOCTOR":
                if not expertise_name:
                    return "CHỈ THỊ CHO AI: Đặt khám bác sĩ bắt buộc chọn chuyên khoa (expertise_name) và tên bác sĩ (target_name)."
                for s in client.get_specialties():
                    if expertise_name.lower() in (s.get("expertiseName") or "").lower():
                        expertise_id = s.get("expertiseId")
                        break
                for d in client.get_doctors(expertise_id=expertise_id):
                    if target_name.lower() in (d.get("fullName") or "").lower():
                        doctor_id = d.get("staffId")
                        break
            elif target_t == "SERVICE":
                for s in client.get_services(bookable_only=True):
                    if target_name.lower() in (s.get("serviceName") or "").lower():
                        service_id = s.get("serviceId")
                        break
            else:
                return "CHỈ THỊ CHO AI: Chỉ hỗ trợ DOCTOR (khám bác sĩ) hoặc SERVICE (xét nghiệm/chụp)."

            if not any([expertise_id, doctor_id, service_id]):
                return f"HỆ THỐNG BÁO LỖI: Không tìm thấy '{target_name}' trong hệ thống. CHỈ THỊ CHO AI: Xin lỗi người dùng và yêu cầu chọn tên khác."

            if not time_slot:
                slots = client.get_available_slots(date_str, doctor_id, expertise_id, service_id)
                if not slots:
                    return f"HỆ THỐNG BÁO LỖI: Ngày {date_str} không có lịch trống. CHỈ THỊ CHO AI: Báo cho người dùng và gợi ý chọn ngày khác."
                slot_times = [s.get("startTime") for s in slots]
                return f"HỆ THỐNG BÁO: Ngày {date_str} có các giờ sau: {', '.join(slot_times)}. CHỈ THỊ CHO AI: Liệt kê các giờ này và bảo người dùng chọn."
                
            if not symptoms:
                return "CHỈ THỊ CHO AI: Hỏi người dùng mô tả ngắn gọn triệu chứng để bác sĩ chuẩn bị."
                
            if not access_token:
                return "CHỈ THỊ CHO AI: Yêu cầu người dùng Đăng nhập tài khoản trên web để chốt lịch hẹn."
                
            time_start = time_slot.split(" - ")[0].strip()
            time_end = time_slot.split(" - ")[1].strip() if " - " in time_slot else ""
            if not time_end and ":" in time_start:
                try:
                    from datetime import datetime, timedelta
                    start_dt = datetime.strptime(time_start, "%H:%M")
                    time_end = (start_dt + timedelta(minutes=30)).strftime("%H:%M")
                except:
                    time_end = time_start

            payload = {
                "appointmentDate": date_str,
                "timeStart": time_start,
                "timeEnd": time_end,
                "note": symptoms,
                "bookingMode": target_t,
                "mainDoctorId": doctor_id,
                "expertiseId": expertise_id,
                "serviceId": service_id,
                "appointmentType": "ONLINE",
                "createdBy": "PATIENT"
            }
            res = client.create_appointment(payload, access_token)
            return f"HỆ THỐNG BÁO: Đặt lịch THÀNH CÔNG! Mã vé: {res.get('id', 'N/A')}. CHỈ THỊ CHO AI: Chúc mừng người dùng."
        except Exception as e:
            return f"HỆ THỐNG LỖI: {e}. CHỈ THỊ CHO AI: Báo lỗi cho người dùng."

    def _resolve_token(self, session_id: str, access_token: str | None) -> str | None:
        if access_token:
            self._session_tokens[session_id] = access_token
        return self._session_tokens.get(session_id)

    def _should_rewrite_query(self, message: str, history: list) -> bool:
        if not history:
            return False
            
        msg_lower = message.lower().strip()
        # Không bao giờ rewrite các câu lệnh tab trực tiếp
        if msg_lower in ["lịch làm việc", "đặt lịch khám", "chi phí khám", "bảng giá", "giá khám"]:
            return False
            
        word_count = len(message.split())
        if word_count < 6:
            # Nếu câu ngắn nhưng không chứa đại từ liên kết thì cũng không cần rewrite
            pronouns = ["nó", "cái đó", "bác sĩ đó", "ngày đó", "ở đó", "khoa nào", "vậy á", "có không", "được không", "vậy", "thì sao", "gì", "ai", "mấy giờ", "nhiêu", "sao", "ở đâu", "khi nào"]
            if any(p in msg_lower for p in pronouns):
                return True
            return False
            
        return False

    def _rewrite_query(self, message: str, history: list) -> str:
        # Chuyển history thành text
        history_lines = []
        for msg in history[-4:]:
            role = "User" if isinstance(msg, HumanMessage) else "AI"
            history_lines.append(f"{role}: {msg.content}")
        history_str = "\n".join(history_lines)

        prompt = f"""Bạn là trợ lý AI chuyên viết lại câu hỏi cuối cùng của người dùng dựa vào lịch sử trò chuyện.
Yêu cầu: Viết lại thành một câu hỏi độc lập ngắn gọn, đầy đủ ngữ cảnh bằng tiếng Việt để tìm kiếm thông tin. KHÔNG trả lời câu hỏi đó. KHÔNG giải thích.
Chỉ trả về JSON định dạng: {{"rewritten_query": "câu hỏi độc lập"}}

Ví dụ 1:
Lịch sử:
User: Khoa Tai Mũi Họng ở đâu?
AI: Ở tầng 2.
User: Có bác sĩ nào?
Kết quả: {{"rewritten_query": "Khoa Tai Mũi Họng có những bác sĩ nào?"}}

Ví dụ 2:
Lịch sử:
User: Bác sĩ Trần Minh Sang có tốt không?
AI: Bác sĩ Sang có 5 sao đánh giá.
User: Lịch làm việc?
Kết quả: {{"rewritten_query": "Lịch làm việc của bác sĩ Trần Minh Sang"}}

Lịch sử trò chuyện thực tế:
{history_str}
User: {message}
Kết quả:"""

        messages = [SystemMessage(content=prompt)]
        
        try:
            from langchain_ollama import ChatOllama
            from app.config import settings
            import json
            import re
            
            # Khởi tạo LLM ép JSON mode để chống luyên thuyên
            rewrite_llm = ChatOllama(
                model=settings.MODEL_NAME,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.0,
                format="json"
            )
            response = rewrite_llm.invoke(messages)
            content = (response.content or "").strip()
            
            try:
                data = json.loads(content)
                rewritten = data.get("rewritten_query", "")
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    rewritten = data.get("rewritten_query", "")
                else:
                    rewritten = ""
                    
            if rewritten and len(rewritten) > 5 and not any(kw in rewritten.lower() for kw in ["xin lỗi", "không có thông tin", "tôi chưa"]):
                print(f"QUERY REWRITTEN: '{message}' -> '{rewritten}'")
                return rewritten
            return message
        except Exception as e:
            print(f"Lỗi rewrite: {e}")
            return message

    def send_message(
        self,
        message: str,
        session_id: str = "default_session",
        access_token: str | None = None,
    ) -> str:
        history = self._get_history(session_id)
        
        # Bước 0: Conditional Rewrite
        search_query = message
        if self._should_rewrite_query(message, history):
            search_query = self._rewrite_query(message, history)
            
        # Bước 1: Intent Routing (dùng câu đã rewrite)
        intent = self.router_service.get_intent(search_query)
        
        # Bước 2: RAG / Python Pipeline
        knowledge = self._build_knowledge_context(search_query, intent, history, access_token)

        print("=" * 80)
        print(f"INTENT CLASSIFIED: {intent}")
        print(f"QUESTION: {message}")
        if knowledge:
            print("KNOWLEDGE FETCHED:")
            print(knowledge[:500] + "..." if len(knowledge) > 500 else knowledge)
        print("=" * 80)

        token = self._resolve_token(session_id, access_token)
        
        # Bước 3: Đưa vào LLMService kèm Intent
        reply = self.llm_service.chat(
            user_message=message,
            history=history,
            knowledge_context=knowledge,
            access_token=token,
            intent=intent,
        )
        self._append_history(session_id, message, reply)
        return reply

    def stream_message(
        self,
        message: str,
        session_id: str = "default_session",
        access_token: str | None = None,
    ):
        history = self._get_history(session_id)
        
        # Bước 0: Conditional Rewrite
        search_query = message
        if self._should_rewrite_query(message, history):
            search_query = self._rewrite_query(message, history)

        # Bước 1: Intent Routing
        intent = self.router_service.get_intent(search_query)
        
        # Bước 2: RAG / Python Pipeline
        knowledge = self._build_knowledge_context(search_query, intent, history, access_token)
        
        print("=" * 80)
        print(f"INTENT CLASSIFIED (STREAM): {intent}")
        print("=" * 80)
        
        token = self._resolve_token(session_id, access_token)
        chunks: list[str] = []

        # Bước 3: Đưa vào LLMService
        for chunk in self.llm_service.stream_chat(
            user_message=message,
            history=history,
            knowledge_context=knowledge,
            access_token=token,
            intent=intent,
        ):
            chunks.append(chunk)
            yield chunk

        full_reply = "".join(chunks)
        if full_reply:
            self._append_history(session_id, message, full_reply)

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._session_tokens.pop(session_id, None)
