import logging
from langchain_ollama import ChatOllama
from app.config import settings

logger = logging.getLogger(__name__)

def get_llm(temperature: float = None, max_tokens: int = None, **kwargs):
    """
    Factory function để trả về đối tượng LLM tương ứng.
    Nếu cấu hình MODAL_API_URL, hệ thống sẽ gọi API của vLLM trên Modal.com.
    Ngược lại, hệ thống sẽ sử dụng Ollama chạy ở Local.
    """
    temp = settings.LLM_TEMPERATURE if temperature is None else temperature
    max_t = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    if settings.MODAL_API_URL and settings.MODAL_API_URL.strip():
        # Xử lý format="json" cho OpenAI
        openai_kwargs = dict(kwargs)
        if openai_kwargs.get("format") == "json":
            openai_kwargs["response_format"] = {"type": "json_object"}
        if "format" in openai_kwargs:
            del openai_kwargs["format"]

        try:
            from langchain_openai import ChatOpenAI
            logger.info(f"Khởi tạo Model từ Modal API Endpoint: {settings.MODAL_API_URL}")
            return ChatOpenAI(
                model=settings.MODEL_NAME,
                openai_api_key="modal-clinic-key",
                openai_api_base=settings.MODAL_API_URL,
                temperature=temp,
                max_tokens=max_t,
                **openai_kwargs
            )
        except ImportError:
            logger.error("Thiếu thư viện langchain-openai. Vui lòng chạy: pip install langchain-openai")
            raise

    # Mặc định sử dụng Ollama local
    logger.info(f"Khởi tạo Ollama Local (model={settings.MODEL_NAME}) tại {settings.OLLAMA_BASE_URL}")
    return ChatOllama(
        model=settings.MODEL_NAME,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=temp,
        num_ctx=4096,
        **kwargs
    )
