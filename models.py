import enum
import uuid

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ComplaintType(str, enum.Enum):
    waste = "waste"
    plastic = "plastic"
    noise = "noise"


class ComplaintStatus(str, enum.Enum):
    reported = "reported"
    assigned = "assigned"
    resolved = "resolved"


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Ward(Base):
    __tablename__ = "wards"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(80), nullable=False, unique=True)
    officer_name = Column(String(120), nullable=True)
    officer_contact = Column(String(50), nullable=True)

    complaints = relationship("Complaint", back_populates="ward")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    display_name = Column(String(120), nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    device_uuid = Column(String(64), unique=True, nullable=True)  # anonymous demo identity
    is_staff = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaints = relationship("Complaint", back_populates="reporter")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    type = Column(Enum(ComplaintType), nullable=False)
    status = Column(Enum(ComplaintStatus), nullable=False, default=ComplaintStatus.reported)
    severity = Column(Enum(Severity), nullable=False, default=Severity.medium)

    description = Column(Text, nullable=True)
    address = Column(String(255), nullable=False)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)

    photo_url = Column(String(255), nullable=True)
    after_photo_url = Column(String(255), nullable=True)

    noise_source = Column(String(80), nullable=True)
    loudness = Column(Float, nullable=True)  # 0-100 relative reading, informational only

    community_open = Column(Boolean, default=False)

    ward_id = Column(UUID(as_uuid=False), ForeignKey("wards.id"), nullable=True)
    reporter_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ward = relationship("Ward", back_populates="complaints")
    reporter = relationship("User", back_populates="complaints")
    volunteers = relationship("Volunteer", back_populates="complaint", cascade="all, delete-orphan")
    ai_classification = relationship(
        "AIClassification", back_populates="complaint", uselist=False, cascade="all, delete-orphan"
    )


class Volunteer(Base):
    __tablename__ = "volunteers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    complaint_id = Column(UUID(as_uuid=False), ForeignKey("complaints.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="volunteers")


class AIClassification(Base):
    """Stores the Claude vision classification for a complaint's photo."""

    __tablename__ = "ai_classifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    complaint_id = Column(UUID(as_uuid=False), ForeignKey("complaints.id"), unique=True, nullable=False)

    waste_types = Column(String(255), nullable=True)  # comma-separated, e.g. "plastic bottles,food waste"
    plastic_detected = Column(Boolean, default=False)
    suggested_severity = Column(Enum(Severity), nullable=True)
    summary = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="ai_classification")
