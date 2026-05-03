# StratXG — Scope 3 Emissions Intelligence Platform
**Phase 1 + Phase 2 Active · GHG Protocol · GRI 305 · DEFRA 2024 · IPCC AR6 · PCAF**

---

## Quick Start (2 commands)

```bash
git clone <your-repo>
cd scope3-platform-v5_college
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ML Service | http://localhost:8001 |

> **First run only:** The database auto-seeds on startup (`FORCE_RESEED=true` in docker-compose).
> After seeding completes (look for `✅ All seeds complete` in backend logs), set `FORCE_RESEED: "false"` to protect live data.

---

## Demo Credentials

| Role | Email | Password | Region |
|------|-------|----------|--------|
| **Admin** | admin@stratxg.com | Admin@1234 | All |
| **Manager (North)** | manager.north@stratxg.com | Manager@1234 | North |
| **Manager (South)** | manager.south@stratxg.com | Manager@1234 | South |
| **Auditor** | auditor@stratxg.com | Auditor@1234 | — |
| **Vendor — Acme Supplies** (Cat 1 Steel) | vendor@acmesupplies.com | Vendor@1234 | North |
| **Vendor — GreenTrans Logistics** (Cat 4 Transport) | vendor@greentrans.com | Vendor@1234 | South |
| **Vendor — WasteCare Solutions** (Cat 5 Waste) | vendor@wastecare.com | Vendor@1234 | North |
| **Vendor — EnergyTech Industries** (Cat 3 Fuel) | vendor@energytech.com | Vendor@1234 | West |
| **Vendor — BuildCorp Limited** (Cat 2 Capital) | vendor@buildcorp.com | Vendor@1234 | East |
| **Vendor — TravelPro Services** (Cat 6 Travel) | vendor@travelpro.com | Vendor@1234 | Central |
| **Vendor — Commuteplus Solutions** (Cat 7 Commute) | vendor@commuteplus.com | Vendor@1234 | West |

---

## Demo Flow (for judges)

1. **Admin** → Dashboard: 36-month emission trend, LSTM 3-month forecast, regional heatmap, YoY comparison
2. **Admin** → Settings: Phase 2 AI features panel (active models, disclaimers, roadmap)
3. **Vendor (Acme)** → Submit Data: parametric entry for Cat 1, unit mismatch warning, data quality explainer
4. **Vendor (GreenTrans)** → Submit Data: parametric Cat 4 (distance × weight → tonne-km), AI spend estimate
5. **Manager (North)** → Emission Records: bulk approve/reject with reason codes, anomaly flags
6. **Vendor (Acme)** → My History: rejected record with reason, "Revise & Resubmit" flow
7. **Admin** → Reports: GRI-305 Excel export
8. **Auditor** → Audit Log → Export CSV

---

## Architecture

```
React Frontend (Port 3000)
        │ JWT Bearer tokens
        ▼
FastAPI Backend (Port 8000)
        │ SQLAlchemy ORM
        ▼
PostgreSQL (Port 5432)
        
FastAPI ML Service (Port 8001) ← called by backend for anomaly, forecast, spend estimation
```

### Role-Based Access

| Role | Capabilities |
|------|-------------|
| **Admin** | All regions · All data · User management · EF library · Period locking · Settings |
| **Manager** | Own region vendors · Approve/reject records · Bulk actions · Vendor engagement |
| **Vendor** | Own emissions · Submit (manual/parametric/CSV) · Draft save · Revise rejected · AI estimate |
| **Auditor** | Read-only: all records · Calculation traces · Audit log · Export |

---

## Project Structure

```
scope3-platform-v5_college/
├── docker-compose.yml              # One-command deploy (all 3 services)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app, router registration, startup seed
│       ├── core/
│       │   ├── config.py           # Settings: DB, JWT, AI flags, FORCE_RESEED
│       │   └── security.py         # JWT auth, RBAC decorators
│       ├── db/
│       │   ├── database.py         # SQLAlchemy engine + session
│       │   └── seed.py             # Full demo data: 11 users, 32 EFs, 3 periods,
│       │                           #   ~300 emission records (36 months), 6 targets
│       ├── models/
│       │   ├── user.py             # All core models: User, VendorProfile, EmissionRecord,
│       │   │                       #   EmissionFactor, ReportingPeriod, EmissionTarget,
│       │   │                       #   AIEstimate, AuditLog, Notification, VendorInvitation
│       │   ├── attachment.py       # RecordAttachment (file uploads per record)
│       │   └── notification.py     # Notification model + NotificationType enum
│       ├── schemas/
│       │   └── schemas.py          # All Pydantic schemas incl. RejectionReasonCode,
│       │                           #   BulkStatusUpdate, ParametricCalculateRequest
│       ├── api/routes/
│       │   ├── auth.py             # POST /auth/login, GET /auth/me, change-password
│       │   ├── users.py            # User CRUD, vendor invite, onboarding wizard
│       │   ├── emissions.py        # Records CRUD, parametric calc, draft/submit,
│       │   │                       #   bulk-status, CSV upload, AI estimate, audit trace
│       │   ├── dashboard.py        # Summary, category/region breakdown, trend, forecast
│       │   ├── reports.py          # GRI-305 Excel, CSV template download
│       │   ├── misc.py             # EF library CRUD, audit log, reporting periods
│       │   ├── attachments.py      # File upload/list/delete per emission record
│       │   ├── vendor_tools.py     # Vendor history, intensity, CSV export, BRSR
│       │   ├── notifications.py    # Notification bell, mark-read
│       │   ├── profile.py          # Profile get/update, change password/email
│       │   └── targets.py          # Emission targets CRUD
│       ├── services/
│       │   ├── calculation_engine.py  # CO2e formula, unit normalisation, unit mismatch
│       │   │                          #   check, parametric calculators (Cat 1/3/4/5/6/7/8)
│       │   ├── ai_estimation.py       # ML spend model + DEFRA rule-based fallback
│       │   │                          #   for all 15 categories
│       │   ├── ml_client.py           # HTTP client for ML service (anomaly, spend, forecast)
│       │   ├── audit_service.py       # Append-only audit log writer
│       │   ├── email_service.py       # Vendor invitation + status notification emails
│       │   ├── notification_service.py # In-app notification writer
│       │   └── report_service.py      # GRI-305 Excel generation
│       └── utils/
│           └── helpers.py             # Region enum helpers
│
├── ml-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── service_app.py              # FastAPI ML service (port 8001)
│   ├── serving/
│   │   └── inference.py            # Model loading + prediction logic
│   │                               #   (anomaly, spend, forecast with TFT→LSTM fallback)
│   ├── train/
│   │   ├── train_anomaly.py        # Autoencoder / VAE / IsolationForest
│   │   ├── train_forecasting.py    # SARIMA / LSTM / TFT
│   │   └── train_spend.py          # XGBoost / MLP+Embeddings / TabNet
│   ├── models/                     # Model class definitions
│   ├── data/                       # Data generation / fetch scripts
│   ├── preprocessing/              # Feature engineering pipelines
│   └── saved_models/               # Trained .pkl / .pt / .json files
│       ├── anomaly/best_model.json
│       ├── forecasting/best_model.json
│       └── spend/best_model.json
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.tsx                 # Router, protected routes, role guards
        ├── store/authStore.ts      # Zustand auth state
        ├── utils/
        │   ├── api.ts              # Typed Axios client: authApi, emissionsApi, efApi,
        │   │                       #   dashboardApi, attachmentsApi, emissionFactorsApi, etc.
        │   ├── constants.ts        # SCOPE3_CATEGORIES, CHART_COLORS, formatCO2e, formatDate
        │   └── indiaGeo.ts         # States/cities/pincode lookup for onboarding
        ├── components/
        │   ├── ui/                 # KpiCard, Modal, Select, StatusBadge, QualityBadge,
        │   │                       #   PageLoader, SectionHeader, EmptyState, Spinner
        │   ├── charts/             # Recharts wrappers
        │   └── layout/
        │       ├── AppLayout.tsx   # Sidebar nav (role-filtered), top bar, notification bell
        │       └── NotificationBell.tsx
        └── pages/
            ├── auth/
            │   ├── LoginPage.tsx
            │   └── ChangePasswordPage.tsx
            ├── DashboardPage.tsx   # KPIs, category/region charts, trend, LSTM forecast panel
            ├── EmissionsPage.tsx   # Records table, bulk approve/reject, calculation trace modal
            ├── ReportsPage.tsx     # GRI-305 Excel download, CSV template
            ├── AuditPage.tsx       # Audit log table + CSV export
            ├── vendor/
            │   ├── OnboardingPage.tsx      # 4-step wizard: company, location, ops, contact
            │   ├── SubmitDataPage.tsx      # Direct/parametric entry, unit warning, quality
            │   │                           #   explainer, AI estimate, draft save, attachments
            │   ├── SubmissionHistory.tsx   # Tabs: all/submitted/approved/rejected/draft
            │   │                           #   Rejection reason display + Revise & Resubmit
            │   └── ActivityCalculator.tsx  # Step-by-step guide for each Scope 3 category
            ├── manager/
            │   └── VendorsPage.tsx         # Vendor list, invite, engagement scores
            └── admin/
                ├── UsersPage.tsx           # User management
                ├── EFLibraryPage.tsx       # Emission factor CRUD
                └── SettingsPage.tsx        # Platform config, Phase 2 status panel
```

---

## Key Features

### Data Submission (Vendor)
- **Direct entry** — enter calculated activity value directly
- **Parametric entry** — enter raw measurements; system calculates activity value
  - Cat 1: quantity (kg/tonne) → tonnes
  - Cat 4 & 8: distance (km) × weight (tonnes) → tonne-km
  - Cat 5: landfill + incineration + recycling → total tonnes
  - Cat 6: trips × distance × passengers → passenger-km
  - Cat 7: employees × distance × days × (1−WFH%) × 2 → vehicle-km
  - Cat 3: fuel volume → litres
- **Unit mismatch warning** — real-time check: EF denominator vs activity unit
- **Data quality explainer** — A/B/C grade explained with examples per selection
- **AI spend estimate** — all 15 categories (ML model for Cat 1/2/13–15; DEFRA rule-based fallback for rest)
- **Draft auto-save** — save without submitting; submit later from My History
- **Attachment upload** — attach PDFs, invoices, Excel, images to any record
- **Revise & resubmit** — rejected records pre-fill the form; new record links to original

### Approval Workflow (Manager)
- **Single approve/reject** with required reason code + notes
- **Bulk approve/reject** — checkbox-select multiple submitted records
- **Rejection reason codes** — 8 categories (wrong_unit, inflated_value, wrong_ef_applied, etc.)
- **Re-review notification** — original rejector notified when vendor resubmits

### Dashboard (Admin/Manager)
- KPI tiles: total CO₂e, YoY change, pending records, data quality distribution
- Category breakdown (bar chart + table)
- Regional breakdown (pie chart, admin/auditor only)
- Monthly/quarterly/yearly trend chart with target reference line
- **AI forecast panel** — LSTM 3-month forecast with 90% prediction intervals, sector selector

### Calculation Engine
- Formula: `CO₂e (tCO₂e) = Activity Data × EF (kgCO₂e/unit) ÷ 1000`
- 30+ seeded DEFRA/IPCC/CPCB/PCAF emission factors across all 15 categories
- Unit normalisation: g→tonne, kWh→MWh, ml→litre, etc.
- Unit compatibility check: warns when activity unit doesn't match EF denominator
- Full calculation trace on every record (EF source, version, step-by-step)

### AI / ML Features (Phase 2, Active)
| Model | Task | Status |
|-------|------|--------|
| XGBoost | Spend-based emission estimation (Cat 1/2/13–15) | ✅ Active |
| DEFRA Rule-based | Spend estimation fallback (all 15 categories) | ✅ Active |
| Autoencoder | Anomaly detection on submission | ✅ Active |
| LSTM | 3-month emission forecast | ✅ Active (requires ≥12 months data) |
| SARIMA | Forecast fallback | ✅ Active |
| TFT | Forecast candidate | ⚠️ Fallback to LSTM (shape mismatch in training) |

### Reporting & Audit
- GRI-305 Scope 3 Excel export
- CSV upload template (with dropdown validation)
- Append-only audit log (every create/update/approve/reject)
- Audit log CSV export
- Calculation trace: EF source URL, version, step-by-step, anomaly flag, parametric inputs

---

## Calculation Methodology

All emissions follow GHG Protocol:
```
CO₂e (tCO₂e) = Activity Data × Emission Factor (kgCO₂e/unit) ÷ 1000
```

**EF sources seeded:**
| Source | Coverage |
|--------|----------|
| DEFRA 2024 | Transport, waste, fuels, travel, freight |
| IPCC AR6 | Capital goods, products, processing, investments |
| CPCB 2023 | India national grid electricity |
| PCAF 2023 | Investment portfolio emissions (Cat 14) |

**AI Estimation (Phase 2):**
```
Estimated CO₂e = (Spend ÷ 1000) × Sector EF (kgCO₂e/1000 INR) × Year Adjustment ÷ 1000
```
- ML model: DEFRA/EEIO hybrid XGBoost with NIC sector + region features
- Rule-based: DEFRA spend intensity per category with ±1.5%/yr decay
- Confidence always capped at 0.75 (C-grade) per GHG Protocol Tier 3

---

## Standards Compliance

| Standard | Coverage |
|----------|----------|
| GHG Protocol Corporate Value Chain | All 15 Scope 3 categories |
| GRI 305-3 | Disclosure-ready Excel export |
| DEFRA 2024 | Transport, waste, fuel, travel EFs |
| IPCC AR6 | Global default EFs |
| CPCB 2023 | India grid electricity |
| PCAF 2023 | Investment emissions (Cat 14) |

---

## Configuration

All configuration is via `docker-compose.yml` environment variables:

```yaml
backend:
  environment:
    DATABASE_URL: postgresql://scope3:scope3pass@db:5432/scope3db
    SECRET_KEY: change-this-in-production
    AI_ESTIMATION_ENABLED: "true"      # enables /estimate-missing endpoint
    ML_SERVICE_URL: http://ml-service:8001
    FORCE_RESEED: "true"               # wipe + re-seed on startup; set false after first run
```

---

## Development Without Docker

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://scope3:scope3pass@localhost:5432/scope3db \
AI_ESTIMATION_ENABLED=true \
ML_SERVICE_URL=http://localhost:8001 \
uvicorn app.main:app --reload

# ML Service
cd ml-service
pip install -r requirements.txt
uvicorn service_app:app --port 8001 --reload

# Frontend
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

---

## Re-seeding Demo Data

```bash
# Full wipe + reseed (destroys all data)
FORCE_RESEED=true docker-compose up --build

# Or set in docker-compose.yml:
#   FORCE_RESEED: "true"
# then: docker-compose down -v && docker-compose up --build
```

After seeding, set `FORCE_RESEED: "false"` to prevent accidental data loss.

---

## ML Model Notes

| Model | Metric | Note |
|-------|--------|------|
| Spend XGBoost | R²=0.99 | Trained on synthetic data — expect ±40-60% on real procurement |
| Anomaly Autoencoder | PR-AUC=0.70 | Precision@FPR10%=36%; use as advisory, not hard gate |
| Forecast LSTM | MAPE=11.5% | Uses macro India sector data as proxy; PI coverage ~63% (nominal 90%) |
| Forecast TFT | — | Falls back to LSTM (shape mismatch in training pipeline) |
