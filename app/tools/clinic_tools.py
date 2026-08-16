from typing import Optional
from langchain_core.tools import tool

from app.clients.backend_client import BackendClient
from app.core.exceptions import BackendClientError
from app.schemas.domain_models import Specialty, Doctor, Service, ClinicInfo
from app.services.response_validator import ResponseValidator
from app.services.response_formatter import ResponseFormatter


@tool
def get_specialties_tool() -> str:
    """
    Dùng khi:
    - Người dùng hỏi phòng khám có những chuyên khoa nào.
    - Người dùng không biết nên chọn chuyên khoa nào và cần xem danh sách.
    
    TUYỆT ĐỐI KHÔNG dùng tool này để tìm bác sĩ hay lịch khám.
    """
    client = BackendClient()
    try:
        raw_data = client.get_specialties()
        validated_data = ResponseValidator.validate_list(raw_data, "chuyên khoa")
        
        # Mapper
        specialties = []
        for item in validated_data:
            specialties.append(Specialty(
                id=item.get("expertiseId") or item.get("id"),
                name=item.get("expertiseName") or item.get("name") or "Không rõ"
            ))
            
        # Formatter
        return ResponseFormatter.format_specialties(specialties)
    except ValueError as e:
        return str(e)
    except BackendClientError as e:
        return "Hệ thống Backend hiện không phản hồi."


@tool
def get_doctors_tool(expertise_name: Optional[str] = None, doctor_name: Optional[str] = None) -> str:
    """
    Dùng khi:
    - Người dùng hỏi danh sách bác sĩ chung.
    - Người dùng hỏi bác sĩ thuộc một chuyên khoa cụ thể (truyền expertise_name).
    - Người dùng tìm một bác sĩ cụ thể bằng tên (truyền doctor_name, ví dụ: "Tuấn").
    
    TUYỆT ĐỐI KHÔNG dùng tool này để kiểm tra lịch làm việc, lịch trống hay ngày làm việc.
    """
    # Chuẩn hoá: biến None / chuỗi rỗng về chuỗi trống để tránh lỗi .strip()
    expertise_name = (expertise_name or "").strip()
    doctor_name = (doctor_name or "").strip()

    client = BackendClient()
    try:
        expertise_id = None
        if expertise_name:
            raw_specialties = client.get_specialties()
            keyword = expertise_name.lower()
            if raw_specialties:
                for item in raw_specialties:
                    name = (item.get("expertiseName") or "").lower()
                    if keyword in name or name in keyword:
                        expertise_id = item.get("expertiseId")
                        break

        raw_doctors = client.get_doctors(expertise_id=expertise_id)
        
        if doctor_name:
            keyword_doc = doctor_name.strip().lower()
            # Loại bỏ các tiền tố để match chính xác hơn
            for prefix in ["bác sĩ ", "bac si ", "bác sỹ ", "bs ", "bs. ", "thạc sĩ ", "tiến sĩ "]:
                keyword_doc = keyword_doc.replace(prefix, "")
            keyword_doc = keyword_doc.strip()
            
            if raw_doctors:
                raw_doctors = [d for d in raw_doctors if keyword_doc in (d.get("fullName") or "").lower()]

        validated_doctors = ResponseValidator.validate_list(raw_doctors, "bác sĩ")
        
        # Mapper
        doctors = []
        for d in validated_doctors:
            doctors.append(Doctor(
                id=d.get("id"),
                name=d.get("fullName") or "Bác sĩ",
                expertise=d.get("expertiseName") or "Chuyên khoa",
                rating=d.get("rating"),
                patient_count=d.get("patientCount"),
                consultation_final_fee=d.get("consultationFinalFee")
            ))
            
        # Formatter
        return ResponseFormatter.format_doctors(doctors[:50])
    except ValueError as e:
        return str(e)
    except BackendClientError as e:
        return "Hệ thống Backend hiện không phản hồi."


@tool
def get_services_tool(featured_only: bool = False) -> str:
    """
    Dùng khi:
    - Người dùng hỏi về các dịch vụ xét nghiệm, chụp chiếu, gói khám.
    - Người dùng hỏi về giá tiền dịch vụ.
    - Đặt featured_only=true nếu người dùng hỏi dịch vụ nổi bật, khuyến mãi.
    """
    client = BackendClient()
    try:
        raw_services = client.get_services(featured_only=featured_only)
        validated_services = ResponseValidator.validate_list(raw_services, "dịch vụ nổi bật" if featured_only else "dịch vụ")
        
        # Mapper
        services = []
        for s in validated_services:
            services.append(Service(
                id=s.get("id"),
                name=s.get("serviceName") or "Dịch vụ",
                description=s.get("description"),
                original_price=s.get("originalPrice"),
                discount_amount=s.get("discountAmount")
            ))
            
        # Formatter
        return ResponseFormatter.format_services(services[:10], featured_only=featured_only)
    except ValueError as e:
        return str(e)
    except BackendClientError as e:
        return "Hệ thống Backend hiện không phản hồi."


@tool
def get_clinic_info_tool() -> str:
    """
    Dùng khi:
    - Người dùng hỏi giờ làm việc chung của phòng khám.
    - Người dùng hỏi địa chỉ, hotline, email của phòng khám.
    """
    client = BackendClient()
    try:
        raw_info = client.get_clinic_settings()
        validated_info = ResponseValidator.validate_dict(raw_info, "thông tin phòng khám")
        
        # Mapper
        info = ClinicInfo(
            name=validated_info.get("clinic_name"),
            address=validated_info.get("clinic_address"),
            phone=validated_info.get("clinic_phone"),
            email=validated_info.get("clinic_email"),
            working_hours=validated_info.get("working_hours")
        )
        
        # Formatter
        return ResponseFormatter.format_clinic_info(info)
    except ValueError as e:
        return str(e)
    except BackendClientError as e:
        # Fallback static info if backend is down or 403
        return """Thông tin phòng khám ClinicPro:
- Tên phòng khám: Phòng khám Đa khoa ClinicPro
- Địa chỉ: 71-73 Ngô Thời Nhiệm, Phường Võ Thị Sáu, Quận 3, TP.HCM
- Hotline: 1900 2115
- Email: cskh@clinic.com
- Giờ làm việc: 07:30 – 17:00 từ Thứ 2 đến Thứ 7 (Nghỉ Chủ Nhật)"""

@tool
def get_medical_records_tool(access_token: str | None = None) -> str:
    """
    Dùng khi người dùng hỏi về hồ sơ bệnh án hoặc kết quả khám bệnh của chính họ.
    """
    if not access_token:
        return "Lỗi: Khách chưa đăng nhập."
        
    client = BackendClient()
    try:
        raw_records = client.get_my_medical_records(access_token=access_token)
        if not raw_records:
            return "HỆ THỐNG BÁO: Hiện tại bạn chưa có hồ sơ bệnh án nào trong hệ thống."
            
        lines = ["Danh sách hồ sơ bệnh án của bạn:"]
        for r in raw_records[:5]:
            date_str = r.get("createdAt", "N/A")
            if "T" in date_str:
                date_str = date_str.split("T")[0]
                
            lines.append(f"- Ngày khám: {date_str}")
            lines.append(f"  Bác sĩ: {r.get('mainDoctorName', 'N/A')}")
            lines.append(f"  Trạng thái: {r.get('status', 'N/A')}")
            lines.append(f"  Chẩn đoán: {r.get('diagnosis') or 'Chưa có'}")
            lines.append(f"  Hướng điều trị: {r.get('treatment') or 'Chưa có'}")
            lines.append(f"  Ghi chú: {r.get('note') or 'Không có'}")
            
        return "\n".join(lines)
    except BackendClientError as e:
        error_msg = str(e)
        if "403" in error_msg or "401" in error_msg:
            return "Lỗi 403: Phiên đăng nhập hết hạn."
        return f"Lỗi Backend: {error_msg}."
    except Exception as e:
        return str(e)

