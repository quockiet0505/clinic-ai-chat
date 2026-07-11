"""
Modal script to train/fine-tune the Clinic AI model (Qwen2.5-7B-Instruct) using QLoRA.
Run:
  modal run modal_train_llm.py
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
app = modal.App(name="clinic-ai-training")

# 3. Define Docker Image
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        "transformers>=4.45.0",
        "peft>=0.12.0",
        "trl>=0.9.0",
        "bitsandbytes>=0.43.0",
        "accelerate>=0.30.0",
        "datasets",
        "huggingface_hub",
        "sentencepiece",
        "protobuf"
    )
)

# 4. Load Secrets dynamically from local .env
secrets_list = []
local_keys = {}
# Read HF_TOKEN from local environment
hf_token = os.environ.get("HF_TOKEN")
if hf_token:
    local_keys["HF_TOKEN"] = hf_token
    secrets_list.append(modal.Secret.from_dict(local_keys))
else:
    # Fallback to predefined Modal Secret if deploying from CI/CD
    secrets_list.append(modal.Secret.from_name("huggingface-secret"))


@app.function(
    image=image,
    volumes={"/storage": volume},
    gpu="a100",  # Using A100 for fast QLoRA training
    timeout=14400,  # 4 hours max timeout
    secrets=secrets_list,
)
def train():
    import os
    import torch
    import shutil
    from pathlib import Path
    from datasets import load_dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig

    model_name = "Qwen/Qwen2.5-7B-Instruct"
    max_seq_length = 512

    # Login to HF Hub
    hf_token_val = os.environ.get("HF_TOKEN")
    if hf_token_val:
        from huggingface_hub import login
        login(token=hf_token_val)
        print("✅ Đã đăng nhập Hugging Face thành công!")
    else:
        print("⚠️ Không tìm thấy HF_TOKEN. Download model có thể thất bại nếu là gated repo.")

    # 1. Config 4-bit Quantization for QLoRA
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    print("📥 Đang tải Tokenizer và Base Model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.padding_side = "right"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto"
    )

    model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    # 2. Setup LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    print("✅ Cấu hình LoRA Adapter thành công!")
    model.print_trainable_parameters()

    # 3. Chuẩn bị Dataset
    print("📥 Đang tải dataset tư vấn y tế từ HuggingFace...")
    raw_dataset = load_dataset("hungnm/vietnamese-medical-qa", split="train")

    system_prompt = (
        "Bạn là một bác sĩ tư vấn y tế ảo của phòng khám ClinicPro. "
        "Nhiệm vụ của bạn là tư vấn sức khỏe, giải đáp triệu chứng và đưa ra lời khuyên y khoa an toàn dựa trên chuyên môn."
    )

    # Format ChatML / Qwen template
    def formatting_prompts_func(examples):
        texts = []
        for q, a in zip(examples["question"], examples["answer"]):
            if not q or not a:
                continue
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q.strip()},
                {"role": "assistant", "content": a.strip()}
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        return {"text": texts}

    # Map và Train/Val Split
    print("🧹 Đang xử lý dữ liệu và chia tập train/val...")
    formatted_dataset = raw_dataset.map(formatting_prompts_func, batched=True, remove_columns=raw_dataset.column_names)
    
    # Tokenize
    def tokenize_func(example):
        return tokenizer(example["text"], truncation=True, max_length=max_seq_length, padding=False)
        
    tokenized_dataset = formatted_dataset.map(tokenize_func, batched=True, remove_columns=["text"])
    split_ds = tokenized_dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = split_ds["train"]
    eval_dataset = split_ds["test"]

    print(f"📊 Dataset: {len(train_dataset)} train samples | {len(eval_dataset)} val samples")

    # 4. Cấu hình Trainer
    output_dir = Path("/storage/checkpoints")
    output_dir.mkdir(parents=True, exist_ok=True)

    from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,  # Effective Batch Size = 16
        optim="paged_adamw_8bit",
        num_train_epochs=3,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        logging_steps=10,
        learning_rate=2e-4,
        weight_decay=0.01,
        bf16=True,
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        save_total_limit=2,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    )

    print("🔥 Bắt đầu quá trình huấn luyện QLoRA...")
    trainer.train()
    print("🎉 Hoàn tất huấn luyện!")

    # Lưu adapter
    lora_dir = Path("/storage/clinic_qwen_7b_lora")
    if lora_dir.exists():
        shutil.rmtree(lora_dir)
    lora_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(lora_dir))
    tokenizer.save_pretrained(str(lora_dir))
    print(f"💾 Đã lưu LoRA adapter tại {lora_dir}")

    # 5. Giải phóng GPU và gộp Model (Merge & Save)
    print("🧹 Giải phóng bộ nhớ GPU...")
    del model
    del trainer
    torch.cuda.empty_cache()

    print("🚀 Nạp lại mô hình ở FP16 trên CPU và gộp não phụ (Merge)...")
    base_model_cpu = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="cpu"
    )
    
    from peft import PeftModel
    merged_model = PeftModel.from_pretrained(base_model_cpu, str(lora_dir))
    merged_model = merged_model.merge_and_unload()

    # Lưu model hoàn chỉnh
    final_output_dir = Path("/storage/clinic_qwen_7b_merged")
    if final_output_dir.exists():
        shutil.rmtree(final_output_dir)
    final_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"💾 Đang lưu model nguyên khối tại {final_output_dir}...")
    merged_model.save_pretrained(str(final_output_dir))
    tokenizer.save_pretrained(str(final_output_dir))

    volume.commit()
    print(f"🎉 HOÀN TẤT! Model đã được lưu trữ an toàn trên Modal Volume tại {final_output_dir}")
