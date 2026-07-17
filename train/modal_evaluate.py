import modal

app = modal.App("clinic-model-evaluation")

import os
from pathlib import Path

current_dir = Path(__file__).parent
dataset_dir = current_dir / "dataset"

# Cài đặt các thư viện toán học và NLP cần thiết
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "wget", "unzip")
    .pip_install(
        "torch",
        "transformers",
        "datasets",
        "nltk",
        "rouge_score",
        "bert_score",
        "accelerate",
        "bitsandbytes",
        "git+https://github.com/google-research/bleurt.git"
    )
    .run_commands(
        "wget https://storage.googleapis.com/bleurt-oss-21/BLEURT-20.zip",
        "unzip BLEURT-20.zip -d /bleurt-model",
        "rm BLEURT-20.zip"
    )
    .add_local_dir(local_path=str(dataset_dir), remote_path="/workspace/dataset")
)

volume = modal.Volume.from_name("clinic-model-vol", create_if_missing=True)

@app.function(
    image=image,
    volumes={"/storage": volume},
    gpu="H100", # Nâng cấp lên H100 để đánh giá siêu tốc
    timeout=3600 # Tăng timeout lên 1 tiếng
)
def evaluate_models(hf_token: str, hf_username: str):
    import json
    import time
    import torch
    from datasets import load_dataset
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from rouge_score import rouge_scorer
    from bert_score import score as bert_score_func
    from bleurt import score as bleurt_score
    print("📥 Đang đọc 100 câu hỏi đánh giá y tế từ file test_100_v2.json...")
    # ==============================================================================
    # NGUỒN TÀI LIỆU ĐÁNH GIÁ V2 (100 Câu Test Cố Định)
    # Lấy từ file test_100_v2.json ở local đẩy lên Modal
    # ==============================================================================
    with open("/workspace/dataset/test_100_v2.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)
    
    models_to_test = {
        "qwen": f"{hf_username}/clinic-qwen-7b-v2",
        "seallm": f"{hf_username}/clinic-seallm-7b-v2",
        "llama": f"{hf_username}/clinic-vinallama-7b-v2"
    }
    
    results = {}
    detailed_logs = {}
    
    # Khởi tạo công cụ chấm điểm
    rouge = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=False)
    smoothie = SmoothingFunction().method4
    print("Tải mô hình BLEURT vào RAM...")
    bleurt_scorer = bleurt_score.BleurtScorer("/bleurt-model/BLEURT-20")
    
    # Cấu hình 4-bit cho transformers mới
    bnb_config = BitsAndBytesConfig(load_in_4bit=True)
    
    for model_name, model_path in models_to_test.items():
        print(f"\n🚀 --- ĐANG ĐÁNH GIÁ MÔ HÌNH: {model_name.upper()} ---")
        detailed_logs[model_name] = []
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path, token=hf_token)
            
            # Load mô hình ở chế độ 4-bit để tiết kiệm RAM GPU
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                quantization_config=bnb_config,
                token=hf_token
            )
            
            total_tokens = 0
            total_time = 0
            
            preds = []
            refs = []
            
            for idx, item in enumerate(test_data):
                question = item["question"]
                reference = item["answer"]
                
                # Bọc câu hỏi bằng Chat Template
                messages = [
                    {"role": "system", "content": "Bạn là một bác sĩ tư vấn y tế tận tâm. Hãy trả lời ngắn gọn và chính xác."},
                    {"role": "user", "content": question}
                ]
                
                try:
                    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                except Exception:
                    # Fallback nếu model không hỗ trợ chat template chuẩn
                    prompt = f"System: Bạn là bác sĩ tư vấn y tế.\nUser: {question}\nAssistant:"
                
                inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
                
                start_time = time.time()
                with torch.no_grad():
                    # Tăng giới hạn lên 512 token để model có thể trả lời đầy đủ các câu dài
                    outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False)
                end_time = time.time()
                
                # Tính số token sinh ra (chỉ lấy phần model tự sinh, trừ đi prompt)
                gen_tokens = outputs.shape[1] - inputs.input_ids.shape[1]
                total_tokens += gen_tokens
                total_time += (end_time - start_time)
                
                # Decode câu trả lời
                pred_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                
                preds.append(pred_text)
                refs.append(reference)
                
                detailed_logs[model_name].append({
                    "question": question,
                    "reference": reference,
                    "prediction": pred_text
                })
                
                if (idx + 1) % 20 == 0:
                    print(f"   Đã trả lời {idx + 1}/100 câu...")
                    
            print(f"📊 Đang chấm điểm toán học cho {model_name}...")
            
            # Tính Tốc độ (Tokens/second)
            tps = total_tokens / total_time if total_time > 0 else 0
            
            # Tính BLEU
            bleu_scores = []
            for p, r in zip(preds, refs):
                bleu = sentence_bleu([r.split()], p.split(), smoothing_function=smoothie)
                bleu_scores.append(bleu)
            avg_bleu = sum(bleu_scores) / len(bleu_scores)
            
            # Tính ROUGE-L
            rouge_l_scores = []
            for p, r in zip(preds, refs):
                r_score = rouge.score(r, p)
                rouge_l_scores.append(r_score['rougeL'].fmeasure)
            avg_rouge = sum(rouge_l_scores) / len(rouge_l_scores)
            
            # Tính BERTScore (Dùng mô hình nhúng mặc định)
            P, R, F1 = bert_score_func(preds, refs, lang="vi", verbose=False)
            avg_bertscore = F1.mean().item()
            
            # Tính BLEURT
            bl_scores = bleurt_scorer.score(references=refs, candidates=preds)
            avg_bleurt = sum(bl_scores) / len(bl_scores)
            
            results[model_name] = {
                "bleu": round(avg_bleu, 4),
                "rouge_l": round(avg_rouge, 4),
                "bertscore": round(avg_bertscore, 4),
                "bleurt": round(avg_bleurt, 4),
                "tokens_per_sec": round(tps, 2)
            }
            
            print(f"Kết quả {model_name}: BLEU={avg_bleu:.4f}, ROUGE-L={avg_rouge:.4f}, BERTScore={avg_bertscore:.4f}, BLEURT={avg_bleurt:.4f}, Speed={tps:.2f} t/s")
            
            # Giải phóng RAM GPU cho model tiếp theo
            del model
            del tokenizer
            torch.cuda.empty_cache()
            
        except Exception as e:
            print(f"❌ Lỗi khi đánh giá {model_name}: {e}")
            results[model_name] = {"error": str(e)}

    return results, detailed_logs

@app.local_entrypoint()
def main():
    import json
    from dotenv import load_dotenv
    
    # Load .env file
    env_path = current_dir.parent / ".env"
    load_dotenv(env_path)
    
    hf_token = os.getenv("HF_TOKEN")
    hf_username = "quockietdev"
    
    if not hf_token:
        print("❌ Không tìm thấy HF_TOKEN trong file .env!")
        return

    print(f"Bắt đầu đẩy lệnh đánh giá lên Modal cho user: {hf_username}...")
    results, detailed_logs = evaluate_models.remote(hf_token, hf_username)
    
    # Lưu kết quả xuống máy tính cục bộ
    output_path = dataset_dir / "evaluation_results_v2.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    logs_path = dataset_dir / "evaluation_detailed_logs_v2.json"
    with open(logs_path, "w", encoding="utf-8") as f:
        json.dump(detailed_logs, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Hoàn tất toàn bộ! Kết quả đã được TẢI VỀ và lưu tại:")
    print(f"   - {output_path}")
    print(f"   - {logs_path}")
