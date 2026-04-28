"""
Audit Service
=============
Central service for writing audit log entries.
Every mutation in the system should call log_action().
"""

from sqlalchemy.orm import Session
from app.models.user import AuditLog
from typing import Optional, Any


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    table_name: Optional[str] = None,
    record_id: Optional[int] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
        description=description,
        ip_address=ip_address,
    )
    db.add(entry)
    # Caller is responsible for db.commit()
