from typing import Any

import httpx

from app.config import settings
from app.core.exceptions import BackendClientError


class BackendClient:
    """HTTP client gọi clinic-backend (Spring Boot)."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        self.base_url = (base_url or settings.CLINIC_BACKEND_URL).rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, **kwargs)
                data = response.json()
        except httpx.RequestError as exc:
            raise BackendClientError(f"Không kết nối được backend: {exc}") from exc
        except ValueError as exc:
            raise BackendClientError("Backend trả về dữ liệu không hợp lệ") from exc

        if response.status_code >= 400:
            message = data.get("message") if isinstance(data, dict) else str(data)
            raise BackendClientError(message or f"Lỗi HTTP {response.status_code}")

        if isinstance(data, dict) and "success" in data and not data.get("success"):
            raise BackendClientError(data.get("message") or "Yêu cầu thất bại")

        if isinstance(data, dict) and "data" in data:
            return data.get("data")

        return data

    def register_patient(
        self,
        email: str,
        password: str,
        full_name: str,
        phone: str,
    ) -> dict:
        return self._request(
            "POST",
            "/api/v1/auth/patient/register",
            json={
                "email": email,
                "password": password,
                "fullName": full_name,
                "phone": phone,
            },
        )

    def get_doctors(self, expertise_id: int | None = None) -> list[dict]:
        params: dict[str, Any] = {"staffType": "DOCTOR"}
        if expertise_id is not None:
            params["expertiseId"] = expertise_id
        result = self._request("GET", "/api/v1/staffs/filter", params=params)
        return result if isinstance(result, list) else []

    def get_specialties(self) -> list[dict]:
        result = self._request("GET", "/api/v1/expertise/all")
        return result if isinstance(result, list) else []

    def get_services(self, featured_only: bool = False) -> list[dict]:
        path = "/api/v1/services/featured" if featured_only else "/api/v1/services/all"
        result = self._request("GET", path)
        return result if isinstance(result, list) else []

    def get_clinic_settings(self) -> dict[str, str]:
        result = self._request("GET", "/api/v1/settings")
        return result if isinstance(result, dict) else {}

    def get_available_slots(
        self,
        appointment_date: str,
        doctor_id: int | None = None,
        expertise_id: int | None = None,
        service_id: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"date": appointment_date}
        if doctor_id is not None:
            params["doctorId"] = doctor_id
        if expertise_id is not None:
            params["expertiseId"] = expertise_id
        if service_id is not None:
            params["serviceId"] = service_id
        result = self._request("GET", "/api/v1/appointments/slots", params=params)
        return result if isinstance(result, list) else []

    def create_appointment(self, payload: dict[str, Any], access_token: str) -> dict:
        return self._request(
            "POST",
            "/api/v1/appointments",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def get_my_appointments(self, access_token: str) -> list[dict]:
        result = self._request(
            "GET",
            "/api/v1/appointments/my",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return result if isinstance(result, list) else []

    def cancel_appointment(self, appointment_id: int, reason: str, access_token: str) -> dict:
        return self._request(
            "PATCH",
            f"/api/v1/appointments/{appointment_id}/cancel",
            params={"reason": reason},
            headers={"Authorization": f"Bearer {access_token}"},
        )
