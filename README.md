# StratXG — Scope 3 Emissions Intelligence Platform
**Phase 1 · GHG Protocol · GRI 305 · DEFRA · IPCC**

---

## Quick Start (2 commands)

```bash
git clone <your-repo>
cd scope3-platform
docker-compose up --build
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@stratxg.com | Admin@1234 |
| Manager (North) | manager.north@stratxg.com | Manager@1234 |
| Vendor | vendor@acmesupplies.com | Vendor@1234 |
| Auditor | auditor@stratxg.com | Auditor@1234 |

---

## Project Structure

```
scope3-platform/
├── docker-compose.yml          # One-command deploy
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py       # Settings + Phase 2 flags
│   │   │   └── security.py     # JWT + RBAC
│   │   ├── db/
│   │   │   ├── database.py     # SQLAlchemy engine
│   │   │   └── seed.py         # Initial data + 30+ EFs
│   │   ├── models/user.py      # All DB models (incl. Phase 2 AIEstimate)
│   │   ├── schemas/schemas.py  # Pydantic request/response schemas
│   │   ├── api/routes/
│   │   │   ├── auth.py         # Login, change-password, /me
│   │   │   ├── users.py        # User CRUD, vendor invite, onboarding
│   │   │   ├── emissions.py    # Records CRUD, CSV upload, trace
│   │   │   ├── dashboard.py    # Analytics, trends, breakdowns
│   │   │   ├── reports.py      # Excel export, CSV template
│   │   │   └── misc.py         # EF library, audit log, periods
│   │   └── services/
│   │       ├── calculation_engine.py  # Core CO2e formula + Phase 2 hook
│   │       ├── audit_service.py       # Append-only audit log writer
│   │       ├── email_service.py       # Vendor invitation emails
│   │       └── report_service.py      # Excel/CSV generation
└── frontend/
    └── src/
        ├── App.tsx             # Router + protected routes
        ├── store/authStore.ts  # Zustand auth state
        ├── utils/
        │   ├── api.ts          # Typed API client
        │   └── constants.ts    # Categories, regions, helpers
        ├── components/
        │   ├── ui/             # Shared components (KpiCard, Modal, etc.)
        │   ├── charts/         # Recharts wrappers (Trend, Category, Region)
        │   └── layout/         # AppLayout sidebar
        └── pages/
            ├── auth/           # Login, ChangePassword, Onboarding
            ├── DashboardPage   # Role-aware KPIs + charts
            ├── EmissionsPage   # Records table + calculation trace modal
            ├── ReportsPage     # GRI-305 Excel download
            ├── AuditPage       # Audit log (admin/auditor)
            ├── vendor/         # SubmitDataPage (manual + CSV)
            ├── manager/        # VendorsPage (list + invite)
            └── admin/          # UsersPage, EFLibraryPage, SettingsPage
```

---

## Architecture

```
React Frontend (Port 3000)
        ↓ JWT Bearer tokens
FastAPI Backend (Port 8000)
        ↓ SQLAlchemy ORM
PostgreSQL (Port 5432)
```

**Role-based access:**
- **Admin** — All regions, all data, user management, EF library, period locking
- **Manager** — Own region vendors and emissions, can invite/manage vendors
- **Vendor** — Own emissions only, data submission, onboarding wizard
- **Auditor** — Read-only: all records, calculation traces, audit log

---

## Phase 2 Extension Points

The codebase is structured so Phase 2 features drop in without restructuring:

### 1. Enable AI Estimation
```bash
# In docker-compose.yml environment:
AI_ESTIMATION_ENABLED=true
```
Then implement `app/services/ai_estimation.py`. The hook is already called in:
`calculation_engine.py → estimate_missing_data()`

The `ai_estimates` table is already in the database schema.

### 2. Add new dashboard endpoints
Add to `app/api/routes/dashboard.py`:
- `GET /dashboard/forecast` — predictive emissions
- `GET /dashboard/benchmark` — industry comparison  
- `GET /dashboard/carbon-price` — carbon pricing simulation

### 3. Add PDF report generation
Install `reportlab`, implement in `report_service.py`, add route in `reports.py`.

### 4. Add supplier portal (external vendor submission)
The vendor invitation + onboarding flow is already built.
For an external portal, create a separate React app that hits the same API with vendor-scoped JWT tokens.

---

## Calculation Methodology

All emissions use the GHG Protocol formula:

```
CO₂e (tCO₂e) = Activity Data × Emission Factor (kgCO₂e/unit) ÷ 1000
```

**Emission factor sources seeded:**
- DEFRA 2024 (transport, waste, fuels, business travel)
- IPCC AR6 (capital goods, products, investments)
- CPCB 2023 (India grid electricity)

Every calculation is fully traceable — open the "Calculation Trace" on any record to see the exact formula, EF source, version, and step-by-step breakdown.

---

## Standards Compliance

| Standard | Coverage |
|----------|----------|
| GHG Protocol Corporate Value Chain | All 15 Scope 3 categories |
| GRI 305 | Disclosure-ready Excel export |
| DEFRA 2024 | Transport, waste, fuel EFs |
| IPCC AR6 | Default global EFs |
| CPCB 2023 | India grid electricity |
| PCAF | Investment emissions (Category 14) |

---

## Development (without Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://scope3:scope3pass@localhost:5432/scope3db uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```
