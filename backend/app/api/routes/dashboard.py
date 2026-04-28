from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
from typing import Optional, List
from datetime import date

from app.db.database import get_db
from app.models.user import EmissionRecord, VendorProfile, User
from app.core.security import get_current_user
from app.services.calculation_engine import get_category_name

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
