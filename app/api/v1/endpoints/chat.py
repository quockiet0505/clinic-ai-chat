from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.exceptions import LLMServiceError
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        reply_text = chat_service.send_message(
            message=request.message,
            session_id=request.session_id,
            access_token=request.access_token,
        )
    except LLMServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(reply=reply_text, session_id=request.session_id)


@router.post("/stream")
async def stream_message(request: ChatRequest):
    def generate():
        try:
            for chunk in chat_service.stream_message(
                message=request.message,
                session_id=request.session_id,
                access_token=request.access_token,
            ):
                yield f"data: {chunk}\n\n"
        except LLMServiceError as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    chat_service.clear_session(session_id)
    return {"status": "ok", "session_id": session_id}
