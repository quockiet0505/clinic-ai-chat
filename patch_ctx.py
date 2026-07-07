import re

def patch_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # If it already has num_ctx, don't add it
    if "num_ctx" not in content:
        content = re.sub(
            r"(model=.*?,\s*base_url=.*?,\s*temperature=.*?,?)",
            r"\1\n            num_ctx=4096,",
            content,
            flags=re.DOTALL
        )
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {file_path}")
    else:
        print(f"Already patched {file_path}")

patch_file(r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\llm_service.py')
patch_file(r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\query_analyzer.py')
