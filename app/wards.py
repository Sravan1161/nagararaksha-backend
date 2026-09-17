from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ward
from app.schemas import WardOut

router = APIRouter(prefix="/wards", tags=["wards"])


@router.get("", response_model=list[WardOut])
def list_wards(db: Session = Depends(get_db)):
    return db.query(Ward).order_by(Ward.name).all()
