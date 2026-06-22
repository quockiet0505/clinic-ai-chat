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
        content = load_system_prompt()
        if knowledge_context.strip():
            content += (
                "\n\n## Kiến thức tham khảo (FAQ nội bộ)\n"
                f"{knowledge_context.strip()}\n\n"
                "Dùng phần FAQ trên cho câu hỏi quy trình/chính sách. "
                "Dữ liệu bác sĩ/giá/lịch trống vẫn phải gọi tool."
            )
        return SystemMessage(content=content)

    def chat(
        self,
        user_message: str,
        history: list | None = None,
        knowledge_context: str = "",
        access_token: str | None = None,
    ) -> str:
        messages = [self._build_system_message(knowledge_context)]
        if history:
            messages.extend(history)
        messages.append(HumanMessage(content=user_message))

        try:
            response = self.llm.invoke(messages)
        except Exception as exc:
            raise LLMServiceError(f"Không gọi được Ollama: {exc}") from exc

        if getattr(response, "tool_calls", None):
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_result = self._execute_tool(tool_call, access_token=access_token)
                messages.append(
                    ToolMessage(content=tool_result, tool_call_id=tool_call["id"])
                )

            try:
                final_response = self.llm.invoke(messages)
            except Exception as exc:
                raise LLMServiceError(f"Không gọi được Ollama sau tool: {exc}") from exc
            return final_response.content or ""

        return response.content or ""

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
        tool = TOOL_REGISTRY.get(name)

        if tool is None:
            return f"Công cụ '{name}' chưa được hỗ trợ."

        if name == "book_appointment_tool" and access_token:
            args.setdefault("access_token", access_token)

        return tool.invoke(args)
