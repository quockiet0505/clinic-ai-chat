import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import ClinicAIError, LLMServiceError
from app.schemas.chat import HealthResponse

app = FastAPI(
    title="Clinic AI Chat Microservice",
    description="Microservice AI Chat dùng Llama 3.2 3B (Ollama) cho phòng khám ClinicPro",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(LLMServiceError)
async def llm_error_handler(_: Request, exc: LLMServiceError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ClinicAIError)
async def clinic_ai_error_handler(_: Request, exc: ClinicAIError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        model=settings.MODEL_NAME,
        ollama=settings.OLLAMA_BASE_URL,
        backend=settings.CLINIC_BACKEND_URL,
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
