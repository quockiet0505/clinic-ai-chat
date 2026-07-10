from fastapi import APIRouter

from app.api.v1.endpoints import chat
from app.api.v1.endpoints import moderation

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["Moderation"])
