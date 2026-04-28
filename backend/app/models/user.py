from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Enum, JSON, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    admin   = "admin"
    manager = "manager"
    vendor  = "vendor"
    auditor = "auditor"


class Region(str, enum.Enum):
    north   = "north"
    south   = "south"
    east    = "east"
    west    = "west"
    central = "central"
    all     = "all"


class DataQuality(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


class InputMethod(str, enum.Enum):
    manual = "manual"
    csv    = "csv"
    api    = "api"


class RecordStatus(str, enum.Enum):
    draft     = "draft"
    submitted = "submitted"
    approved  = "approved"
    rejected  = "rejected"


class EFSource(str, enum.Enum):
    DEFRA  = "DEFRA"
    IPCC   = "IPCC"
    CPCB   = "CPCB"
    custom = "custom"


# ── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                   = Column(Integer, primary_key=True, index=True)
    email                = Column(String(255), unique=True, index=True, nullable=False)
    password_hash        = Column(String(255), nullable=False)
    full_name            = Column(String(255))
    phone                = Column(String(30))
    designation          = Column(String(255))
    role                 = Column(Enum(UserRole), nullable=False)
    region               = Column(Enum(Region), nullable=True)
    is_active            = Column(Boolean, default=True)
    onboarding_complete  = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=False)
    avatar_initials      = Column(String(4))
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    vendor_profile  = relationship("VendorProfile", back_populates="user", uselist=False)
    emission_records = relationship(
        "EmissionRecord",
        back_populates="submitted_by_user",
        foreign_keys="[EmissionRecord.submitted_by]",
    )
    audit_logs       = relationship("AuditLog", back_populates="user")
    sent_invitations = relationship("VendorInvitation", back_populates="invited_by_user")
    notifications    = relationship("Notification", back_populates="user",
                                    order_by="Notification.created_at.desc()")


# ── Vendor Profile ────────────────────────────────────────────────────────────

class VendorProfile(Base):
    __tablename__ = "vendor_profiles"

    id                   = Column(Integer, primary_key=True, index=True)
    user_id              = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    company_name         = Column(String(255))
    trade_name           = Column(String(255))
    gst_number           = Column(String(20))
    pan_number           = Column(String(15))
    cin_number           = Column(String(25))
    year_established     = Column(Integer)
    state                = Column(String(100))
    city                 = Column(String(100))
    region               = Column(Enum(Region))
    pin_code             = Column(String(10))
    address              = Column(Text)
    nic_code             = Column(String(10))
    material_category    = Column(Integer)
    material_name        = Column(String(255))
    supply_frequency     = Column(String(50))
    avg_annual_volume    = Column(Float)
    volume_unit          = Column(String(50))
    has_own_carbon_system = Column(Boolean, default=False)
    contact_name         = Column(String(255))
    contact_designation  = Column(String(255))
    contact_phone        = Column(String(20))
    onboarded_at         = Column(DateTime(timezone=True))

    user             = relationship("User", back_populates="vendor_profile")
    emission_records = relationship("EmissionRecord", back_populates="vendor")


# ── Vendor Invitation ─────────────────────────────────────────────────────────

class VendorInvitation(Base):
    __tablename__ = "vendor_invitations"

    id                = Column(Integer, primary_key=True, index=True)
    invited_by        = Column(Integer, ForeignKey("users.id"), nullable=False)
    email             = Column(String(255), nullable=False)
    temp_password_hash = Column(String(255), nullable=False)
    region            = Column(Enum(Region), nullable=False)
    status            = Column(String(20), default="pending")
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    expires_at        = Column(DateTime(timezone=True))

    invited_by_user = relationship("User", back_populates="sent_invitations")


# ── Emission Factor ───────────────────────────────────────────────────────────

class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id           = Column(Integer, primary_key=True, index=True)
    source       = Column(Enum(EFSource), nullable=False)
    category_id  = Column(Integer, nullable=False)
    subcategory  = Column(String(255))
    material_type = Column(String(255))
    factor_value = Column(Float, nullable=False)
    unit         = Column(String(100), nullable=False)
    region       = Column(String(100), default="global")
    version_tag  = Column(String(50), nullable=False)
    valid_from   = Column(Date)
    valid_to     = Column(Date)
    source_url   = Column(Text)
    notes        = Column(Text)
    is_active    = Column(Boolean, default=True)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    emission_records = relationship("EmissionRecord", back_populates="emission_factor")


# ── AI Estimate (Phase 2) ─────────────────────────────────────────────────────

class AIEstimate(Base):
    __tablename__ = "ai_estimates"

    id                     = Column(Integer, primary_key=True, index=True)
    model_used             = Column(String(100))
    inputs_json            = Column(JSON)
    baseline_ef            = Column(Float)
    ai_correction_factor   = Column(Float)
    confidence_score       = Column(Float)
    explanation_text       = Column(Text)
    methodology_reference  = Column(String(255))
    created_at             = Column(DateTime(timezone=True), server_default=func.now())

    emission_record = relationship("EmissionRecord", back_populates="ai_estimate", uselist=False)


# ── Emission Record ───────────────────────────────────────────────────────────

class EmissionRecord(Base):
    __tablename__ = "emission_records"

    id             = Column(Integer, primary_key=True, index=True)
    vendor_id      = Column(Integer, ForeignKey("vendor_profiles.id"), nullable=False)
    submitted_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    category_id    = Column(Integer, nullable=False)
    period_start   = Column(Date, nullable=False)
    period_end     = Column(Date, nullable=False)
    activity_value = Column(Float, nullable=False)
    activity_unit  = Column(String(100), nullable=False)
    ef_id          = Column(Integer, ForeignKey("emission_factors.id"), nullable=False)
    calculated_co2e = Column(Float)
    data_quality   = Column(Enum(DataQuality), default=DataQuality.B)
    input_method   = Column(Enum(InputMethod), default=InputMethod.manual)
    region         = Column(Enum(Region))
    status         = Column(Enum(RecordStatus), default=RecordStatus.draft)
    notes          = Column(Text)
    rejection_reason = Column(Text)          # shown to vendor when rejected

    is_ai_estimated = Column(Boolean, default=False)
    ai_estimate_id  = Column(Integer, ForeignKey("ai_estimates.id"), nullable=True)

    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at  = Column(DateTime(timezone=True))

    vendor           = relationship("VendorProfile", back_populates="emission_records")
    submitted_by_user = relationship("User", back_populates="emission_records",
                                     foreign_keys=[submitted_by])
    approved_by_user  = relationship("User", foreign_keys=[approved_by])
    emission_factor   = relationship("EmissionFactor", back_populates="emission_records")
    ai_estimate       = relationship("AIEstimate", back_populates="emission_record",
                                     foreign_keys=[ai_estimate_id])


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    action     = Column(String(100), nullable=False)
    table_name = Column(String(100))
    record_id  = Column(Integer)
    old_value  = Column(JSON)
    new_value  = Column(JSON)
    description = Column(Text)
    ip_address = Column(String(50))
    timestamp  = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")


# ── Reporting Period ──────────────────────────────────────────────────────────

class ReportingPeriod(Base):
    __tablename__ = "reporting_periods"

    id           = Column(Integer, primary_key=True, index=True)
    label        = Column(String(100), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end   = Column(Date, nullable=False)
    is_locked    = Column(Boolean, default=False)
    locked_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    locked_at    = Column(DateTime(timezone=True))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


# ── Emission Target (suggestion #6) ──────────────────────────────────────────

class EmissionTarget(Base):
    __tablename__ = "emission_targets"

    id           = Column(Integer, primary_key=True, index=True)
    label        = Column(String(100))          # e.g. "FY2025 Target"
    target_co2e  = Column(Float, nullable=False) # tCO2e
    year         = Column(Integer, nullable=False)
    region       = Column(Enum(Region), nullable=True)  # null = all regions
    created_by   = Column(Integer, ForeignKey("users.id"))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
