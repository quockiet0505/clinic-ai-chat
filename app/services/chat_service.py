from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import time

from app.services.llm_service import LLMService
from app.services.router_service import RouterService
from app.services.query_analyzer import QueryAnalyzerService
from app.rag.retriever import KnowledgeRetriever
from app.rag.medical_retriever import MedicalRetriever


class ChatService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        router_service: RouterService | None = None,
        analyzer_service: QueryAnalyzerService | None = None,
        clinic_retriever: KnowledgeRetriever | None = None,
        medical_retriever: MedicalRetriever | None = None,
    ):
        self.llm_service = llm_service or LLMService()
        self.router_service = router_service or RouterService()
        self.analyzer_service = analyzer_service or QueryAnalyzerService()
        self.clinic_retriever = clinic_retriever or KnowledgeRetriever()
        self.medical_retriever = medical_retriever or MedicalRetriever()
    def _convert_history(self, history_dicts: list[dict]) -> list:
        history = []
        for msg in history_dicts:
            if msg.get("role") == "user":
                history.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                history.append(AIMessage(content=msg.get("content", "")))
        return history

    def _should_rewrite_query(self, message: str, history: list) -> bool:
        if not history:
            return False
            
        msg_lower = message.lower().strip()
        if msg_lower in ["lịch làm việc", "đặt lịch khám", "chi phí khám", "bảng giá", "giá khám"]:
            return False
            
        word_count = len(message.split())
        if word_count < 6:
            pronouns = ["nó", "cái đó", "bác sĩ đó", "ngày đó", "ở đó", "khoa nào", "vậy á", "có không", "được không", "vậy", "thì sao", "gì", "ai", "mấy giờ", "nhiêu", "sao", "ở đâu", "khi nào"]
            if any(p in msg_lower for p in pronouns):
                return True
            return False
            
        return False

    def analyze_query(self, message: str, history_dicts: list[dict]) -> dict:
        start_time = time.time()
        history = self._convert_history(history_dicts)
        
        # Rule-based fast check
        fast_intent = self.router_service.get_rule_based_intent(message)
        search_query = message
        intent = fast_intent
        params = {}
        
        needs_rewrite = self._should_rewrite_query(message, history)
        
        if needs_rewrite or fast_intent in ["BOOKING", "DOCTOR_INFO", "CLINIC_SYMPTOM"] or not fast_intent:
            analysis = self.analyzer_service.analyze(message, history)
            search_query = analysis.get("rewritten_query", message)
            
            if fast_intent in ["CLINIC_INFO", "GENERAL", "MEDICAL_QA", "EMERGENCY"] and not needs_rewrite:
                intent = fast_intent
            else:
                intent = analysis.get("intent", fast_intent or "GENERAL")
                
            params = analysis.get("parameters", {})
        else:
            intent = fast_intent
            
        print(f"[ANALYZE] Time: {time.time()-start_time:.2f}s | fast_intent={fast_intent}, final_intent={intent}, params={params}")
        
        return {
            "intent": intent,
            "parameters": params,
            "rewritten_query": search_query
        }

    def stream_response(self, message: str, history_dicts: list[dict], intent: str, knowledge_context: str, search_query: str = ""):
        start_time = time.time()
        history = self._convert_history(history_dicts)
        
        # Lấy từ RAG (Chroma) nếu Backend không cung cấp context
        if not knowledge_context.strip():
            query_to_search = search_query if search_query else message
            if intent == "MEDICAL_QA" or intent == "CLINIC_SYMPTOM":
                knowledge_context = self.medical_retriever.retrieve(query_to_search, top_k=3)
            elif intent in ["CLINIC_INFO", "CLINIC_FAQ", "GENERAL"]:
                knowledge_context = self.clinic_retriever.retrieve(query_to_search, top_k=3)
        
        print("=" * 80)
        print(f"INTENT CLASSIFIED: {intent}")
        print(f"QUESTION: {message}")
        if knowledge_context:
            print("KNOWLEDGE CONTEXT:")
            print(knowledge_context[:800] + "..." if len(knowledge_context) > 800 else knowledge_context)
        print("=" * 80)

        chunks = []
        is_first_token = True

        for chunk in self.llm_service.stream_chat(
            user_message=message,
            history=history,
            knowledge_context=knowledge_context,
            intent=intent,
            access_token=None # Tokens are managed by the Spring Boot Orchestrator now
        ):
            if is_first_token:
                ttft = time.time() - start_time
                print(f"[METRIC] Time To First Token (TTFT): {ttft:.2f} s")
                is_first_token = False
                
            chunks.append(chunk)
            yield chunk

        print(f"[METRIC] Total Stream Time: {time.time() - start_time:.2f} s")
        print("=" * 80)
