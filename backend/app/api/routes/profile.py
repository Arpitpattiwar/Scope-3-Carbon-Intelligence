from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.models.user import User, VendorProfile
from app.schemas.schemas import UserOut
from app.core.security import get_current_user, verify_password, get_password_hash
from app.services.audit_service import log_action

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None


class EmailUpdate(BaseModel):
    new_email: EmailStr
    current_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class VendorProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    trade_name: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    cin_number: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pin_code: Optional[str] = None
    address: Optional[str] = None
    nic_code: Optional[str] = None
    material_name: Optional[str] = None
    supply_frequency: Optional[str] = None
    avg_annual_volume: Optional[float] = None
    volume_unit: Optional[str] = None
    has_own_carbon_system: Optional[bool] = None
    contact_name: Optional[str] = None
    contact_designation: Optional[str] = None
    contact_phone: Optional[str] = None


@router.get("", response_model=UserOut)
def get_profile(current_user=Depends(get_current_user)):
    return current_user


@router.patch("", response_model=UserOut)
def update_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    old = {"full_name": current_user.full_name, "phone": current_user.phone}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    log_action(db, current_user.id, "UPDATE_PROFILE", "users",
               current_user.id, old_value=old)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    current_user.password_hash = get_password_hash(body.new_password)
    current_user.must_change_password = False
    log_action(db, current_user.id, "CHANGE_PASSWORD", "users", current_user.id)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/change-email")
def change_email(
    body: EmailUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    existing = db.query(User).filter(User.email == body.new_email).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="Email already in use")
    old_email = current_user.email
    current_user.email = body.new_email
    log_action(db, current_user.id, "CHANGE_EMAIL", "users", current_user.id,
               old_value={"email": old_email}, new_value={"email": body.new_email})
    db.commit()
    return {"message": "Email updated successfully"}


@router.get("/vendor-details")
def get_vendor_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Vendor only")
    profile = db.query(VendorProfile).filter(
        VendorProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/vendor-details")
def update_vendor_profile(
    body: VendorProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Vendor only")
    profile = db.query(VendorProfile).filter(
        VendorProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    if body.contact_name:
        current_user.full_name = body.contact_name
    log_action(db, current_user.id, "UPDATE_VENDOR_PROFILE", "vendor_profiles", profile.id)
    db.commit()
    db.refresh(profile)
    return profile
