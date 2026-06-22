from langchain_core.messages import AIMessage, HumanMessage

from app.rag.retriever import KnowledgeRetriever
from app.services.llm_service import LLMService


class ChatService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        retriever: KnowledgeRetriever | None = None,
    ):
        self.llm_service = llm_service or LLMService()
        self.retriever = retriever or KnowledgeRetriever()
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

    def _build_knowledge_context(self, message: str) -> str:
        return self.retriever.retrieve(message)

    def _resolve_token(self, session_id: str, access_token: str | None) -> str | None:
        if access_token:
            self._session_tokens[session_id] = access_token
        return self._session_tokens.get(session_id)

    def send_message(
        self,
        message: str,
        session_id: str = "default_session",
        access_token: str | None = None,
    ) -> str:
        history = self._get_history(session_id)
        knowledge = self._build_knowledge_context(message)
        token = self._resolve_token(session_id, access_token)
        reply = self.llm_service.chat(
            message,
            history=history,
            knowledge_context=knowledge,
            access_token=token,
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
        knowledge = self._build_knowledge_context(message)
        token = self._resolve_token(session_id, access_token)
        chunks: list[str] = []

        for chunk in self.llm_service.stream_chat(
            message,
            history=history,
            knowledge_context=knowledge,
            access_token=token,
        ):
            chunks.append(chunk)
            yield chunk

        full_reply = "".join(chunks)
        if full_reply:
            self._append_history(session_id, message, full_reply)

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._session_tokens.pop(session_id, None)
