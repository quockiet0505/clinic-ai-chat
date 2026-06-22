from app.tools.appointment_tools import (
    book_appointment_tool,
    get_available_slots_tool,
    suggest_expertise_tool,
)
from app.tools.clinic_tools import (
    get_clinic_info_tool,
    get_doctors_tool,
    get_services_tool,
    get_specialties_tool,
)
from app.tools.patient_tools import register_patient_tool

ALL_TOOLS = [
    get_specialties_tool,
    get_doctors_tool,
    get_services_tool,
    get_clinic_info_tool,
    get_available_slots_tool,
    suggest_expertise_tool,
    book_appointment_tool,
    register_patient_tool,
]

TOOL_REGISTRY = {tool.name: tool for tool in ALL_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "TOOL_REGISTRY",
    "get_specialties_tool",
    "get_doctors_tool",
    "get_services_tool",
    "get_clinic_info_tool",
    "get_available_slots_tool",
    "suggest_expertise_tool",
    "book_appointment_tool",
    "register_patient_tool",
]
