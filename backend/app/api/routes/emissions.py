from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from typing import List, Optional
import logging
import pandas as pd
import io
from datetime import datetime, date

from app.db.database import get_db
from app.models.user import (
    EmissionRecord, EmissionFactor, VendorProfile, User,
    ReportingPeriod, RejectionReasonCode as RRCode,
)
from app.models.notification import NotificationType
from app.schemas.schemas import (
    EmissionRecordCreate, EmissionRecordOut, EmissionRecordWithTrace,
    MissingDataEstimateRequest, MissingDataEstimateResponse,
    RecordStatusUpdate, BulkStatusUpdate,
    ParametricCalculateRequest, ParametricCalculateResponse,
    RejectionReasonCode, REJECTION_CODE_LABELS,
)
from app.core.security import get_current_user, require_manager
from app.core.config import settings
from app.services.calculation_engine import (
    calculate_co2e, estimate_missing_data, get_category_name,
    validate_activity_data, calculate_parametric, get_parametric_schema,
)
from app.services.audit_service import log_action
from app.services.ai_estimation import ALL_SPEND_CATEGORIES
from app.services.ml_client import MLServiceError, build_anomaly_payload, score_anomaly
from app.services.notification_service import notify
from app.services.email_service import send_record_status_email
from app.utils.helpers import region_value
from pydantic import BaseModel, Field

router = APIRouter(prefix="/emissions", tags=["emissions"])
logger = logging.getLogger(__name__)


class AIEstimateAcceptRequest(BaseModel):
    category_id: int = Field(ge=1, le=15)
    period_start: date
    period_end: date
    spend_inr: float = Field(gt=0)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    nic_4digit: Optional[int] = Field(default=None, gt=0)
    region: Optional[str] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_period_locked(db, period_start, period_end):
    locked = db.query(ReportingPeriod).filter(
        ReportingPeriod.is_locked == True,
        ReportingPeriod.period_start <= period_end,
        ReportingPeriod.period_end >= period_start,
    ).first()
    if locked:
        raise HTTPException(status_code=423, detail=f"Reporting period '{locked.label}' is locked.")

def _get_vendor_profile(db, user):
    p = db.query(VendorProfile).filter(VendorProfile.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Vendor profile not found. Complete onboarding first.")
    return p

def _enrich_records(records, db):
    vids = list({r.vendor_id for r in records})
    profiles = {p.id: p for p in db.query(VendorProfile).filter(VendorProfile.id.in_(vids)).all()}
    result = []
    for r in records:
        d = EmissionRecordOut.model_validate(r).model_dump()
        p = profiles.get(r.vendor_id)
        d["vendor_company_name"] = p.company_name if p else None
        result.append(d)
    return result

def _safe_parse_nic(raw):
    if raw in (None, ""): return None
    digits = "".join(c for c in str(raw) if c.isdigit())
    return int(digits) if digits else None

def _safe_anomaly_check(*, category_id, activity_value, activity_unit, ef_value, calculated_co2e, data_quality, region):
    try:
        payload = build_anomaly_payload(
            category_id=category_id, activity_value=activity_value,
            activity_unit=activity_unit, ef_value=ef_value,
            calculated_co2e=calculated_co2e, data_quality=data_quality, region=region,
        )
        return score_anomaly(payload)
    except (MLServiceError, ValueError) as exc:
        logger.warning("Anomaly check unavailable: %s", exc)
        return None

def _notify_resubmit(db, record, profile, original_rejector_id, co2e):
    """Notify managers and original rejector that a revised record was submitted."""
    managers = db.query(User).filter(
        User.role == "manager", User.region == record.region, User.is_active == True,
    ).all()
    comp = profile.company_name or "Vendor"
    cat  = get_category_name(record.category_id)
    msg  = f"{comp} revised and resubmitted {cat} record (originally rejected). CO₂e: {co2e:.3f} tCO₂e"
    notified = set()
    for mgr in managers:
        notify(db, mgr.id, NotificationType.record_submitted,
               "Revised record — please re-review", msg, link="/emissions?status=submitted")
        notified.add(mgr.id)
    # Also ping original rejector if they are not already in the manager list
    if original_rejector_id and original_rejector_id not in notified:
        notify(db, original_rejector_id, NotificationType.record_submitted,
               "Revised record awaiting re-review", msg, link="/emissions?status=submitted")


# ── Parametric calculation helper ─────────────────────────────────────────────

@router.post("/calculate-parametric", response_model=ParametricCalculateResponse)
def calculate_parametric_activity(
    body: ParametricCalculateRequest,
    current_user=Depends(get_current_user),
):
    """Convert raw measurement parameters into activity_value + unit."""
    try:
        result = calculate_parametric(body.category_id, body.params)
        return ParametricCalculateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/parametric-schema/{category_id}")
def get_parametric_entry_schema(category_id: int, current_user=Depends(get_current_user)):
    """Return field definitions for parametric entry mode for a given category."""
    schema = get_parametric_schema(category_id)
    if not schema:
        return {"supported": False, "category_id": category_id}
    return {"supported": True, "category_id": category_id, **schema}


# ── Create record ─────────────────────────────────────────────────────────────

@router.post("", response_model=EmissionRecordOut)
def create_emission_record(body: EmissionRecordCreate, db: Session = Depends(get_db),
                            current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can submit records")
    _check_period_locked(db, body.period_start, body.period_end)

    ef = db.query(EmissionFactor).filter(
        EmissionFactor.id == body.ef_id, EmissionFactor.is_active == True).first()
    if not ef:
        raise HTTPException(status_code=404, detail="Emission factor not found")

    validation = validate_activity_data(body.category_id, body.activity_value, body.activity_unit)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail="; ".join(validation["errors"]))

    result = calculate_co2e(body.activity_value, ef.factor_value, body.activity_unit, ef.unit)
    anomaly_check = _safe_anomaly_check(
        category_id=body.category_id, activity_value=body.activity_value,
        activity_unit=body.activity_unit, ef_value=ef.factor_value,
        calculated_co2e=result["calculated_co2e"], data_quality=body.data_quality,
        region=current_user.region,
    )
    profile = _get_vendor_profile(db, current_user)

    record = EmissionRecord(
        vendor_id=profile.id, submitted_by=current_user.id,
        category_id=body.category_id, period_start=body.period_start,
        period_end=body.period_end, activity_value=body.activity_value,
        activity_unit=body.activity_unit, ef_id=body.ef_id,
        calculated_co2e=result["calculated_co2e"],
        data_quality=body.data_quality, input_method=body.input_method,
        input_mode=body.input_mode or "direct",
        parametric_inputs=body.parametric_inputs,
        parent_record_id=body.parent_record_id,
        region=current_user.region, status="submitted",
        notes=body.notes, is_ai_estimated=False,
    )
    db.add(record)
    db.flush()

    # If this is a resubmit, notify original rejector
    if body.parent_record_id:
        parent = db.query(EmissionRecord).filter(
            EmissionRecord.id == body.parent_record_id).first()
        original_rejector = parent.approved_by if parent else None
        _notify_resubmit(db, record, profile, original_rejector, result["calculated_co2e"])
    else:
        managers = db.query(User).filter(
            User.role == "manager", User.region == current_user.region,
            User.is_active == True).all()
        comp = profile.company_name or current_user.email
        for mgr in managers:
            notify(db, mgr.id, NotificationType.record_submitted,
                   "New emission record submitted",
                   f"{comp} submitted a {get_category_name(body.category_id)} record "
                   f"({result['calculated_co2e']:.3f} tCO₂e)", link="/emissions")

    log_action(db, current_user.id, "CREATE_EMISSION_RECORD", "emission_records", record.id,
               new_value={
                   "co2e": result["calculated_co2e"], "category": body.category_id,
                   "anomaly_flagged": anomaly_check.get("is_flagged") if anomaly_check else None,
                   "unit_warning": result.get("unit_check", {}).get("warning"),
                   "parent_record_id": body.parent_record_id,
               })
    db.commit()
    db.refresh(record)
    resp = EmissionRecordOut.model_validate(record).model_dump()
    resp["anomaly_check"] = anomaly_check
    if result.get("unit_check", {}).get("warning"):
        resp["unit_warning"] = result["unit_check"]["warning"]
    return resp


# ── Draft save ────────────────────────────────────────────────────────────────

@router.post("/draft", response_model=EmissionRecordOut)
def save_draft(body: EmissionRecordCreate, db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    """Save a record as draft without submitting for approval."""
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can save drafts")
    profile = _get_vendor_profile(db, current_user)

    ef = db.query(EmissionFactor).filter(
        EmissionFactor.id == body.ef_id, EmissionFactor.is_active == True).first()
    if not ef:
        raise HTTPException(status_code=404, detail="Emission factor not found")

    result = calculate_co2e(body.activity_value, ef.factor_value, body.activity_unit, ef.unit)
    record = EmissionRecord(
        vendor_id=profile.id, submitted_by=current_user.id,
        category_id=body.category_id, period_start=body.period_start,
        period_end=body.period_end, activity_value=body.activity_value,
        activity_unit=body.activity_unit, ef_id=body.ef_id,
        calculated_co2e=result["calculated_co2e"],
        data_quality=body.data_quality, input_method=body.input_method,
        input_mode=body.input_mode or "direct",
        parametric_inputs=body.parametric_inputs,
        parent_record_id=body.parent_record_id,
        region=current_user.region, status="draft",
        notes=body.notes, is_ai_estimated=False,
    )
    db.add(record)
    log_action(db, current_user.id, "SAVE_DRAFT", "emission_records", None,
               new_value={"category": body.category_id, "co2e": result["calculated_co2e"]})
    db.commit()
    db.refresh(record)
    return EmissionRecordOut.model_validate(record)


# ── Submit draft ──────────────────────────────────────────────────────────────

@router.post("/{record_id}/submit", response_model=EmissionRecordOut)
def submit_draft(record_id: int, db: Session = Depends(get_db),
                 current_user=Depends(get_current_user)):
    """Promote a draft record to 'submitted' for manager review."""
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can submit records")
    profile = _get_vendor_profile(db, current_user)
    record  = db.query(EmissionRecord).filter(
        EmissionRecord.id == record_id,
        EmissionRecord.vendor_id == profile.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.status not in ("draft",):
        raise HTTPException(status_code=422, detail=f"Record is '{record.status}' — only drafts can be submitted")
    _check_period_locked(db, record.period_start, record.period_end)

    record.status = "submitted"
    managers = db.query(User).filter(
        User.role == "manager", User.region == current_user.region, User.is_active == True).all()
    comp = profile.company_name or current_user.email
    for mgr in managers:
        notify(db, mgr.id, NotificationType.record_submitted,
               "Draft record submitted for approval",
               f"{comp} submitted {get_category_name(record.category_id)} record "
               f"({record.calculated_co2e:.3f} tCO₂e)", link="/emissions")
    log_action(db, current_user.id, "SUBMIT_DRAFT", "emission_records", record_id)
    db.commit()
    db.refresh(record)
    return EmissionRecordOut.model_validate(record)


# ── CSV upload ────────────────────────────────────────────────────────────────

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can upload data")
    profile = _get_vendor_profile(db, current_user)
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse CSV file")
    required = {"category_id","period_start","period_end","activity_value","activity_unit","ef_id"}
    missing  = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing columns: {missing}")
    try:
        starts = pd.to_datetime(df["period_start"], errors="coerce").dropna()
        ends   = pd.to_datetime(df["period_end"],   errors="coerce").dropna()
        if not starts.empty and not ends.empty:
            _check_period_locked(db, starts.min().date(), ends.max().date())
    except HTTPException:
        raise
    except Exception:
        pass
    created, errors, flagged_rows = [], [], []
    for idx, row in df.iterrows():
        try:
            ef = db.query(EmissionFactor).filter(
                EmissionFactor.id == int(row["ef_id"]), EmissionFactor.is_active == True).first()
            if not ef:
                errors.append({"row": idx+2, "error": f"EF id {row['ef_id']} not found"}); continue
            result = calculate_co2e(float(row["activity_value"]), ef.factor_value,
                                    str(row["activity_unit"]), ef.unit)
            anomaly_check = _safe_anomaly_check(
                category_id=int(row["category_id"]), activity_value=float(row["activity_value"]),
                activity_unit=str(row["activity_unit"]), ef_value=ef.factor_value,
                calculated_co2e=result["calculated_co2e"],
                data_quality=str(row.get("data_quality","B")), region=current_user.region,
            )
            record = EmissionRecord(
                vendor_id=profile.id, submitted_by=current_user.id,
                category_id=int(row["category_id"]),
                period_start=row["period_start"], period_end=row["period_end"],
                activity_value=float(row["activity_value"]), activity_unit=str(row["activity_unit"]),
                ef_id=int(row["ef_id"]), calculated_co2e=result["calculated_co2e"],
                data_quality=str(row.get("data_quality","B")), input_method="csv",
                region=current_user.region, status="submitted",
                notes=str(row.get("notes","") or ""), is_ai_estimated=False,
            )
            db.add(record); created.append(idx+2)
            if anomaly_check and anomaly_check.get("is_flagged"):
                flagged_rows.append({"row": idx+2, "category_id": int(row["category_id"]),
                                     "anomaly_check": anomaly_check})
        except Exception as e:
            errors.append({"row": idx+2, "error": str(e)})
    if created:
        log_action(db, current_user.id, "CSV_UPLOAD", "emission_records",
                   description=f"Uploaded {len(created)} records via CSV")
        db.commit()
    return {"created": len(created), "errors": errors, "total_rows": len(df),
            "flagged_count": len(flagged_rows), "flagged_rows": flagged_rows}


# ── Status update (single) ────────────────────────────────────────────────────

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
    if current_user.role == "manager":
        if region_value(record.region) != region_value(current_user.region):
            raise HTTPException(status_code=403, detail="Access denied")

    # Rejection MUST have a reason code
    if body.status == "rejected" and not body.rejection_reason_code:
        raise HTTPException(status_code=422,
                            detail="rejection_reason_code is required when rejecting a record")

    old_status = record.status
    record.status = body.status
    if body.status == "approved":
        record.approved_by = current_user.id
        record.approved_at = datetime.utcnow()
    if body.status == "rejected":
        record.rejection_reason_code = body.rejection_reason_code
        code_label = REJECTION_CODE_LABELS.get(body.rejection_reason_code, "")
        record.rejection_reason = (
            f"[{code_label}] {body.notes}" if body.notes else code_label
        )
        # Track who rejected for re-review notifications
        record.approved_by = current_user.id

    vendor_user = record.vendor.user if record.vendor else None
    if vendor_user:
        is_approved = (body.status == "approved")
        msg = (f"Record #{record_id} approved." if is_approved
               else (f"Record #{record_id} rejected — "
                     f"{REJECTION_CODE_LABELS.get(str(body.rejection_reason_code or ''), '')}. "
                     f"{body.notes or ''}").strip())
        notify(db, vendor_user.id,
               NotificationType.record_approved if is_approved else NotificationType.record_rejected,
               f"Record {body.status.title()}", msg, link="/history")
        send_record_status_email(vendor_user.email, vendor_user.full_name or vendor_user.email,
                                  record_id, body.status, record.rejection_reason)

    log_action(db, current_user.id, "STATUS_UPDATE", "emission_records", record_id,
               old_value={"status": getattr(old_status,"value",str(old_status))},
               new_value={"status": getattr(body.status,"value",str(body.status)), "rejection_code": getattr(body.rejection_reason_code,"value","") if body.rejection_reason_code else ""},
               description=body.notes)
    db.commit()
    return {"message": f"Status updated to {body.status}"}


# ── Bulk status update ────────────────────────────────────────────────────────

@router.patch("/bulk-status")
def bulk_update_status(body: BulkStatusUpdate, db: Session = Depends(get_db),
                        current_user=Depends(require_manager)):
    if body.status == "rejected" and not body.rejection_reason_code:
        raise HTTPException(status_code=422, detail="rejection_reason_code required for bulk rejection")

    records = db.query(EmissionRecord).options(
        joinedload(EmissionRecord.vendor).joinedload(VendorProfile.user)
    ).filter(EmissionRecord.id.in_(body.record_ids)).all()

    if not records:
        raise HTTPException(status_code=404, detail="No matching records found")

    updated = []
    skipped = []
    for record in records:
        # Region check
        if current_user.role == "manager":
            if region_value(record.region) != region_value(current_user.region):
                skipped.append({"id": record.id, "reason": "outside your region"})
                continue
        # Only process submitted records
        if record.status != "submitted":
            skipped.append({"id": record.id, "reason": f"status is '{record.status}'"})
            continue
        try:
            _check_period_locked(db, record.period_start, record.period_end)
        except HTTPException:
            skipped.append({"id": record.id, "reason": "period is locked"})
            continue

        record.status = body.status
        if body.status == "approved":
            record.approved_by = current_user.id
            record.approved_at = datetime.utcnow()
        if body.status == "rejected":
            record.rejection_reason_code = body.rejection_reason_code
            code_label = REJECTION_CODE_LABELS.get(str(body.rejection_reason_code), "")
            record.rejection_reason = f"[{code_label}] {body.notes}" if body.notes else code_label
            record.approved_by = current_user.id

        vendor_user = record.vendor.user if record.vendor else None
        if vendor_user:
            is_approved = (body.status == "approved")
            msg = (f"Record #{record.id} bulk {body.status}."
                   + ("" if is_approved else f" Reason: {record.rejection_reason}"))
            notify(db, vendor_user.id,
                   NotificationType.record_approved if is_approved else NotificationType.record_rejected,
                   f"Record {body.status.title()}", msg, link="/history")
        updated.append(record.id)

    log_action(db, current_user.id, "BULK_STATUS_UPDATE", "emission_records",
               description=f"Bulk {body.status}: {len(updated)} records",
               new_value={"updated": updated, "skipped": [s["id"] for s in skipped]})
    db.commit()
    return {"updated": len(updated), "skipped": skipped,
            "message": f"Updated {len(updated)} records to '{body.status}'"}


# ── List records ──────────────────────────────────────────────────────────────

@router.get("")
def list_records(region: Optional[str] = None, category_id: Optional[int] = None,
                  vendor_id: Optional[int] = None, status: Optional[str] = None,
                  year: Optional[int] = None, db: Session = Depends(get_db),
                  current_user=Depends(get_current_user)):
    q = db.query(EmissionRecord).options(joinedload(EmissionRecord.emission_factor))
    if current_user.role == "vendor":
        profile = _get_vendor_profile(db, current_user)
        q = q.filter(EmissionRecord.vendor_id == profile.id)
    elif current_user.role == "manager":
        q = q.filter(EmissionRecord.region == current_user.region)
    if region and current_user.role in ("admin","auditor"):
        q = q.filter(EmissionRecord.region == region)
    if category_id:
        q = q.filter(EmissionRecord.category_id == category_id)
    if vendor_id and current_user.role in ("admin","manager"):
        q = q.filter(EmissionRecord.vendor_id == vendor_id)
    if status:
        q = q.filter(EmissionRecord.status == status)
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)
    records = q.order_by(EmissionRecord.submitted_at.desc()).limit(500).all()
    if current_user.role != "vendor":
        return _enrich_records(records, db)
    return [EmissionRecordOut.model_validate(r) for r in records]


# ── Trace ─────────────────────────────────────────────────────────────────────

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
    trace = calculate_co2e(record.activity_value, ef.factor_value if ef else 0,
                            record.activity_unit, ef.unit if ef else "unknown")
    anomaly_check = None
    if ef:
        anomaly_check = _safe_anomaly_check(
            category_id=record.category_id, activity_value=record.activity_value,
            activity_unit=record.activity_unit, ef_value=ef.factor_value,
            calculated_co2e=record.calculated_co2e or trace["calculated_co2e"],
            data_quality=record.data_quality, region=record.region,
        )
    result = EmissionRecordWithTrace.model_validate(record)
    result.anomaly_check = anomaly_check
    result.calculation_trace = {
        **trace["calculation_trace"],
        "ef_source": ef.source if ef else None,
        "ef_version": ef.version_tag if ef else None,
        "ef_source_url": ef.source_url if ef else None,
        "ef_material_type": ef.material_type if ef else None,
        "data_quality": str(record.data_quality),
        "is_ai_estimated": record.is_ai_estimated,
        "submitted_at": str(record.submitted_at),
        "submitted_by": record.submitted_by,
        "rejection_reason": record.rejection_reason,
        "rejection_reason_code": str(record.rejection_reason_code) if record.rejection_reason_code else None,
        "parent_record_id": record.parent_record_id,
        "parametric_inputs": record.parametric_inputs,
        "anomaly_check": anomaly_check,
    }
    return result


# ── AI Estimation ─────────────────────────────────────────────────────────────

@router.post("/estimate-missing", response_model=MissingDataEstimateResponse)
def estimate_missing_record_data(body: MissingDataEstimateRequest, db: Session = Depends(get_db),
                                   current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can request AI estimations")
    if not settings.AI_ESTIMATION_ENABLED:
        raise HTTPException(status_code=503, detail="AI estimation is not enabled. Set AI_ESTIMATION_ENABLED=true.")
    if body.category_id not in ALL_SPEND_CATEGORIES:
        raise HTTPException(status_code=422, detail="category_id must be 1-15")
    profile    = _get_vendor_profile(db, current_user)
    nic_4digit = body.nic_4digit or _safe_parse_nic(profile.nic_code)
    region     = (getattr(body.region,"value",body.region) or
                  getattr(profile.region,"value",profile.region) or
                  getattr(current_user.region,"value",current_user.region))
    estimation = estimate_missing_data(body.category_id,
        {"spend_inr": body.spend_inr, "year": body.year or date.today().year,
         "nic_4digit": nic_4digit, "region": region},
        {"nic_code": nic_4digit, "region": region, "company_name": profile.company_name})
    if not estimation:
        raise HTTPException(status_code=503, detail="AI estimation unavailable")
    return estimation


@router.post("/accept-estimate", response_model=EmissionRecordOut)
def accept_ai_estimate(body: AIEstimateAcceptRequest, db: Session = Depends(get_db),
                        current_user=Depends(get_current_user)):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403, detail="Only vendors can accept AI estimates")
    if not settings.AI_ESTIMATION_ENABLED:
        raise HTTPException(status_code=503, detail="AI estimation not enabled")
    if body.category_id not in ALL_SPEND_CATEGORIES:
        raise HTTPException(status_code=422, detail="category_id must be 1-15")
    _check_period_locked(db, body.period_start, body.period_end)
    profile    = _get_vendor_profile(db, current_user)
    nic_4digit = body.nic_4digit or _safe_parse_nic(profile.nic_code)
    region     = (body.region or getattr(profile.region,"value",profile.region) or
                  getattr(current_user.region,"value",current_user.region))
    estimation = estimate_missing_data(body.category_id,
        {"spend_inr": body.spend_inr, "year": body.year or body.period_start.year,
         "nic_4digit": nic_4digit, "region": str(region)},
        {"nic_code": nic_4digit, "region": str(region), "company_name": profile.company_name})
    if not estimation:
        raise HTTPException(status_code=503, detail="AI estimation failed")
    ef = db.query(EmissionFactor).filter(
        EmissionFactor.category_id == body.category_id,
        EmissionFactor.is_active == True).first()
    if not ef:
        raise HTTPException(status_code=422,
                            detail=f"No active EF for category {body.category_id}")
    record = EmissionRecord(
        vendor_id=profile.id, submitted_by=current_user.id,
        category_id=body.category_id, period_start=body.period_start,
        period_end=body.period_end, activity_value=body.spend_inr, activity_unit="INR",
        ef_id=ef.id, calculated_co2e=estimation["estimated_co2e"],
        data_quality="C", input_method="ai_estimate", region=current_user.region,
        status="draft", notes=body.notes or estimation["explanation"], is_ai_estimated=True,
    )
    db.add(record)
    log_action(db, current_user.id, "ACCEPT_AI_ESTIMATE", "emission_records", None,
               new_value={"category_id": body.category_id,
                          "estimated_co2e": estimation["estimated_co2e"],
                          "confidence_score": estimation["confidence_score"],
                          "model_used": estimation["model_used"]})
    db.commit()
    db.refresh(record)
    return EmissionRecordOut.model_validate(record)
