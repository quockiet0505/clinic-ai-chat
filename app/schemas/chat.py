from pydantic import BaseModel, Field
from typing import Any

class MessageHistory(BaseModel):
    role: str = Field(description="Role: user or assistant")
    content: str = Field(description="Nội dung tin nhắn")

class AnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Tin nhắn người dùng hiện tại")
    history: list[MessageHistory] = Field(default_factory=list, description="Lịch sử trò chuyện để tham chiếu")

class AnalyzeResponse(BaseModel):
    intent: str = Field(description="Intent phân loại (BOOKING, CLINIC_FAQ, etc)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Các tham số được trích xuất (ngày, chuyên khoa,...)")
    rewritten_query: str = Field(description="Câu hỏi được viết lại rõ nghĩa")

class GenerateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="Tin nhắn người dùng hiện tại")
    history: list[MessageHistory] = Field(default_factory=list, description="Lịch sử trò chuyện để tham chiếu")
    intent: str = Field(description="Intent đã được phân loại")
    rewritten_query: str = Field(default="", description="Câu hỏi đã được rewrite")
    knowledge_context: str = Field(default="", description="Bối cảnh/Dữ liệu từ Database do Backend cung cấp")

class HealthResponse(BaseModel):
    status: str
    model: str
    ollama: str
    backend: str
