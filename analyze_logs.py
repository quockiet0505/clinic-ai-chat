import json, os
log_dir = r'D:\Information Technology\LV_CNTT\core_code\clinic-frontend\admin-web\src\assets\data\ai_logs'

files = {
    'Qwen V1': 'qwen_log.json',
    'Qwen V2': 'qwen_trainer_state_v2.json',
    'SeaLLM V1': 'seallm_log.json',
    'SeaLLM V2': 'seallm_trainer_state_v2.json',
    'VinaLlama V1': 'llama_log.json',
    'VinaLlama V2': 'vinallama_trainer_state_v2.json'
}

for name, fname in files.items():
    path = os.path.join(log_dir, fname)
    if not os.path.exists(path):
        print(f'{name}: FILE NOT FOUND')
        continue
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logs = data.get('log_history', [])
    eval_logs = [x for x in logs if 'eval_loss' in x]
    train_logs = [x for x in logs if 'loss' in x]
    
    if eval_logs:
        last_eval = eval_logs[-1]['eval_loss']
    else:
        last_eval = 'N/A'
        
    if train_logs:
        last_train = train_logs[-1]['loss']
    else:
        last_train = 'N/A'
        
    print(f'{name}: Final Eval Loss: {last_eval} | Final Train Loss: {last_train}')
