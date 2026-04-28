from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    admin   = "admin"
    manager = "manager"
    vendor  = "vendor"
    auditor = "auditor"


class Region(str, Enum):
    north   = "north"
    south   = "south"
    east    = "east"
    west    = "west"
    central = "central"
    all     = "all"


class DataQuality(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class RecordStatus(str, Enum):
    draft     = "draft"
    submitted = "submitted"
    approved  = "approved"
    rejected  = "rejected"


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    phone: Optional[str] = None
    designation: Optional[str] = None
    role: UserRole
    region: Optional[Region]
    is_active: bool
    onboarding_complete: bool
    must_change_password: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    region: Optional[Region] = None
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    region: Optional[Region] = None
    role: Optional[UserRole] = None      # admin can change role
    is_active: Optional[bool] = None


# ── Vendor Invitation ─────────────────────────────────────────────────────────

class InviteVendorRequest(BaseModel):
    email: EmailStr
    region: Region


class InvitationOut(BaseModel):
    id: int
    email: str
    region: Region
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Vendor Profile ────────────────────────────────────────────────────────────

class VendorProfileOut(BaseModel):
    id: int
    user_id: int
    company_name: Optional[str]
    trade_name: Optional[str]
    gst_number: Optional[str]
    pan_number: Optional[str]
    cin_number: Optional[str]
    year_established: Optional[int]
    state: Optional[str]
    city: Optional[str]
    pin_code: Optional[str]
    address: Optional[str]
    region: Optional[Region]
    nic_code: Optional[str]
    material_category: Optional[int]
    material_name: Optional[str]
    supply_frequency: Optional[str]
    avg_annual_volume: Optional[float]
    volume_unit: Optional[str]
    has_own_carbon_system: Optional[bool]
    contact_name: Optional[str]
    contact_designation: Optional[str]
    contact_phone: Optional[str]
    onboarded_at: Optional[datetime]

    class Config:
        from_attributes = True


class VendorDetailOut(BaseModel):
    """Full vendor detail — user + profile combined."""
    id: int
    email: str
    full_name: Optional[str]
    region: Optional[str]
    is_active: bool
    onboarding_complete: bool
    created_at: datetime
    profile: Optional[VendorProfileOut]

    class Config:
        from_attributes = True


# ── Emission Factor ───────────────────────────────────────────────────────────

class EmissionFactorOut(BaseModel):
    id: int
    source: str
    category_id: int
    subcategory: Optional[str]
    material_type: Optional[str]
    factor_value: float
    unit: str
    region: Optional[str]
    version_tag: str
    valid_from: Optional[date]
    source_url: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class EmissionFactorCreate(BaseModel):
    source: str
    category_id: int = Field(ge=1, le=15)
    subcategory: Optional[str] = None
    material_type: Optional[str] = None
    factor_value: float
    unit: str
    region: str = "global"
    version_tag: str
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    source_url: Optional[str] = None
    notes: Optional[str] = None


# ── Emission Record ───────────────────────────────────────────────────────────

class EmissionRecordCreate(BaseModel):
    category_id: int = Field(ge=1, le=15)
    period_start: date
    period_end: date
    activity_value: float
    activity_unit: str
    ef_id: int
    data_quality: DataQuality = DataQuality.B
    input_method: str = "manual"
    notes: Optional[str] = None


class EmissionRecordOut(BaseModel):
    id: int
    vendor_id: int
    vendor_company_name: Optional[str] = None   # populated in route
    category_id: int
    period_start: date
    period_end: date
    activity_value: float
    activity_unit: str
    calculated_co2e: Optional[float]
    data_quality: DataQuality
    input_method: str
    region: Optional[Region]
    status: RecordStatus
    notes: Optional[str]
    rejection_reason: Optional[str] = None
    is_ai_estimated: bool
    submitted_at: datetime
    emission_factor: Optional[EmissionFactorOut]

    class Config:
        from_attributes = True


class EmissionRecordWithTrace(EmissionRecordOut):
    calculation_trace: Optional[dict] = None
    vendor: Optional[VendorProfileOut] = None


class RecordStatusUpdate(BaseModel):
    status: RecordStatus
    notes: Optional[str] = None


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    table_name: Optional[str]
    record_id: Optional[int]
    description: Optional[str]
    old_value: Optional[dict]
    new_value: Optional[dict]
    ip_address: Optional[str]
    timestamp: datetime
    user: Optional[UserOut]

    class Config:
        from_attributes = True


# ── Reporting Period ──────────────────────────────────────────────────────────

class ReportingPeriodCreate(BaseModel):
    label: str
    period_start: date
    period_end: date


class ReportingPeriodOut(BaseModel):
    id: int
    label: str
    period_start: date
    period_end: date
    is_locked: bool
    locked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
