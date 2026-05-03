from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


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

class RejectionReasonCode(str, Enum):
    wrong_unit       = "wrong_unit"
    inflated_value   = "inflated_value"
    wrong_ef_applied = "wrong_ef_applied"
    missing_docs     = "missing_docs"
    data_quality_low = "data_quality_low"
    duplicate_entry  = "duplicate_entry"
    period_mismatch  = "period_mismatch"
    other            = "other"

REJECTION_CODE_LABELS: Dict[str, str] = {
    "wrong_unit":       "Incorrect unit (e.g. kg instead of tonnes)",
    "inflated_value":   "Activity value appears inflated or implausible",
    "wrong_ef_applied": "Wrong emission factor selected for this activity",
    "missing_docs":     "Supporting documentation required",
    "data_quality_low": "Data quality grade too low — primary data required",
    "duplicate_entry":  "Duplicate record for this period",
    "period_mismatch":  "Period dates do not match supporting data",
    "other":            "Other (see notes)",
}


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
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


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


class EmissionRecordCreate(BaseModel):
    category_id: int = Field(ge=1, le=15)
    period_start: date
    period_end: date
    activity_value: float
    activity_unit: str
    ef_id: int
    data_quality: DataQuality = DataQuality.B
    input_method: str = "manual"
    input_mode: str = "direct"
    parametric_inputs: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    parent_record_id: Optional[int] = None

class ParametricCalculateRequest(BaseModel):
    category_id: int = Field(ge=1, le=15)
    params: Dict[str, Any]

class ParametricCalculateResponse(BaseModel):
    activity_value: float
    activity_unit: str
    formula_used: str
    steps: List[str]

class AnomalyCheckOut(BaseModel):
    anomaly_score: float
    raw_score: Optional[float] = None
    threshold: Optional[float] = None
    is_flagged: bool
    confidence: str
    explanation: str
    model_used: str

class EmissionRecordOut(BaseModel):
    id: int
    vendor_id: int
    vendor_company_name: Optional[str] = None
    category_id: int
    period_start: date
    period_end: date
    activity_value: float
    activity_unit: str
    calculated_co2e: Optional[float]
    data_quality: DataQuality
    input_method: str
    input_mode: Optional[str] = "direct"
    region: Optional[Region]
    status: RecordStatus
    notes: Optional[str]
    rejection_reason: Optional[str] = None
    rejection_reason_code: Optional[RejectionReasonCode] = None
    parent_record_id: Optional[int] = None
    is_ai_estimated: bool
    anomaly_check: Optional[AnomalyCheckOut] = None
    submitted_at: datetime
    emission_factor: Optional[EmissionFactorOut]
    class Config:
        from_attributes = True

class EmissionRecordWithTrace(EmissionRecordOut):
    calculation_trace: Optional[dict] = None
    vendor: Optional[VendorProfileOut] = None

class RecordStatusUpdate(BaseModel):
    status: RecordStatus
    rejection_reason_code: Optional[RejectionReasonCode] = None
    notes: Optional[str] = None

    @validator("notes")
    def notes_required_for_rejection(cls, v, values):
        if values.get("status") == RecordStatus.rejected and not (v and v.strip()):
            raise ValueError("A rejection reason note is required when rejecting a record")
        return v

class BulkStatusUpdate(BaseModel):
    record_ids: List[int] = Field(min_length=1)
    status: RecordStatus
    rejection_reason_code: Optional[RejectionReasonCode] = None
    notes: Optional[str] = None

    @validator("notes")
    def notes_required_for_rejection(cls, v, values):
        if values.get("status") == RecordStatus.rejected and not (v and v.strip()):
            raise ValueError("A rejection note is required for bulk rejection")
        return v


class MissingDataEstimateRequest(BaseModel):
    category_id: int = Field(ge=1, le=15)
    spend_inr: float = Field(gt=0)
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    nic_4digit: Optional[int] = Field(default=None, gt=0)
    region: Optional[Region] = None

class MissingDataEstimateResponse(BaseModel):
    estimated_value: float
    estimated_co2e: float
    confidence_score: float
    confidence_band: List[float]
    explanation: str
    model_used: str
    data_quality: str
    inputs_used: dict
    methodology_reference: str


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
