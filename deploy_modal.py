import os
import modal

# 1. Khởi tạo Modal App
app = modal.App("clinic-ai-vllm")

# 2. Định nghĩa Volume để lưu trữ Model (Làm bộ nhớ đệm Cache cho HuggingFace)
VOLUME_NAME = "clinic-model-vol"
try:
    volume = modal.Volume.lookup(VOLUME_NAME, create_if_missing=True)
except Exception:
    volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 3. Môi trường chạy (Docker Image)
# Cài thêm huggingface_hub và kích hoạt hf_transfer để tải model tốc độ bàn thờ (lên tới 5GB/s)
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "vllm==0.5.1",
        "fastapi",
        "uvicorn",
        "hf-transfer",
        "huggingface_hub"
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

# 4. Định nghĩa Server chạy vLLM (Chuẩn API của OpenAI)
@app.function(
    image=image,
    gpu="L4", # Dùng card Nvidia L4 (24GB VRAM)
    volumes={"/models": volume},
    timeout=600,
)
@modal.asgi_app()
def serve():
    import os
    import fastapi
    from vllm.entrypoints.openai.api_server import build_async_app
    from vllm.entrypoints.openai.cli_args import make_arg_parser
    
    # Thiết lập thư mục Cache của HuggingFace trỏ vào Volume. 
    # Bằng cách này, Modal chỉ tải model 1 lần duy nhất từ HF về ổ đĩa, các lần sau tự lấy ra xài.
    os.environ["HF_HOME"] = "/models/hf_cache"
    
    # Parse tham số cho vLLM
    parser = make_arg_parser()
    args = parser.parse_args([
        "--model", "quockiet/clinic-ai-F16.gguf", #  Đọc model trực tiếp từ HuggingFace của anh
        "--tokenizer", "Qwen/Qwen2.5-3B-Instruct", # Bắt buộc phải khai báo tokenizer gốc đối với GGUF
        "--served-model-name", "clinic-ai-finetuned", # Tên model hiển thị ra API
        "--max-model-len", "4096", # Giới hạn Context Length
        "--gpu-memory-utilization", "0.90",
        "--trust-remote-code"
    ])
    
    # Khởi tạo ASGI App chuẩn OpenAI
    vllm_app = build_async_app(args)
    return vllm_app

"""
====================================================================
HƯỚNG DẪN DEPLOY TRỰC TIẾP TỪ HUGGING FACE
====================================================================

BƯỚC 1: Vì anh đã up model lên Hugging Face thành công, anh không cần upload lên Modal nữa.

BƯỚC 2: Chỉ cần gõ lệnh Deploy, Modal sẽ tự động vào HuggingFace tải file đó về bằng đường truyền cáp quang siêu tốc của nó (chỉ mất vài giây là xong 6GB).
    modal deploy deploy_modal.py

Sau khi lệnh chạy xong, Modal sẽ in ra màn hình một đường link dạng:
🔗 https://<username>--clinic-ai-vllm-serve.modal.run

BƯỚC 3: Cập nhật biến môi trường
Copy đường link trên và dán vào file `.env` của thư mục clinic-ai-chat:
    USE_MODAL_LLM=True
    MODAL_BASE_URL=https://<username>--clinic-ai-vllm-serve.modal.run
    MODAL_MODEL_NAME=clinic-ai-finetuned
====================================================================
"""
