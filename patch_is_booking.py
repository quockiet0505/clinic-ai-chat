import re

file_path = r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\chat_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the is_booking initialization
content = content.replace(
    '''        is_booking = bool(memory_params.get("target_type"))''',
    '''        is_booking = memory_params.get("is_booking", False) or bool(memory_params.get("target_type"))'''
)

# Replace the intent classification block to set is_booking=True if intent=="BOOKING"
# We need to find where intent is assigned and set memory_params["is_booking"] = True if it's BOOKING
# Let's just do it right before the Bắt buộc khóa luồng lại comment
replace_block = '''        else:
            intent = fast_intent
            
        if intent == "BOOKING":
            memory_params["is_booking"] = True
            is_booking = True
            
        # Bắt buộc khóa luồng lại nếu đang đặt lịch dở dang'''

content = content.replace(
    '''        else:
            intent = fast_intent
            
        # Bắt buộc khóa luồng lại nếu đang đặt lịch dở dang''',
    replace_block
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching is_booking")
