from app.utils.helpers import region_value
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.user import User, VendorProfile, VendorInvitation, EmissionRecord
from app.models.notification import NotificationType
from app.schemas.schemas import UserCreate, UserOut, UserUpdate, InviteVendorRequest, InvitationOut, VendorDetailOut
from app.core.security import get_password_hash, require_admin, require_manager, get_current_user
from app.services.audit_service import log_action
from app.services.email_service import send_vendor_invitation
from app.services.notification_service import notify

router = APIRouter(prefix="/users", tags=["users"])

# Role hierarchy: what each role can delete/deactivate
DELETABLE_BY = {
    "admin":   ["manager", "vendor", "auditor"],  # admin can manage all non-admin
    "manager": ["vendor"],                         # manager can only manage their vendors
}


def _can_manage(actor_role: str, target_role: str) -> bool:
    return target_role in DELETABLE_BY.get(actor_role, [])


# ── Admin: list / create / update / delete users ──────────────────────────────

@router.get("", response_model=List[UserOut])
def list_users(role: Optional[str] = None, db: Session = Depends(get_db),
               current_user=Depends(require_admin)):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.order_by(User.created_at.desc()).all()


@router.post("", response_model=UserOut)
def create_user(body: UserCreate, db: Session = Depends(get_db),
                current_user=Depends(require_admin)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email, full_name=body.full_name, role=body.role,
        region=body.region, password_hash=get_password_hash(body.password),
        onboarding_complete=True,
    )
    db.add(user)
    db.flush()
    log_action(db, current_user.id, "CREATE_USER", "users", user.id,
               new_value={"email": user.email, "role": str(user.role)})
    db.commit()
    db.refresh(user)
    return user


# ── Vendor list + detail (manager / admin) — MUST be before /{user_id} ───────

@router.get("/vendors", response_model=List[dict])
def list_vendors(region: Optional[str] = None, db: Session = Depends(get_db),
                 current_user=Depends(require_manager)):
    q = db.query(User, VendorProfile).join(
        VendorProfile, VendorProfile.user_id == User.id, isouter=True
    ).filter(User.role == "vendor")
    if current_user.role == "manager":
        q = q.filter(User.region == current_user.region)
    elif region:
        q = q.filter(User.region == region)
    results = []
    for u, p in q.all():
        results.append({
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "region": region_value(u.region) if u.region else None,
            "is_active": u.is_active,
            "onboarding_complete": u.onboarding_complete,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "company_name": p.company_name if p else None,
            "trade_name": p.trade_name if p else None,
            "gst_number": p.gst_number if p else None,
            "pan_number": p.pan_number if p else None,
            "state": p.state if p else None,
            "city": p.city if p else None,
            "pin_code": p.pin_code if p else None,
            "address": p.address if p else None,
            "nic_code": p.nic_code if p else None,
            "material_category": p.material_category if p else None,
            "material_name": p.material_name if p else None,
            "supply_frequency": p.supply_frequency if p else None,
            "avg_annual_volume": p.avg_annual_volume if p else None,
            "volume_unit": p.volume_unit if p else None,
            "has_own_carbon_system": p.has_own_carbon_system if p else None,
            "contact_name": p.contact_name if p else None,
            "contact_designation": p.contact_designation if p else None,
            "contact_phone": p.contact_phone if p else None,
            "onboarded_at": p.onboarded_at.isoformat() if p and p.onboarded_at else None,
            "record_count": db.query(EmissionRecord).filter(
                EmissionRecord.vendor_id == p.id).count() if p else 0,
        })
    return results


@router.get("/vendors/{vendor_id}")
def get_vendor_detail(vendor_id: int, db: Session = Depends(get_db),
                      current_user=Depends(require_manager)):
    user = db.query(User).filter(User.id == vendor_id, User.role == "vendor").first()
    if not user:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if current_user.role == "manager":
        r_user = region_value(user.region)
        r_curr = region_value(current_user.region)
        if r_user != r_curr:
            raise HTTPException(status_code=403, detail="Access denied")
    profile = db.query(VendorProfile).filter(VendorProfile.user_id == vendor_id).first()
    from sqlalchemy import func as sqlfunc
    record_count = 0
    total_co2e = 0.0
    if profile:
        record_count = db.query(EmissionRecord).filter(
            EmissionRecord.vendor_id == profile.id).count()
        total_co2e = float(db.query(
            sqlfunc.coalesce(sqlfunc.sum(EmissionRecord.calculated_co2e), 0)
        ).filter(EmissionRecord.vendor_id == profile.id).scalar() or 0)
    return {
        "id": user.id, "email": user.email, "full_name": user.full_name,
        "region": region_value(user.region) if user.region else None,
        "is_active": user.is_active,
        "onboarding_complete": user.onboarding_complete,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "profile": profile,
        "record_count": record_count,
        "total_co2e": float(total_co2e or 0),
    }


# ── Admin: get / update / delete a specific user ──────────────────────────────

@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db),
             current_user=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db),
                current_user=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        # Prevent admin from deactivating/changing their own role
        if body.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        if body.role and body.role != user.role:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
    old = {"is_active": user.is_active, "region": str(user.region), "role": str(user.role)}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    log_action(db, current_user.id, "UPDATE_USER", "users", user_id, old_value=old)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    """
    Soft-delete: deactivates user. Preserves emission records for audit integrity.
    Admin can delete managers/auditors/vendors.
    Manager can only delete their own region's vendors.
    """
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Not authorized")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if not _can_manage(current_user.role, str(user.role).split(".")[-1]):
        raise HTTPException(status_code=403,
                            detail=f"You cannot delete a {user.role} user")

    # Manager can only delete vendors in their own region
    if current_user.role == "manager":
        r_user = str(user.region).split(".")[-1] if user.region else ""
        r_curr = str(current_user.region).split(".")[-1] if current_user.region else ""
        if r_user != r_curr:
            raise HTTPException(status_code=403,
                                detail="Can only delete vendors in your region")

    user.is_active = False
    log_action(db, current_user.id, "DELETE_USER", "users", user_id,
               description=f"Soft-deleted {user.role} user {user.email}")
    db.commit()
    return {"message": f"User {user.email} deactivated successfully"}


# ── Manager / Admin: invite vendors ──────────────────────────────────────────

@router.post("/invite-vendor")
def invite_vendor(body: InviteVendorRequest, db: Session = Depends(get_db),
                  current_user=Depends(require_manager)):
    rv = region_value(body.region)
    if current_user.role == "manager":
        curr_rv = region_value(current_user.region)
        if curr_rv != rv:
            raise HTTPException(status_code=403,
                                detail="Cannot invite vendors outside your region")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    temp_password = secrets.token_urlsafe(10)
    expires = datetime.utcnow() + timedelta(hours=48)

    new_user = User(
        email=body.email, role="vendor", region=body.region,
        password_hash=get_password_hash(temp_password),
        must_change_password=True, onboarding_complete=False,
    )
    db.add(new_user)
    db.flush()

    profile = VendorProfile(user_id=new_user.id, region=body.region)
    db.add(profile)

    invitation = VendorInvitation(
        invited_by=current_user.id, email=body.email,
        temp_password_hash=get_password_hash(temp_password),
        region=body.region, status="pending", expires_at=expires,
    )
    db.add(invitation)

    notify(db, current_user.id, NotificationType.vendor_invited,
           "Vendor invitation sent",
           f"Invitation sent to {body.email} ({rv.title()} region)",
           link="/vendors")
    log_action(db, current_user.id, "INVITE_VENDOR", "vendor_invitations",
               description=f"Invited {body.email} to {rv} region")
    db.commit()
    db.refresh(invitation)

    send_vendor_invitation(
        body.email, temp_password,
        current_user.full_name or current_user.email,
        rv,
    )

    return {
        "id": invitation.id,
        "email": invitation.email,
        "region": rv,
        "status": invitation.status,
        "created_at": invitation.created_at,
        "temp_password": temp_password,
    }


@router.get("/invitations/list", response_model=List[InvitationOut])
def list_invitations(db: Session = Depends(get_db),
                     current_user=Depends(require_manager)):
    q = db.query(VendorInvitation)
    if current_user.role == "manager":
        q = q.filter(VendorInvitation.invited_by == current_user.id)
    return q.order_by(VendorInvitation.created_at.desc()).all()


# ── Vendor onboarding ─────────────────────────────────────────────────────────

@router.post("/onboard", response_model=UserOut)
def complete_onboarding(body: dict, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can use this endpoint")

    profile = db.query(VendorProfile).filter(
        VendorProfile.user_id == current_user.id).first()
    if not profile:
        profile = VendorProfile(user_id=current_user.id)
        db.add(profile)

    allowed = [
        "company_name","trade_name","gst_number","pan_number","cin_number",
        "year_established","state","city","pin_code","address","nic_code",
        "material_category","material_name","supply_frequency","avg_annual_volume",
        "volume_unit","has_own_carbon_system","contact_name","contact_designation",
        "contact_phone",
    ]
    for field in allowed:
        if field in body:
            setattr(profile, field, body[field])

    profile.onboarded_at = datetime.utcnow()
    current_user.onboarding_complete = True
    current_user.full_name = body.get("contact_name", current_user.full_name)

    from app.models.user import UserRole as UR
    managers = db.query(User).filter(
        User.role == UR.manager,
        User.region == current_user.region,
        User.is_active == True,
    ).all()
    for mgr in managers:
        notify(db, mgr.id, NotificationType.vendor_onboarded,
               "New vendor onboarded",
               f"{body.get('company_name', current_user.email)} completed onboarding",
               link="/vendors")

    log_action(db, current_user.id, "VENDOR_ONBOARDING", "vendor_profiles", profile.id,
               description=f"Vendor {body.get('company_name')} onboarded")
    db.commit()
    db.refresh(current_user)
    return current_user


# (vendor routes moved above /{user_id} to avoid route conflict)
