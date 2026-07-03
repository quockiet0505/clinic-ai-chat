from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import time

from app.rag.retriever import KnowledgeRetriever
from app.rag.medical_retriever import MedicalRetriever
from app.services.llm_service import LLMService
from app.services.router_service import RouterService
from app.services.query_analyzer import QueryAnalyzerService


class ChatService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        retriever: KnowledgeRetriever | None = None,
        medical_retriever: MedicalRetriever | None = None,
        router_service: RouterService | None = None,
        analyzer_service: QueryAnalyzerService | None = None,
    ):
        self.llm_service = llm_service or LLMService()
        self.retriever = retriever or KnowledgeRetriever()
        self.medical_retriever = medical_retriever or MedicalRetriever()
        self.router_service = router_service or RouterService()
        self.analyzer_service = analyzer_service or QueryAnalyzerService()
        
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
            # Nếu param có sẵn từ Unified Analyzer
            from app.tools.clinic_tools import get_doctors_tool, get_specialties_tool
            # Try to get parameters if this was passed via kwarg (we will update callers)
            pass
            
        elif intent == "CLINIC_INFO":
            from app.tools.clinic_tools import get_services_tool, get_clinic_info_tool
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in ["giá", "dịch vụ", "xét nghiệm", "chi phí", "bao nhiêu"]):
                return get_services_tool.invoke({"featured_only": False})
            else:
                return get_clinic_info_tool.invoke({})
                
        elif intent == "BOOKING":
            pass
            
        else:
            return ""

    def _execute_booking_flow(self, state: dict, date_str: str, time_slot: str, access_token: str | None) -> str:
        target_type = state.get("target_type")
        target_name = state.get("target_name")
        expertise_name = state.get("expertise_name")
        symptoms = state.get("symptoms")

        if not target_type or not target_name:
            return "CHỈ THỊ CHO AI: Dạ vâng, bạn muốn đặt lịch khám bác sĩ (cần chọn chuyên khoa) hay muốn làm dịch vụ xét nghiệm/chụp chiếu ạ? Xin hãy hỏi người dùng một cách ngắn gọn và tự nhiên."
            
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
                    return "CHỈ THỊ CHO AI: Xin hãy hỏi người dùng muốn khám chuyên khoa nào (ví dụ: Tai Mũi Họng, Nội, Sản...) để tôi tìm bác sĩ phù hợp ạ."
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
                return "CHỈ THỊ CHO AI: Xin hãy hỏi lại người dùng là muốn khám bác sĩ hay sử dụng dịch vụ xét nghiệm/chụp chiếu."

            if not any([expertise_id, doctor_id, service_id]):
                return f"HỆ THỐNG BÁO LỖI: Không tìm thấy '{target_name}' trong hệ thống. CHỈ THỊ CHO AI: Xin lỗi người dùng và yêu cầu chọn tên khác."

            if not time_slot:
                slots = client.get_available_slots(date_str, doctor_id, expertise_id, service_id)
                if not slots:
                    return f"HỆ THỐNG BÁO LỖI: Ngày {date_str} hiện không còn giờ trống hoặc phòng khám nghỉ. CHỈ THỊ CHO AI: Xin lỗi người dùng và mời họ chọn một ngày khác."
                slot_times = [s.get("startTime") for s in slots]
                return f"HỆ THỐNG BÁO: Ngày {date_str} có các giờ sau: {', '.join(slot_times)}. CHỈ THỊ CHO AI: Liệt kê các giờ này thật ngắn gọn và mời người dùng chọn."
                
            if not symptoms:
                return "CHỈ THỊ CHO AI: Dạ vâng, xin bạn chia sẻ ngắn gọn triệu chứng đang gặp phải hoặc lý do khám để bác sĩ chuẩn bị tốt hơn nhé."
                
            if not access_token:
                return "CHỈ THỊ CHO AI: Xin lỗi, bạn cần Đăng nhập tài khoản trên web/app để hoàn tất chốt lịch hẹn. Xin hãy hướng dẫn người dùng đăng nhập."
                
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
        start_time = time.time()
        history = self._get_history(session_id)
        
        # Rule-based fast check
        fast_intent = self.router_service.get_rule_based_intent(message)
        search_query = message
        intent = fast_intent
        params = {}
        
        # Chỉ gọi LLM Analyzer nếu:
        # 1. Câu hỏi cần rewrite (theo logic cũ)
        # 2. Hoặc intent là BOOKING / DOCTOR_INFO / CLINIC_SYMPTOM (vì cần extract tham số)
        # 3. Hoặc Rule-based không nhận diện được (fallback)
        needs_rewrite = self._should_rewrite_query(message, history)
        
        if needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent:
            analysis = self.analyzer_service.analyze(message, history)
            search_query = analysis.get("rewritten_query", message)
            
            # Cập nhật intent nếu LLM phân tích
            if fast_intent in ["CLINIC_INFO", "GENERAL", "MEDICAL_QA", "EMERGENCY"] and not needs_rewrite:
                intent = fast_intent
            else:
                intent = analysis.get("intent", fast_intent or "GENERAL")
                
            params = analysis.get("parameters", {})
        else:
            intent = fast_intent
            
        print(f"DEBUG: fast_intent={fast_intent}, final_intent={intent}, params={params}")
            
        # Xử lý lấy bối cảnh (Knowledge/Tools)
        knowledge = ""
        if intent == "BOOKING":
            knowledge = self._execute_booking_flow(params, date_str=params.get("date"), time_slot=params.get("time_slot"), access_token=access_token)
        elif intent in ["DOCTOR_INFO", "CLINIC_SYMPTOM"]:
            from app.tools.clinic_tools import get_doctors_tool, get_specialties_tool
            if params.get("doctor_name") or params.get("expertise_name"):
                knowledge = get_doctors_tool.invoke(params)
            elif "bác sĩ" in search_query.lower():
                knowledge = get_doctors_tool.invoke({})
            else:
                knowledge = get_specialties_tool.invoke({})
        else:
            knowledge = self._build_knowledge_context(search_query, intent, history, access_token)

        print("=" * 80)
        print(f"INTENT CLASSIFIED: {intent}")
        print(f"QUESTION: {message}")
        if knowledge:
            print("KNOWLEDGE FETCHED:")
            print(knowledge[:800] + "..." if len(knowledge) > 800 else knowledge)
        print("=" * 80)

        token = self._resolve_token(session_id, access_token)
        reply = self.llm_service.chat(
            user_message=message,
            history=history,
            knowledge_context=knowledge,
            access_token=token,
            intent=intent,
        )
        total_time = time.time() - start_time
        print(f"[METRIC] Total Response Time: {total_time:.2f} seconds")
        print("=" * 80)
        
        self._append_history(session_id, message, reply)
        return reply

    def stream_message(
        self,
        message: str,
        session_id: str = "default_session",
        access_token: str | None = None,
    ):
        start_time = time.time()
        history = self._get_history(session_id)
        
        fast_intent = self.router_service.get_rule_based_intent(message)
        search_query = message
        intent = fast_intent
        params = {}
        
        needs_rewrite = self._should_rewrite_query(message, history)
        
        if needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent:
            analysis = self.analyzer_service.analyze(message, history)
            search_query = analysis.get("rewritten_query", message)
            
            if fast_intent in ["CLINIC_INFO", "GENERAL", "MEDICAL_QA", "EMERGENCY"] and not needs_rewrite:
                intent = fast_intent
            else:
                intent = analysis.get("intent", fast_intent or "GENERAL")
                
            params = analysis.get("parameters", {})
        else:
            intent = fast_intent
            
        print(f"DEBUG (STREAM): fast_intent={fast_intent}, final_intent={intent}, params={params}")
            
        knowledge = ""
        if intent == "BOOKING":
            knowledge = self._execute_booking_flow(params, date_str=params.get("date"), time_slot=params.get("time_slot"), access_token=access_token)
        elif intent in ["DOCTOR_INFO", "CLINIC_SYMPTOM"]:
            from app.tools.clinic_tools import get_doctors_tool, get_specialties_tool
            if params.get("doctor_name") or params.get("expertise_name"):
                knowledge = get_doctors_tool.invoke(params)
            elif "bác sĩ" in search_query.lower():
                knowledge = get_doctors_tool.invoke({})
            else:
                knowledge = get_specialties_tool.invoke({})
        else:
            knowledge = self._build_knowledge_context(search_query, intent, history, access_token)
        
        print("=" * 80)
        print(f"INTENT CLASSIFIED (STREAM): {intent}")
        print(f"QUESTION: {message}")
        if knowledge:
            print("KNOWLEDGE FETCHED:")
            print(knowledge[:800] + "..." if len(knowledge) > 800 else knowledge)
        print("=" * 80)
        
        token = self._resolve_token(session_id, access_token)
        chunks: list[str] = []
        is_first_token = True

        for chunk in self.llm_service.stream_chat(
            user_message=message,
            history=history,
            knowledge_context=knowledge,
            access_token=token,
            intent=intent,
        ):
            if is_first_token:
                ttft = time.time() - start_time
                print(f"[METRIC] Time To First Token (TTFT): {ttft:.2f} seconds")
                is_first_token = False
                
            chunks.append(chunk)
            yield chunk

        total_time = time.time() - start_time
        print(f"[METRIC] Total Stream Time: {total_time:.2f} seconds")
        print("=" * 80)
        
        full_reply = "".join(chunks)
        if full_reply:
            self._append_history(session_id, message, full_reply)

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._session_tokens.pop(session_id, None)
