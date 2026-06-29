import json

notebook = {
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "# Kaggle Notebook: Huấn luyện AI Y tế (Clinic AI) - HUGGINGFACE NATIVE STACK\n",
        "**HƯỚNG DẪN:** Bấm Run All. Quá trình chia thành 3 giai đoạn: Train, Merge và Quantize GGUF."
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 1. Cài đặt môi trường chuẩn HuggingFace"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "%%capture\n",
        "!pip install -U transformers peft trl bitsandbytes accelerate datasets\n"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "from kaggle_secrets import UserSecretsClient\n",
        "from huggingface_hub import login\n",
        "import os\n",
        "\n",
        "try:\n",
        "    # Lấy HF_TOKEN từ Kaggle Secrets\n",
        "    user_secrets = UserSecretsClient()\n",
        "    hf_token = user_secrets.get_secret(\"HF_TOKEN\")\n",
        "    login(token=hf_token)\n",
        "    print(\"✅ Đã đăng nhập Hugging Face thành công bằng Token từ Kaggle Secrets!\")\n",
        "except Exception as e:\n",
        "    print(\"⚠️ Lưu ý: Không tìm thấy Token. Nếu bạn dùng máy ảo Kaggle, hãy tạo một Secret tên là HF_TOKEN.\")"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 2. Khởi tạo Mô hình & LoRA Adapter"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "import torch\n",
        "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n",
        "from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training\n",
        "\n",
        "# Cấu hình an toàn để trị dứt điểm OOM\n",
        "model_name = \"Qwen/Qwen2.5-3B-Instruct\"\n",
        "max_seq_length = 256\n",
        "\n",
        "# Tải mô hình dưới dạng 4-bit\n",
        "bnb_config = BitsAndBytesConfig(\n",
        "    load_in_4bit=True,\n",
        "    bnb_4bit_use_double_quant=True,\n",
        "    bnb_4bit_quant_type=\"nf4\",\n",
        "    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16\n",
        ")\n",
        "\n",
        "tokenizer = AutoTokenizer.from_pretrained(model_name)\n",
        "tokenizer.padding_side = \"right\" # Rất quan trọng với Causal LM như Qwen\n",
        "if tokenizer.pad_token is None:\n",
        "    tokenizer.pad_token = tokenizer.eos_token\n",
        "\n",
        "print(\"Đang tải mô hình gốc...\")\n",
        "model = AutoModelForCausalLM.from_pretrained(\n",
        "    model_name,\n",
        "    quantization_config=bnb_config,\n",
        "    device_map=\"auto\"\n",
        ")\n",
        "\n",
        "# Chuẩn bị cho K-bit training và bật Gradient Checkpointing (Tiết kiệm VRAM tối đa)\n",
        "model = prepare_model_for_kbit_training(model)\n",
        "model.config.use_cache = False # Bắt buộc Tắt Cache khi train\n",
        "\n",
        "# Khởi tạo não phụ LoRA\n",
        "lora_config = LoraConfig(\n",
        "    r=16,\n",
        "    lora_alpha=16,\n",
        "    target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\", \"gate_proj\", \"up_proj\", \"down_proj\"],\n",
        "    lora_dropout=0.05,\n",
        "    bias=\"none\",\n",
        "    task_type=\"CAUSAL_LM\"\n",
        ")\n",
        "\n",
        "model = get_peft_model(model, lora_config)\n",
        "print(\"✅ Khởi tạo Mô hình HuggingFace Native & LoRA thành công!\")\n",
        "model.print_trainable_parameters()"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 3. Chuẩn bị dữ liệu"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "from datasets import load_dataset\n",
        "import json\n",
        "\n",
        "print(\"Đang tải dataset 9.400 câu hỏi y tế...\")\n",
        "raw_dataset = load_dataset(\"hungnm/vietnamese-medical-qa\", split=\"train\")\n",
        "\n",
        "system_prompt = \"Bạn là một bác sĩ tư vấn y tế ảo của phòng khám ClinicPro. Nhiệm vụ của bạn là tư vấn sức khỏe, giải đáp triệu chứng và đưa ra lời khuyên y khoa an toàn dựa trên chuyên môn.\"\n",
        "\n",
        "formatted_data = []\n",
        "for row in raw_dataset:\n",
        "    q = row.get(\"question\", \"\").strip()\n",
        "    a = row.get(\"answer\", \"\").strip()\n",
        "    if not q or not a: continue\n",
        "    formatted_data.append({\"instruction\": system_prompt, \"input\": q, \"output\": a})\n",
        "\n",
        "DATASET_PATH = \"/kaggle/working/medical_9400_alpaca.jsonl\"\n",
        "with open(DATASET_PATH, \"w\", encoding=\"utf-8\") as f:\n",
        "    for rec in formatted_data:\n",
        "        f.write(json.dumps(rec, ensure_ascii=False) + \"\\n\")\n",
        "\n",
        "def formatting_prompts_func(examples):\n",
        "    instructions = examples[\"instruction\"]\n",
        "    inputs       = examples[\"input\"]\n",
        "    outputs      = examples[\"output\"]\n",
        "    texts = []\n",
        "    for instruction, input, output in zip(instructions, inputs, outputs):\n",
        "        messages = [\n",
        "            {\"role\": \"system\", \"content\": instruction},\n",
        "            {\"role\": \"user\", \"content\": input},\n",
        "            {\"role\": \"assistant\", \"content\": output}\n",
        "        ]\n",
        "        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)\n",
        "        texts.append(text)\n",
        "    return { \"text\" : texts }\n",
        "\n",
        "dataset = load_dataset(\"json\", data_files=DATASET_PATH, split=\"train\")\n",
        "dataset = dataset.map(formatting_prompts_func, batched = True)\n",
        "\n",
        "train_temp = dataset.train_test_split(test_size=0.3, seed=42)\n",
        "train_dataset = train_temp[\"train\"]\n",
        "temp_dataset = train_temp[\"test\"]\n",
        "valid_test = temp_dataset.train_test_split(test_size=0.3333, seed=42)\n",
        "eval_dataset = valid_test[\"train\"]\n",
        "test_dataset = valid_test[\"test\"]\n",
        "\n",
        "print(f\"Train: {len(train_dataset)} | Val: {len(eval_dataset)} | Test: {len(test_dataset)}\")"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 4. Training (Trái tim của hệ thống)"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "from transformers import TrainerCallback, EarlyStoppingCallback\n",
        "from trl import SFTTrainer, SFTConfig\n",
        "import csv, os, torch\n",
        "\n",
        "class CSVLoggerCallback(TrainerCallback):\n",
        "    def __init__(self, log_path=\"/kaggle/working/training_log.csv\"):\n",
        "        self.log_path = log_path\n",
        "        self.header_written = False\n",
        "\n",
        "    def on_log(self, args, state, control, logs=None, **kwargs):\n",
        "        if logs is None: return\n",
        "        gpu_memory = round(torch.cuda.memory_reserved() / 1024 / 1024 / 1024, 2)\n",
        "        log_data = {\n",
        "            \"step\": state.global_step, \"epoch\": logs.get(\"epoch\", 0),\n",
        "            \"train_loss\": logs.get(\"loss\", \"\"), \"eval_loss\": logs.get(\"eval_loss\", \"\"),\n",
        "            \"learning_rate\": logs.get(\"learning_rate\", \"\"), \"grad_norm\": logs.get(\"grad_norm\", \"\"),\n",
        "            \"gpu_memory\": gpu_memory,\n",
        "            \"samples_per_second\": logs.get(\"train_samples_per_second\", logs.get(\"eval_samples_per_second\", \"\")),\n",
        "            \"steps_per_second\": logs.get(\"train_steps_per_second\", logs.get(\"eval_steps_per_second\", \"\")),\n",
        "            \"runtime\": logs.get(\"train_runtime\", logs.get(\"eval_runtime\", \"\"))\n",
        "        }\n",
        "        file_exists = os.path.isfile(self.log_path)\n",
        "        with open(self.log_path, mode='a', newline='') as f:\n",
        "            writer = csv.DictWriter(f, fieldnames=log_data.keys())\n",
        "            if not file_exists and not self.header_written:\n",
        "                writer.writeheader(); self.header_written = True\n",
        "            writer.writerow(log_data)\n",
        "\n",
        "torch.cuda.empty_cache()\n",
        "\n",
        "training_args = SFTConfig(\n",
        "    output_dir=\"/kaggle/working/checkpoints\",\n",
        "    dataset_text_field=\"text\",\n",
        "    max_length=max_seq_length,\n",
        "    packing=False,\n",
        "    per_device_train_batch_size=1, # ÉP LUỘT!\n",
        "    per_device_eval_batch_size=1,  # ÉP LUỘT!\n",
        "    gradient_accumulation_steps=4,\n",
        "    optim=\"paged_adamw_8bit\", # Optimizer tối ưu RAM của BitsAndBytes\n",
        "    num_train_epochs=3, # Học đi học lại toàn bộ 9400 câu 3 lần\n",
        "    eval_strategy=\"steps\",\n",
        "    eval_steps=50,\n",
        "    save_strategy=\"steps\",\n",
        "    save_steps=50,\n",
        "    logging_steps=10,\n",
        "    learning_rate=2e-4,\n",
        "    weight_decay=0.01,\n",
        "    fp16=not torch.cuda.is_bf16_supported(),\n",
        "    bf16=torch.cuda.is_bf16_supported(),\n",
        "    max_grad_norm=0.3,\n",
        "    warmup_steps=5,\n",
        "    lr_scheduler_type=\"cosine\",\n",
        "    load_best_model_at_end=True,\n",
        "    metric_for_best_model=\"eval_loss\",\n",
        "    save_total_limit=3,\n",
        "    report_to=\"none\"\n",
        ")\n",
        "\n",
        "trainer = SFTTrainer(\n",
        "    model=model,\n",
        "    train_dataset=train_dataset,\n",
        "    eval_dataset=eval_dataset,\n",
        "    tokenizer=tokenizer,\n",
        "    args=training_args,\n",
        "    callbacks=[CSVLoggerCallback(), EarlyStoppingCallback(early_stopping_patience=5)],\n",
        ")\n",
        "\n",
        "print(\"🚀 BẮT ĐẦU QUÁ TRÌNH HUẤN LUYỆN NGUYÊN BẢN (NATIVE)!\")\n",
        "trainer.train()\n",
        "print(\"🎉 HOÀN TẤT HUẤN LUYỆN!\")\n",
        "\n",
        "# Lưu não phụ\n",
        "trainer.model.save_pretrained(\"/kaggle/working/lora_adapter\")\n",
        "tokenizer.save_pretrained(\"/kaggle/working/lora_adapter\")"
      ]
    },
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": [
        "## 5. Xuất GGUF (Bằng Llama.cpp)"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "import gc\n",
        "import torch\n",
        "from transformers import AutoModelForCausalLM, AutoTokenizer\n",
        "from peft import PeftModel\n",
        "\n",
        "print(\"Đang dọn dẹp RAM VÀ VRAM...\")\n",
        "del model\n",
        "del trainer\n",
        "torch.cuda.empty_cache()\n",
        "gc.collect()\n",
        "\n",
        "print(\"Đang nạp lại Mô hình vào RAM CPU (Tránh OOM khi Merge)...\")\n",
        "base_model = AutoModelForCausalLM.from_pretrained(\n",
        "    \"Qwen/Qwen2.5-3B-Instruct\",\n",
        "    torch_dtype=torch.float16,\n",
        "    device_map=\"cpu\"\n",
        ")\n",
        "\n",
        "print(\"Đang gộp não phụ vào não chính...\")\n",
        "model = PeftModel.from_pretrained(base_model, \"/kaggle/working/lora_adapter\")\n",
        "model = model.merge_and_unload()\n",
        "\n",
        "print(\"Đang lưu mô hình nguyên khối...\")\n",
        "model.save_pretrained(\"/kaggle/working/merged_model\")\n",
        "tokenizer = AutoTokenizer.from_pretrained(\"/kaggle/working/lora_adapter\")\n",
        "tokenizer.save_pretrained(\"/kaggle/working/merged_model\")\n",
        "\n",
        "print(\"✅ Xong quá trình gộp khối!\")"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "%%capture\n",
        "!git clone https://github.com/ggerganov/llama.cpp.git\n",
        "!cd llama.cpp && pip install -r requirements.txt\n",
        "!cd llama.cpp && make -j"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": [
        "print(\"Đang ép xung sang GGUF FP16...\")\n",
        "!python llama.cpp/convert_hf_to_gguf.py /kaggle/working/merged_model --outfile /kaggle/working/my_clinic_ai-F16.gguf --outtype f16\n",
        "\n",
        "print(\"Đang nén xuống GGUF Q4_K_M (Siêu nhẹ)...\")\n",
        "!./llama.cpp/llama-quantize /kaggle/working/my_clinic_ai-F16.gguf /kaggle/working/my_clinic_ai-Q4_K_M.gguf Q4_K_M\n",
        "\n",
        "print(\"🎉🎉🎉 ĐÃ HOÀN TẤT TOÀN BỘ QUÁ TRÌNH! FILE CỦA BẠN LÀ: my_clinic_ai-Q4_K_M.gguf 🎉🎉🎉\")"
      ]
    }
  ],
  "metadata": {
    "kernelspec": {
      "display_name": "Python 3",
      "language": "python",
      "name": "python3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 4
}

with open(r"d:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\docs\07_KAGGLE_NATIVE_HF.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=2)
print("Generated native notebook")
