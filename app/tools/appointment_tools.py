from langchain_core.tools import tool

from app.clients.backend_client import BackendClient
from app.core.exceptions import BackendClientError
from app.rag.retriever import KnowledgeRetriever


import unicodedata

def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    text = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return text.replace('đ', 'd').replace('Đ', 'd')

def _find_doctor_id(client: BackendClient, doctor_name: str, expertise_id: int | None = None) -> int | None:
    doctors = client.get_doctors(expertise_id=expertise_id)
    keyword = remove_accents(doctor_name.strip()).lower()
    if not keyword:
        return None

    for doctor in doctors:
        full_name = remove_accents(doctor.get("fullName") or "").lower()
        if keyword in full_name or full_name in keyword:
            return doctor.get("staffId")

    return None


def _find_expertise_id(client: BackendClient, expertise_name: str) -> int | None:
    keyword = remove_accents(expertise_name.strip()).lower()
    if not keyword:
        return None
    for item in client.get_specialties():
        name = remove_accents(item.get("expertiseName") or "").lower()
        if keyword in name or name in keyword:
            return item.get("expertiseId")
    return None


def _find_bookable_service_id(client: BackendClient, service_name: str) -> int | None:
    keyword = service_name.strip().lower()
    if not keyword:
        return None
    for svc in client.get_services(bookable_only=True):
        name = (svc.get("serviceName") or "").lower()
        if keyword in name or name in keyword:
            return svc.get("serviceId")
    return None


def _suggest_expertise_from_symptoms(symptoms: str) -> str:
    retriever = KnowledgeRetriever()
    context = retriever.retrieve(symptoms)
    return context or "Không có gợi ý cụ thể từ FAQ."


@tool
def get_available_slots_tool(
    appointment_date: str = "",
    doctor_name: str = "",
    expertise_name: str = "",
    service_name: str = "",
) -> str:
    """
    Dùng khi:
    - Bệnh nhân hỏi lịch làm việc của bác sĩ.
    - Bệnh nhân hỏi giờ khám, giờ trống.
    - Bệnh nhân hỏi ngày mai, tuần sau, thứ 2, thứ 3... còn chỗ không.

    Tham số truyền vào:
    appointment_date: YYYY-MM-DD (Nếu bệnh nhân hỏi ngày mai, tuần sau, thì BỎ TRỐNG trường này, hệ thống sẽ tự quét 7 ngày tới)
    doctor_name: tên bác sĩ (bắt buộc khi đặt khám bác sĩ — phải kèm expertise_name)
    expertise_name: chuyên khoa (bắt buộc khi đặt khám bác sĩ)
    service_name: tên dịch vụ xét nghiệm/chụp (luồng SERVICE, không cần bác sĩ)
    """
    client = BackendClient()
    try:
        doctor_id = None
        expertise_id = None
        service_id = None

        if service_name.strip():
            service_id = _find_bookable_service_id(client, service_name)
            if service_id is None:
                return f"Không tìm thấy dịch vụ '{service_name}' có thể đặt lịch trực tiếp."
        elif doctor_name.strip() or expertise_name.strip():
            if not expertise_name.strip():
                return "Đặt khám bác sĩ bắt buộc chọn chuyên khoa (expertise_name)."
            if not doctor_name.strip():
                return "Đặt khám bác sĩ bắt buộc chọn bác sĩ cụ thể (doctor_name). Gọi get_doctors_tool để xem danh sách."
            expertise_id = _find_expertise_id(client, expertise_name)
            if expertise_id is None:
                return f"Không tìm thấy chuyên khoa '{expertise_name}'."
            doctor_id = _find_doctor_id(client, doctor_name, expertise_id=expertise_id)
            if doctor_id is None:
                return f"Không tìm thấy bác sĩ '{doctor_name}' thuộc chuyên khoa '{expertise_name}'."
        else:
            return "Cần doctor_name + expertise_name (khám bác sĩ) hoặc service_name (xét nghiệm/chụp)."

        import datetime

        dates_to_check = [appointment_date.strip()] if appointment_date.strip() else []
        if not dates_to_check:
            today = datetime.date.today()
            dates_to_check = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        all_available = []
        for d in dates_to_check:
            slots = client.get_available_slots(
                appointment_date=d,
                doctor_id=doctor_id,
                expertise_id=expertise_id,
                service_id=service_id,
            )
            for s in slots:
                if s.get("isAvailable"):
                    s["query_date"] = d
                    all_available.append(s)

        if not all_available:
            date_label = f"ngày {appointment_date}" if appointment_date.strip() else "7 ngày tới"
            return f"Không còn giờ trống {date_label} với tiêu chí đã chọn."

        label = service_name or f"{doctor_name} ({expertise_name})"
        lines = [f"Giờ trống ({label}) tìm thấy:"]
        for slot in all_available[:12]:
            q_date = slot.get("query_date")
            start = str(slot.get("timeStart") or "--:--")[:5]
            end = str(slot.get("timeEnd") or "")[:5]
            lines.append(f"- {q_date} {start}" + (f" - {end}" if end else ""))
        return "\n".join(lines)
    except BackendClientError as exc:
        return f"Không kiểm tra được giờ trống: {exc}"


@tool
def suggest_expertise_tool(symptoms: str) -> str:
    """
    Dùng khi:
    - Bệnh nhân kể bệnh, mô tả triệu chứng (ví dụ: "tôi bị đau đầu", "tôi hay chóng mặt").
    - Bệnh nhân hỏi nên đi khám khoa nào, khám bác sĩ nào cho bệnh này.

    symptoms: mô tả chi tiết triệu chứng của bệnh nhân.
    LƯU Ý: Tool này chỉ gợi ý chuyên khoa, KHÔNG ĐƯỢC tự ý chẩn đoán bệnh.
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
            + "\n\nSau khi chọn chuyên khoa, bệnh nhân vẫn phải chọn bác sĩ cụ thể trước khi đặt lịch."
        )
    except BackendClientError as exc:
        return f"{rag_hint}\n\n(Không tải được danh sách chuyên khoa: {exc})"


@tool
def book_appointment_tool(
    appointment_date: str = "",
    time_start: str = "",
    time_end: str = "",
    booking_mode: str = "DOCTOR",
    note: str = "",
    doctor_name: str = "",
    expertise_name: str = "",
    service_name: str = "",
    suggested_expertise_name: str = "",
    access_token: str = "",
) -> str:
    """
    Dùng khi:
    - Bệnh nhân đồng ý chốt ngày giờ khám.
    - Bệnh nhân yêu cầu "đặt lịch cho tôi", "tôi muốn khám vào lúc...".

    Yêu cầu: Phải có đủ ngày và giờ thì mới được gọi tool này.

    Tham số:
    booking_mode: DOCTOR (bắt buộc doctor_name + expertise_name) | SERVICE (service_name, không cần bác sĩ)
    time_start/time_end: HH:MM:SS (vd 09:00:00, 09:30:00)
    suggested_expertise_name: chuyên khoa AI gợi ý (nếu khác chuyên khoa bệnh nhân chọn)
    """
    if not access_token or not access_token.strip():
        return (
            "Không thể đặt lịch tự động vì bạn chưa đăng nhập. "
            "Vui lòng đăng nhập trên app/website rồi thử lại, hoặc tự đặt tại mục Đặt lịch."
        )

    if not appointment_date or not time_start or not time_end:
        return "Thiếu thông tin ngày giờ khám (appointment_date, time_start, time_end). Vui lòng kiểm tra lại lịch trống và hỏi bệnh nhân."

    client = BackendClient()
    mode = booking_mode.strip().upper()
    if mode not in {"DOCTOR", "SERVICE"}:
        return "booking_mode phải là DOCTOR (khám bác sĩ) hoặc SERVICE (xét nghiệm/chụp)."

    try:
        from datetime import datetime
        apt_date_obj = datetime.strptime(appointment_date, "%Y-%m-%d")
        if apt_date_obj.weekday() == 6:  # 6 is Sunday
            return "Vui lòng chọn ngày khác vì phòng khám không làm việc vào ngày Chủ Nhật. Hãy thông báo lại cho bệnh nhân."
        
        now = datetime.now()
        time_str_parsed = time_start if len(time_start) > 5 else f"{time_start}:00"
        apt_time_str = f"{appointment_date} {time_str_parsed}"
        apt_datetime = datetime.strptime(apt_time_str, "%Y-%m-%d %H:%M:%S")
        
        if (apt_datetime - now).total_seconds() < 24 * 3600:
            return "Lịch khám phải được đặt trước ít nhất 24 giờ. Hãy yêu cầu bệnh nhân chọn ngày/giờ khác xa hơn."
    except ValueError:
        return "Định dạng ngày giờ không hợp lệ. Hãy kiểm tra lại định dạng YYYY-MM-DD và HH:MM:SS."

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
        if mode == "DOCTOR":
            if not expertise_name.strip() or not doctor_name.strip():
                return "Đặt khám bác sĩ bắt buộc có expertise_name và doctor_name."
            exp_id = _find_expertise_id(client, expertise_name)
            if exp_id is None:
                return f"Không tìm thấy chuyên khoa '{expertise_name}'."
            payload["expertiseId"] = exp_id
            doc_id = _find_doctor_id(client, doctor_name, expertise_id=exp_id)
            if doc_id is None:
                return f"Không tìm thấy bác sĩ '{doctor_name}' thuộc chuyên khoa '{expertise_name}'."
            payload["mainDoctorId"] = doc_id
        elif mode == "SERVICE":
            if not service_name.strip():
                return "Đặt xét nghiệm/chụp bắt buộc có service_name."
            service_id = _find_bookable_service_id(client, service_name)
            if service_id is None:
                return f"Không tìm thấy dịch vụ '{service_name}' có thể đặt lịch trực tiếp."
            payload["serviceId"] = service_id

        if suggested_expertise_name.strip():
            sug_id = _find_expertise_id(client, suggested_expertise_name)
            if sug_id:
                payload["suggestedExpertiseId"] = sug_id

        result = client.create_appointment(payload, access_token.strip())
        apt_id = result.get("appointmentId") or result.get("appointment_id")
        return f"Đã tạo lịch hẹn thành công (mã #{apt_id}). Trạng thái: PENDING — chờ phòng khám xác nhận."
    except BackendClientError as exc:
        return f"Không đặt được lịch: {exc}. Bạn có thể tự đặt trên app/website."


@tool
def get_my_appointments_tool(access_token: str = "") -> str:
    """
    Dùng khi:
    - Bệnh nhân muốn xem lại các lịch đã đặt.
    - Bệnh nhân hỏi "tôi có lịch khám nào sắp tới không", "lịch khám của tôi là khi nào".

    Yêu cầu: Bệnh nhân phải đăng nhập (token tự gắn).
    """
    if not access_token or not access_token.strip():
        return "Vui lòng đăng nhập để xem lịch hẹn của bạn."

    client = BackendClient()
    try:
        appointments = client.get_my_appointments(access_token.strip())
        if not appointments:
            return "Bạn hiện không có lịch khám nào."

        lines = ["Danh sách lịch khám của bạn:"]
        for apt in appointments[:5]:
            apt_id = apt.get("appointmentId")
            date = apt.get("appointmentDate")
            start = str(apt.get("timeStart") or "")[:5]
            status = apt.get("status")
            doctor = apt.get("doctorName") or "Chưa gán"
            specialty = apt.get("expertiseName") or ""
            service = apt.get("serviceName") or ""

            detail = [d for d in [specialty, service, f"BS {doctor}" if doctor != "Chưa gán" else ""] if d]
            lines.append(f"- Lịch #{apt_id}: {date} {start} | {', '.join(detail)} | Trạng thái: {status}")

        return "\n".join(lines)
    except BackendClientError as exc:
        return f"Không thể lấy danh sách lịch khám: {exc}"


@tool
def cancel_appointment_tool(appointment_id: int, reason: str, access_token: str = "") -> str:
    """
    Dùng khi:
    - Bệnh nhân yêu cầu hủy lịch khám, hủy hẹn.

    Tham số:
    appointment_id: mã lịch khám cần hủy (bắt buộc)
    reason: lý do hủy (bắt buộc)
    """
    if not access_token or not access_token.strip():
        return "Vui lòng đăng nhập để hủy lịch hẹn."

    if not reason.strip():
        return "Vui lòng cung cấp lý do hủy lịch."

    client = BackendClient()
    try:
        client.cancel_appointment(appointment_id, reason, access_token.strip())
        return f"Đã hủy lịch khám #{appointment_id} thành công."
    except BackendClientError as exc:
        return f"Hủy lịch thất bại: {exc}"
