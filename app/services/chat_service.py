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
        self._session_params: dict[str, dict] = {}

    def _get_history(self, session_id: str) -> list:
        history = self._sessions.get(session_id, [])
        return history[-6:] if len(history) > 6 else history

    def _append_history(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        history = self._sessions.setdefault(session_id, [])
        history.append(HumanMessage(content=user_message))
        history.append(AIMessage(content=assistant_reply))
        if len(history) > 10:
            self._sessions[session_id] = history[-10:]

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
        doctor_name = state.get("doctor_name")
        service_name = state.get("service_name")
        expertise_name = state.get("expertise_name")
        symptoms = state.get("symptoms")

        target_t = (target_type or "").upper()
        
        if not target_t:
            if expertise_name or doctor_name:
                target_t = "DOCTOR"
            elif service_name:
                target_t = "SERVICE"
            else:
                return "[DIRECT_REPLY] Xin hỏi bạn muốn đặt lịch khám với Bác sĩ/Chuyên khoa hay sử dụng Dịch vụ (Xét nghiệm, Chụp X-Quang)?"
                
            # Cập nhật ngược lại state để session lưu lại
            state["target_type"] = target_t

        target_name = doctor_name if target_t == "DOCTOR" else service_name

        from app.clients.backend_client import BackendClient
        client = BackendClient()
        try:
            expertise_id = None
            doctor_id = None
            service_id = None
            
            if target_t == "DOCTOR":
                if not expertise_name and not target_name:
                    return "[DIRECT_REPLY] Xin hỏi bạn muốn khám chuyên khoa nào (ví dụ: Tai Mũi Họng, Nội, Sản...) để mình tìm bác sĩ phù hợp ạ?"
                
                if expertise_name:
                    for s in client.get_specialties():
                        if expertise_name.lower() in (s.get("expertiseName") or "").lower():
                            expertise_id = s.get("expertiseId")
                            break
                    if not expertise_id:
                        return f"[DIRECT_REPLY] Xin lỗi, mình không tìm thấy chuyên khoa '{expertise_name}' trong hệ thống. Bạn vui lòng chọn chuyên khoa khác nhé."
                        
                if not target_name:
                    doctors = client.get_doctors(expertise_id=expertise_id)
                    if not doctors:
                        return f"[DIRECT_REPLY] Xin lỗi, hiện chưa có bác sĩ nào thuộc chuyên khoa '{expertise_name}'."
                    doc_names = [d.get("fullName", "") for d in doctors]
                    return f"[DIRECT_REPLY] Các bác sĩ thuộc chuyên khoa '{expertise_name}' gồm có: {', '.join(doc_names)}. Bạn muốn chọn bác sĩ nào ạ?"
                if target_name:
                    for d in client.get_doctors(expertise_id=expertise_id):
                        db_name = (d.get("fullName") or "").lower()
                        user_name = target_name.lower()
                        
                        def norm_name(s: str) -> str:
                            for t in ["bác sĩ", "bs.", "bs", "thạc sĩ", "tiến sĩ", "ths", "ts", "ckii", "cki", "ck2", "ck1", "."]:
                                s = s.replace(t, " ")
                            import re
                            s = re.sub(r'\s+', ' ', s).strip()
                            return s
                            
                        norm_db = norm_name(db_name)
                        norm_user = norm_name(user_name)
                        
                        if norm_user and norm_db and (norm_user in norm_db or norm_db in norm_user):
                            doctor_id = d.get("staffId")
                            if not expertise_id and "expertiseId" in d:
                                expertise_id = d.get("expertiseId")
                            break
                    if not doctor_id:
                        return f"[DIRECT_REPLY] Xin lỗi, mình không tìm thấy bác sĩ '{target_name}'. Bạn vui lòng kiểm tra lại tên hoặc chọn bác sĩ khác nhé."
                        
            elif target_t == "SERVICE":
                if not target_name:
                    return "[DIRECT_REPLY] Xin hỏi bạn muốn sử dụng dịch vụ chụp chiếu hoặc xét nghiệm nào ạ?"
                for s in client.get_services(bookable_only=True):
                    if target_name.lower() in (s.get("serviceName") or "").lower():
                        service_id = s.get("serviceId")
                        break
                if not service_id:
                    return f"[DIRECT_REPLY] Xin lỗi, mình không tìm thấy dịch vụ '{target_name}'. Bạn vui lòng chọn dịch vụ khác nhé."
            else:
                return "[DIRECT_REPLY] Xin vui lòng xác nhận lại bạn muốn khám bác sĩ hay sử dụng dịch vụ chụp chiếu ạ."

            if not date_str:
                return "[DIRECT_REPLY] Xin vui lòng cung cấp ngày bạn muốn đi khám nhé (Lưu ý: phòng khám nghỉ ngày Chủ Nhật)."

            if not time_slot:
                slots = client.get_available_slots(date_str, doctor_id, expertise_id, service_id)
                if not slots:
                    return f"[DIRECT_REPLY] Xin lỗi, ngày {date_str} không còn giờ trống hoặc phòng khám nghỉ. Bạn vui lòng chọn ngày khác nhé."
                slot_times = [s.get("timeStart") for s in slots if s.get("timeStart")]
                return f"[DIRECT_REPLY] Ngày {date_str} có các giờ trống sau: {', '.join(slot_times)}. Bạn muốn chọn khung giờ nào ạ?"
                
            if not symptoms:
                return "[DIRECT_REPLY] Để hoàn tất hồ sơ, xin bạn mô tả ngắn gọn triệu chứng đang gặp phải hoặc lý do đi khám nhé."
            if not access_token or access_token == "null" or access_token == "undefined":
                return "[DIRECT_REPLY] Bạn vui lòng đăng nhập tài khoản trên web/app để hoàn tất đặt lịch nhé."
                
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
            return f"[DIRECT_REPLY] Đặt lịch thành công! Mã vé của bạn là {res.get('appointmentId', 'N/A')}. Cảm ơn bạn đã sử dụng dịch vụ của AI-Doctor!"
        except Exception as e:
            return f"[DIRECT_REPLY] Rất xin lỗi, có lỗi xảy ra khi đặt lịch: {e}. Bạn vui lòng thử lại sau nhé."

    def _resolve_token(self, session_id: str, access_token: str | None) -> str | None:
        if access_token:
            self._session_tokens[session_id] = access_token
        return self._session_tokens.get(session_id)

    def _should_rewrite_query(self, message: str, history: list) -> bool:
        if not history:
            return False
            
        msg_lower = message.lower().strip()
        # Không bao giờ rewrite các câu lệnh tab trực tiếp
        if msg_lower in ["lịch làm việc", "đặt lịch khám", "chi phí khám", "bảng giá", "giá khám", "giờ làm việc", "các chuyên khoa", "hồ sơ bệnh án", "chuyên khoa"]:
            return False
            
        word_count = len(message.split())
        # Trả lời ngắn (< 5 từ) thường là đang cung cấp thông tin (như tên, ngày, giờ) cho AI
        if word_count < 5:
            return True
            
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
            from app.core.llm import get_llm
            import json
            import re
            
            # Khởi tạo LLM ép JSON mode để chống luyên thuyên
            rewrite_llm = get_llm(
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
        
        # Đã loại bỏ Cache cứng theo yêu cầu, AI sẽ tự trả lời tự nhiên qua LLM
        
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
        
        msg_lower = message.lower().strip()
        generic_phrases = [
            "đặt lịch", "đặt khám", "đặt lịch khám", "đặt lịch khám bệnh", "tôi muốn đặt lịch", "cho tôi đặt lịch",
            "bác sĩ", "danh sách bác sĩ", "tìm bác sĩ", 
            "khoa nào", "khám khoa nào",
            "chuyên khoa", "các chuyên khoa", "danh sách chuyên khoa", "chuyen khoa", "cac chuyen khoa",
            "giờ làm việc", "phòng khám", "ở đâu", "địa chỉ", "liên hệ", "giá", "dịch vụ"
        ]
        skip_analyze = msg_lower in generic_phrases
        
        memory_params = self._session_params.setdefault(session_id, {})
        is_booking = memory_params.get("is_booking", False) or bool(memory_params.get("target_type"))
        confirming_cancel = memory_params.get("confirming_cancel", False)

        msg_lower = message.lower().strip()
        
        if confirming_cancel:
            if "tiếp tục" in msg_lower or "tiep tuc" in msg_lower or msg_lower in ["có", "co", "thoát", "hủy"]:
                pending_message = memory_params.get("pending_message", message)
                self.clear_session(session_id)
                memory_params = self._session_params.setdefault(session_id, {})
                is_booking = False
                message = pending_message
                msg_lower = message.lower().strip()
                fast_intent = self.router_service.get_rule_based_intent(message)
                skip_analyze = msg_lower in generic_phrases
            elif "quay lại" in msg_lower or "quay lai" in msg_lower or "không" in msg_lower:
                memory_params["confirming_cancel"] = False
                self._session_params[session_id] = memory_params
                # Continue as if they didn't interrupt
                intent = "BOOKING"
                msg_lower = "quay lại" # just a safe fallback to trigger the booking flow again
                fast_intent = "BOOKING"
                skip_analyze = True
            else:
                self.clear_session(session_id)
                memory_params = self._session_params.setdefault(session_id, {})
                is_booking = False

        cancel_keywords = ["hủy đặt", "không đặt", "dừng đặt", "cancel booking"]
        if is_booking and any(k in msg_lower for k in cancel_keywords):
            self.clear_session(session_id)
            is_booking = False
            # We need to return this properly in the stream/send method, let's just clear session and let the LLM reply or hardcode it
            message = "hủy đặt lịch thành công"
            msg_lower = message.lower()

        # Skip analyzer nếu đang booking và fast_intent đã rõ là BOOKING (kể cả câu ngắn)
        # → tiết kiệm 20-30 giây gọi LLM không cần thiết
        booking_shortcut = is_booking and fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"]

        if (is_booking or needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent) and not skip_analyze and not booking_shortcut:
            analysis = self.analyzer_service.analyze(message, history)
            search_query = analysis.get("rewritten_query", message)
            
            # Cập nhật intent nếu LLM phân tích
            if fast_intent and not needs_rewrite and not is_booking:
                intent = fast_intent
            else:
                intent = analysis.get("intent", fast_intent or "GENERAL")
                
            params = analysis.get("parameters", {})
        else:
            intent = fast_intent or "BOOKING"
            
        if intent == "BOOKING":
            memory_params["is_booking"] = True
            is_booking = True
            
        # Bắt buộc khóa luồng lại nếu đang đặt lịch dở dang
        if is_booking:
            if intent not in ["BOOKING", "GENERAL"] and not (memory_params.get("time_slot") and not memory_params.get("symptoms") and len(message.split()) < 10):
                memory_params["confirming_cancel"] = True
                memory_params["pending_message"] = message
                self._session_params[session_id] = memory_params
                intent = "CONFIRM_CANCEL" # Special bypass
            else:
                intent = "BOOKING"
                # Nếu đã chọn được giờ mà chưa có triệu chứng, gán message hiện tại thành triệu chứng
                if memory_params.get("time_slot") and not memory_params.get("symptoms"):
                    params["symptoms"] = message.strip()
            
        merged_params = memory_params.copy()
        params = merged_params
        
        # Lưu lại vào session memory cho các lượt sau
        self._session_params[session_id] = params

            
        # Xử lý lấy bối cảnh (Knowledge/Tools)
        knowledge = ""
        if intent == "BOOKING":
            knowledge = self._execute_booking_flow(params, date_str=params.get("date"), time_slot=params.get("time_slot"), access_token=access_token)
            if "[DIRECT_REPLY] Đặt lịch thành công" in knowledge:
                self._session_params.pop(session_id, None)
        elif intent == "CONFIRM_CANCEL":
            knowledge = "[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn muốn:\n__BUTTON:Tiếp tục tư vấn__\n__BUTTON:Quay lại đặt lịch__"
        elif intent == "PERSONAL_RECORD":
            if not access_token or access_token == "null" or access_token == "undefined":
                return "Dạ, để xem hồ sơ bệnh án, bạn vui lòng đăng nhập vào tài khoản trên web hoặc app nhé."
            from app.tools.clinic_tools import get_medical_records_tool
            knowledge = get_medical_records_tool.invoke({"access_token": access_token})
            if "Lỗi 403" in knowledge:
                return "Dạ, phiên đăng nhập của bạn đã hết hạn hoặc không hợp lệ. Bạn vui lòng đăng xuất và đăng nhập lại trên ứng dụng để tôi có thể tải hồ sơ cho bạn nhé!"
        elif intent in ["DOCTOR_INFO", "CLINIC_SYMPTOM"]:
            from app.tools.clinic_tools import get_doctors_tool, get_specialties_tool
            if params.get("doctor_name") or params.get("expertise_name"):
                knowledge = "[DIRECT_REPLY]\n" + get_doctors_tool.invoke(params)
            elif "bác sĩ" in message.lower():
                knowledge = "[DIRECT_REPLY]\n" + get_doctors_tool.invoke({})
            else:
                knowledge = "[DIRECT_REPLY]\n" + get_specialties_tool.invoke({})
        elif intent == "CLINIC_INFO":
            from app.tools.clinic_tools import get_services_tool, get_clinic_info_tool
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in ["giá", "dịch vụ", "xét nghiệm", "chi phí", "bao nhiêu"]):
                knowledge = "[DIRECT_REPLY]\n" + get_services_tool.invoke({"featured_only": False})
            else:
                knowledge = "[DIRECT_REPLY]\n" + get_clinic_info_tool.invoke({})
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
        
        if knowledge and knowledge.startswith("[DIRECT_REPLY]"):
            reply = knowledge.replace("[DIRECT_REPLY]", "").strip()
        else:
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
        
        # Đã loại bỏ Cache cứng theo yêu cầu, AI sẽ tự trả lời tự nhiên qua LLM
        
        fast_intent = self.router_service.get_rule_based_intent(message)
        search_query = message
        intent = fast_intent
        params = {}
        
        needs_rewrite = self._should_rewrite_query(message, history)
        
        msg_lower = message.lower().strip()
        generic_phrases = [
            "đặt lịch", "đặt khám", "đặt lịch khám", "đặt lịch khám bệnh", "tôi muốn đặt lịch", "cho tôi đặt lịch",
            "bác sĩ", "danh sách bác sĩ", "tìm bác sĩ", 
            "khoa nào", "khám khoa nào",
            "chuyên khoa", "các chuyên khoa", "danh sách chuyên khoa", "chuyen khoa", "cac chuyen khoa",
            "giờ làm việc", "phòng khám", "ở đâu", "địa chỉ", "liên hệ", "giá", "dịch vụ"
        ]
        skip_analyze = msg_lower in generic_phrases
        
        memory_params = self._session_params.setdefault(session_id, {})
        is_booking = memory_params.get("is_booking", False) or bool(memory_params.get("target_type"))
        confirming_cancel = memory_params.get("confirming_cancel", False)

        msg_lower = message.lower().strip()
        
        if confirming_cancel:
            if "tiếp tục" in msg_lower or "tiep tuc" in msg_lower or msg_lower in ["có", "co", "thoát", "hủy"]:
                pending_message = memory_params.get("pending_message", message)
                self.clear_session(session_id)
                memory_params = self._session_params.setdefault(session_id, {})
                is_booking = False
                message = pending_message
                msg_lower = message.lower().strip()
                fast_intent = self.router_service.get_rule_based_intent(message)
                skip_analyze = msg_lower in generic_phrases
            elif "quay lại" in msg_lower or "quay lai" in msg_lower or "không" in msg_lower:
                memory_params["confirming_cancel"] = False
                self._session_params[session_id] = memory_params
                # Continue as if they didn't interrupt
                intent = "BOOKING"
                msg_lower = "quay lại" # just a safe fallback to trigger the booking flow again
                fast_intent = "BOOKING"
                skip_analyze = True
            else:
                self.clear_session(session_id)
                memory_params = self._session_params.setdefault(session_id, {})
                is_booking = False

        cancel_keywords = ["hủy đặt", "không đặt", "dừng đặt", "cancel booking"]
        if is_booking and any(k in msg_lower for k in cancel_keywords):
            self.clear_session(session_id)
            is_booking = False
            # We need to return this properly in the stream/send method, let's just clear session and let the LLM reply or hardcode it
            message = "hủy đặt lịch thành công"
            msg_lower = message.lower()

        # Skip analyzer nếu đang booking và fast_intent đã rõ là BOOKING (kể cả câu ngắn)
        # → tiết kiệm 20-30 giây gọi LLM không cần thiết
        booking_shortcut = is_booking and fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"]

        if (is_booking or needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent) and not skip_analyze and not booking_shortcut:
            analysis = self.analyzer_service.analyze(message, history)
            search_query = analysis.get("rewritten_query", message)
            
            if fast_intent and not needs_rewrite and not is_booking:
                intent = fast_intent
            else:
                intent = analysis.get("intent", fast_intent or "GENERAL")
                
            params = analysis.get("parameters", {})
        else:
            intent = fast_intent or "BOOKING"
            
        if intent == "BOOKING":
            memory_params["is_booking"] = True
            is_booking = True
            
        # Bắt buộc khóa luồng lại nếu đang đặt lịch dở dang
        if is_booking:
            if intent in ["DOCTOR_INFO", "CLINIC_SYMPTOM"]:
                intent = "BOOKING"
                
            if intent not in ["BOOKING", "GENERAL"] and not (memory_params.get("time_slot") and not memory_params.get("symptoms") and len(message.split()) < 10):
                memory_params["confirming_cancel"] = True
                memory_params["pending_message"] = message
                self._session_params[session_id] = memory_params
                intent = "CONFIRM_CANCEL" # Special bypass
            else:
                intent = "BOOKING"
                # Nếu đã chọn được giờ mà chưa có triệu chứng, gán message hiện tại thành triệu chứng
                if memory_params.get("time_slot") and not memory_params.get("symptoms"):
                    params["symptoms"] = message.strip()
            
        merged_params = memory_params.copy()
        merged_params.update(params)
        params = merged_params
        
        # Lưu lại vào session memory cho các lượt sau
        self._session_params[session_id] = params
            
        knowledge = ""
        if intent == "BOOKING":
            knowledge = self._execute_booking_flow(params, date_str=params.get("date"), time_slot=params.get("time_slot"), access_token=access_token)
            if "[DIRECT_REPLY] Đặt lịch thành công" in knowledge:
                self._session_params.pop(session_id, None)
        elif intent == "CONFIRM_CANCEL":
            knowledge = "[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn muốn:\n__BUTTON:Tiếp tục tư vấn__\n__BUTTON:Quay lại đặt lịch__"
        elif intent == "PERSONAL_RECORD":
            if not access_token or access_token == "null" or access_token == "undefined":
                yield "Dạ, để xem hồ sơ bệnh án, bạn vui lòng đăng nhập vào tài khoản trên web hoặc app nhé."
                return
            from app.tools.clinic_tools import get_medical_records_tool
            knowledge = get_medical_records_tool.invoke({"access_token": access_token})
            if "Lỗi 403" in knowledge:
                yield "Dạ, phiên đăng nhập của bạn đã hết hạn hoặc không hợp lệ. Bạn vui lòng đăng xuất và đăng nhập lại trên ứng dụng để tôi có thể tải hồ sơ cho bạn nhé!"
                return
        elif intent in ["DOCTOR_INFO", "CLINIC_SYMPTOM"]:
            from app.tools.clinic_tools import get_doctors_tool, get_specialties_tool
            if params.get("doctor_name") or params.get("expertise_name"):
                knowledge = "[DIRECT_REPLY]\n" + get_doctors_tool.invoke(params)
            elif "bác sĩ" in message.lower():
                knowledge = "[DIRECT_REPLY]\n" + get_doctors_tool.invoke({})
            else:
                knowledge = "[DIRECT_REPLY]\n" + get_specialties_tool.invoke({})
        elif intent == "CLINIC_INFO":
            from app.tools.clinic_tools import get_services_tool, get_clinic_info_tool
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in ["giá", "dịch vụ", "xét nghiệm", "chi phí", "bao nhiêu"]):
                knowledge = "[DIRECT_REPLY]\n" + get_services_tool.invoke({"featured_only": False})
            else:
                knowledge = "[DIRECT_REPLY]\n" + get_clinic_info_tool.invoke({})
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

        if knowledge and knowledge.startswith("[DIRECT_REPLY]"):
            reply = knowledge.replace("[DIRECT_REPLY]", "").strip()
            chunks.append(reply)
            yield reply
        else:
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
        self._session_params.pop(session_id, None)
