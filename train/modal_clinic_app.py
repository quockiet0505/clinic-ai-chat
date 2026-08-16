"""
Modal Cloud Deployment Script for Clinic AI Chat.

This UNIFIED script runs the entire clinic-ai-chat system on a SINGLE GPU container:
  1. Qwen LLM (Transformers) - served on internal port 8001
  2. Ollama daemon          - for nomic-embed-text embeddings
  3. FastAPI application    - the main clinic chatbot API

Deploy:
  modal deploy modal_clinic_app.py

Dev/preview:
  modal serve modal_clinic_app.py
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import modal

# ---------------------------------------------------------------------------
# Persistent volume and app definition
# ---------------------------------------------------------------------------
volume = modal.Volume.from_name("clinic-model-vol", create_if_missing=True)

app = modal.App(name="clinic-ai-chat")

# ---------------------------------------------------------------------------
# Container image: Ollama + Transformers + FastAPI deps
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        # FastAPI / server
        "fastapi>=0.111.0",
        "uvicorn>=0.29.0",
        "pydantic>=2.7.1",
        "pydantic-settings>=2.2.1",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.1",
        "sse-starlette>=2.1.0",
        # LangChain stack
        "langchain>=0.2.1",
        "langchain-community>=0.2.1",
        "langchain-core>=0.2.20",
        "langchain-ollama>=0.1.0",
        "langchain-openai",
        # RAG / Vector DB
        "chromadb>=0.5.0",
        "langchain-chroma>=0.1.1",
        "datasets",
        "sentence-transformers",
        "sentencepiece",
        "protobuf",
        "einops",
        "langchain-huggingface",
        "langchain-text-splitters",
        # LLM (Transformers)
        "huggingface_hub",
        "transformers>=4.45.0",
        "torch>=2.0.0",
        "accelerate>=0.30.0",
        "bitsandbytes",
    )
    .add_local_dir(
        local_path=".",
        remote_path="/workspace",
        ignore=[".venv", "venv", "data", "exported", "__pycache__", ".git", "models"],
        copy=True,
    )
)

# ---------------------------------------------------------------------------
# Secrets: load from local .env or fall back to Modal secret store
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Main entrypoint: single GPU container running everything
# ---------------------------------------------------------------------------
@app.function(
    image=image,
    volumes={"/storage": volume},
    timeout=600,
    secrets=secrets_list,
    gpu="a10g",       # A10G fits Qwen-7B (4-bit ~4GB) + Ollama (~2GB) comfortably
    min_containers=0, # Scale to zero when idle to save cost
)
@modal.asgi_app()
def fastapi_app():
    import os
    import sys
    import subprocess
    import time
    import threading
    import shutil

    import httpx
    import uvicorn
    import torch
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    # -----------------------------------------------------------------------
    # Step 1: Load Qwen LLM into GPU VRAM
    # -----------------------------------------------------------------------
    # Path to the fine-tuned V2 Qwen model stored on Modal Volume
    model_path = "/storage/clinic_qwen_7b_merged_v2"
    if not os.path.exists(model_path) or not os.path.exists(f"{model_path}/config.json"):
        print("[LLM] Merged model not found. Falling back to Qwen/Qwen2.5-7B-Instruct base model.")
        model_path = "Qwen/Qwen2.5-7B-Instruct"
    else:
        print(f"[LLM] Loading fine-tuned model from volume: {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    llm_model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    llm_model.eval()
    print("[LLM] Qwen model loaded successfully.")

    # -----------------------------------------------------------------------
    # Step 2: Start an internal OpenAI-compatible server on port 8001
    #         so that app/core/llm.py (LangChain + ChatOpenAI) can call it
    #         without any code changes.
    # -----------------------------------------------------------------------
    internal_app = FastAPI(title="Clinic Internal LLM")

    class Message(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        messages: List[Message]
        temperature: Optional[float] = 0.3
        max_tokens: Optional[int] = 512
        # Accept (and ignore) extra fields sent by LangChain
        model: Optional[str] = None
        stream: Optional[bool] = False

    @internal_app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest):
        try:
            formatted_messages = [{"role": m.role, "content": m.content} for m in req.messages]
            prompt = tokenizer.apply_chat_template(
                formatted_messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = tokenizer(prompt, return_tensors="pt").to(llm_model.device)
            with torch.no_grad():
                outputs = llm_model.generate(
                    **inputs,
                    max_new_tokens=req.max_tokens or 512,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.85,
                    top_k=50,
                    repetition_penalty=1.05,
                    tokenizer=tokenizer,
                    stop_strings=["<|im_end|>", "<|im_start|>", "</s>"],
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.eos_token_id,
                )
            input_len = inputs["input_ids"].shape[1]
            response_text = tokenizer.decode(
                outputs[0][input_len:], skip_special_tokens=True
            ).strip()

            return {
                "id": "chatcmpl-modal",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": input_len, "completion_tokens": len(outputs[0]) - input_len},
            }
        except Exception as e:
            print(f"[LLM] Generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _run_internal_server():
        uvicorn.run(internal_app, host="127.0.0.1", port=8001, log_level="warning")

    threading.Thread(target=_run_internal_server, daemon=True).start()

    # Tell LangChain (app/core/llm.py) to call this internal endpoint
    os.environ["MODAL_API_URL"] = "http://127.0.0.1:8001/v1"
    os.environ["IS_MODAL"] = "true"

    # Wait briefly for internal server to be ready
    for _ in range(10):
        try:
            if httpx.get("http://127.0.0.1:8001/docs").status_code < 500:
                break
        except Exception:
            time.sleep(0.5)
    print("[LLM] Internal OpenAI-compatible server is ready on port 8001.")

    # Step 3: Ollama is bypassed. Using sentence-transformers on CPU instead.
    os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434" # Keep env just in case but unused

    # -----------------------------------------------------------------------
    # Step 4: Sync local vector_db to persistent storage (first-run only)
    # -----------------------------------------------------------------------
    storage_vector_dir = "/storage/vector_db"
    local_vector_dir = "/workspace/vector_db"

    if not os.path.exists(storage_vector_dir) or not os.listdir(storage_vector_dir):
        if os.path.exists(local_vector_dir) and os.listdir(local_vector_dir):
            print("[RAG] Copying vector_db to persistent storage...")
            try:
                shutil.copytree(local_vector_dir, storage_vector_dir, dirs_exist_ok=True)
                print("[RAG] vector_db copied successfully.")
            except Exception as e:
                print(f"[RAG] Error copying vector_db: {e}")

    # -----------------------------------------------------------------------
    # Step 5: Hand off to the main FastAPI application
    # -----------------------------------------------------------------------
    sys.path.insert(0, "/workspace")
    print("[App] Starting main FastAPI application...")
    from app.main import app as clinic_app
    clinic_app.mount("/llm", internal_app)
    return clinic_app
