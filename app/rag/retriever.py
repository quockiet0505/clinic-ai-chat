import hashlib
import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"
VECTOR_DB_DIR = Path(__file__).resolve().parents[2] / "vector_db"
HASH_FILE = VECTOR_DB_DIR / ".knowledge_hash"

class KnowledgeRetriever:
    """Vector RAG: Dùng ChromaDB và Ollama Embeddings (nomic-embed-text)."""

    def __init__(self, knowledge_dir: Path | None = None, persist_dir: Path | None = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.persist_dir = persist_dir or VECTOR_DB_DIR
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=settings.OLLAMA_BASE_URL,
        )
        self.vector_store = self._initialize_vector_store()

    def _compute_dir_hash(self) -> str:
        """Tính MD5 hash của tất cả file markdown để detect thay đổi."""
        if not self.knowledge_dir.exists():
            return ""
        
        md5 = hashlib.md5()
        for filepath in sorted(self.knowledge_dir.rglob("*.md")):
            md5.update(filepath.name.encode('utf-8'))
            md5.update(filepath.read_bytes())
        return md5.hexdigest()

    def _initialize_vector_store(self) -> Chroma:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        current_hash = self._compute_dir_hash()
        
        saved_hash = ""
        if HASH_FILE.exists():
            saved_hash = HASH_FILE.read_text().strip()

        db_exists = (self.persist_dir / "chroma.sqlite3").exists()
        
        # Smart Ingestion: Chỉ rebuild nếu dữ liệu đổi hoặc db mất
        if db_exists and current_hash == saved_hash and current_hash != "":
            return Chroma(
                persist_directory=str(self.persist_dir),
                embedding_function=self.embeddings
            )
            
        print("Knowledge base changed or missing. Rebuilding ChromaDB...")
        
        documents = self._load_and_split_documents()
        
        if not documents:
            return Chroma(
                persist_directory=str(self.persist_dir),
                embedding_function=self.embeddings
            )

        # Clear old database before rebuilding to prevent duplicates
        if self.persist_dir.exists():
            import shutil
            shutil.rmtree(self.persist_dir)

        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=str(self.persist_dir)
        )
        
        HASH_FILE.write_text(current_hash)
        print("ChromaDB rebuild complete.")
        return vector_store

    def _load_and_split_documents(self) -> list[Document]:
        if not self.knowledge_dir.exists():
            return []

        # Split 2 tầng: Markdown Header -> Recursive Character
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        docs = []
        for file_path in self.knowledge_dir.rglob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Thêm Metadata: source và type
                rel_path = file_path.relative_to(self.knowledge_dir)
                doc_type = rel_path.parent.name if rel_path.parent.name else "general"
                
                md_header_splits = markdown_splitter.split_text(content)
                for split in md_header_splits:
                    split.metadata["source"] = file_path.name
                    split.metadata["type"] = doc_type
                
                final_splits = text_splitter.split_documents(md_header_splits)
                docs.extend(final_splits)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                
        return docs

    def retrieve(self, query: str, top_k: int | None = None) -> str:
        if not settings.RAG_ENABLED:
            return ""
            
        top_k = top_k or settings.RAG_TOP_K
        
        try:
            # Retriever với tính năng filter điểm số (score thresholding)
            retriever = self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"score_threshold": 0.5, "k": top_k}
            )
            docs = retriever.invoke(query)
            
            # Fallback nếu threshold trả về rỗng, lấy 2 kết quả gần nhất bất chấp
            if not docs:
                docs = self.vector_store.similarity_search(query, k=2)
                
            selected = []
            for doc in docs:
                header = " > ".join([v for k, v in doc.metadata.items() if k.startswith("Header")])
                source = doc.metadata.get("source", "")
                title = f"[{source} - {header}]" if header else f"[{source}]"
                selected.append(f"{title}\n{doc.page_content}")
                
            return "\n\n".join(selected)
        except Exception as e:
            logger.error(f"RAG Retrieval failed: {e}")
            return ""
