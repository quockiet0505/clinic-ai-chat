from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.exceptions import LLMServiceError
from app.schemas.chat import AnalyzeRequest, AnalyzeResponse, GenerateRequest
from app.services.chat_service import ChatService

router = APIRouter()
chat_service = ChatService()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_query(request: AnalyzeRequest):
    try:
        analysis = chat_service.analyze_query(
            message=request.message,
            history_dicts=[h.dict() for h in request.history]
        )
        return AnalyzeResponse(**analysis)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/generate")
async def generate_response(request: GenerateRequest):
    def generate():
        try:
            for chunk in chat_service.stream_response(
                message=request.message,
                history_dicts=[h.dict() for h in request.history],
                intent=request.intent,
                knowledge_context=request.knowledge_context,
                search_query=request.rewritten_query
            ):
                yield f"data: {chunk}\n\n"
        except LLMServiceError as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
