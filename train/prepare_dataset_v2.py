import json
import os
import random
from datasets import load_dataset

def main():
    print("📥 Đang tải dataset hungnm/vietnamese-medical-qa (Version Cũ)...")
    dataset = load_dataset("hungnm/vietnamese-medical-qa", split="train")
    
    # Dataset features: ['question', 'answer']
    all_data = []
    for item in dataset:
        if item["question"] and item["answer"]:
            all_data.append({
                "question": item["question"].strip(),
                "answer": item["answer"].strip()
            })
            
    print(f"Tổng số câu ban đầu: {len(all_data)}")
    
    # Shuffle với seed cố định để luôn lấy ra cùng 1 bộ 100 câu Test
    random.seed(42)
    random.shuffle(all_data)
    
    # Chia theo tỉ lệ vàng chuẩn Machine Learning: 80% Train - 10% Valid - 10% Test
    total_size = len(all_data)
    train_size = int(total_size * 0.8)
    valid_size = int(total_size * 0.1)
    # Phần còn lại làm Test
    test_size = total_size - train_size - valid_size
    
    # 1. Tập Train (80%)
    train_data = all_data[:train_size]
    
    # 2. Tập Valid (10%)
    valid_data = all_data[train_size:train_size + valid_size]
    
    # 3. Tập Test Full (10%)
    test_full_data = all_data[train_size + valid_size:]
    
    # 4. Trích xuất đúng 100 câu từ tập Test Full làm bài thi nhanh (Test 100)
    test_100_data = test_full_data[:100]
    
    # Lưu vào thư mục dataset
    os.makedirs("dataset", exist_ok=True)
    
    with open("dataset/train_v2.json", "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=4)
        
    with open("dataset/valid_v2.json", "w", encoding="utf-8") as f:
        json.dump(valid_data, f, ensure_ascii=False, indent=4)
        
    with open("dataset/test_full_v2.json", "w", encoding="utf-8") as f:
        json.dump(test_full_data, f, ensure_ascii=False, indent=4)
        
    with open("dataset/test_100_v2.json", "w", encoding="utf-8") as f:
        json.dump(test_100_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Đã chia xong hoàn hảo cho V2 (Thành 4 file):")
    print(f"  - Tập Train    : {len(train_data)} câu (dataset/train_v2.json)")
    print(f"  - Tập Valid    : {len(valid_data)} câu (dataset/valid_v2.json)")
    print(f"  - Tập Test Full: {len(test_full_data)} câu (dataset/test_full_v2.json)")
    print(f"  - Tập Test 100 : {len(test_100_data)} câu (dataset/test_100_v2.json) -> Lấy từ Test Full")
    
if __name__ == "__main__":
    main()
