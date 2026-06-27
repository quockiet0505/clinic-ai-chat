import hashlib
import logging
from pathlib import Path
from datasets import load_dataset

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)

VECTOR_DB_DIR = Path(__file__).resolve().parents[2] / "vector_db"
MEDICAL_DB_DIR = VECTOR_DB_DIR / "medical_chroma"
MEDICAL_HASH_FILE = VECTOR_DB_DIR / ".medical_hash"

class MedicalRetriever:
    """Medical RAG: Tải dataset từ HuggingFace và lưu vào ChromaDB riêng."""

    def __init__(self, persist_dir: Path | None = None):
        self.persist_dir = persist_dir or MEDICAL_DB_DIR
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=settings.OLLAMA_BASE_URL,
        )
        self.vector_store = self._initialize_vector_store()
        
        # Khởi tạo Re-ranker siêu nhẹ
        try:
            from langchain_community.cross_encoders import HuggingFaceCrossEncoder
            self.reranker_model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
            self.reranking_enabled = True
            print("Re-ranker initialized successfully (ms-marco-MiniLM-L-6-v2).")
        except Exception as e:
            print(f"Re-ranker initialization skipped: {e}")
            self.reranking_enabled = False

    def _initialize_vector_store(self) -> Chroma:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Dataset versioning or simple flag to avoid rebuilding
        dataset_name = "hungnm/vietnamese-medical-qa"
        
        saved_hash = ""
        if MEDICAL_HASH_FILE.exists():
            saved_hash = MEDICAL_HASH_FILE.read_text().strip()

        db_exists = (self.persist_dir / "chroma.sqlite3").exists()
        
        # Smart Ingestion: Chỉ rebuild nếu db mất hoặc chưa build
        if db_exists and saved_hash == dataset_name:
            return Chroma(
                persist_directory=str(self.persist_dir),
                embedding_function=self.embeddings
            )
            
        print("Medical knowledge base missing. Downloading and Building Medical ChromaDB... (This may take a few minutes)")
        
        documents = self._load_and_split_documents(dataset_name)
        
        if not documents:
            return Chroma(
                persist_directory=str(self.persist_dir),
                embedding_function=self.embeddings
            )

        # Clear old database before rebuilding
        if self.persist_dir.exists():
            import shutil
            shutil.rmtree(self.persist_dir)

        # Build in batches to avoid memory overload for Ollama
        vector_store = Chroma(
            persist_directory=str(self.persist_dir),
            embedding_function=self.embeddings
        )
        
        batch_size = 32
        total_batches = (len(documents) + batch_size - 1) // batch_size
        print(f"Bắt đầu nhúng {len(documents)} chunks thành {total_batches} batches (chia nhỏ để bảo vệ RAM/VRAM)...")
        
        import time
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            try:
                vector_store.add_documents(batch)
                print(f" - Đã nhúng xong batch {i//batch_size + 1}/{total_batches}")
                time.sleep(0.2) # Nghỉ để Ollama dọn rác RAM/VRAM
            except Exception as e:
                print(f"Lỗi ở batch {i//batch_size + 1}, có thể do tràn RAM. Bỏ qua và tiếp tục...")
                time.sleep(2)
            
        MEDICAL_HASH_FILE.write_text(dataset_name)
        print("Medical ChromaDB build complete.")
        return vector_store

    def _load_and_split_documents(self, dataset_name: str) -> list[Document]:
        docs = []
        try:
            print(f"Loading dataset {dataset_name} from HuggingFace...")
            dataset = load_dataset(dataset_name, split='train')
            
            # Không dùng TextSplitter vì mỗi dòng đã là 1 cặp QA ngắn gọn
            # Việc split sẽ làm vỡ ngữ cảnh và tạo ra quá nhiều chunks (25563 thay vì 9335)
            
            for i, row in enumerate(dataset):
                question = row.get("question", "")
                answer = row.get("answer", "")
                
                content = f"Câu hỏi y tế: {question}\nTrích xuất kiến thức: {answer}"
                doc = Document(
                    page_content=content,
                    metadata={"source": "vietnamese-medical-qa", "id": i}
                )
                docs.append(doc)
                
            print(f"Generated {len(docs)} documents (1 Document per QA pair) for Medical RAG.")
        except Exception as e:
            logger.error(f"Error loading Medical Dataset: {e}")
            
        return docs

    def retrieve(self, query: str, top_k: int = 3) -> str:
        if not settings.RAG_ENABLED:
            return ""
            
        try:
            if getattr(self, 'reranking_enabled', False):
                # Bước 1: Lấy Top 15 từ Vector Search thô (Recall cao)
                base_docs = self.vector_store.similarity_search(query, k=15)
                
                # Bước 2: Chấm điểm lại (Re-ranking) bằng ngữ nghĩa sâu (Precision cao)
                pairs = [[query, doc.page_content] for doc in base_docs]
                scores = self.reranker_model.score(pairs)
                
                scored_docs = list(zip(scores, base_docs))
                scored_docs.sort(key=lambda x: x[0], reverse=True)
                
                docs = [doc for score, doc in scored_docs[:top_k]]
                print(f"Reranker applied: Lọc {len(base_docs)} xuống {len(docs)} documents.")
            else:
                # Retriever cũ nếu không có Re-ranker
                retriever = self.vector_store.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={"score_threshold": 0.4, "k": top_k}
                )
                docs = retriever.invoke(query)
                
                if not docs:
                    docs = self.vector_store.similarity_search(query, k=top_k)
                
            selected = []
            for doc in docs:
                selected.append(doc.page_content)
                
            return "\n\n---\n\n".join(selected)
        except Exception as e:
            logger.error(f"Medical RAG Retrieval failed: {e}")
            return ""
