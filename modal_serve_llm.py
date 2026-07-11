"""
Modal script to serve the fine-tuned Clinic AI model (Qwen2.5-7B-Instruct) using vLLM.
Deploy to Modal:
  modal deploy modal_serve_llm.py
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
app = modal.App(name="clinic-ai-serving")

# 3. Define Docker Image with vLLM installed
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "vllm==0.5.4",  # Phiên bản vLLM ổn định hoạt động tốt trên A10G
        "fastapi",
        "pydantic",
        "huggingface_hub",
        "pyairports"
    )
)

# 4. Load Secrets dynamically from local .env
secrets_list = []
local_keys = {}
hf_token = os.environ.get("HF_TOKEN")
if hf_token:
    local_keys["HF_TOKEN"] = hf_token
    secrets_list.append(modal.Secret.from_dict(local_keys))
else:
    secrets_list.append(modal.Secret.from_name("huggingface-secret"))


@app.cls(
    image=image,
    volumes={"/storage": volume},
    gpu="a10g",          # GPU A10G (24GB VRAM) hoàn hảo để chạy model 7B/8B
    timeout=600,
    min_containers=0,     # Cho phép scale về 0 khi không có yêu cầu để tiết kiệm tiền (chỉ tốn tiền khi có người chat)
    secrets=secrets_list,
)
class ClinicModel:
    @modal.enter()
    def load_model(self):
        import os
        from vllm import LLM
        
        model_path = "/storage/clinic_qwen_7b_merged"
        
        # Nếu chưa chạy train hoặc chưa có model merge trong Volume, tự động fallback về base model gốc
        if not os.path.exists(model_path) or not os.path.exists(f"{model_path}/config.json"):
            print(f"⚠️ Không tìm thấy model đã gộp tại {model_path}. Tự động fallback về base model gốc: Qwen/Qwen2.5-7B-Instruct")
            model_path = "Qwen/Qwen2.5-7B-Instruct"
        else:
            print(f"🤖 Đang nạp model y tế đã được gộp từ Volume: {model_path}")
            
        # Khởi tạo engine vLLM
        self.llm = LLM(
            model=model_path,
            max_model_len=2048,           # Giới hạn context length để tối ưu hóa bộ nhớ
            gpu_memory_utilization=0.90,  # Dành 90% GPU VRAM cho model
            trust_remote_code=True
        )
        self.tokenizer = self.llm.get_tokenizer()
        print("✅ vLLM Engine đã khởi động thành công!")

    @modal.asgi_app()
    def app(self):
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        from typing import List, Optional
        from fastapi.middleware.cors import CORSMiddleware

        web_app = FastAPI(title="Clinic AI Service")

        # Cho phép gọi API từ local Frontend (CORS)
        web_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        class Message(BaseModel):
            role: str
            content: str

        class ChatRequest(BaseModel):
            messages: List[Message]
            temperature: Optional[float] = 0.3
            max_tokens: Optional[int] = 512

        @web_app.post("/v1/chat/completions")
        async def chat(req: ChatRequest):
            from vllm import SamplingParams
            
            try:
                # 1. Định dạng hội thoại qua tokenizer chat template
                formatted_messages = [{"role": msg.role, "content": msg.content} for msg in req.messages]
                prompt = self.tokenizer.apply_chat_template(
                    formatted_messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                # 2. Cấu hình tham số sinh (greedy decoding cho sự chuẩn xác y khoa)
                sampling_params = SamplingParams(
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    stop=["<|im_end|>", "<|im_start|>", "</s>"]
                )
                
                # 3. Chạy inference qua vLLM
                outputs = self.llm.generate([prompt], sampling_params)
                response_text = outputs[0].outputs[0].text
                
                # 4. Trả về kết quả theo chuẩn format OpenAI
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "finish_reason": "stop"
                        }
                    ]
                }
            except Exception as e:
                print(f"❌ Error during generation: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        return web_app
