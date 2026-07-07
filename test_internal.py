import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.chat_service import ChatService
from app.services.router_service import RouterService
from app.services.query_analyzer import QueryAnalyzerService

def test_booking_internal():
    router = RouterService()
    analyzer = QueryAnalyzerService()
    chat_svc = ChatService(None, analyzer, router)
    
    session_id = "test_session_123"
    messages = [
        "Tôi muốn đặt lịch khám bệnh",
        "Bác sĩ Lê Tuấn",
        "2026-07-09",
        "08:00",
        "Tôi bị đau bụng âm ỉ"
    ]
    
    # Simulate chat_service logic step by step
    for msg in messages:
        print(f"\nUser: {msg}")
        reply = chat_svc.send_message(msg, session_id=session_id, access_token="mock_token")
        print(f"AI: {reply}")

if __name__ == "__main__":
    test_booking_internal()
