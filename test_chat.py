import requests
import time
import uuid
import datetime

BASE_URL = "http://127.0.0.1:8000/api/v1/chat"
BACKEND_URL = "http://127.0.0.1:8080/api/v1"

def get_auth_token() -> str:
    test_email = f"test_{int(time.time())}@clinic.com"
    test_pwd = "password123"
    
    requests.post(f"{BACKEND_URL}/auth/patient/register", json={
        "email": test_email,
        "password": test_pwd,
        "fullName": "Test Patient",
        "phone": "0901234567"
    })
    
    login_res = requests.post(f"{BACKEND_URL}/auth/patient/login", json={
        "email": test_email,
        "password": test_pwd
    })
    
    if login_res.status_code == 200:
        data = login_res.json()
        return data.get("data", {}).get("token", "")
    return ""

def send_chat(message: str, session_id: str, access_token: str) -> str:
    response = requests.post(f"{BASE_URL}/stream", json={
        "message": message,
        "session_id": session_id,
        "access_token": access_token
    }, stream=True)
    
    full_text = ""
    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith('data: '):
                txt = decoded[6:]
                print(txt, end="", flush=True)
                full_text += txt
    print()
    return full_text

def run_flow(name: str, msgs: list, log_path: str, access_token: str, clear: bool = False):
    session_id = str(uuid.uuid4())
    mode = "w" if clear else "a"
    with open(log_path, mode, encoding="utf-8") as f:
        f.write(f"=== {name.upper()} FLOW ===\n")
        
        # Test without token first
        print(f"\nUser ({name}) [NO TOKEN]: {msgs[0]}")
        reply_no_token = send_chat(msgs[0], session_id, "")
        f.write(f"User: {msgs[0]} [No Token]\nAI: {reply_no_token}\n\n")
        time.sleep(1)
        
        for m in msgs:
            print(f"\nUser ({name}): {m}")
            reply = send_chat(m, session_id, access_token)
            f.write(f"User: {m}\nAI: {reply}\n\n")
            f.flush()
            time.sleep(1)
        f.write("=== END OF FLOW ===\n\n")

if __name__ == "__main__":
    print("Getting access token...")
    token = get_auth_token()
    print(f"Token obtained: {token[:20]}...")
    
    log_file = "chat_log.txt"
    book_date = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    
    print("\n--- Bắt đầu Luồng 1: Đặt lịch Bác sĩ / Chuyên khoa ---")
    doctor_msgs = [
        "Tôi muốn đặt lịch khám bệnh",
        "Bác sĩ Lê Tuấn",
        book_date,
        "08:00",
        "Tôi bị đau bụng âm ỉ"
    ]
    run_flow("doctor", doctor_msgs, log_file, token, clear=True)
    
    print("\n--- Bắt đầu Luồng 2: Đặt lịch Dịch vụ ---")
    service_msgs = [
        "Tôi muốn đặt lịch xét nghiệm",
        "Xét nghiệm máu",
        book_date,
        "09:00",
        "Kiểm tra sức khỏe định kỳ"
    ]
    run_flow("service", service_msgs, log_file, token, clear=False)
