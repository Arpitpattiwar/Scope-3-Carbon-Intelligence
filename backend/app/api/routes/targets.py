from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.db.database import get_db
from app.models.user import EmissionTarget
from app.core.security import require_admin, get_current_user

router = APIRouter(prefix="/targets", tags=["targets"])


class TargetCreate(BaseModel):
    label: Optional[str] = None   # auto-generated if blank
    target_co2e: float
    year: int
    region: Optional[str] = None

    @field_validator('region', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty string "" → None so Enum validation passes."""
        if v == '' or v is None:
            return None
        return v

    @field_validator('label', mode='before')
    @classmethod
    def default_label(cls, v):
        return v if v else None  # will be filled in route if None


class TargetOut(BaseModel):
    id: int
    label: Optional[str]
    target_co2e: float
    year: int
    region: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[TargetOut])
def list_targets(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(EmissionTarget)
    if year:
        q = q.filter(EmissionTarget.year == year)
    return q.order_by(EmissionTarget.year.desc()).all()


@router.post("", response_model=TargetOut)
def create_target(
    body: TargetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    label = body.label or f"FY{body.year} Target"
    region_val = body.region  # already None if blank, thanks to validator

    target = EmissionTarget(
        label=label,
        target_co2e=body.target_co2e,
        year=body.year,
        region=region_val,
        created_by=current_user.id,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{target_id}")
def delete_target(
    target_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    t = db.query(EmissionTarget).filter(EmissionTarget.id == target_id).first()
    if not t:
        raise HTTPException(status_code=404)
    db.delete(t)
    db.commit()
    return {"message": "Target deleted"}
