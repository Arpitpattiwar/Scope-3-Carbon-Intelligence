from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import Optional
import io

from app.db.database import get_db
from app.models.user import EmissionRecord, VendorProfile
from app.core.security import get_current_user
from app.services.report_service import generate_excel_report, generate_csv_template

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/download-excel")
def download_excel(
    year: Optional[int] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from sqlalchemy import extract

    q = db.query(EmissionRecord).options(
        joinedload(EmissionRecord.emission_factor),
        joinedload(EmissionRecord.vendor),
    ).filter(EmissionRecord.status.in_(["submitted", "approved"]))

    if current_user.role == "vendor":
        profile = db.query(VendorProfile).filter(VendorProfile.user_id == current_user.id).first()
        q = q.filter(EmissionRecord.vendor_id == profile.id)
    elif current_user.role == "manager":
        q = q.filter(EmissionRecord.region == current_user.region)

    if year:
        q = q.filter(extract("year", EmissionRecord.period_start) == year)
    if region and current_user.role in ("admin", "auditor"):
        q = q.filter(EmissionRecord.region == region)

    records = q.all()
    record_dicts = [
        {
            "ID": r.id,
            "Category": r.category_id,
            "Vendor": r.vendor.company_name if r.vendor else "",
            "Region": str(r.region),
            "Period Start": str(r.period_start),
            "Period End": str(r.period_end),
            "Activity Value": r.activity_value,
            "Activity Unit": r.activity_unit,
            "EF Source": r.emission_factor.source if r.emission_factor else "",
            "EF Version": r.emission_factor.version_tag if r.emission_factor else "",
            "EF Value": r.emission_factor.factor_value if r.emission_factor else "",
            "EF Unit": r.emission_factor.unit if r.emission_factor else "",
            "CO2e (tCO2e)": r.calculated_co2e,
            "Data Quality": str(r.data_quality),
            "Status": str(r.status),
            "AI Estimated": r.is_ai_estimated,
            "Submitted At": str(r.submitted_at),
        }
        for r in records
    ]

    total_co2e = sum(r.calculated_co2e or 0 for r in records)
    summary = {"total_co2e": total_co2e, "record_count": len(records)}

    excel_bytes = generate_excel_report(record_dicts, summary)

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=scope3_emissions_{year or 'all'}.xlsx"},
    )


@router.get("/csv-template")
def download_template():
    csv_bytes = generate_csv_template()
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scope3_upload_template.csv"},
    )
