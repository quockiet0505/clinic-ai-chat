from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Tin nhắn người dùng")
    session_id: str = Field(default="default_session", description="ID phiên chat")
    access_token: str | None = Field(default=None, description="JWT bệnh nhân (để đặt lịch qua AI)")


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama: str
    backend: str
