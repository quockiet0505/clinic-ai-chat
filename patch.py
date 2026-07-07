import re

file_path = r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\chat_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for the memory_params line down to skip_analyze
replace1 = '''        memory_params = self._session_params.setdefault(session_id, {})
        is_booking = bool(memory_params.get("target_type"))
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
            elif "quay lại" in msg_lower or "quay lai" in msg_lower or "không" in msg_lower:
                memory_params["confirming_cancel"] = False
                self._session_params[session_id] = memory_params
                # Continue as if they didn't interrupt
                intent = "BOOKING"
                msg_lower = "quay lại" # just a safe fallback to trigger the booking flow again
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

        if (is_booking or needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent) and not skip_analyze:'''

content = content.replace(
    '''        memory_params = self._session_params.setdefault(session_id, {})
        is_booking = bool(memory_params.get("target_type"))
        
        if (is_booking or needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent) and not skip_analyze:''',
    replace1
)

replace2 = '''        # Bắt buộc khóa luồng lại nếu đang đặt lịch dở dang
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
                    params["symptoms"] = message.strip()'''

content = content.replace(
    '''        # Bắt buộc khóa luồng lại nếu đang đặt lịch dở dang
        if is_booking:
            intent = "BOOKING"
            # Nếu đã chọn được giờ mà chưa có triệu chứng, gán message hiện tại thành triệu chứng
            if memory_params.get("time_slot") and not memory_params.get("symptoms"):
                params["symptoms"] = message.strip()''',
    replace2
)


replace3 = '''        if intent == "BOOKING":
            knowledge = self._execute_booking_flow(params, date_str=params.get("date"), time_slot=params.get("time_slot"), access_token=access_token)
            if "[DIRECT_REPLY] Đặt lịch thành công" in knowledge:
                self._session_params.pop(session_id, None)
        elif intent == "CONFIRM_CANCEL":
            knowledge = "[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn có muốn tiếp tục không?\\n[Tiếp tục tư vấn] | [Quay lại đặt lịch]"
        elif intent == "PERSONAL_RECORD":'''

content = content.replace(
    '''        if intent == "BOOKING":
            knowledge = self._execute_booking_flow(params, date_str=params.get("date"), time_slot=params.get("time_slot"), access_token=access_token)
            if "[DIRECT_REPLY] Đặt lịch thành công" in knowledge:
                self._session_params.pop(session_id, None)
        elif intent == "PERSONAL_RECORD":''',
    replace3
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done replacement")
