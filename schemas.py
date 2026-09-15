from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    officer_name: Optional[str] = None
    officer_contact: Optional[str] = None


class AIClassificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    waste_types: Optional[str] = None
    plastic_detected: bool = False
    suggested_severity: Optional[str] = None
    summary: Optional[str] = None


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    status: str
    severity: str
    description: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_url: Optional[str] = None
    after_photo_url: Optional[str] = None
    noise_source: Optional[str] = None
    loudness: Optional[float] = None
    community_open: bool
    ward_id: Optional[str] = None
    reporter_id: Optional[str] = None
    volunteer_count: int = 0
    created_at: datetime
    updated_at: datetime
    ai: Optional[AIClassificationOut] = None


class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None


class HotspotOut(BaseModel):
    cluster_id: int
    report_count: int
    centroid_lat: float
    centroid_lng: float
    sample_address: str
    ward_id: Optional[str] = None


class VolunteerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    complaint_id: str
    user_id: str
    joined_at: datetime
