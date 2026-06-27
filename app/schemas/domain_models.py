from pydantic import BaseModel
from typing import Optional, List, Any

class Specialty(BaseModel):
    id: Optional[int] = None
    name: str

class Doctor(BaseModel):
    id: Optional[int] = None
    name: str
    expertise: str
    rating: Optional[float] = None
    patient_count: Optional[int] = None
    consultation_fee: Optional[float] = None

class Service(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    original_price: Optional[float] = None
    discount_price: Optional[float] = None

class ClinicInfo(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    working_hours: Optional[str] = None

# Có thể mở rộng cho TimeSlot, Appointment...
