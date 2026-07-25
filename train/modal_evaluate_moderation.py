import modal
import os
from pathlib import Path

app = modal.App("clinic-moderation-evaluation")

current_dir = Path(__file__).parent
project_dir = current_dir.parent
data_dir = project_dir / "data"

image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("torch", "transformers", "accelerate", "bitsandbytes")
    .add_local_dir(local_path=str(data_dir), remote_path="/workspace/data")
)

volume = modal.Volume.from_name("clinic-model-vol", create_if_missing=True)

@app.function(
    image=image,
    volumes={"/storage": volume},
    gpu="H100",
    timeout=3600
)
def evaluate_moderation(hf_token: str, hf_username: str):
    import json
    import time
    import torch
    import re
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

    # =====================================================================
    # COPY LOGIC LỚP 1 VÀ PROMPT TỪ MODERATION.PY ĐỂ CHẠY ĐỘC LẬP TRÊN MODAL
    # =====================================================================
    TOXIC_KEYWORDS = [
        "địt", "đụ", "đéo", "đé0", "đoo", "cặc", "lồn", "buồi", "bùi", "nứng", "đụ má", "đậu má", 
        "chịch", "vcl", "đkm", "đm", "dkm", "dm", "vl", "cl", "sml", "đmm", "đb",
        "óc chó", "oc cho", "ngu l", "chó má", "cho ma", "đồ khốn", "đồ chó", "hãm l", "ham l",
        "mất dạy", "mat day", "vô học", "vo hoc", "khốn nạn", "khon nan", "đồ ngu", "thằng điên", 
        "con điên", "thằng chó", "ăn hại", "an hai", "đầu bò", "dau bo", "hãm tài", "ham tai",
        "fuck", "shit", "bitch", "asshole", "idiot", "motherfucker"
    ]

    SPAM_PATTERNS = [
        r"https?://\S+", r"www\.\S+",
        r"\b[a-zA-Z0-9.-]+\.(?:com|net|org|vn|edu|gov|xyz|club|me|info|io|tk|ml|ga|cf|gq)\b",
        r"t\.me/\S+", r"zalo\.me/\S+", r"fb\.me/\S+",
        r"(?:\+84|0)[35789](?:[\s.-]?\d){8}\b",
        r"(?:\+84|0)2(?:[\s.-]?\d){9}\b",
        r"@[a-zA-Z0-9_]{5,}\b"
    ]

    INCOHERENT_PATTERNS = [
        r"^[^a-zA-Zàáảãạăắặẳẵầấậẩẫâèéẻẽẹêếệểễơớợởỡôốộổỗưứựửữùúủũụìíỉĩịòóỏõọđ\s]{0,10}$",
        r"^(.)\1{4,}$",
        r"^[!?.,\s]{0,20}$",
    ]

    TOXIC_REGEX_PATTERNS = [
        r"đ\s*[\._\-]?\s*ị\s*[\._\-]?\s*t", r"đ\s*[\._\-]?\s*é\s*[\._\-]?\s*[o0]",
        r"c\s*[\._\-]?\s*ặ\s*[\._\-]?\s*c", r"l\s*[\._\-]?\s*ồ\s*[\._\-]?\s*n",
        r"b\s*[\._\-]?\s*u\s*[\._\-]?\s*ồ\s*[\._\-]?\s*i", r"\bđ\s*[\._\-]?\s*(?:k\s*[\._\-]?\s*)?m\b",
        r"\bv\s*[\._\-]?\s*(?:c\s*[\._\-]?\s*)?l\b", r"v\s*[\._\-]?\s*ã\s*[\._\-]?\s*i\s*[\._\-]?\s*[lđc]"
    ]

    MODERATION_SYSTEM_PROMPT = """Bạn là hệ thống kiểm duyệt bình luận chuyên nghiệp cho ứng dụng y tế phòng khám.

╔══════════════════════════════════════════════════════════════════╗
║              4 NHÓM QUY TẮC KIỂM DUYỆT CHI TIẾT                ║
╚══════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 1: [TOXIC] TỪ NGỮ THÔ TỤC / CÔNG KÍCH CÁ NHÂN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.1 TỪ CHỐI nếu có chửi thề, từ ngữ xúc phạm, tiếng lóng tục tĩu.
1.2 TỪ CHỐI nếu tấn công cá nhân bác sĩ/nhân viên bằng tên riêng kèm lời lẽ xúc phạm.
1.3 TỪ CHỐI nếu có lời đe dọa, uy hiếp, tống tiền, kêu gọi tẩy chay phối hợp.
1.4 TỪ CHỐI nếu kỳ thị giới tính, dân tộc, tôn giáo.
1.5 TỪ CHỐI nếu bình luận lan truyền tin đồn y tế thất thiệt, tung tin giả ác ý về phòng khám.
✅ CHO PHÉP phản hồi tiêu cực LỊCH SỰ (ví dụ: "Chờ đợi quá lâu", "Bác sĩ không nhiệt tình").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 2: [SPAM] TIN RÁC / QUẢNG CÁO NGOÀI LỀ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.1 TỪ CHỐI nếu chứa liên kết website, URL, đường dẫn bất kỳ.
2.2 TỪ CHỐI nếu chứa số điện thoại, địa chỉ email quảng cáo dịch vụ bên ngoài.
2.3 TỪ CHỐI nếu quảng cáo sản phẩm/thuốc/dịch vụ không thuộc phòng khám.
2.4 TỪ CHỐI nếu bình luận trông giống bot: lặp từ ngữ giống hệt nhau nhiều lần.
2.5 TỪ CHỐI nếu bình luận có ý đồ bôi nhọ, chơi xấu từ đối thủ (chê bai và lôi kéo bệnh nhân sang cơ sở khác).
✅ CHO PHÉP đề cập đến tên phòng khám hoặc bác sĩ trong ngữ cảnh đánh giá thật sự.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 3: [IRRELEVANT] KHÔNG LIÊN QUAN ĐẾN TRẢI NGHIỆM Y TẾ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.1 TỪ CHỐI nếu nội dung hoàn toàn không đề cập gì đến: khám bệnh, điều trị, bác sĩ,
    điều dưỡng, dược sĩ, cơ sở vật chất, thời gian chờ, giá cả khám chữa bệnh.
3.2 TỪ CHỐI nếu chia sẻ tin tức thời sự, chính trị, thể thao không liên quan đến y tế.
3.3 TỪ CHỐI nếu nội dung là truyện kể, thơ, câu đố không liên quan đến trải nghiệm khám.
✅ CHO PHÉP bình luận tổng quát như "Rất hài lòng", "Dịch vụ tốt", "Sẽ quay lại".
✅ CHO PHÉP đề cập cảm xúc/trải nghiệm cá nhân gắn với việc khám bệnh.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 4: [INCOHERENT] VÔ NGHĨA / GÕ LINH TINH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4.1 TỪ CHỐI nếu chỉ là chuỗi ký tự ngẫu nhiên không có nghĩa (ví dụ: "asdfghjkl", "qwerty123").
4.2 TỪ CHỐI nếu lặp lại 1 từ/cụm từ vô nghĩa (ví dụ: "oke oke oke", "haha haha haha").
4.3 TỪ CHỐI nếu chỉ có dấu câu, biểu tượng cảm xúc mà không có nội dung thực chất.
4.4 TỪ CHỐI nếu độ dài quá ngắn và không mang thông tin gì (dưới 5 từ không có nghĩa).
✅ CHO PHÉP bình luận ngắn nhưng có nội dung rõ ràng (ví dụ: "Rất tốt!", "Hài lòng.").

╔══════════════════════════════════════════════════════════════════╗
║      HƯỚNG DẪN XỬ LÝ SỐ SAO (RATING) NHẸ NHÀNG & HỢP LÝ          ║
╚══════════════════════════════════════════════════════════════════╝
- Đánh giá 1-2 sao (Sao quá thấp): Để bảo vệ hình ảnh và uy tín phòng khám, mọi đánh giá từ 1-2 sao đều BẮT BUỘC bị từ chối (thiết lập approved = false).
- Đánh giá 3-5 sao: Cho hiển thị nếu không có vi phạm. Tuy nhiên, nếu phát hiện bẫy phá rối (Đánh 5 sao nhưng bình luận chửi thề hoặc chèn quảng cáo) -> vẫn phải chặn (Approved = false).

╔══════════════════════════════════════════════════════════════════╗
║                   QUY TẮC PHÂN TÍCH                             ║
╚══════════════════════════════════════════════════════════════════╝
- Hãy đánh giá bình luận DỰA TRÊN NGỮ CẢNH TỔNG THỂ, không phán xét quá mức một từ riêng lẻ.
- Bình luận TIÊU CỰC LỊCH SỰ (phàn nàn, phê bình xây dựng) → VẪN CHO PHÉP.
- Bình luận CÓ DẤU HIỆU VI PHẠM RÕ RÀNG → TỪ CHỐI.
- Trường hợp KHÔNG CHẮC CHẮN → ƯU TIÊN CHO PHÉP (benefit of the doubt).

╔══════════════════════════════════════════════════════════════════╗
║                   FORMAT TRẢ LỜI BẮT BUỘC                       ║
╚══════════════════════════════════════════════════════════════════╝
Chỉ trả về JSON hợp lệ DUY NHẤT theo format sau, KHÔNG thêm bất kỳ văn bản nào khác:
{
  "approved": true/false,
  "violation_type": "CLEAN" | "TOXIC" | "SPAM" | "IRRELEVANT" | "INCOHERENT",
  "reason": "Lý do cụ thể bằng tiếng Việt (tối đa 100 từ)"
}
"""

    def quick_filter(comment, rating):
        comment_lower = comment.lower()
        if rating <= 2:
            return {"approved": False, "violation_type": "TOXIC", "reason": "Sao thấp"}
        if len(comment.strip()) < 3:
            return {"approved": True, "violation_type": "CLEAN", "reason": "Ngắn"}
        for pattern in INCOHERENT_PATTERNS:
            if re.fullmatch(pattern, comment.strip(), re.IGNORECASE | re.UNICODE):
                return {"approved": False, "violation_type": "INCOHERENT", "reason": "Vô nghĩa"}
        for pattern in TOXIC_REGEX_PATTERNS:
            if re.search(pattern, comment_lower, re.IGNORECASE):
                return {"approved": False, "violation_type": "TOXIC", "reason": "Chửi thề regex"}
        for keyword in TOXIC_KEYWORDS:
            if keyword in comment_lower:
                return {"approved": False, "violation_type": "TOXIC", "reason": "Từ thô tục"}
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, comment_lower, re.IGNORECASE):
                return {"approved": False, "violation_type": "SPAM", "reason": "Spam pattern"}
        return None

    def parse_llm_response(raw):
        json_candidates = re.findall(r'\{[^{}]+\}', raw, re.DOTALL)
        for candidate in json_candidates:
            try:
                data = json.loads(candidate)
                return {
                    "approved": bool(data.get("approved", True)),
                    "violation_type": str(data.get("violation_type", "UNKNOWN")),
                    "reason": str(data.get("reason", ""))
                }
            except json.JSONDecodeError:
                continue
        raw_lower = raw.lower()
        if "false" in raw_lower or "không" in raw_lower or "từ chối" in raw_lower:
            return {"approved": False, "violation_type": "UNKNOWN", "reason": "Parse failed but rejected"}
        return {"approved": True, "violation_type": "CLEAN", "reason": "Parse failed auto approve"}

    print("📥 Đang đọc 100 câu test kiểm duyệt từ file moderation_test_cases.json...")
    with open("/workspace/data/moderation_test_cases.json", "r", encoding="utf-8") as f:
        test_data = json.load(f)

    # ĐÁNH GIÁ CẢ 2 MÔ HÌNH ĐỂ SO SÁNH (Mô hình gốc vs Mô hình tinh chỉnh)
    models_to_test = {
        "qwen_base": "Qwen/Qwen2.5-7B-Instruct",
        "qwen_finetuned": f"{hf_username}/clinic-qwen-7b-v2"
    }

    results_summary = {}
    detailed_logs = {}
    
    bnb_config = BitsAndBytesConfig(load_in_4bit=True)
    
    for model_name, model_path in models_to_test.items():
        print(f"\n🚀 --- ĐANG ĐÁNH GIÁ MÔ HÌNH: {model_name.upper()} ---")
        detailed_logs[model_name] = []
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path, token=hf_token)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                quantization_config=bnb_config,
                token=hf_token
            )
            
            correct_approval = 0
            correct_violation = 0
            
            for idx, tc in enumerate(test_data):
                comment = tc["comment"]
                rating = tc["rating"]
                exp_appr = tc["expected_approved"]
                exp_viol = tc["expected_violation_type"]
                
                # Check Quick Filter (Lớp 1)
                quick_result = quick_filter(comment, rating)
                if quick_result is not None:
                    actual_appr = quick_result["approved"]
                    actual_viol = quick_result["violation_type"]
                    reason = quick_result["reason"]
                else:
                    # Chạy Lớp 2 bằng mô hình
                    user_prompt = f"Hãy kiểm duyệt bình luận sau của bệnh nhân theo đúng 4 nhóm quy tắc trong hướng dẫn:\n\nSố sao bệnh nhân chấm: {rating}/5\nNội dung bình luận: \"{comment}\"\n\nTrả về JSON theo đúng format yêu cầu."
                    
                    messages = [
                        {"role": "system", "content": MODERATION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ]
                    
                    try:
                        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    except Exception:
                        prompt = f"<|im_start|>system\n{MODERATION_SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
                        
                    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
                    with torch.no_grad():
                        outputs = model.generate(**inputs, max_new_tokens=200, do_sample=False)
                    
                    raw_response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                    
                    parsed = parse_llm_response(raw_response)
                    actual_appr = parsed["approved"]
                    actual_viol = parsed["violation_type"]
                    reason = parsed["reason"]
                    
                is_appr_correct = (actual_appr == exp_appr)
                is_viol_correct = (actual_viol == exp_viol)
                
                if is_appr_correct: correct_approval += 1
                if is_viol_correct: correct_violation += 1
                
                detailed_logs[model_name].append({
                    "id": tc["id"],
                    "comment": comment,
                    "expected_approved": exp_appr,
                    "actual_approved": actual_appr,
                    "expected_violation": exp_viol,
                    "actual_violation": actual_viol,
                    "reason": reason,
                    "is_appr_correct": is_appr_correct
                })
                
                if (idx + 1) % 20 == 0:
                    print(f"   Đã kiểm duyệt {idx + 1}/{len(test_data)} câu...")

            total = len(test_data)
            results_summary[model_name] = {
                "approval_accuracy": round((correct_approval / total) * 100, 2) if total > 0 else 0,
                "violation_accuracy": round((correct_violation / total) * 100, 2) if total > 0 else 0
            }
            print(f"✅ {model_name} - Độ chính xác Quyết định: {results_summary[model_name]['approval_accuracy']}%")
            
            del model
            del tokenizer
            torch.cuda.empty_cache()
            
        except Exception as e:
            print(f"❌ Lỗi khi đánh giá {model_name}: {e}")
            results_summary[model_name] = {"error": str(e)}
            
    return results_summary, detailed_logs

@app.local_entrypoint()
def main():
    import json
    from dotenv import load_dotenv
    
    env_path = current_dir.parent / ".env"
    load_dotenv(env_path)
    
    hf_token = os.getenv("HF_TOKEN")
    hf_username = "quockietdev" # Tên username trên Hugging Face
    
    if not hf_token:
        print("❌ Không tìm thấy HF_TOKEN trong file .env!")
        return

    print("🚀 Bắt đầu đẩy lệnh Đánh giá Kiểm duyệt lên Modal (Sẽ test cả Qwen Base và Qwen Finetuned)...")
    results_summary, detailed_logs = evaluate_moderation.remote(hf_token, hf_username)
    
    output_path = data_dir / "moderation_eval_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=4)
        
    logs_path = data_dir / "moderation_eval_detailed.json"
    with open(logs_path, "w", encoding="utf-8") as f:
        json.dump(detailed_logs, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Hoàn tất toàn bộ! Kết quả đánh giá trên H100 đã được TẢI VỀ máy và lưu tại:")
    print(f"   - {output_path}")
    print(f"   - {logs_path}")
