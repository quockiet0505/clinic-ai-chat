import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.config import settings

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"
VIETNAMESE_STOPWORDS = {
    "la", "va", "cua", "cho", "voi", "mot", "cac", "nhung", "thi", "duoc",
    "khong", "co", "toi", "ban", "nay", "do", "neu", "hay", "gi", "nao",
}


@dataclass
class KnowledgeChunk:
    source: str
    title: str
    content: str

    @property
    def text(self) -> str:
        return f"[{self.title}]\n{self.content}"


class KnowledgeRetriever:
    """RAG nhẹ: chunk markdown theo heading, retrieve bằng keyword overlap."""

    def __init__(self, knowledge_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.chunks = self._load_chunks()

    def _load_chunks(self) -> list[KnowledgeChunk]:
        if not self.knowledge_dir.exists():
            return []

        chunks: list[KnowledgeChunk] = []
        for file_path in sorted(self.knowledge_dir.glob("*.md")):
            text = file_path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            chunks.extend(self._split_markdown(file_path.name, text))
        return chunks

    def _split_markdown(self, source: str, text: str) -> list[KnowledgeChunk]:
        sections = re.split(r"(?m)^##\s+", text)
        chunks: list[KnowledgeChunk] = []

        if sections and not text.lstrip().startswith("##"):
            intro = sections[0].strip()
            if intro:
                chunks.append(KnowledgeChunk(source=source, title="Tổng quan", content=intro))
            sections = sections[1:]

        for section in sections:
            lines = section.strip().splitlines()
            if not lines:
                continue
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if body:
                chunks.append(KnowledgeChunk(source=source, title=title, content=body))
        return chunks

    def _tokenize(self, text: str) -> set[str]:
        normalized = unicodedata.normalize("NFD", text.lower())
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        words = re.findall(r"[a-z0-9]+", normalized)
        return {word for word in words if len(word) > 1 and word not in VIETNAMESE_STOPWORDS}

    def _score(self, query_tokens: set[str], chunk: KnowledgeChunk) -> float:
        chunk_tokens = self._tokenize(f"{chunk.title} {chunk.content}")
        if not query_tokens or not chunk_tokens:
            return 0.0
        overlap = len(query_tokens & chunk_tokens)
        return overlap / len(query_tokens)

    def retrieve(self, query: str, top_k: int | None = None) -> str:
        if not settings.RAG_ENABLED or not self.chunks:
            return ""

        top_k = top_k or settings.RAG_TOP_K
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return ""

        scored = [
            (self._score(query_tokens, chunk), chunk)
            for chunk in self.chunks
        ]
        scored.sort(key=lambda item: item[0], reverse=True)

        selected: list[str] = []
        for score, chunk in scored[:top_k]:
            if score < settings.RAG_MIN_SCORE:
                continue
            selected.append(chunk.text)

        return "\n\n".join(selected)
