import re

file_path = r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\chat_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''        generic_phrases = [
            "đặt lịch", "đặt khám", "đặt lịch khám", "đặt lịch khám bệnh", "tôi muốn đặt lịch", "cho tôi đặt lịch",
            "bác sĩ", "danh sách bác sĩ", "tìm bác sĩ", 
            "khoa nào", "khám khoa nào"
        ]''',
    '''        generic_phrases = [
            "đặt lịch", "đặt khám", "đặt lịch khám", "đặt lịch khám bệnh", "tôi muốn đặt lịch", "cho tôi đặt lịch",
            "bác sĩ", "danh sách bác sĩ", "tìm bác sĩ", 
            "khoa nào", "khám khoa nào",
            "chuyên khoa", "các chuyên khoa", "danh sách chuyên khoa", "chuyen khoa", "cac chuyen khoa",
            "giờ làm việc", "phòng khám", "ở đâu", "địa chỉ", "liên hệ", "giá", "dịch vụ"
        ]'''
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated chat_service.py generic phrases")
