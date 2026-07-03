import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import argparse
import gc

def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-3B-Instruct", help="HuggingFace Hub ID of the base model")
    parser.add_argument("--adapter_path", type=str, default="../models/clinic-ai-lora", help="Path to the local LoRA adapter")
    parser.add_argument("--output_path", type=str, default="../models/clinic-ai-merged", help="Path to save the merged model")
    args = parser.parse_args()

    print("==================================================")
    print(f"1. Loading base model '{args.base_model}' in FP16 to RAM...")
    print("==================================================")
    # Load on CPU to avoid CUDA OOM errors during merge
    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16,
        device_map="cpu" 
    )
    
    print("\n==================================================")
    print(f"2. Loading LoRA adapter from '{args.adapter_path}'...")
    print("==================================================")
    model = PeftModel.from_pretrained(base_model, args.adapter_path)
    
    print("\n==================================================")
    print("3. Merging adapter into base model...")
    print("==================================================")
    model = model.merge_and_unload()
    
    print("\n==================================================")
    print(f"4. Saving merged model to '{args.output_path}'...")
    print("==================================================")
    model.save_pretrained(args.output_path)
    
    print("5. Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.adapter_path)
    tokenizer.save_pretrained(args.output_path)
    
    # Cleanup memory
    del model
    del base_model
    gc.collect()

    print("\n✅ Merge complete!")
    print("Next steps to convert to GGUF:")
    print("1. git clone https://github.com/ggerganov/llama.cpp.git")
    print("2. pip install -r llama.cpp/requirements.txt")
    print(f"3. python llama.cpp/convert_hf_to_gguf.py {args.output_path} --outfile ../models/clinic-ai-F16.gguf --outtype f16")

if __name__ == "__main__":
    main()
