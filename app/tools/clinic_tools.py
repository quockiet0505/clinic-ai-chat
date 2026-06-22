from langchain_core.tools import tool

from app.clients.backend_client import BackendClient
from app.core.exceptions import BackendClientError


def _format_price(value) -> str:
    try:
        number = float(value)
        return f"{number:,.0f} VND".replace(",", ".")
    except (TypeError, ValueError):
        return "Liên hệ phòng khám"


@tool
def get_specialties_tool() -> str:
    """Lấy danh sách chuyên khoa của phòng khám. Dùng khi bệnh nhân hỏi về chuyên khoa hoặc cần gợi ý khám ở khoa nào."""
    client = BackendClient()
    try:
        specialties = client.get_specialties()
        if not specialties:
            return "Hiện chưa có dữ liệu chuyên khoa trong hệ thống."

        lines = ["Danh sách chuyên khoa:"]
        for item in specialties[:15]:
            name = item.get("expertiseName") or item.get("name") or "Không rõ"
            lines.append(f"- {name}")
        return "\n".join(lines)
    except BackendClientError as exc:
        return f"Không lấy được danh sách chuyên khoa: {exc}"


@tool
def get_doctors_tool(expertise_name: str = "") -> str:
    """
    Lấy danh sách bác sĩ. Có thể lọc theo tên chuyên khoa (expertise_name) nếu bệnh nhân đã chọn chuyên khoa.
    """
    client = BackendClient()
    try:
        expertise_id = None
        if expertise_name.strip():
            specialties = client.get_specialties()
            keyword = expertise_name.strip().lower()
            for item in specialties:
                name = (item.get("expertiseName") or "").lower()
                if keyword in name or name in keyword:
                    expertise_id = item.get("expertiseId")
                    break

        doctors = client.get_doctors(expertise_id=expertise_id)
        if not doctors:
            return "Hiện chưa có bác sĩ phù hợp trong hệ thống."

        lines = ["Danh sách bác sĩ:"]
        for doctor in doctors[:10]:
            name = doctor.get("fullName") or "Bác sĩ"
            specialty = doctor.get("expertiseName") or "Chuyên khoa"
            rating = doctor.get("rating")
            patients = doctor.get("patientCount")
            extra = []
            if rating is not None:
                extra.append(f"★ {rating}")
            if patients is not None:
                extra.append(f"{patients} BN")
            suffix = f" ({', '.join(extra)})" if extra else ""
            lines.append(f"- {name} - {specialty}{suffix}")
        return "\n".join(lines)
    except BackendClientError as exc:
        return f"Không lấy được danh sách bác sĩ: {exc}"


@tool
def get_services_tool(featured_only: bool = False) -> str:
    """
    Lấy danh sách dịch vụ/gói khám. Đặt featured_only=true nếu bệnh nhân hỏi dịch vụ nổi bật hoặc khuyến mãi.
    """
    client = BackendClient()
    try:
        services = client.get_services(featured_only=featured_only)
        if not services:
            label = "nổi bật" if featured_only else ""
            return f"Hiện chưa có dịch vụ {label} trong hệ thống.".strip()

        lines = ["Danh sách dịch vụ:" if not featured_only else "Dịch vụ nổi bật:"]
        for service in services[:10]:
            name = service.get("serviceName") or "Dịch vụ"
            description = service.get("description") or ""
            original = service.get("originalPrice")
            discount = service.get("discountPrice")
            price = discount or original
            line = f"- {name}: {_format_price(price)}"
            if description:
                line += f" | {description[:80]}"
            lines.append(line)
        return "\n".join(lines)
    except BackendClientError as exc:
        return f"Không lấy được danh sách dịch vụ: {exc}"


@tool
def get_clinic_info_tool() -> str:
    """Lấy thông tin phòng khám: hotline, địa chỉ, giờ làm việc... Dùng khi bệnh nhân hỏi thông tin liên hệ."""
    client = BackendClient()
    try:
        settings_map = client.get_clinic_settings()
        if not settings_map:
            return (
                "Thông tin phòng khám ClinicPro:\n"
                "- Giờ làm việc: 7:00 - 19:00 hàng ngày\n"
                "- Vui lòng liên hệ quầy lễ tân để biết thêm chi tiết."
            )

        labels = {
            "clinic_name": "Tên phòng khám",
            "clinic_address": "Địa chỉ",
            "clinic_phone": "Hotline",
            "clinic_email": "Email",
            "working_hours": "Giờ làm việc",
        }
        lines = ["Thông tin phòng khám:"]
        for key, label in labels.items():
            if key in settings_map and settings_map[key]:
                lines.append(f"- {label}: {settings_map[key]}")
        return "\n".join(lines) if len(lines) > 1 else "Chưa có cấu hình thông tin phòng khám."
    except BackendClientError as exc:
        return f"Không lấy được thông tin phòng khám: {exc}. Giờ làm việc mặc định: 7:00 - 19:00."
