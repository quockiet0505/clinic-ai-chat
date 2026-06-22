from langchain_core.tools import tool

from app.clients.backend_client import BackendClient
from app.core.exceptions import BackendClientError
from app.rag.retriever import KnowledgeRetriever


def _find_doctor_id(client: BackendClient, doctor_name: str) -> int | None:
    doctors = client.get_doctors()
    keyword = doctor_name.strip().lower()
    if not keyword:
        return None

    for doctor in doctors:
        full_name = (doctor.get("fullName") or "").lower()
        if keyword in full_name or full_name in keyword:
            return doctor.get("staffId")

    return None


def _find_expertise_id(client: BackendClient, expertise_name: str) -> int | None:
    keyword = expertise_name.strip().lower()
    if not keyword:
        return None
    for item in client.get_specialties():
        name = (item.get("expertiseName") or "").lower()
        if keyword in name or name in keyword:
            return item.get("expertiseId")
    return None


def _suggest_expertise_from_symptoms(symptoms: str) -> str:
    retriever = KnowledgeRetriever()
    context = retriever.retrieve(symptoms)
    return context or "Không có gợi ý cụ thể từ FAQ."


@tool
def get_available_slots_tool(
    appointment_date: str,
    doctor_name: str = "",
    expertise_name: str = "",
    service_name: str = "",
) -> str:
    """
    Kiểm tra khung giờ trống theo ngày.
    appointment_date: YYYY-MM-DD
    doctor_name: tên bác sĩ (ưu tiên nếu có)
    expertise_name: chuyên khoa (nếu chưa chọn bác sĩ)
    service_name: tên dịch vụ xét nghiệm/chụp (mode SERVICE)
    """
    client = BackendClient()
    try:
        doctor_id = None
        expertise_id = None
        service_id = None

        if doctor_name.strip():
            doctor_id = _find_doctor_id(client, doctor_name)
            if doctor_id is None:
                return f"Không tìm thấy bác sĩ '{doctor_name}'. Gọi get_doctors_tool để xem danh sách."
        elif expertise_name.strip():
            expertise_id = _find_expertise_id(client, expertise_name)
            if expertise_id is None:
                return f"Không tìm thấy chuyên khoa '{expertise_name}'."
        elif service_name.strip():
            services = client.get_services()
            keyword = service_name.strip().lower()
            for svc in services:
                if keyword in (svc.get("serviceName") or "").lower():
                    service_id = svc.get("serviceId")
                    break
            if service_id is None:
                return f"Không tìm thấy dịch vụ '{service_name}'."

        slots = client.get_available_slots(
            appointment_date=appointment_date,
            doctor_id=doctor_id,
            expertise_id=expertise_id,
            service_id=service_id,
        )
        available = [s for s in slots if s.get("isAvailable")]

        if not available:
            return f"Không còn giờ trống ngày {appointment_date} với tiêu chí đã chọn."

        label = doctor_name or expertise_name or service_name or "lịch khám"
        lines = [f"Giờ trống ({label}) ngày {appointment_date}:"]
        for slot in available[:12]:
            start = str(slot.get("timeStart") or "--:--")[:5]
            end = str(slot.get("timeEnd") or "")[:5]
            doc = slot.get("doctorName") or ""
            suffix = f" — BS {doc}" if doc else ""
            lines.append(f"- {start}" + (f" - {end}" if end else "") + suffix)
        return "\n".join(lines)
    except BackendClientError as exc:
        return f"Không kiểm tra được giờ trống: {exc}"


@tool
def suggest_expertise_tool(symptoms: str) -> str:
    """
    Gợi ý chuyên khoa tham khảo từ triệu chứng (không chẩn đoán).
    symptoms: mô tả triệu chứng của bệnh nhân
    """
    client = BackendClient()
    rag_hint = _suggest_expertise_from_symptoms(symptoms)
    try:
        specialties = client.get_specialties()
        names = [s.get("expertiseName") for s in specialties[:8] if s.get("expertiseName")]
        return (
            "Gợi ý tham khảo từ triệu chứng:\n"
            f"{rag_hint}\n\n"
            "Chuyên khoa trên hệ thống: " + ", ".join(names)
            + "\n\nĐây chỉ là gợi ý ban đầu, không thay thế chẩn đoán bác sĩ."
        )
    except BackendClientError as exc:
        return f"{rag_hint}\n\n(Không tải được danh sách chuyên khoa: {exc})"


@tool
def book_appointment_tool(
    appointment_date: str,
    time_start: str,
    time_end: str,
    booking_mode: str,
    note: str,
    doctor_name: str = "",
    expertise_name: str = "",
    service_name: str = "",
    suggested_expertise_name: str = "",
    access_token: str = "",
) -> str:
    """
    Đặt lịch hộ bệnh nhân (cần đăng nhập — token được hệ thống tự gắn).
    booking_mode: DOCTOR | EXPERTISE | SERVICE | DIRECT
    time_start/time_end: HH:MM:SS (vd 09:00:00, 09:30:00)
    suggested_expertise_name: chuyên khoa AI gợi ý (nếu khác chuyên khoa bệnh nhân chọn)
    """
    if not access_token or not access_token.strip():
        return (
            "Không thể đặt lịch tự động vì bạn chưa đăng nhập. "
            "Vui lòng đăng nhập trên app/website rồi thử lại, hoặc tự đặt tại mục Đặt lịch."
        )

    client = BackendClient()
    mode = booking_mode.strip().upper()
    if mode not in {"DOCTOR", "EXPERTISE", "SERVICE", "DIRECT"}:
        return "booking_mode phải là DOCTOR, EXPERTISE, SERVICE hoặc DIRECT."

    payload: dict = {
        "appointmentDate": appointment_date,
        "timeStart": time_start if len(time_start) > 5 else f"{time_start}:00",
        "timeEnd": time_end if len(time_end) > 5 else f"{time_end}:00",
        "appointmentType": "ONLINE",
        "createdBy": "PATIENT",
        "bookingMode": mode,
        "note": note,
        "isAiSuggested": True,
    }

    try:
        if doctor_name.strip():
            doc_id = _find_doctor_id(client, doctor_name)
            if doc_id:
                payload["mainDoctorId"] = doc_id
        if expertise_name.strip():
            exp_id = _find_expertise_id(client, expertise_name)
            if exp_id:
                payload["expertiseId"] = exp_id
        if service_name.strip():
            for svc in client.get_services():
                if service_name.strip().lower() in (svc.get("serviceName") or "").lower():
                    payload["serviceId"] = svc.get("serviceId")
                    break
        if suggested_expertise_name.strip():
            sug_id = _find_expertise_id(client, suggested_expertise_name)
            if sug_id:
                payload["suggestedExpertiseId"] = sug_id

        result = client.create_appointment(payload, access_token.strip())
        apt_id = result.get("appointmentId") or result.get("appointment_id")
        return f"Đã tạo lịch hẹn thành công (mã #{apt_id}). Trạng thái: PENDING — chờ phòng khám xác nhận."
    except BackendClientError as exc:
        return f"Không đặt được lịch: {exc}. Bạn có thể tự đặt trên app/website."
