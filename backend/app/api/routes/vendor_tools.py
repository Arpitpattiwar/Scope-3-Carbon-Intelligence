"""
Vendor-specific tools: export own data, BRSR report, submission history,
bulk reminders, intensity metrics, data quality upgrade prompts.
"""
import io, csv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import datetime, date

from app.db.database import get_db
from app.models.user import (
    EmissionRecord, VendorProfile, EmissionFactor, User
)
from app.core.security import get_current_user, require_manager
from app.services.email_service import send_email
from app.utils.helpers import region_value

router = APIRouter(prefix="/vendor", tags=["vendor-tools"])


def _get_profile(db, user):
    p = db.query(VendorProfile).filter(VendorProfile.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    return p


# ── Submission history (timeline view) ───────────────────────────────────────

@router.get("/history")
def submission_history(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403)
    profile = _get_profile(db, current_user)
    q = db.query(EmissionRecord).filter(EmissionRecord.vendor_id == profile.id)
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)
    records = q.order_by(EmissionRecord.period_start.desc()).all()

    result = []
    for r in records:
        ef = db.query(EmissionFactor).filter(EmissionFactor.id == r.ef_id).first()
        result.append({
            "id": r.id,
            "category_id": r.category_id,
            "period_start": str(r.period_start),
            "period_end": str(r.period_end),
            "activity_value": r.activity_value,
            "activity_unit": r.activity_unit,
            "calculated_co2e": r.calculated_co2e,
            "data_quality": str(r.data_quality),
            "status": str(r.status),
            "rejection_reason": r.rejection_reason,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "ef_source": ef.source if ef else None,
            "ef_unit": ef.unit if ef else None,
        })
    return result


# ── Emission intensity stats ──────────────────────────────────────────────────

@router.get("/intensity")
def emission_intensity(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403)
    profile = _get_profile(db, current_user)

    records = db.query(EmissionRecord).filter(
        EmissionRecord.vendor_id == profile.id,
        EmissionRecord.status.in_(["submitted", "approved"]),
    ).all()

    if not records:
        return {"message": "No submitted records yet", "records": 0}

    total_co2e = sum(r.calculated_co2e or 0 for r in records)
    count = len(records)
    by_quality = {"A": 0, "B": 0, "C": 0}
    for r in records:
        q = str(r.data_quality).split(".")[-1]
        by_quality[q] = by_quality.get(q, 0) + 1

    # Monthly trend
    monthly: dict = {}
    for r in records:
        key = f"{r.period_start.year}-{r.period_start.month:02d}"
        monthly[key] = monthly.get(key, 0) + (r.calculated_co2e or 0)
    trend = [{"period": k, "co2e": round(v, 4)} for k, v in sorted(monthly.items())]

    # Upgradeable records (C grade, not locked)
    upgradeable = [
        {"id": r.id, "category_id": r.category_id,
         "period": str(r.period_start), "co2e": r.calculated_co2e}
        for r in records if str(r.data_quality).endswith("C")
    ]

    return {
        "total_co2e": round(total_co2e, 4),
        "record_count": count,
        "co2e_per_record": round(total_co2e / count, 4) if count else 0,
        "data_quality": by_quality,
        "quality_score_pct": round((by_quality["A"] + by_quality["B"] * 0.5) / count * 100, 1) if count else 0,
        "trend": trend,
        "upgradeable_records": upgradeable,
    }


# ── Vendor export own data ────────────────────────────────────────────────────

@router.get("/export-csv")
def export_own_data(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "vendor":
        raise HTTPException(status_code=403)
    profile = _get_profile(db, current_user)
    q = db.query(EmissionRecord).filter(EmissionRecord.vendor_id == profile.id)
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)
    records = q.order_by(EmissionRecord.period_start).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID", "Category ID", "Period Start", "Period End",
        "Activity Value", "Activity Unit", "CO2e (tCO2e)",
        "Data Quality", "EF Source", "EF Version", "Status", "Submitted At",
    ])
    for r in records:
        ef = db.query(EmissionFactor).filter(EmissionFactor.id == r.ef_id).first()
        writer.writerow([
            r.id, r.category_id, r.period_start, r.period_end,
            r.activity_value, r.activity_unit, r.calculated_co2e,
            str(r.data_quality).split(".")[-1],
            ef.source if ef else "", ef.version_tag if ef else "",
            str(r.status).split(".")[-1],
            r.submitted_at.strftime("%Y-%m-%d %H:%M") if r.submitted_at else "",
        ])
    output.seek(0)
    fname = f"my_emissions_{year or 'all'}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ── BRSR report (India SEBI format) ──────────────────────────────────────────

@router.get("/brsr-export")
def brsr_export(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generates a BRSR (Business Responsibility & Sustainability Report)
    Principle 6 — Environment section export aligned to SEBI 2023 format.
    Returns CSV with the standard BRSR energy/emissions disclosure table.
    """
    if current_user.role not in ("admin", "manager", "auditor", "vendor"):
        raise HTTPException(status_code=403)

    # Collect data
    if current_user.role == "vendor":
        profile = _get_profile(db, current_user)
        vendor_filter = EmissionRecord.vendor_id == profile.id
        entity_name = profile.company_name or current_user.email
    else:
        vendor_filter = None
        entity_name = "All Vendors"

    q = db.query(EmissionRecord).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )
    if vendor_filter is not None:
        q = q.filter(vendor_filter)
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)
    records = q.all()

    total_scope3 = sum(r.calculated_co2e or 0 for r in records)
    by_cat: dict = {}
    for r in records:
        by_cat[r.category_id] = by_cat.get(r.category_id, 0) + (r.calculated_co2e or 0)

    output = io.StringIO()
    writer = csv.writer(output)

    # BRSR header
    writer.writerow(["BRSR — Principle 6: Environment"])
    writer.writerow(["Section C — Essential Indicators"])
    writer.writerow(["Entity:", entity_name])
    writer.writerow(["Reporting Period:", f"FY{year or date.today().year}"])
    writer.writerow(["Standard:", "SEBI BRSR 2023 / GHG Protocol Scope 3"])
    writer.writerow([])

    writer.writerow(["Disclosure", "Unit", "Current FY", "Previous FY (N/A)"])
    writer.writerow(["Total Scope 3 GHG Emissions", "tCO2e", round(total_scope3, 2), ""])
    writer.writerow([])

    writer.writerow(["Scope 3 Category Breakdown"])
    writer.writerow(["Category", "Description", "tCO2e"])
    from app.services.calculation_engine import get_category_name, SCOPE3_CATEGORIES
    for cat_id in sorted(by_cat.keys()):
        writer.writerow([cat_id, get_category_name(cat_id), round(by_cat[cat_id], 4)])

    writer.writerow([])
    writer.writerow(["Methodology", "GHG Protocol Corporate Value Chain (Scope 3) Standard"])
    writer.writerow(["Emission Factors", "DEFRA 2024 / IPCC AR6 / CPCB"])
    writer.writerow(["Assurance", "Internal"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=BRSR_Scope3_{year or 'all'}.csv"},
    )


# ── Bulk reminder to vendors ──────────────────────────────────────────────────

@router.post("/bulk-reminder")
def send_bulk_reminder(
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Email all vendors in region who have no records in the current quarter."""
    from calendar import monthrange
    now = datetime.utcnow()
    q_month = ((now.month - 1) // 3) * 3 + 1
    q_start = date(now.year, q_month, 1)
    q_end_month = q_month + 2
    q_end = date(now.year, q_end_month, monthrange(now.year, q_end_month)[1])

    # Find vendors in region
    q = db.query(User, VendorProfile).join(
        VendorProfile, VendorProfile.user_id == User.id
    ).filter(User.role == "vendor", User.is_active == True)
    if current_user.role == "manager":
        q = q.filter(User.region == current_user.region)

    reminded = []
    for user, profile in q.all():
        if not user.onboarding_complete:
            continue
        has_records = db.query(EmissionRecord).filter(
            EmissionRecord.vendor_id == profile.id,
            EmissionRecord.period_start >= q_start,
        ).first()
        if not has_records:
            body = f"""Dear {profile.contact_name or user.full_name or 'Vendor'},

This is a reminder to submit your Scope 3 emission data for Q{((now.month-1)//3)+1} {now.year}.

Period: {q_start} to {q_end}

Please log in and submit your data at: {__import__('app.core.config', fromlist=['settings']).settings.FRONTEND_URL}/submit

If you need assistance, contact your regional manager.

Regards,
ESG Platform
"""
            send_email(user.email, f"Reminder: Submit Q{((now.month-1)//3)+1} {now.year} Emission Data", body)
            reminded.append(user.email)

    return {
        "message": f"Reminder sent to {len(reminded)} vendors",
        "vendors": reminded,
        "period": f"{q_start} to {q_end}",
    }
