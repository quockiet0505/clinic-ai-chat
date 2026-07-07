import re

def fix_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix the bad syntax
    if "num_ctx=4096,settings.LLM_TEMPERATURE," in content:
        content = content.replace(
            "temperature=\n            num_ctx=4096,settings.LLM_TEMPERATURE,",
            "temperature=settings.LLM_TEMPERATURE,\n            num_ctx=4096,"
        )
    elif "num_ctx=4096,0.0," in content:
        content = content.replace(
            "temperature=\n            num_ctx=4096,0.0,",
            "temperature=0.0,\n            num_ctx=4096,"
        )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed {file_path}")

fix_file(r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\llm_service.py')
fix_file(r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\query_analyzer.py')
