import re

file_path = r'd:\Information Technology\LV_CNTT\core_code\clinic-ai-chat\app\services\chat_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _get_history
content = content.replace(
    '''    def _get_history(self, session_id: str) -> list:
        return self._sessions.get(session_id, [])''',
    '''    def _get_history(self, session_id: str) -> list:
        history = self._sessions.get(session_id, [])
        return history[-6:] if len(history) > 6 else history'''
)

# Replace the CONFIRM_CANCEL text in send_message
content = content.replace(
    '''[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn muốn:\\n👉 Gõ **'Tiếp tục'** để nghe tư vấn (Hủy đặt lịch)\\n👉 Gõ **'Quay lại'** để tiếp tục đặt lịch''',
    '''[DIRECT_REPLY] Bạn đang trong quá trình đặt lịch khám. Nếu chuyển sang chủ đề khác, quá trình đặt lịch hiện tại sẽ bị hủy. Bạn muốn:\\n__BUTTON:Tiếp tục tư vấn__\\n__BUTTON:Quay lại đặt lịch__'''
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated chat_service.py")
