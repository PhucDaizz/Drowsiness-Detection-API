from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- User Schemas ---
class UserBase(BaseModel):
    email: str
    full_name: str
    phone_number: str
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    user_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None


# --- Emergency Contact Schemas ---
class ContactBase(BaseModel):
    name: str
    phone_number: str
    is_active: bool = True

class ContactCreate(ContactBase):
    pass

class ContactResponse(ContactBase):
    contact_id: int
    user_id: int
    class Config:
        from_attributes = True

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None


# --- Trip Schemas ---
class TripStatus(str, Enum):
    ONGOING = "ONGOING"
    FINISHED = "FINISHED"

class TripBase(BaseModel):
    pass

class TripCreate(TripBase):
    # Usually started by the authenticated user, no input needed strictly unless initial params
    pass

class TripResponse(TripBase):
    trip_id: int
    user_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TripStatus

    class Config:
        from_attributes = True

# --- Detection Log Schemas ---
class DetectionLogBase(BaseModel):
    event_type: str
    confidence: float
    gps_location: Optional[str] = None
    timestamp: Optional[datetime] = None

class DetectionLogCreate(DetectionLogBase):
    pass

class DetectionLogResponse(DetectionLogBase):
    log_id: int
    trip_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Statistics Schemas ---
class TripWithLogs(TripResponse):
    logs: List[DetectionLogResponse] = []
    total_detections: int = 0
    duration_minutes: Optional[int] = None

class StatsPeriod(str, Enum):
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"
    THIS_MONTH = "THIS_MONTH"
    THIS_YEAR = "THIS_YEAR"

class DrivingStatsResponse(BaseModel):
    today_hours: float
    week_hours: float
    month_hours: float
    year_hours: float

class CalendarCheckinResponse(BaseModel):
    active_days: List[datetime] # List of dates where driving occurred

class TripSummary(TripResponse):
    total_detections: int = 0
    duration_minutes: Optional[int] = None

class UserStatistics(BaseModel):
    total_trips: int
    total_detections: int
    total_duration_minutes: int
    detection_breakdown: dict  # {"drowsy": 5, "yawn": 3, ...}
    recent_trips: List[TripSummary]
