import json
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.core.prompts import load_system_prompt
from app.tools import ALL_TOOLS, TOOL_REGISTRY


class LLMService:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            num_predict=settings.LLM_MAX_TOKENS,
        ).bind_tools(ALL_TOOLS)

    def _build_system_message(self, knowledge_context: str = "") -> SystemMessage:
        import datetime
        today = datetime.date.today()
        
        content = f"""THÔNG TIN HỆ THỐNG:
- Hôm nay là: {today.isoformat()}
- Nếu người dùng nói: hôm nay, ngày mai, tuần sau... hãy tính theo ngày này.

"""
        content += load_system_prompt()
        if knowledge_context.strip():
            content += (
                "\n\n## Kiến thức tham khảo (FAQ nội bộ)\n"
                f"{knowledge_context.strip()}\n\n"
                "Dùng phần FAQ trên cho câu hỏi quy trình/chính sách. "
                "Dữ liệu bác sĩ/giá/lịch trống vẫn phải gọi tool."
            )
        return SystemMessage(content=content)

    def chat(self, user_message: str, history: list | None = None, knowledge_context: str = "", access_token: str | None = None) -> str:
        messages = [self._build_system_message(knowledge_context)]
        if history:
            messages.extend(history)
        messages.append(HumanMessage(content=user_message))

        for _ in range(5):  # Agent loop
            try:
                ai_msg = self.llm.invoke(messages)
            except Exception as exc:
                raise LLMServiceError(f"Không gọi được Ollama: {exc}") from exc

            # 1. Native Tool Call
            if getattr(ai_msg, "tool_calls", None):
                messages.append(ai_msg)
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call.get("args", {})
                    
                    if access_token and tool_name in ["book_appointment_tool", "get_my_appointments_tool", "cancel_appointment_tool"]:
                        tool_args.setdefault("access_token", access_token)
                    
                    tool_func = TOOL_REGISTRY.get(tool_name)
                    if tool_func:
                        try:
                            tool_result = tool_func.invoke(tool_args)
                            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))
                        except Exception as e:
                            messages.append(ToolMessage(content=f"Lỗi: {e}", tool_call_id=tool_call["id"]))
                    else:
                        messages.append(ToolMessage(content="Tool không tồn tại", tool_call_id=tool_call["id"]))
                continue

            # 2. Fallback JSON parsing
            raw_text = (ai_msg.content or "").strip()
            if "name" in raw_text and "parameters" in raw_text:
                import re
                # Thử tìm chuỗi JSON giữa {}
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(0))
                        tool_name = parsed.get("name")
                        tool_args = parsed.get("parameters", {})
                        
                        if tool_name and isinstance(tool_args, dict):
                            if access_token and tool_name in ["book_appointment_tool", "get_my_appointments_tool", "cancel_appointment_tool"]:
                                tool_args.setdefault("access_token", access_token)
                            
                            tool_func = TOOL_REGISTRY.get(tool_name)
                            if tool_func:
                                try:
                                    tool_result = tool_func.invoke(tool_args)
                                    messages.append(AIMessage(content="", tool_calls=[{"name": tool_name, "args": tool_args, "id": "fallback"}]))
                                    messages.append(ToolMessage(content=str(tool_result), tool_call_id="fallback"))
                                    continue
                                except Exception as e:
                                    pass
                    except json.JSONDecodeError:
                        pass
            
            # Trả về kết quả cuối cùng
            return raw_text or "Xin lỗi, hệ thống đang bận."
        
        return "Xin lỗi, hệ thống đang bận do quá nhiều bước xử lý."

    def stream_chat(
        self,
        user_message: str,
        history: list | None = None,
        knowledge_context: str = "",
        access_token: str | None = None,
        chunk_size: int = 20,
    ):
        reply = self.chat(
            user_message,
            history=history,
            knowledge_context=knowledge_context,
            access_token=access_token,
        )
        if not reply:
            return

        for index in range(0, len(reply), chunk_size):
            yield reply[index : index + chunk_size]

    def _execute_tool(self, tool_call: dict, access_token: str | None = None) -> str:
        name = tool_call.get("name")
        args = dict(tool_call.get("args") or {})
        
        # Chặn các giá trị None (null) do AI sinh ra, Pydantic sẽ ném lỗi nếu tham số yêu cầu string
        for k, v in args.items():
            if v is None:
                args[k] = ""

        tool = TOOL_REGISTRY.get(name)

        if tool is None:
            return f"Công cụ '{name}' chưa được hỗ trợ."

        if access_token and name in [
            "book_appointment_tool",
            "get_my_appointments_tool",
            "cancel_appointment_tool",
        ]:
            args.setdefault("access_token", access_token)

        try:
            return tool.invoke(args)
        except Exception as e:
            return f"Lỗi khi chạy công cụ {name}: {e}. Hãy bỏ qua các tham số không rõ (hoặc gán bằng chuỗi rỗng) và thử lại."
