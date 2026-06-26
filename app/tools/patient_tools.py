from langchain_core.tools import tool

from app.clients.backend_client import BackendClient
from app.core.exceptions import BackendClientError


@tool
def register_patient_tool(email: str, password: str, full_name: str, phone: str) -> str:
    """
    Dùng khi:
    - Người dùng chưa có tài khoản và muốn đăng ký tài khoản mới.
    - Người dùng muốn tạo tài khoản để đặt lịch khám.
    
    Tham số:
    email: email của bệnh nhân (bắt buộc)
    password: mật khẩu (bắt buộc)
    full_name: họ và tên (bắt buộc)
    phone: số điện thoại (bắt buộc)
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
