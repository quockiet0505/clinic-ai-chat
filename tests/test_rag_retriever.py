
from app.rag.retriever import KnowledgeRetriever


def test_retriever_finds_booking_content():
    retriever = KnowledgeRetriever()
    result = retriever.retrieve("lam sao dat lich kham")
    assert "dat lich" in result.lower() or "đặt lịch" in result.lower() or "buoc" in result.lower() or "bước" in result.lower()


def test_retriever_finds_symptom_content():
    retriever = KnowledgeRetriever()
    result = retriever.retrieve("dau dau chong mat")
    assert result  # should match symptom guide
