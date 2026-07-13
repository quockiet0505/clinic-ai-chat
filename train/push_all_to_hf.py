import os
import modal

volume = modal.Volume.from_name("clinic-model-vol")
app = modal.App("push-all-to-hf")

image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install("huggingface_hub")
)

@app.function(
    image=image,
    volumes={"/storage": volume},
    timeout=14400 # Cho phép chạy tối đa 4 tiếng
)
def push_full_backup(hf_token: str, hf_username: str):
    from huggingface_hub import HfApi, create_repo
    api = HfApi(token=hf_token)
    
    models = {
        "Qwen": {
            "repo": f"{hf_username}/clinic-qwen-7b-v2",
            "folders": {
                "/storage/clinic_qwen_7b_merged_v2": "",            # Thư mục gốc
                "/storage/checkpoints_qwen_v2": "checkpoints",      # Bao gồm cả file Log ở bên trong
                "/storage/clinic_qwen_7b_lora_v2": "lora_adapter"
            }
        },
        "SeaLLM": {
            "repo": f"{hf_username}/clinic-seallm-7b-v2",
            "folders": {
                "/storage/clinic_seallm_7b_merged_v2": "",
                "/storage/checkpoints_seallm_v2": "checkpoints",
                "/storage/clinic_seallm_7b_lora_v2": "lora_adapter"
            }
        },
        "VinaLlama": {
            "repo": f"{hf_username}/clinic-vinallama-7b-v2",
            "folders": {
                "/storage/clinic_vinallama_7b_merged_v2": "",
                "/storage/checkpoints_vinallama_v2": "checkpoints",
                "/storage/clinic_vinallama_7b_lora_v2": "lora_adapter"
            }
        }
    }

    print("✅ Đã kết nối Hugging Face thành công!")
    for name, info in models.items():
        repo_id = info["repo"]
        print(f"\n=======================================================")
        print(f"🚀 XỬ LÝ MÔ HÌNH: {name} ({repo_id})")
        print(f"=======================================================")
        
        # Tạo kho (nếu chưa có)
        create_repo(repo_id=repo_id, private=True, exist_ok=True, token=hf_token)
        
        # Upload tuần tự các thư mục
        for local_path, remote_path in info["folders"].items():
            if os.path.exists(local_path):
                dest_msg = remote_path if remote_path else "thư mục gốc (Root)"
                print(f"⏳ Đang upload '{local_path}' lên '{dest_msg}'...")
                try:
                    api.upload_folder(
                        folder_path=local_path,
                        path_in_repo=remote_path,
                        repo_id=repo_id,
                        repo_type="model"
                    )
                    print(f"✅ Xong: {local_path}")
                except Exception as e:
                    print(f"❌ Lỗi khi upload {local_path}: {e}")
            else:
                print(f"⚠️ BỎ QUA: Không tìm thấy '{local_path}' trong Modal.")

@app.local_entrypoint()
def main(hf_token: str, hf_username: str):
    print("Khởi động tiến trình đồng bộ toàn diện lên Hugging Face...")
    push_full_backup.remote(hf_token, hf_username)
