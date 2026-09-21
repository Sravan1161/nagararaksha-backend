from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.auth import issue_staff_token

router = APIRouter(prefix="/auth", tags=["auth"])


class StaffLoginRequest(BaseModel):
    password: str


class StaffLoginResponse(BaseModel):
    token: str


@router.post("/staff-login", response_model=StaffLoginResponse)
def staff_login(body: StaffLoginRequest):
    if body.password != settings.staff_password:
        raise HTTPException(status_code=401, detail="Incorrect password")
    return {"token": issue_staff_token()}
