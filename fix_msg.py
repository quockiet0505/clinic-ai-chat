import re

file_path = r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\chat_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn có muốn tiếp tục không?\\n[Tiếp tục tư vấn] | [Quay lại đặt lịch]''',
    '''[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn muốn:\\n👉 Gõ **'Tiếp tục'** để nghe tư vấn (Hủy đặt lịch)\\n👉 Gõ **'Quay lại'** để tiếp tục đặt lịch'''
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
