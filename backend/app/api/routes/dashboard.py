from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
from typing import Optional, List
from datetime import date

from app.db.database import get_db
from app.models.user import EmissionRecord, VendorProfile, User
from app.core.security import get_current_user
from app.services.calculation_engine import get_category_name
from app.services.ml_client import forecast_emissions, MLServiceError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

REGIONS = ["north", "south", "east", "west", "central"]


def _base_query(db, current_user, region=None, vendor_id=None):
    q = db.query(EmissionRecord).join(
        VendorProfile, VendorProfile.id == EmissionRecord.vendor_id
    )
    if current_user.role == "vendor":
        q = q.filter(VendorProfile.user_id == current_user.id)
    elif current_user.role == "manager":
        q = q.filter(EmissionRecord.region == current_user.region)
    # admin/auditor: no region restriction by default

    if region and current_user.role in ("admin", "auditor"):
        q = q.filter(EmissionRecord.region == region)
    if vendor_id and current_user.role in ("admin", "manager"):
        q = q.filter(EmissionRecord.vendor_id == vendor_id)
    return q


@router.get("/summary")
def get_summary(
    region: Optional[str] = None,
    year: Optional[int] = None,
    vendor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = _base_query(db, current_user, region, vendor_id).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)

    total = q.with_entities(func.coalesce(func.sum(EmissionRecord.calculated_co2e), 0)).scalar()
    count = q.count()

    # YoY comparison
    prev_year = (year or date.today().year) - 1
    q_prev = _base_query(db, current_user, region, vendor_id).filter(
        EmissionRecord.status.in_(["submitted", "approved"]),
        extract("year", EmissionRecord.period_start) == prev_year,
    )
    prev_total = q_prev.with_entities(
        func.coalesce(func.sum(EmissionRecord.calculated_co2e), 0)
    ).scalar()

    yoy_change = None
    if prev_total and prev_total > 0:
        yoy_change = round(((float(total) - float(prev_total)) / float(prev_total)) * 100, 2)

    # Data quality distribution
    quality_counts = q.with_entities(
        EmissionRecord.data_quality,
        func.count(EmissionRecord.id)
    ).group_by(EmissionRecord.data_quality).all()

    # Pending records count for manager/admin action badge
    pending_q = _base_query(db, current_user, region, vendor_id).filter(
        EmissionRecord.status == "submitted"
    )
    pending_count = pending_q.count()

    return {
        "total_co2e": round(float(total), 3),
        "record_count": count,
        "pending_records": pending_count,
        "yoy_change_pct": yoy_change,
        "prev_year_co2e": round(float(prev_total), 3),
        "data_quality_distribution": {str(q): c for q, c in quality_counts},
        "year": year or date.today().year,
    }


@router.get("/category-breakdown")
def get_category_breakdown(
    region: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = _base_query(db, current_user, region).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)

    rows = q.with_entities(
        EmissionRecord.category_id,
        func.coalesce(func.sum(EmissionRecord.calculated_co2e), 0).label("total"),
        func.count(EmissionRecord.id).label("count"),
    ).group_by(EmissionRecord.category_id).order_by(func.sum(EmissionRecord.calculated_co2e).desc()).all()

    grand_total = sum(float(r.total) for r in rows) or 1

    return [
        {
            "category_id": r.category_id,
            "category_name": get_category_name(r.category_id),
            "total_co2e": round(float(r.total), 3),
            "percentage": round((float(r.total) / grand_total) * 100, 2),
            "record_count": r.count,
        }
        for r in rows
    ]


@router.get("/region-breakdown")
def get_region_breakdown(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ("admin", "auditor"):
        return []

    q = db.query(EmissionRecord).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )
    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)

    rows = q.with_entities(
        EmissionRecord.region,
        func.coalesce(func.sum(EmissionRecord.calculated_co2e), 0).label("total"),
        func.count(func.distinct(EmissionRecord.vendor_id)).label("vendor_count"),
    ).group_by(EmissionRecord.region).all()

    grand_total = sum(float(r.total) for r in rows) or 1

    return [
        {
            "region": str(r.region),
            "total_co2e": round(float(r.total), 3),
            "percentage": round((float(r.total) / grand_total) * 100, 2),
            "vendor_count": r.vendor_count,
        }
        for r in rows
    ]


@router.get("/trend")
def get_trend(
    region: Optional[str] = None,
    vendor_id: Optional[int] = None,
    frequency: str = Query("monthly", enum=["monthly", "quarterly", "yearly"]),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = _base_query(db, current_user, region, vendor_id).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )

    if frequency == "monthly":
        rows = q.with_entities(
            extract("year", EmissionRecord.period_start).label("yr"),
            extract("month", EmissionRecord.period_start).label("mo"),
            func.sum(EmissionRecord.calculated_co2e).label("total"),
            func.count(EmissionRecord.id).label("count"),
        ).group_by("yr", "mo").order_by("yr", "mo").all()
        return [
            {"period": f"{int(r.yr)}-{int(r.mo):02d}",
             "total_co2e": round(float(r.total or 0), 3),
             "record_count": r.count}
            for r in rows
        ]

    elif frequency == "quarterly":
        rows = q.with_entities(
            extract("year", EmissionRecord.period_start).label("yr"),
            ((extract("month", EmissionRecord.period_start) - 1) / 3 + 1).label("qtr"),
            func.sum(EmissionRecord.calculated_co2e).label("total"),
            func.count(EmissionRecord.id).label("count"),
        ).group_by("yr", "qtr").order_by("yr", "qtr").all()
        return [
            {"period": f"{int(r.yr)}-Q{int(r.qtr)}",
             "total_co2e": round(float(r.total or 0), 3),
             "record_count": r.count}
            for r in rows
        ]

    else:  # yearly
        rows = q.with_entities(
            extract("year", EmissionRecord.period_start).label("yr"),
            func.sum(EmissionRecord.calculated_co2e).label("total"),
            func.count(EmissionRecord.id).label("count"),
        ).group_by("yr").order_by("yr").all()
        return [
            {"period": str(int(r.yr)),
             "total_co2e": round(float(r.total or 0), 3),
             "record_count": r.count}
            for r in rows
        ]


@router.get("/forecast")
def get_forecast(
    sector: str = Query(
        "coal",
        enum=["oil", "coal", "gas", "cement"],
        description=(
            "Macro sector proxy used for forecasting. "
            "oil→transport, coal→industrial/purchased goods, "
            "gas→fuel & energy, cement→construction. "
            "The forecast uses this sector's national emission pattern "
            "scaled to your organisation's recent emission history."
        ),
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Return a 3-month emission forecast for the current user's scope,
    augmented with ML-model confidence intervals.

    Method
    ------
    1. Pull the last ≤24 months of approved/submitted emission totals
       from the database for this user's scope.
    2. Pass the last 12 months as history to the ML forecasting service.
    3. The ML service (LSTM winner) scales the supplied history through
       the sector-specific MinMax scaler, runs inference, and returns
       3-month point forecasts + 90% prediction intervals.
    4. The returned forecast values are *relative*: they represent
       expected change patterns from the history, not absolute MtCO₂.

    If fewer than 12 months of data exist, the endpoint returns the
    history with a `forecast_available: false` flag and a reason.
    """
    # ── Step 1: Fetch last 24 months of actual data ──────────────────────────
    q = _base_query(db, current_user).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )
    db_rows = q.with_entities(
        extract("year",  EmissionRecord.period_start).label("yr"),
        extract("month", EmissionRecord.period_start).label("mo"),
        func.sum(EmissionRecord.calculated_co2e).label("total"),
    ).group_by("yr", "mo").order_by("yr", "mo").all()

    history_full = [
        {
            "period": f"{int(r.yr)}-{int(r.mo):02d}",
            "value":  round(float(r.total or 0), 3),
        }
        for r in db_rows
    ]

    # ── Step 2: Require at least 12 months for a meaningful forecast ─────────
    if len(history_full) < 12:
        return {
            "history": history_full,
            "forecast": [],
            "lower_90": [],
            "upper_90": [],
            "forecast_available": False,
            "reason": (
                f"Need at least 12 months of data to forecast. "
                f"Currently have {len(history_full)} month(s). "
                "Keep submitting records and the forecast will activate automatically."
            ),
            "model_used": None,
            "sector": sector,
        }

    # ── Step 3: Build the 12-point history vector ────────────────────────────
    history_values = [p["value"] for p in history_full[-12:]]
    history_display = history_full[-12:]

    # ── Step 4: Call ML service ───────────────────────────────────────────────
    try:
        ml_result = forecast_emissions(sector=sector, history=history_values)
    except MLServiceError as exc:
        return {
            "history": history_display,
            "forecast": [],
            "lower_90": [],
            "upper_90": [],
            "forecast_available": False,
            "reason": (
                f"Forecast service is warming up or temporarily unavailable. "
                f"Details: {exc}"
            ),
            "model_used": None,
            "sector": sector,
        }

    # ── Step 5: Build forecast period labels (month after last history point) ─
    last = history_display[-1]["period"]          # e.g. "2024-11"
    last_yr, last_mo = int(last[:4]), int(last[5:7])
    forecast_periods = []
    for i in range(1, 4):
        mo = (last_mo - 1 + i) % 12 + 1
        yr = last_yr + (last_mo - 1 + i) // 12
        forecast_periods.append(f"{yr}-{mo:02d}")

    forecast_points = ml_result.get("forecast", [])
    lower_90        = ml_result.get("lower_90", [])
    upper_90        = ml_result.get("upper_90", [])

    # Pad/trim to 3 points in case model returns different length
    def _pad3(lst):
        lst = list(lst)[:3]
        while len(lst) < 3:
            lst.append(lst[-1] if lst else 0.0)
        return [round(v, 3) for v in lst]

    forecast_points = _pad3(forecast_points)
    lower_90        = _pad3(lower_90)
    upper_90        = _pad3(upper_90)

    return {
        "history":            history_display,
        "forecast_periods":   forecast_periods,
        "forecast":           forecast_points,
        "lower_90":           lower_90,
        "upper_90":           upper_90,
        "forecast_available": True,
        "model_used":         ml_result.get("model_used", "unknown"),
        "sector":             sector,
        "disclaimer": (
            "Forecast uses macro India sector emission patterns as a proxy. "
            "Values represent expected trend direction, not exact quantities. "
            "90% prediction intervals are indicative only (PI coverage ~63% in backtesting)."
        ),
    }


@router.get("/top-vendors")
def get_top_vendors(
    region: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ("admin", "manager", "auditor"):
        return []

    q = db.query(
        VendorProfile.id,
        VendorProfile.company_name,
        EmissionRecord.region,
        func.sum(EmissionRecord.calculated_co2e).label("total"),
        func.count(EmissionRecord.id).label("count"),
        func.max(EmissionRecord.submitted_at).label("last_submission"),
    ).join(EmissionRecord, EmissionRecord.vendor_id == VendorProfile.id).filter(
        EmissionRecord.status.in_(["submitted", "approved"])
    )

    if current_user.role == "manager":
        q = q.filter(EmissionRecord.region == current_user.region)
    elif region:
        q = q.filter(EmissionRecord.region == region)

    rows = q.group_by(
        VendorProfile.id, VendorProfile.company_name, EmissionRecord.region
    ).order_by(func.sum(EmissionRecord.calculated_co2e).desc()).limit(limit).all()

    return [
        {
            "vendor_id": r.id,
            "company_name": r.company_name or "Unknown",
            "region": str(r.region) if r.region else None,
            "total_co2e": round(float(r.total or 0), 3),
            "record_count": r.count,
            "last_submission": r.last_submission,
        }
        for r in rows
    ]


@router.get("/vendor-engagement")
def get_vendor_engagement(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Vendor engagement scores for manager/admin view."""
    if current_user.role not in ("admin", "manager"):
        return []

    q = db.query(User, VendorProfile).join(
        VendorProfile, VendorProfile.user_id == User.id
    ).filter(User.role == "vendor", User.is_active == True)

    if current_user.role == "manager":
        q = q.filter(User.region == current_user.region)

    results = []
    for user, profile in q.all():
        record_count = db.query(func.count(EmissionRecord.id)).filter(
            EmissionRecord.vendor_id == profile.id
        ).scalar() or 0

        # Simple engagement score (0-100)
        score = min(100, (
            (30 if user.onboarding_complete else 0) +
            (40 if record_count > 0 else 0) +
            (20 if record_count > 5 else (10 if record_count > 1 else 0)) +
            (10 if profile and profile.has_own_carbon_system else 0)
        ))

        results.append({
            "vendor_id": user.id,
            "company_name": profile.company_name if profile else user.email,
            "region": str(user.region) if user.region else None,
            "onboarding_complete": user.onboarding_complete,
            "record_count": record_count,
            "engagement_score": score,
        })

    return sorted(results, key=lambda x: x["engagement_score"], reverse=True)
