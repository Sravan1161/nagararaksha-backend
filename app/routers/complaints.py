from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import (
    AIClassification, Complaint, ComplaintStatus, ComplaintType, Severity,
    User, Volunteer,
)
from app.schemas import ComplaintOut, ComplaintUpdate
from app.services.ai_classify import classify_photo
from app.services.auth import require_staff
from app.services.storage import photo_path_from_url, save_photo

router = APIRouter(prefix="/complaints", tags=["complaints"])


def get_or_create_user(db: Session, device_uuid: str) -> User:
    user = db.query(User).filter(User.device_uuid == device_uuid).first()
    if user:
        return user
    user = User(device_uuid=device_uuid)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def serialize(c: Complaint) -> dict:
    lat = lng = None
    if c.location is not None:
        point = to_shape(c.location)
        lng, lat = point.x, point.y

    ai = None
    if c.ai_classification:
        ai = {
            "waste_types": c.ai_classification.waste_types,
            "plastic_detected": c.ai_classification.plastic_detected,
            "suggested_severity": c.ai_classification.suggested_severity,
            "summary": c.ai_classification.summary,
        }

    return {
        "id": c.id,
        "type": c.type.value,
        "status": c.status.value,
        "severity": c.severity.value,
        "description": c.description,
        "address": c.address,
        "latitude": lat,
        "longitude": lng,
        "photo_url": c.photo_url,
        "after_photo_url": c.after_photo_url,
        "noise_source": c.noise_source,
        "loudness": c.loudness,
        "community_open": c.community_open,
        "ward_id": c.ward_id,
        "reporter_id": c.reporter_id,
        "volunteer_count": len(c.volunteers or []),
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "ai": ai,
    }


@router.post("", response_model=ComplaintOut)
def create_complaint(
    device_uuid: str = Form(...),
    type: ComplaintType = Form(...),
    address: str = Form(...),
    description: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    ward_id: Optional[str] = Form(None),
    community_open: bool = Form(False),
    noise_source: Optional[str] = Form(None),
    loudness: Optional[float] = Form(None),
    photo: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
):
    reporter = get_or_create_user(db, device_uuid)

    location = None
    if latitude is not None and longitude is not None:
        location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

    photo_url = save_photo(photo) if photo is not None else None

    complaint = Complaint(
        type=type,
        address=address,
        description=description,
        location=location,
        ward_id=ward_id,
        community_open=community_open,
        noise_source=noise_source,
        loudness=loudness,
        photo_url=photo_url,
        reporter_id=reporter.id,
        status=ComplaintStatus.reported,
        severity=Severity.medium,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Best-effort AI triage -- never blocks complaint creation if it fails.
    if photo_url:
        result = classify_photo(photo_path_from_url(photo_url), type.value)
        if result:
            classification = AIClassification(
                complaint_id=complaint.id,
                waste_types=result["waste_types"],
                plastic_detected=result["plastic_detected"],
                suggested_severity=result["suggested_severity"],
                summary=result["summary"],
                raw_response=result["raw_response"],
            )
            db.add(classification)
            if result["suggested_severity"] in (Severity.low, Severity.medium, Severity.high, "low", "medium", "high"):
                complaint.severity = Severity(result["suggested_severity"])
            db.commit()
            db.refresh(complaint)

    return serialize(complaint)


@router.get("", response_model=list[ComplaintOut])
def list_complaints(
    type: Optional[ComplaintType] = None,
    status: Optional[ComplaintStatus] = None,
    ward_id: Optional[str] = None,
    device_uuid: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Complaint).options(joinedload(Complaint.ai_classification), joinedload(Complaint.volunteers))
    if type:
        q = q.filter(Complaint.type == type)
    if status:
        q = q.filter(Complaint.status == status)
    if ward_id:
        q = q.filter(Complaint.ward_id == ward_id)
    if device_uuid:
        reporter = db.query(User).filter(User.device_uuid == device_uuid).first()
        q = q.filter(Complaint.reporter_id == (reporter.id if reporter else "none"))

    complaints = q.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return [serialize(c) for c in complaints]


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    return serialize(c)


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: str,
    patch: ComplaintUpdate,
    db: Session = Depends(get_db),
    _staff=Depends(require_staff),
):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    if patch.status == "resolved":
        raise HTTPException(400, "Use POST /complaints/{id}/resolve with an after-photo to resolve a complaint")
    if patch.status:
        c.status = ComplaintStatus(patch.status)
    if patch.severity:
        c.severity = Severity(patch.severity)
    db.commit()
    db.refresh(c)
    return serialize(c)


@router.post("/{complaint_id}/resolve", response_model=ComplaintOut)
def resolve_complaint(
    complaint_id: str,
    after_photo: UploadFile,
    db: Session = Depends(get_db),
    _staff=Depends(require_staff),
):
    """Marking a complaint resolved always requires proof-of-cleanup photo evidence."""
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    c.after_photo_url = save_photo(after_photo)
    c.status = ComplaintStatus.resolved
    db.commit()
    db.refresh(c)
    return serialize(c)


@router.post("/{complaint_id}/volunteers")
def join_as_volunteer(complaint_id: str, device_uuid: str = Form(...), db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    if not c.community_open:
        raise HTTPException(400, "This complaint isn't open for community cleanup")
    if len(c.volunteers) >= settings.volunteer_cap:
        raise HTTPException(400, "This cleanup already has enough volunteers")

    user = get_or_create_user(db, device_uuid)
    already = db.query(Volunteer).filter(Volunteer.complaint_id == c.id, Volunteer.user_id == user.id).first()
    if already:
        return {"status": "already joined"}

    db.add(Volunteer(complaint_id=c.id, user_id=user.id))
    db.commit()
    return {"status": "joined"}
