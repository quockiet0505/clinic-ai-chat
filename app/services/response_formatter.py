from typing import List
from app.schemas.domain_models import Specialty, Doctor, Service, ClinicInfo

class ResponseFormatter:
    """
    Formatting Layer: Nhận các Pydantic Models từ Mapper.
    Format chúng thành Markdown/Text chuẩn để nạp cho LLM.
    """

    @staticmethod
    def _format_price(value: float | None) -> str:
        if value is None:
            return "Liên hệ phòng khám"
        return f"{value:,.0f} VNĐ".replace(",", ".")

    @staticmethod
    def format_specialties(specialties: List[Specialty]) -> str:
        lines = ["Danh sách chuyên khoa:"]
        for spec in specialties:
            lines.append(f"- {spec.name}")
        return "\n".join(lines)

    @staticmethod
    def format_doctors(doctors: List[Doctor]) -> str:
        lines = ["Danh sách bác sĩ:"]
        for doc in doctors:
            extra = []
            if doc.rating is not None:
                extra.append(f"★ {doc.rating}")
            if doc.patient_count is not None:
                extra.append(f"{doc.patient_count} BN")
            suffix = f" ({', '.join(extra)})" if extra else ""
            
            fee_str = f" - Giá khám: {ResponseFormatter._format_price(doc.consultation_fee)}" if doc.consultation_fee else ""
            lines.append(f"• BS {doc.name}{fee_str}\n  Chuyên khoa {doc.expertise}{suffix}")
        return "\n".join(lines)

    @staticmethod
    def format_services(services: List[Service], featured_only: bool = False) -> str:
        title = "Dịch vụ nổi bật:" if featured_only else "Danh sách dịch vụ:"
        lines = [title]
        for srv in services:
            price = srv.discount_price if srv.discount_price is not None else srv.original_price
            price_str = ResponseFormatter._format_price(price)
            line = f"• {srv.name}: {price_str}"
            if srv.description:
                line += f"\n  Mô tả: {srv.description[:100]}..."
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def format_clinic_info(info: ClinicInfo) -> str:
        lines = ["Thông tin phòng khám:"]
        if info.name: lines.append(f"- Tên phòng khám: {info.name}")
        if info.address: lines.append(f"- Địa chỉ: {info.address}")
        if info.phone: lines.append(f"- Hotline: {info.phone}")
        if info.email: lines.append(f"- Email: {info.email}")
        if info.working_hours: lines.append(f"- Giờ làm việc: {info.working_hours}")
        
        if len(lines) == 1:
            return "Thông tin phòng khám ClinicPro:\n- Giờ làm việc: 7:00 - 19:00 hàng ngày"
        return "\n".join(lines)
