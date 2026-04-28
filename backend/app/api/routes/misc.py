from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date, datetime
import io
import csv

from app.db.database import get_db
from app.models.user import EmissionFactor, AuditLog, ReportingPeriod
from app.schemas.schemas import (
    EmissionFactorCreate, EmissionFactorOut,
    AuditLogOut, ReportingPeriodCreate, ReportingPeriodOut,
)
from app.core.security import get_current_user, require_admin
from app.services.audit_service import log_action

# ── Emission Factors ──────────────────────────────────────────────────────────

ef_router = APIRouter(prefix="/emission-factors", tags=["emission-factors"])


@ef_router.get("", response_model=List[EmissionFactorOut])
def list_efs(category_id: Optional[int]=None, source: Optional[str]=None,
             region: Optional[str]=None, db: Session=Depends(get_db),
             current_user=Depends(get_current_user)):
    q = db.query(EmissionFactor).filter(EmissionFactor.is_active == True)
    if category_id: q = q.filter(EmissionFactor.category_id == category_id)
    if source:      q = q.filter(EmissionFactor.source == source)
    if region:      q = q.filter(EmissionFactor.region.in_([region, "global"]))
    return q.order_by(EmissionFactor.category_id, EmissionFactor.source).all()


@ef_router.post("", response_model=EmissionFactorOut)
def create_ef(body: EmissionFactorCreate, db: Session=Depends(get_db),
              current_user=Depends(require_admin)):
    ef = EmissionFactor(**body.model_dump(), created_by=current_user.id)
    db.add(ef)
    db.flush()
    log_action(db, current_user.id, "CREATE_EF", "emission_factors", ef.id,
               new_value={"source": body.source, "factor": body.factor_value})
    db.commit()
    db.refresh(ef)
    return ef


@ef_router.delete("/{ef_id}")
def deactivate_ef(ef_id: int, db: Session=Depends(get_db),
                  current_user=Depends(require_admin)):
    ef = db.query(EmissionFactor).filter(EmissionFactor.id == ef_id).first()
    if not ef: raise HTTPException(status_code=404)
    ef.is_active = False
    log_action(db, current_user.id, "DEACTIVATE_EF", "emission_factors", ef_id)
    db.commit()
    return {"message": "Deactivated"}


# ── Audit Log ─────────────────────────────────────────────────────────────────

audit_router = APIRouter(prefix="/audit", tags=["audit"])


@audit_router.get("/logs", response_model=List[AuditLogOut])
def get_audit_logs(user_id: Optional[int]=None, action: Optional[str]=None,
                   table_name: Optional[str]=None,
                   limit: int=Query(100, le=500), offset: int=0,
                   db: Session=Depends(get_db),
                   current_user=Depends(get_current_user)):
    if current_user.role not in ("admin","auditor"):
        raise HTTPException(status_code=403)
    q = db.query(AuditLog).options(joinedload(AuditLog.user))
    if user_id:     q = q.filter(AuditLog.user_id == user_id)
    if action:      q = q.filter(AuditLog.action == action)
    if table_name:  q = q.filter(AuditLog.table_name == table_name)
    return q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()


@audit_router.get("/logs/export-csv")
def export_audit_csv(db: Session=Depends(get_db),
                     current_user=Depends(get_current_user)):
    """Export full audit log as CSV — suggestion #9."""
    if current_user.role not in ("admin","auditor"):
        raise HTTPException(status_code=403)
    logs = db.query(AuditLog).options(joinedload(AuditLog.user))\
              .order_by(AuditLog.timestamp.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Timestamp","User Email","Role","Action",
                     "Table","Record ID","Description","IP Address"])
    for l in logs:
        writer.writerow([
            l.id,
            l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "",
            l.user.email if l.user else "",
            l.user.role if l.user else "",
            l.action, l.table_name or "", l.record_id or "",
            l.description or "", l.ip_address or "",
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )


# ── Reporting Periods ─────────────────────────────────────────────────────────

period_router = APIRouter(prefix="/reporting-periods", tags=["reporting"])


@period_router.get("", response_model=List[ReportingPeriodOut])
def list_periods(db: Session=Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(ReportingPeriod).order_by(ReportingPeriod.period_start.desc()).all()


@period_router.post("", response_model=ReportingPeriodOut)
def create_period(body: ReportingPeriodCreate, db: Session=Depends(get_db),
                  current_user=Depends(require_admin)):
    period = ReportingPeriod(**body.model_dump())
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@period_router.post("/{period_id}/lock")
def lock_period(period_id: int, db: Session=Depends(get_db),
                current_user=Depends(require_admin)):
    period = db.query(ReportingPeriod).filter(ReportingPeriod.id == period_id).first()
    if not period: raise HTTPException(status_code=404)
    period.is_locked = True
    period.locked_by = current_user.id
    period.locked_at = datetime.utcnow()
    log_action(db, current_user.id, "LOCK_PERIOD", "reporting_periods", period_id,
               description=f"Locked: {period.label}")
    db.commit()
    return {"message": f"Period '{period.label}' locked"}
