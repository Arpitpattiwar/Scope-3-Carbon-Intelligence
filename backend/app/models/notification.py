from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class NotificationType(str, enum.Enum):
    vendor_onboarded    = "vendor_onboarded"
    record_submitted    = "record_submitted"
    record_approved     = "record_approved"
    record_rejected     = "record_rejected"
    vendor_invited      = "vendor_invited"
    report_ready        = "report_ready"
    period_locked       = "period_locked"
    system              = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    type        = Column(Enum(NotificationType), nullable=False)
    title       = Column(String(255), nullable=False)
    message     = Column(Text, nullable=False)
    link        = Column(String(255), nullable=True)   # e.g. /emissions?record=42
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
