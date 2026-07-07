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
        lines = ["Dạ, dưới đây là một số chuyên khoa tại phòng khám ClinicPro:"]
        for spec in specialties[:10]:
            lines.append(f"- Chuyên khoa {spec.name}")
        if len(specialties) > 10:
            lines.append(f"\n(...và {len(specialties) - 10} chuyên khoa khác.) Bạn đang cần khám chuyên khoa nào ạ?")
        return "\n".join(lines)

    @staticmethod
    def format_doctors(doctors: List[Doctor]) -> str:
        lines = ["Dạ, đây là một số bác sĩ tại phòng khám ClinicPro:"]
        for doc in doctors[:10]:
            extra = []
            if doc.rating is not None:
                extra.append(f"★ {doc.rating}")
            if doc.patient_count is not None:
                extra.append(f"{doc.patient_count} BN")
            suffix = f" ({', '.join(extra)})" if extra else ""
            
            fee_str = f" - Giá khám: {ResponseFormatter._format_price(doc.consultation_fee)}" if doc.consultation_fee else ""
            
            doc_name = doc.name
            if doc_name.lower().startswith("bác sĩ") or doc_name.lower().startswith("bs"):
                formatted_name = doc_name
            else:
                formatted_name = f"Bác sĩ {doc_name}"
                
            lines.append(f"- {formatted_name}{fee_str}\n  Chuyên khoa: {doc.expertise}{suffix}")
        
        if len(doctors) > 10:
            lines.append(f"\n(...và {len(doctors) - 10} bác sĩ khác.) Bạn muốn tìm bác sĩ theo chuyên khoa nào ạ?")
        return "\n".join(lines)

    @staticmethod
    def format_services(services: List[Service], featured_only: bool = False) -> str:
        title = "Dạ, đây là các dịch vụ xét nghiệm/chụp chiếu nổi bật tại phòng khám:" if featured_only else "Dạ, đây là danh sách các dịch vụ tại phòng khám:"
        lines = [title]
        for srv in services[:10]:
            price = srv.discount_price if srv.discount_price is not None else srv.original_price
            price_str = ResponseFormatter._format_price(price)
            line = f"- {srv.name}: {price_str}"
            if srv.description:
                line += f"\n  Mô tả: {srv.description[:100]}..."
            lines.append(line)
        if len(services) > 10:
            lines.append(f"\n(...và {len(services) - 10} dịch vụ khác.) Bạn muốn biết thêm dịch vụ nào ạ?")
        return "\n".join(lines)

    @staticmethod
    def format_clinic_info(info: ClinicInfo) -> str:
        lines = ["Dạ, dưới đây là thông tin chi tiết về phòng khám ClinicPro:"]
        if info.name: lines.append(f"- Tên phòng khám: {info.name}")
        if info.address: lines.append(f"- Địa chỉ: {info.address}")
        if info.phone: lines.append(f"- Hotline: {info.phone}")
        if info.email: lines.append(f"- Email: {info.email}")
        if info.working_hours: lines.append(f"- Giờ làm việc: {info.working_hours}")
        
        if len(lines) == 1:
            return "Dạ, phòng khám ClinicPro mở cửa hoạt động từ 7:00 đến 19:00 hàng ngày (từ Thứ 2 đến Thứ 7, nghỉ Chủ Nhật)."
            
        return "\n".join(lines)
