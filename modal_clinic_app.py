"""
Modal script to deploy the ENTIRE clinic-ai-chat FastAPI application on Modal.com.
Deploy to Modal:
  modal deploy modal_clinic_app.py
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import modal

# 1. Define Persistent Storage Volume
volume = modal.Volume.from_name("clinic-model-vol", create_if_missing=True)

# 2. Define App
app = modal.App(name="clinic-ai-chat")

# 3. Define Docker Image containing Ollama (for embeddings) and all dependencies
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("curl", "git", "zstd")
    # Cài đặt Ollama vào hệ thống để xử lý Embedding model (nomic-embed-text)
    .run_commands("curl -fsSL https://ollama.com/install.sh | sh")
    # Cài đặt các thư viện Python
    .pip_install(
        "fastapi>=0.111.0",
        "uvicorn>=0.29.0",
        "pydantic>=2.7.1",
        "pydantic-settings>=2.2.1",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.1",
        "langchain>=0.2.1",
        "langchain-community>=0.2.1",
        "langchain-core>=0.2.20",
        "langchain-ollama>=0.1.0",
        "langchain-openai", # Để kết nối với vLLM Model Server trên Modal
        "sse-starlette>=2.1.0",
        "chromadb>=0.5.0",
        "langchain-chroma>=0.1.1",
        "datasets"
    )
    # Copy toàn bộ code nguồn hiện tại vào thư mục /workspace trên Modal
    .add_local_dir(
        local_path=".",
        remote_path="/workspace",
        ignore=[".venv", "data", "exported", "__pycache__", ".git", "venv", "models"],
        copy=True
    )
)

# 4. Load Secrets dynamically from local .env
secrets_list = []
local_keys = {}
for key in ["CLINIC_BACKEND_URL", "MODAL_API_URL", "HF_TOKEN", "CORS_ORIGINS"]:
    val = os.environ.get(key)
    if val:
        local_keys[key] = val

if local_keys:
    secrets_list.append(modal.Secret.from_dict(local_keys))
else:
    secrets_list.append(modal.Secret.from_name("clinic-secrets"))


@app.function(
    image=image,
    volumes={"/storage": volume},
    timeout=600,
    secrets=secrets_list,
    min_containers=0,  # Cho phép scale về 0 khi không có yêu cầu để tiết kiệm tiền
)
@modal.asgi_app()
def fastapi_app():
    import os
    import sys
    import subprocess
    import time
    import httpx
    import shutil

    # Cấu hình thư mục lưu model của Ollama lên ổ đĩa persistent volume /storage
    # Giúp nomic-embed-text chỉ phải tải 1 lần duy nhất, các lần khởi động sau sẽ load cực nhanh
    ollama_models_dir = "/storage/ollama_models"
    os.makedirs(ollama_models_dir, exist_ok=True)
    os.environ["OLLAMA_MODELS"] = ollama_models_dir

    # 1. Khởi động Ollama daemon ngầm
    print("[Ollama] Đang khởi động Ollama daemon...")
    subprocess.Popen(["ollama", "serve"], env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434"})
    
    # Chờ Ollama sẵn sàng (tối đa 30s)
    ollama_ready = False
    for i in range(30):
        try:
            if httpx.get("http://127.0.0.1:11434").status_code == 200:
                ollama_ready = True
                break
        except Exception:
            time.sleep(1)
            
    if not ollama_ready:
        print("[Ollama] ERROR: Không thể khởi động Ollama Server.")
    else:
        print("[Ollama] Ollama Server đã sẵn sàng.")
        # 2. Tự động tải embedding model nếu chưa tồn tại
        try:
            res = httpx.get("http://127.0.0.1:11434/api/tags").json()
            models = [m["name"] for m in res.get("models", [])]
            if not any("nomic-embed-text" in m for m in models):
                print("[Ollama] Không tìm thấy nomic-embed-text. Đang tải tự động...")
                subprocess.run(["ollama", "pull", "nomic-embed-text"])
                print("[Ollama] Tải thành công nomic-embed-text.")
        except Exception as e:
            print(f"[Ollama] Lỗi tải embedding model: {e}")

    # 3. Đồng bộ cơ sở dữ liệu Vector DB từ local sang Persistent Volume nếu chưa có
    # Việc này giúp tránh tải dataset từ HuggingFace và nhúng lại từ đầu trên CPU cực kỳ mất thời gian
    storage_vector_dir = "/storage/vector_db"
    local_vector_dir = "/workspace/vector_db"
    if not os.path.exists(storage_vector_dir) or not os.listdir(storage_vector_dir):
        if os.path.exists(local_vector_dir) and os.listdir(local_vector_dir):
            print("[RAG] Sao chép cơ sở dữ liệu Vector DB từ workspace sang persistent storage...")
            try:
                shutil.copytree(local_vector_dir, storage_vector_dir, dirs_exist_ok=True)
                print("[RAG] Sao chép Vector DB thành công!")
            except Exception as e:
                print(f"[RAG] Lỗi sao chép Vector DB: {e}")

    # 4. Import và khởi chạy FastAPI app của bạn
    sys.path.insert(0, "/workspace")
    os.environ["IS_MODAL"] = "true"
    
    # Cập nhật cấu hình OLLAMA_BASE_URL để trỏ đúng vào Ollama đang chạy ngầm trong container
    os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"

    from app.main import app as local_app
    return local_app
