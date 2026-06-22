from langchain_core.tools import tool

from app.clients.backend_client import BackendClient
from app.core.exceptions import BackendClientError


@tool
def register_patient_tool(email: str, password: str, full_name: str, phone: str) -> str:
    """
    Đăng ký tài khoản mới cho bệnh nhân bằng email, mật khẩu, họ tên và số điện thoại.
    Chỉ dùng khi người dùng là khách (chưa có tài khoản) nhưng muốn đặt lịch khám.
    """
    client = BackendClient()
    try:
        result = client.register_patient(
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
        )
        account_id = result.get("accountId", "N/A")
        return f"Đã tạo tài khoản thành công. Mã tài khoản: {account_id}. Bạn có thể tiếp tục đặt lịch khám."
    except BackendClientError as exc:
        return f"Tạo tài khoản thất bại: {exc}"
