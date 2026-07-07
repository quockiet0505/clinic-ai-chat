import re

file_path = r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\chat_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make DOCTOR_INFO and CLINIC_INFO return [DIRECT_REPLY] so they bypass the LLM and TTFT drops to 0.
# We will do this by appending [DIRECT_REPLY] to the knowledge block if intent is DOCTOR_INFO or CLINIC_INFO

content = content.replace(
    '''        elif intent == "DOCTOR_INFO":
            from app.tools.clinic_tools import get_doctors_tool
            knowledge = get_doctors_tool.invoke({})
        elif intent == "CLINIC_INFO":
            from app.tools.clinic_tools import get_services_tool, get_clinic_info_tool
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in ["giá", "dịch vụ", "xét nghiệm", "chi phí", "bao nhiêu"]):
                knowledge = get_services_tool.invoke({"featured_only": False})
            else:
                knowledge = get_clinic_info_tool.invoke({})''',
    '''        elif intent == "DOCTOR_INFO":
            from app.tools.clinic_tools import get_doctors_tool
            knowledge = "[DIRECT_REPLY] " + get_doctors_tool.invoke({})
        elif intent == "CLINIC_INFO":
            from app.tools.clinic_tools import get_services_tool, get_clinic_info_tool
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in ["giá", "dịch vụ", "xét nghiệm", "chi phí", "bao nhiêu"]):
                knowledge = "[DIRECT_REPLY] " + get_services_tool.invoke({"featured_only": False})
            else:
                knowledge = "[DIRECT_REPLY] " + get_clinic_info_tool.invoke({})'''
)

# Wait, there are TWO places where knowledge is evaluated (send_message and stream_message)
# It's better to just replace the blocks directly. Let's do it using Regex to handle both functions.

content = re.sub(
    r'knowledge = get_doctors_tool\.invoke\(\{\}\)',
    r'knowledge = "[DIRECT_REPLY]\n" + get_doctors_tool.invoke({})',
    content
)

content = re.sub(
    r'knowledge = get_services_tool\.invoke\(\{"featured_only": False\}\)',
    r'knowledge = "[DIRECT_REPLY]\n" + get_services_tool.invoke({"featured_only": False})',
    content
)

content = re.sub(
    r'knowledge = get_clinic_info_tool\.invoke\(\{\}\)',
    r'knowledge = "[DIRECT_REPLY]\n" + get_clinic_info_tool.invoke({})',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated chat_service.py to use DIRECT_REPLY for DOCTOR_INFO and CLINIC_INFO")
