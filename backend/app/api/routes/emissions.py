from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from typing import List, Optional
import pandas as pd
import io
from datetime import datetime

from app.db.database import get_db
from app.models.user import EmissionRecord, EmissionFactor, VendorProfile, User, ReportingPeriod
from app.models.notification import NotificationType
from app.schemas.schemas import EmissionRecordCreate, EmissionRecordOut, EmissionRecordWithTrace, RecordStatusUpdate
from app.core.security import get_current_user, require_manager
from app.services.calculation_engine import calculate_co2e, validate_activity_data, get_category_name
from app.services.audit_service import log_action
from app.services.notification_service import notify
from app.services.email_service import send_record_status_email
from app.utils.helpers import region_value

router = APIRouter(prefix="/emissions", tags=["emissions"])


def _check_period_locked(db, period_start, period_end):
    locked = db.query(ReportingPeriod).filter(
        ReportingPeriod.is_locked == True,
        ReportingPeriod.period_start <= period_end,
        ReportingPeriod.period_end >= period_start,
    ).first()
    if locked:
        raise HTTPException(status_code=423,
                            detail=f"Reporting period '{locked.label}' is locked.")


def _get_vendor_profile(db, user):
    profile = db.query(VendorProfile).filter(VendorProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404,
                            detail="Vendor profile not found. Complete onboarding first.")
    return profile


def _enrich_records(records: List[EmissionRecord], db: Session) -> List[dict]:
    """Add vendor_company_name to each record dict for manager/admin views."""
    # Batch-load vendor profiles to avoid N+1
    vendor_ids = list({r.vendor_id for r in records})
    profiles = {
        p.id: p for p in db.query(VendorProfile).filter(
            VendorProfile.id.in_(vendor_ids)).all()
    }
    result = []
    for r in records:
        d = EmissionRecordOut.model_validate(r).model_dump()
        p = profiles.get(r.vendor_id)
        d["vendor_company_name"] = p.company_name if p else None
        result.append(d)
    return result


@router.post("", response_model=EmissionRecordOut)
def create_emission_record(body: EmissionRecordCreate,
                           db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can submit records")
    _check_period_locked(db, body.period_start, body.period_end)

    ef = db.query(EmissionFactor).filter(
        EmissionFactor.id == body.ef_id, EmissionFactor.is_active == True
    ).first()
    if not ef:
        raise HTTPException(status_code=404, detail="Emission factor not found")

    validation = validate_activity_data(body.category_id, body.activity_value, body.activity_unit)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail="; ".join(validation["errors"]))

    result = calculate_co2e(body.activity_value, ef.factor_value,
                            body.activity_unit, ef.unit)
    profile = _get_vendor_profile(db, current_user)

    record = EmissionRecord(
        vendor_id=profile.id, submitted_by=current_user.id,
        category_id=body.category_id, period_start=body.period_start,
        period_end=body.period_end, activity_value=body.activity_value,
        activity_unit=body.activity_unit, ef_id=body.ef_id,
        calculated_co2e=result["calculated_co2e"],
        data_quality=body.data_quality, input_method=body.input_method,
        region=current_user.region, status="submitted",
        notes=body.notes, is_ai_estimated=False,
    )
    db.add(record)
    db.flush()

    # Notify managers in region
    managers = db.query(User).filter(
        User.role == "manager", User.region == current_user.region,
        User.is_active == True,
    ).all()
    company = profile.company_name or current_user.email
    for mgr in managers:
        notify(db, mgr.id, NotificationType.record_submitted,
               "New emission record submitted",
               f"{company} submitted a {get_category_name(body.category_id)} record "
               f"({result['calculated_co2e']:.3f} tCO₂e)",
               link="/emissions")

    log_action(db, current_user.id, "CREATE_EMISSION_RECORD", "emission_records", record.id,
               new_value={"co2e": result["calculated_co2e"], "category": body.category_id})
    db.commit()
    db.refresh(record)
    return record


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...),
                     db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can upload data")
    profile = _get_vendor_profile(db, current_user)
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse CSV file")

    required = {"category_id", "period_start", "period_end",
                 "activity_value", "activity_unit", "ef_id"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing columns: {missing}")

    created, errors = [], []
    for idx, row in df.iterrows():
        try:
            ef = db.query(EmissionFactor).filter(
                EmissionFactor.id == int(row["ef_id"]),
                EmissionFactor.is_active == True,
            ).first()
            if not ef:
                errors.append({"row": idx + 2, "error": f"EF id {row['ef_id']} not found"})
                continue
            result = calculate_co2e(float(row["activity_value"]), ef.factor_value,
                                    str(row["activity_unit"]), ef.unit)
            record = EmissionRecord(
                vendor_id=profile.id, submitted_by=current_user.id,
                category_id=int(row["category_id"]),
                period_start=row["period_start"], period_end=row["period_end"],
                activity_value=float(row["activity_value"]),
                activity_unit=str(row["activity_unit"]), ef_id=int(row["ef_id"]),
                calculated_co2e=result["calculated_co2e"],
                data_quality=str(row.get("data_quality", "B")),
                input_method="csv", region=current_user.region,
                status="submitted", notes=str(row.get("notes", "") or ""),
                is_ai_estimated=False,
            )
            db.add(record)
            created.append(idx + 2)
        except Exception as e:
            errors.append({"row": idx + 2, "error": str(e)})

    if created:
        log_action(db, current_user.id, "CSV_UPLOAD", "emission_records",
                   description=f"Uploaded {len(created)} records via CSV")
        db.commit()
    return {"created": len(created), "errors": errors, "total_rows": len(df)}


@router.get("")
def list_records(region: Optional[str] = None, category_id: Optional[int] = None,
                 vendor_id: Optional[int] = None, status: Optional[str] = None,
                 year: Optional[int] = None,
                 db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    q = db.query(EmissionRecord).options(joinedload(EmissionRecord.emission_factor))

    if current_user.role == "vendor":
        profile = _get_vendor_profile(db, current_user)
        q = q.filter(EmissionRecord.vendor_id == profile.id)
    elif current_user.role == "manager":
        q = q.filter(EmissionRecord.region == current_user.region)

    if region and current_user.role in ("admin", "auditor"):
        q = q.filter(EmissionRecord.region == region)
    if category_id:
        q = q.filter(EmissionRecord.category_id == category_id)
    if vendor_id and current_user.role in ("admin", "manager"):
        q = q.filter(EmissionRecord.vendor_id == vendor_id)
    if status:
        q = q.filter(EmissionRecord.status == status)
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)

    records = q.order_by(EmissionRecord.submitted_at.desc()).limit(500).all()

    # For non-vendor roles, enrich with company names
    if current_user.role != "vendor":
        return _enrich_records(records, db)
    return [EmissionRecordOut.model_validate(r) for r in records]


@router.get("/{record_id}/trace")
def get_record_trace(record_id: int, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    record = db.query(EmissionRecord).options(
        joinedload(EmissionRecord.emission_factor),
        joinedload(EmissionRecord.vendor),
    ).filter(EmissionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if current_user.role == "vendor":
        profile = _get_vendor_profile(db, current_user)
        if record.vendor_id != profile.id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == "manager":
        if region_value(record.region) != region_value(current_user.region):
            raise HTTPException(status_code=403, detail="Access denied")

    ef = record.emission_factor
    trace = calculate_co2e(
        record.activity_value, ef.factor_value if ef else 0,
        record.activity_unit, ef.unit if ef else "unknown",
    )
    result = EmissionRecordWithTrace.model_validate(record)
    result.calculation_trace = {
        **trace["calculation_trace"],
        "ef_source":       ef.source if ef else None,
        "ef_version":      ef.version_tag if ef else None,
        "ef_source_url":   ef.source_url if ef else None,
        "ef_material_type": ef.material_type if ef else None,
        "data_quality":    str(record.data_quality),
        "is_ai_estimated": record.is_ai_estimated,
        "submitted_at":    str(record.submitted_at),
        "submitted_by":    record.submitted_by,
        "rejection_reason": record.rejection_reason,
    }
    return result


@router.patch("/{record_id}/status")
def update_record_status(record_id: int, body: RecordStatusUpdate,
                         db: Session = Depends(get_db),
                         current_user=Depends(require_manager)):
    record = db.query(EmissionRecord).options(
        joinedload(EmissionRecord.vendor).joinedload(VendorProfile.user)
    ).filter(EmissionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    _check_period_locked(db, record.period_start, record.period_end)

    # Manager region check
    if current_user.role == "manager":
        if region_value(record.region) != region_value(current_user.region):
            raise HTTPException(status_code=403, detail="Access denied")

    old_status = record.status
    record.status = body.status
    if body.status == "approved":
        record.approved_by = current_user.id
        record.approved_at = datetime.utcnow()
    if body.status == "rejected" and body.notes:
        record.rejection_reason = body.notes

    vendor_user = record.vendor.user if record.vendor else None
    if vendor_user:
        is_approved = (body.status == "approved")
        msg = (f"Record #{record_id} has been approved."
               if is_approved
               else f"Record #{record_id} was rejected. Reason: {body.notes or 'See platform'}")
        notify(db, vendor_user.id,
               NotificationType.record_approved if is_approved
               else NotificationType.record_rejected,
               f"Record {body.status.title()}", msg,
               link="/emissions")
        send_record_status_email(
            vendor_user.email,
            vendor_user.full_name or vendor_user.email,
            record_id, body.status, body.notes,
        )

    log_action(db, current_user.id, "STATUS_UPDATE", "emission_records", record_id,
               old_value={"status": str(old_status)},
               new_value={"status": str(body.status)},
               description=body.notes)
    db.commit()
    return {"message": f"Status updated to {body.status}"}
