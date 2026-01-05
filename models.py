from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Enum, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base

class TripStatus(str, enum.Enum):
    ONGOING = "ONGOING"
    FINISHED = "FINISHED"

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(15), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contacts = relationship("EmergencyContact", back_populates="owner")
    trips = relationship("Trip", back_populates="driver")

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    contact_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String(100), nullable=False)
    phone_number = Column(String(15), nullable=False)
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="contacts")

class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(TripStatus), default=TripStatus.ONGOING)

    driver = relationship("User", back_populates="trips")
    logs = relationship("DetectionLog", back_populates="trip")

class DetectionLog(Base):
    __tablename__ = "detection_logs"

    log_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.trip_id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    # Event types: distracted, drowsy, head drop, phone, smoking, yawn
    event_type = Column(String(50), nullable=False) 
    confidence = Column(Float, nullable=False)
    gps_location = Column(String(50), nullable=True)

    trip = relationship("Trip", back_populates="logs")
