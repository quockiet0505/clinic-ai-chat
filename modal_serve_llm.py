"""
Modal script to serve the fine-tuned Clinic AI model (Qwen2.5-7B-Instruct) using transformers (stable fallback).
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

# 3. Define Docker Image with transformers installed (same as modal_app.py)
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "fastapi",
        "pydantic",
        "huggingface_hub",
        "transformers>=4.45.0",
        "torch>=2.0.0",
        "accelerate>=0.30.0",
        "bitsandbytes",
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
    gpu="a10g",          # GPU A10G (24GB VRAM)
    timeout=600,
    startup_timeout=600,  # Tối đa 10 phút để nạp model
    min_containers=0,     # Scale về 0 khi không có yêu cầu
    secrets=secrets_list,
)
class ClinicModel:
    @modal.enter()
    def load_model(self):
        import os
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        
        model_path = "/storage/clinic_qwen_7b_merged"
        
        if not os.path.exists(model_path) or not os.path.exists(f"{model_path}/config.json"):
            print(f"⚠️ Không tìm thấy model đã gộp tại {model_path}. Tự động fallback về base model gốc: Qwen/Qwen2.5-7B-Instruct")
            model_path = "Qwen/Qwen2.5-7B-Instruct"
        else:
            print(f"🤖 Đang nạp model y tế đã được gộp từ Volume: {model_path}")
            
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        # Quantize to 4-bit to fit comfortably on A10G (same as modal_app.py)
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True
        )
        self.model.eval()
        print("✅ Transformers Engine đã khởi động thành công!")

    @modal.asgi_app()
    def app(self):
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        from typing import List, Optional
        from fastapi.middleware.cors import CORSMiddleware
        import torch

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
            try:
                formatted_messages = [{"role": msg.role, "content": msg.content} for msg in req.messages]
                prompt = self.tokenizer.apply_chat_template(
                    formatted_messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=req.max_tokens,
                        temperature=req.temperature,
                        do_sample=req.temperature > 0 if req.temperature else False,
                        tokenizer=self.tokenizer,
                        stop_strings=["<|im_end|>", "<|im_start|>", "</s>"],
                        eos_token_id=self.tokenizer.eos_token_id,
                        pad_token_id=self.tokenizer.eos_token_id,
                    )
                
                input_len = inputs["input_ids"].shape[1]
                response_text = self.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
                
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
