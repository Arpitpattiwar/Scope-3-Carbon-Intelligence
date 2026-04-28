from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Page margins ─────────────────────────────────────────────────────────────
section = doc.sections[0]
section.page_width  = Inches(8.5)
section.page_height = Inches(11)
section.left_margin = section.right_margin = Inches(1)
section.top_margin  = section.bottom_margin = Inches(1)

# ── Colour palette ────────────────────────────────────────────────────────────
GREEN  = RGBColor(0x0F, 0x86, 0x60)
DARK   = RGBColor(0x11, 0x18, 0x27)
GREY   = RGBColor(0x6B, 0x72, 0x80)
LGREY  = RGBColor(0xF3, 0xF4, 0xF6)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
RED    = RGBColor(0xDC, 0x26, 0x26)
AMBER  = RGBColor(0xD9, 0x77, 0x06)

# ── Style helpers ─────────────────────────────────────────────────────────────
def shade_cell(cell, hex_color):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def cell_border(cell, sides=('top','bottom','left','right'), sz=4, color='D1D5DB'):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for s in sides:
        b = OxmlElement(f'w:{s}')
        b.set(qn('w:val'), 'single')
        b.set(qn('w:sz'), str(sz))
        b.set(qn('w:space'), '0')
        b.set(qn('w:color'), color)
        tcBorders.append(b)
    tcPr.append(tcBorders)

def add_heading(text, level=1):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    if level == 1:
        run.font.size  = Pt(18)
        run.font.color.rgb = GREEN
        run.bold = True
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after  = Pt(6)
        # underline rule
        pPr = p._p.get_or_add_pPr()
        pBdr= OxmlElement('w:pBdr')
        bot = OxmlElement('w:bottom')
        bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'8')
        bot.set(qn('w:space'),'4');    bot.set(qn('w:color'),'0F8660')
        pBdr.append(bot); pPr.append(pBdr)
    elif level == 2:
        run.font.size  = Pt(13)
        run.font.color.rgb = DARK
        run.bold = True
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after  = Pt(4)
    elif level == 3:
        run.font.size  = Pt(11)
        run.font.color.rgb = GREEN
        run.bold = True
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after  = Pt(2)
    return p

def add_body(text, bold=False, indent=False):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.bold = bold
    run.font.color.rgb = DARK
    if indent:
        p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(3)
    return p

def add_bullet(text, indent_level=0):
    p   = doc.add_paragraph(style='List Bullet')
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.font.color.rgb = DARK
    p.paragraph_format.left_indent  = Inches(0.25 + indent_level * 0.2)
    p.paragraph_format.space_after  = Pt(2)
    return p

def add_code(text):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Courier New'
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    p.paragraph_format.left_indent  = Inches(0.25)
    p.paragraph_format.space_after  = Pt(1)
    # light grey shading on the paragraph
    pPr  = p._p.get_or_add_pPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),'clear'); shd.set(qn('w:color'),'auto')
    shd.set(qn('w:fill'),'F3F4F6')
    pPr.append(shd)
    return p

def add_table(headers, rows, col_widths=None):
    n_cols = len(headers)
    tbl = doc.add_table(rows=1+len(rows), cols=n_cols)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    # header row
    hdr = tbl.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        shade_cell(cell, '0F8660')
        cell_border(cell, color='0F8660')
        run = cell.paragraphs[0].add_run(h)
        run.font.color.rgb = WHITE
        run.font.size = Pt(9)
        run.bold = True
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    # data rows
    for r_idx, row in enumerate(rows):
        bg = 'FFFFFF' if r_idx % 2 == 0 else 'F9FAFB'
        for c_idx, val in enumerate(row):
            cell = tbl.rows[r_idx+1].cells[c_idx]
            shade_cell(cell, bg)
            cell_border(cell, color='E5E7EB')
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(9)
            run.font.color.rgb = DARK
    if col_widths:
        for r in tbl.rows:
            for i, w in enumerate(col_widths):
                r.cells[i].width = Inches(w)
    doc.add_paragraph()
    return tbl

def page_break():
    doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
title_p = doc.add_paragraph()
title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title_p.add_run('\n\n')
r.font.size = Pt(12)

tp = doc.add_paragraph()
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = tp.add_run('StratXG')
run.font.size  = Pt(36)
run.font.color.rgb = GREEN
run.bold = True

tp2 = doc.add_paragraph()
tp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = tp2.add_run('Scope 3 Emissions Intelligence Platform v5')
run2.font.size = Pt(18)
run2.font.color.rgb = DARK
run2.bold = True

doc.add_paragraph()
line = doc.add_paragraph()
line.alignment = WD_ALIGN_PARAGRAPH.CENTER
lr = line.add_run('─' * 50)
lr.font.color.rgb = GREEN

doc.add_paragraph()
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sub.add_run('Complete Technical & Functional Documentation')
sr.font.size = Pt(13)
sr.font.color.rgb = GREY

doc.add_paragraph()
ver = doc.add_paragraph()
ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
vr = ver.add_run('Version 1.2.0  |  31 March 2026')
vr.font.size = Pt(10)
vr.font.color.rgb = GREY

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. SYSTEM OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('1. System Overview', 1)
add_body(
    'StratXG Scope 3 Emissions Intelligence Platform is a full-stack multi-tenant SaaS '
    'application for collecting, calculating, reviewing, and reporting Scope 3 GHG (Greenhouse '
    'Gas) emissions from a company\'s vendor/supplier ecosystem. '
    'It is aligned with the GHG Protocol (all 15 Scope 3 categories) and GRI 305 standards.'
)

add_heading('What the Platform Does', 2)
add_bullet('Managers/Admins invite vendors to the platform, assign them to a region, and review/approve submitted emission records.')
add_bullet('Vendors complete a structured onboarding profile, then periodically submit emission activity data (e.g., steel tonnes, kWh used, km travelled).')
add_bullet('The Calculation Engine automatically converts activity data to CO₂e (tonnes of CO₂ equivalent) using published Emission Factors (DEFRA, IPCC, CPCB).')
add_bullet('Dashboards visualise total emissions, category breakdowns, year-over-year trends, regional distribution, and vendor engagement scores.')
add_bullet('Reports can be exported as Excel or CSV. Every action is logged in an immutable Audit Log.')

add_heading('Technology Stack', 2)
add_table(
    ['Layer', 'Technology'],
    [
        ['Backend Framework', 'FastAPI (Python 3.11)'],
        ['ORM', 'SQLAlchemy'],
        ['Database', 'PostgreSQL 15'],
        ['Authentication', 'JWT (python-jose) + bcrypt (passlib)'],
        ['CSV Processing', 'pandas'],
        ['Excel Export', 'openpyxl'],
        ['Frontend Framework', 'React 18 + TypeScript (Vite)'],
        ['State Management', 'Zustand'],
        ['Form Handling', 'react-hook-form'],
        ['HTTP Client', 'Axios'],
        ['Styling', 'Vanilla CSS + custom design system'],
        ['Containerisation', 'Docker + Docker Compose'],
    ],
    col_widths=[2.5, 4.0]
)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 2. ARCHITECTURE & DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('2. Architecture & Deployment', 1)
add_body(
    'The entire platform runs via docker-compose up --build with three services. '
    'All services communicate on a shared Docker network. The frontend container reaches '
    'the backend via the host machine (VITE_API_URL=http://localhost:8000).'
)

add_heading('Docker Services', 2)

add_heading('db — PostgreSQL 15', 3)
add_bullet('Image: postgres:15-alpine')
add_bullet('Database: scope3db  |  User: scope3  |  Password: scope3pass')
add_bullet('Port: 5432:5432  |  Data persisted in named volume postgres_data')
add_bullet('Health-checked (pg_isready) before the backend container starts.')

add_heading('backend — FastAPI', 3)
add_bullet('Port: 8000:8000, live-reload via uvicorn --reload')
add_bullet('Volume-mounts ./backend:/app for hot-reload during development')
add_table(
    ['Environment Variable', 'Purpose'],
    [
        ['DATABASE_URL', 'PostgreSQL connection string'],
        ['SECRET_KEY', 'JWT signing key (change in production)'],
        ['SMTP_HOST / SMTP_PORT', 'Gmail SMTP server details'],
        ['SMTP_USER / SMTP_PASSWORD', 'Gmail App Password credentials'],
        ['FRONTEND_URL', 'Used in email hyperlinks (default: http://localhost:3000)'],
        ['AI_ESTIMATION_ENABLED', 'Feature flag for Phase 2 AI (currently "false")'],
    ],
    col_widths=[2.5, 4.0]
)

add_heading('frontend — React/Vite', 3)
add_bullet('Port: 3000:3000, VITE_API_URL=http://localhost:8000')
add_bullet('Volume-mounts ./frontend:/app with node_modules isolated inside the container')
add_bullet('npm run dev -- --host serves the Vite dev server accessible from the host browser')

add_heading('Database Initialisation', 2)
add_body('On startup, two things happen automatically:')
add_bullet('Base.metadata.create_all(bind=engine) creates all tables if they do not exist.')
add_bullet('run_all_seeds(db) inserts: default admin user, sample managers per region, 20+ emission factors (DEFRA/IPCC/CPCB), and sample vendor accounts with FY2024 emission records.')

add_heading('Backend Project Structure', 2)
for line in [
    'backend/app/',
    '├── main.py              # FastAPI app factory, router registration, startup seed',
    '├── core/',
    '│   ├── config.py        # Pydantic Settings (reads env vars)',
    '│   └── security.py      # JWT, bcrypt, role-guard Depends()',
    '├── db/',
    '│   ├── database.py      # SQLAlchemy engine + session + Base',
    '│   └── seed.py          # run_all_seeds()',
    '├── models/',
    '│   ├── user.py          # All SQLAlchemy ORM models',
    '│   ├── notification.py  # Notification model',
    '│   └── attachment.py    # Attachment model',
    '├── schemas/schemas.py   # Pydantic request/response schemas',
    '├── api/routes/          # One file per domain (auth, users, emissions…)',
    '└── services/            # Business logic (email, calc, audit, report)',
]:
    add_code(line)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 3. USER ROLES & ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('3. User Roles & Access Control', 1)

add_heading('Role Definitions', 2)
add_table(
    ['Role', 'Description'],
    [
        ['admin', 'Full platform access. Creates/updates/deletes any user. Manages emission factors, reporting periods, platform settings.'],
        ['manager', 'Scoped to their assigned region. Invites vendors, reviews and approves/rejects records, views regional dashboards.'],
        ['vendor', 'Submits emission data. Cannot see other vendors\' data. Must complete onboarding before submitting records.'],
        ['auditor', 'Read-only access across all regions. Can view and export audit logs. Cannot create or modify any data.'],
    ],
    col_widths=[1.2, 5.3]
)

add_heading('Region Scoping', 2)
add_body('Regions are an enum: north, south, east, west, central, all.')
add_bullet('Managers are assigned one region and only see vendors and records within it.')
add_bullet('Admins have region = "all" and see everything regardless of region filters.')
add_bullet('Vendors are assigned a region during invitation; all their emission records are tagged with it automatically.')
add_bullet('Auditors see all records across all regions for verification purposes.')

add_heading('Backend Role Guards', 2)
add_body('Every protected API endpoint uses a FastAPI Depends() guard:')
for line in [
    'require_admin   = require_roles("admin")',
    'require_manager = require_roles("admin", "manager")   # both can access',
    'require_vendor  = require_roles("vendor")',
    'require_auditor = require_roles("admin", "auditor")',
    'require_any     = require_roles("admin", "manager", "vendor", "auditor")',
]:
    add_code(line)

add_heading('Frontend Route Guards', 2)
add_bullet('<RequireAuth> — redirects unauthenticated users to /login')
add_bullet('<RequireOnboarding> — redirects vendors to /onboarding or /change-password if incomplete')
add_bullet('<Wrap roles={[...]}> — combines authentication + onboarding check + AppLayout')
add_bullet('Role-based nav: sidebar links are filtered per role; admin-only routes return <Navigate to /dashboard> for others')

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 4. DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('4. Database Schema & Data Models', 1)
add_body('All models are defined in backend/app/models/user.py using SQLAlchemy ORM.')

add_heading('User Table', 2)
add_table(
    ['Column', 'Type', 'Details'],
    [
        ['id', 'Integer PK', 'Auto-increment primary key'],
        ['email', 'String(255)', 'Unique, indexed — login identifier'],
        ['password_hash', 'String(255)', 'bcrypt hash of password'],
        ['full_name', 'String(255)', 'Display name synced to sidebar/header'],
        ['phone', 'String(30)', 'Optional contact number'],
        ['designation', 'String(255)', 'Job title'],
        ['role', 'Enum', 'admin / manager / vendor / auditor'],
        ['region', 'Enum', 'north / south / east / west / central / all'],
        ['is_active', 'Boolean', 'Soft-delete flag (default True)'],
        ['onboarding_complete', 'Boolean', 'Vendor gate — False until 4-step wizard done'],
        ['must_change_password', 'Boolean', 'True for new invite; forces password change on login'],
        ['created_at', 'DateTime(TZ)', 'Server default NOW()'],
    ],
    col_widths=[1.8, 1.5, 3.2]
)

add_heading('VendorProfile Table', 2)
add_body('Extended company profile created during vendor onboarding. One-to-one with User.')
add_table(
    ['Column', 'Type', 'Details'],
    [
        ['user_id', 'FK → users', 'Unique foreign key'],
        ['company_name', 'String(255)', 'Legal registered company name'],
        ['trade_name', 'String(255)', 'Optional trade / brand name'],
        ['gst_number', 'String(20)', '15-character GST format validated on frontend'],
        ['pan_number', 'String(15)', '10-character PAN format validated on frontend'],
        ['cin_number', 'String(25)', 'Optional Corporate Identity Number'],
        ['state / city', 'String(100)', 'Indian state and city from geo dropdowns'],
        ['region', 'Enum', 'Auto-mapped from state selection'],
        ['pin_code', 'String(10)', '6-digit verified via India Post API'],
        ['address', 'Text', 'Full street address'],
        ['nic_code', 'String(10)', 'NIC industry classification code'],
        ['material_category', 'Integer', 'Scope 3 category 1–15'],
        ['material_name', 'String(255)', 'What the vendor supplies'],
        ['supply_frequency', 'String(50)', 'weekly / monthly / quarterly / annually / on-demand'],
        ['avg_annual_volume', 'Float', 'Typical annual supply quantity'],
        ['volume_unit', 'String(50)', 'Unit matching the volume (tonnes, kWh, km, etc.)'],
        ['has_own_carbon_system', 'Boolean', 'Whether vendor has internal carbon accounting'],
        ['contact_name', 'String(255)', 'Primary ESG contact person'],
        ['onboarded_at', 'DateTime(TZ)', 'Timestamp when onboarding was completed'],
    ],
    col_widths=[1.8, 1.5, 3.2]
)

add_heading('EmissionRecord Table', 2)
add_body('Core data table — one row per vendor emission submission. This is the central table for all analytics.')
add_table(
    ['Column', 'Type', 'Details'],
    [
        ['vendor_id', 'FK → vendor_profiles', 'Submitting vendor'],
        ['submitted_by', 'FK → users', 'User who submitted'],
        ['approved_by', 'FK → users', 'Who approved (nullable)'],
        ['category_id', 'Integer', 'Scope 3 category 1–15'],
        ['period_start / end', 'Date', 'Reporting period date range'],
        ['activity_value', 'Float', 'Measured quantity'],
        ['activity_unit', 'String(100)', 'Unit of activity (tonnes, kWh, km…)'],
        ['ef_id', 'FK → emission_factors', 'Which emission factor was applied'],
        ['calculated_co2e', 'Float', 'Result in tCO₂e (6 decimal precision)'],
        ['data_quality', 'Enum', 'A (primary measured) / B (estimated) / C (spend-based)'],
        ['input_method', 'Enum', 'manual / csv / api'],
        ['region', 'Enum', 'Auto-tagged from vendor\'s assigned region'],
        ['status', 'Enum', 'draft / submitted / approved / rejected'],
        ['rejection_reason', 'Text', 'Shown to vendor when rejected'],
        ['is_ai_estimated', 'Boolean', 'Phase 2 flag (currently always False)'],
        ['submitted_at', 'DateTime(TZ)', 'Auto-set on record creation'],
        ['approved_at', 'DateTime(TZ)', 'Set when manager approves'],
    ],
    col_widths=[2.0, 1.5, 3.0]
)

add_heading('Other Models', 2)
add_table(
    ['Model', 'Purpose', 'Key Fields'],
    [
        ['EmissionFactor', 'Published conversion factors (DEFRA/IPCC/CPCB/custom)', 'source, category_id, factor_value (kgCO₂e/unit), unit, version_tag, is_active'],
        ['VendorInvitation', 'Tracks pending vendor invites', 'email, temp_password_hash, region, status, expires_at (48h)'],
        ['AuditLog', 'Immutable action history', 'user_id, action, table_name, record_id, old_value, new_value (JSON)'],
        ['ReportingPeriod', 'Financial year periods', 'label, period_start, period_end, is_locked, locked_by'],
        ['EmissionTarget', 'Year-wise reduction goals', 'label, target_co2e, year, region'],
        ['Notification', 'In-app notifications', 'user_id, type, title, message, link, is_read'],
        ['Attachment', 'Files linked to records', 'emission_record_id, filename, file_path, file_size'],
        ['AIEstimate', 'Phase 2 AI metadata (schema ready)', 'model_used, inputs_json, confidence_score, explanation_text'],
    ],
    col_widths=[1.8, 2.5, 2.2]
)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. BACKEND API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('5. Backend API — Endpoints Reference', 1)
add_body('Base URL: http://localhost:8000  |  All protected endpoints require: Authorization: Bearer <JWT_TOKEN>')

add_heading('Authentication  /auth', 2)
add_table(
    ['Method', 'Path', 'Auth', 'Description'],
    [
        ['POST', '/auth/login', 'None', 'Returns JWT token. Body: {email, password}. Also returns must_change_password flag.'],
        ['GET', '/auth/me', 'Any', 'Returns current user\'s full profile. Called on app load to refresh auth state.'],
    ],
    col_widths=[0.7, 1.8, 0.6, 3.4]
)

add_heading('User Management  /users', 2)
add_table(
    ['Method', 'Path', 'Auth', 'Description'],
    [
        ['GET', '/users', 'Admin', 'List all users with optional ?role= filter.'],
        ['POST', '/users', 'Admin', 'Create non-vendor user (manager, auditor).'],
        ['GET', '/users/vendors', 'Manager+', 'List all vendors with full profile. Managers see only their region.'],
        ['GET', '/users/vendors/{id}', 'Manager+', 'Detailed vendor view: profile + record count + total CO₂e.'],
        ['GET', '/users/{id}', 'Admin', 'Get single user by ID.'],
        ['PATCH', '/users/{id}', 'Admin', 'Update role, region, is_active. Cannot change own role or deactivate self.'],
        ['DELETE', '/users/{id}', 'Manager+', 'Soft-delete (is_active=False). Managers can only delete their region\'s vendors.'],
        ['POST', '/users/invite-vendor', 'Manager+', 'Invite vendor. Generates temp password (token_urlsafe), sends email.'],
    ],
    col_widths=[0.7, 1.9, 0.9, 3.0]
)

add_heading('Emissions  /emissions', 2)
add_table(
    ['Method', 'Path', 'Auth', 'Description'],
    [
        ['POST', '/emissions', 'Vendor', 'Submit record. Validates period lock + activity data + calculates CO₂e. Notifies managers.'],
        ['POST', '/emissions/upload-csv', 'Vendor', 'Bulk upload via CSV. Row-by-row validation; partial success allowed. Returns {created, errors}.'],
        ['GET', '/emissions', 'Any', 'List records (role-scoped). Filters: region, category_id, vendor_id, status, year.'],
        ['GET', '/emissions/{id}/trace', 'Any', 'Record with full calculation trace + EF metadata + audit info.'],
        ['PATCH', '/emissions/{id}/status', 'Manager+', 'Approve or reject. Sends in-app notification + email. Stores rejection_reason.'],
    ],
    col_widths=[0.7, 2.0, 0.9, 2.9]
)

add_heading('Dashboard  /dashboard', 2)
add_table(
    ['Method', 'Path', 'Description'],
    [
        ['GET', '/dashboard/summary', 'Total CO₂e, record count, pending, YoY % change, prev year total, quality distribution.'],
        ['GET', '/dashboard/category-breakdown', 'CO₂e aggregated by Scope 3 category with percentage.'],
        ['GET', '/dashboard/region-breakdown', 'CO₂e by region with vendor count. Admin/auditor only.'],
        ['GET', '/dashboard/trend', 'Time-series. ?frequency=monthly|quarterly|yearly'],
        ['GET', '/dashboard/top-vendors', 'Top N vendors by total CO₂e. Manager+ only.'],
        ['GET', '/dashboard/vendor-engagement', 'Engagement score (0–100) per vendor. Manager+ only.'],
    ],
    col_widths=[0.7, 2.2, 3.6]
)
add_body('Engagement score formula: onboarding_complete(30) + has_records(40) + many_records(20) + own_carbon_system(10)')

add_heading('Other API Groups', 2)
add_table(
    ['Router', 'Prefix', 'Key Endpoints'],
    [
        ['Profile', '/profile', 'GET/PATCH profile, POST change-password, POST change-email, GET/PATCH vendor-details'],
        ['Reports', '/reports', 'GET download-excel (.xlsx), GET csv-template'],
        ['Emission Factors', '/emission-factors', 'GET list (filterable), POST create (admin), DELETE deactivate (admin)'],
        ['Audit', '/audit', 'GET /logs (paginated, filterable), GET /logs/export-csv'],
        ['Reporting Periods', '/reporting-periods', 'GET list, POST create (admin), POST /{id}/lock (admin)'],
        ['Targets', '/targets', 'GET list by year, POST create (manager+), DELETE'],
        ['Notifications', '/notifications', 'GET list, GET unread-count, POST /{id}/read, POST /read-all'],
        ['Vendor Tools', '/vendor', 'GET history, GET intensity, GET export-csv, GET brsr-export, POST bulk-reminder'],
        ['Attachments', '/attachments', 'GET list by record, POST upload file, DELETE'],
        ['Health', '/health', 'GET — returns {status: ok, version: 1.2.0}. No auth.'],
    ],
    col_widths=[1.5, 2.0, 3.0]
)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 6. CALCULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('6. Calculation Engine', 1)
add_body('File: backend/app/services/calculation_engine.py')

add_heading('Core Formula', 2)
add_code('CO₂e (tCO₂e) = Activity Value  ×  Emission Factor (kgCO₂e/unit)  ÷  1000')
add_body('')
add_body('Every calculation returns a full trace dictionary for audit and transparency:')
for line in [
    '{',
    '  "calculated_co2e": 0.425000,',
    '  "calculation_trace": {',
    '    "formula": "CO2e (tCO2e) = Activity Data × Emission Factor / 1000",',
    '    "activity_value": 500, "activity_unit": "tonnes",',
    '    "ef_value": 0.85, "ef_unit": "kgCO2e/tonne",',
    '    "raw_co2e_kg": 425.0,',
    '    "steps": ["Step 1: Activity = 500 tonnes",',
    '              "Step 2: EF = 0.85 kgCO2e/tonne",',
    '              "Step 3: Raw CO2e = 500 × 0.85 = 425.0 kgCO2e",',
    '              "Step 4: Convert = 425.0 / 1000 = 0.425 tCO2e"]',
    '  }',
    '}',
]:
    add_code(line)

add_heading('Activity Validation', 2)
add_bullet('Activity value must be greater than 0.')
add_bullet('Category-specific sanity checks: Business Travel (Cat 6) > 1M km triggers warning.')
add_bullet('Spend > 1B INR (Cat 1) triggers a warning for unit verification.')
add_bullet('Returns {valid, warnings, errors} — errors block submission, warnings are displayed only.')

add_heading('GHG Protocol Scope 3 Categories (1–15)', 2)
add_table(
    ['#', 'Category Name'],
    [
        ['1', 'Purchased Goods & Services'],
        ['2', 'Capital Goods'],
        ['3', 'Fuel & Energy Related Activities'],
        ['4', 'Upstream Transport & Distribution'],
        ['5', 'Waste Generated in Operations'],
        ['6', 'Business Travel'],
        ['7', 'Employee Commuting'],
        ['8', 'Downstream Transport & Distribution'],
        ['9', 'Processing of Sold Products'],
        ['10', 'Use of Sold Products'],
        ['11', 'End-of-Life Treatment of Sold Products'],
        ['12', 'Leased Assets'],
        ['13', 'Franchises'],
        ['14', 'Investments'],
        ['15', 'Other (Custom)'],
    ],
    col_widths=[0.5, 6.0]
)

add_heading('Phase 2 AI Hook', 2)
add_body(
    'estimate_missing_data() is a stub that returns None when AI_ESTIMATION_ENABLED=false. '
    'The AIEstimate table and schema are already created in the database. '
    'When Phase 2 is activated, the AI Estimation Service will plug in here to fill missing '
    'primary activity data using ML models — without changing the calculation engine interface.'
)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 7. FRONTEND PAGES
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('7. Frontend — Pages & Features', 1)

add_heading('Application Shell (App.tsx)', 2)
add_bullet('React Router v6 with BrowserRouter. All routes registered in a single App.tsx.')
add_bullet('Zustand authStore persists JWT + user object in localStorage.')
add_bullet('On app mount: calls GET /auth/me to validate token and refresh user object; logs out on 401.')
add_bullet('react-hot-toast Toaster in top-right for global success/error notifications.')

add_heading('LoginPage  (/login)', 2)
add_bullet('Email + password form with client-side validation.')
add_bullet('On success: stores JWT + user in authStore via localStorage.')
add_bullet('Auto-redirects: must_change_password=True → /change-password; vendor !onboarding_complete → /onboarding.')

add_heading('ChangePasswordPage  (/change-password)', 2)
add_bullet('Shown when must_change_password=True (temporary password from vendor invitation).')
add_bullet('Fields: current/temporary password, new password, confirm password.')
add_bullet('Calls: POST /profile/change-password {current_password, new_password}.')
add_bullet('On success: clears must_change_password in store → redirects to /onboarding or /dashboard.')

add_heading('DashboardPage  (/dashboard)', 2)
add_body('Visible to all roles. All data is filtered server-side based on the caller\'s role and region.')
add_table(
    ['Widget', 'Visible To', 'Description'],
    [
        ['Year + Region filters', 'All (region only for admin/auditor)', 'Filter all widgets simultaneously'],
        ['KPI Cards (4)', 'All', 'Total CO₂e, Record Count, Pending, YoY % Change'],
        ['Category Breakdown', 'All', 'Horizontal bar chart by Scope 3 category (Recharts)'],
        ['Emission Trend', 'All', 'Line chart; toggle monthly / quarterly / yearly'],
        ['Region Breakdown', 'Admin/Auditor', 'CO₂e by region with vendor count'],
        ['Top Vendors Table', 'Manager+', 'Ranked by total emissions with last-submission date'],
        ['Vendor Engagement', 'Manager+', 'Score 0–100 per vendor'],
        ['Target Overlay', 'All', 'If targets exist for year, shows target line on trend chart'],
    ],
    col_widths=[2.0, 1.5, 3.0]
)

add_heading('EmissionsPage  (/emissions)', 2)
add_bullet('Filterable data table: category, status, vendor (manager+), year, region (admin).')
add_bullet('Status badges with colour coding: Draft (grey), Submitted (amber), Approved (green), Rejected (red).')
add_bullet('Click any record → detail drawer with full calculation trace, EF details, quality, rejection reason.')
add_bullet('Approve / Reject actions inline (manager+) with optional rejection reason text field.')
add_bullet('File attachments list per record; upload button.')

add_heading('ReportsPage  (/reports)', 2)
add_bullet('Download Excel report (.xlsx) filtered by year/region — two sheets: data + summary.')
add_bullet('Download blank CSV upload template with all required column headers.')
add_bullet('Reporting periods panel: list, create, lock periods (admin).')
add_bullet('Emission targets panel: set year targets (manager+), delete.')
add_bullet('BRSR export for vendor own data (required for Indian listed companies).')

add_heading('AuditPage  (/audit)', 2)
add_bullet('Admin and Auditor only. Shows filterable audit log table.')
add_bullet('Filters: user, action type (CREATE/UPDATE/DELETE…), table name.')
add_bullet('Export CSV button — downloads up to 5,000 most recent entries.')

add_heading('ProfilePage  (/profile)', 2)
add_body('Three tabs:')
add_bullet('Personal Info — edit full name, phone, designation.')
add_bullet('Security — change password (current → new → confirm), change email (requires password confirmation).')
add_bullet('Company Profile (vendor only) — edit all editable VendorProfile fields. On save: syncs contact_name → full_name in global authStore so sidebar/topbar update immediately without reload.')

page_break()

add_heading('VendorsPage  (/vendors)  [Manager/Admin]', 2)
add_bullet('Table of all vendors in manager\'s region (admin sees all). Searchable by company name or email.')
add_bullet('Columns: Company Name, Region, State, Onboarding Status, Record Count, Last Submission.')
add_bullet('Click vendor → side panel with full VendorProfile, total CO₂e, record history.')
add_bullet('Invite Vendor button → modal: email, region (admin only), sends invitation email with temp password.')
add_bullet('If SMTP not configured, temp password is shown directly in the modal for manual sharing.')
add_bullet('Send Reminder + Deactivate buttons per vendor row.')

add_heading('UsersPage  (/users)  [Admin only]', 2)
add_bullet('Full user management: all roles in one table with role-filter tabs.')
add_bullet('Create user form (name, email, password, role, region).')
add_bullet('Edit inline: role, region, is_active. Delete with confirmation dialog (soft-delete).')

add_heading('EFLibraryPage  (/emission-factors)  [Admin only]', 2)
add_bullet('Searchable/filterable table of active emission factors. Filter by category, source.')
add_bullet('Create new EF (all fields). Deactivate/hide EF (soft-delete).')

add_heading('Vendor-Specific Pages', 2)
add_table(
    ['Page', 'Route', 'Description'],
    [
        ['OnboardingPage', '/onboarding', '4-step wizard for vendor profile setup (see Section 8)'],
        ['SubmitDataPage', '/submit', 'Manual entry + CSV upload tabs for emission records (see Section 9)'],
        ['SubmissionHistory', '/history', 'Timeline of own submissions with status, rejection reason, intensity stats'],
        ['ActivityCalculator', '/activity-calculator', 'Guided instructions for measuring activity data per Scope 3 category'],
    ],
    col_widths=[1.8, 1.8, 3.0]
)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 8. VENDOR ONBOARDING FLOW
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('8. Vendor Onboarding Flow', 1)
add_body('The onboarding flow is a mandatory 4-step wizard that vendors must complete before they can submit any emission data.')

add_heading('Full Flow Sequence', 2)
steps = [
    ('Manager invites vendor', 'POST /users/invite-vendor  →  backend generates temp password (secrets.token_urlsafe(10)), creates User (role=vendor, must_change_password=True), stores hash in VendorInvitation, sends invitation email.'),
    ('Vendor receives email', 'Email contains: login URL, email address, temporary password (valid 48 hours), assigned region.'),
    ('Vendor logs in', 'Backend returns must_change_password=True in token response.'),
    ('Change password', 'Frontend redirects to /change-password. Vendor sets permanent password. Backend verifies current, sets new hash, clears must_change_password=False.'),
    ('Redirect to onboarding', 'Frontend detects vendor role + !onboarding_complete → redirects to /onboarding.'),
    ('4-step wizard', 'Steps: Company Info → Location → Operations → Contact (detail below).'),
    ('Onboarding complete', 'Backend creates VendorProfile, sets onboarding_complete=True. Frontend redirects to /dashboard.'),
]
for i, (title, desc) in enumerate(steps, 1):
    p = doc.add_paragraph()
    r1 = p.add_run(f'Step {i}: {title}  — ')
    r1.bold = True; r1.font.size = Pt(10); r1.font.color.rgb = GREEN
    r2 = p.add_run(desc)
    r2.font.size = Pt(10); r2.font.color.rgb = DARK
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.space_after = Pt(4)

add_heading('Onboarding Wizard Steps', 2)
add_table(
    ['Step', 'Title', 'Fields & Validation'],
    [
        ['1', 'Company Info', 'Company name, Trade name, Year established (dropdown 1500–2076), GST (15-char regex), PAN (10-char regex), CIN (optional, regex), NIC industry code.'],
        ['2', 'Location', 'State (all Indian states grouped by region), City (populated on state change), PIN code (async API verified — blocks progression if invalid), Full address.'],
        ['3', 'Operations', 'Scope 3 category (1–15), Material name, Supply frequency (weekly/monthly/quarterly/annually/on-demand), Avg annual volume, Volume unit (full unit list + custom option), Own carbon system checkbox.'],
        ['4', 'Contact', 'Contact name, Designation, Phone, Declaration checkbox (must check to submit).'],
    ],
    col_widths=[0.5, 1.3, 4.7]
)

add_heading('PIN Code Verification Logic', 2)
add_bullet('User types a 6-digit PIN code in the Location step.')
add_bullet('After 800ms debounce, frontend calls the India Post API: https://api.postalpincode.in/pincode/{pin}')
add_bullet('While checking: spinner shown, "Continue" button is disabled.')
add_bullet('If valid: shows green tick with matched city and state name.')
add_bullet('If invalid: shows red error message; "Continue" button remains disabled.')
add_bullet('If API call fails (network error): silently accepts (fail open) to not block the user.')

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 9. EMISSION DATA SUBMISSION
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('9. Emission Data Submission Flow', 1)

add_heading('Manual Submission (Tab 1)', 2)
add_table(
    ['Field', 'Type', 'Behaviour'],
    [
        ['Category', 'Dropdown', 'Pre-filled from vendor profile but changeable. Triggers EF + unit list reload.'],
        ['Period Start', 'Date picker', 'Any date. Sets minimum for Period End.'],
        ['Period End', 'Date picker', 'Disabled until Period Start chosen. Backend validates period not locked.'],
        ['Activity Value', 'Number', 'Must be > 0. Triggers live CO₂e preview.'],
        ['Unit', 'Dropdown', 'Category-specific units from UNIT_BY_CATEGORY map. Falls back to ALL_UNITS if no category. "Other" reveals custom text input (stored as custom_unit, merged to activity_unit on submit).'],
        ['Emission Factor', 'Dropdown', 'Loaded from /emission-factors?category_id=X. Shows source + version + material type.'],
        ['Data Quality', 'Dropdown', 'A = primary measured, B = estimated, C = spend-based.'],
        ['Notes', 'Textarea', 'Optional free text.'],
    ],
    col_widths=[1.5, 0.8, 4.2]
)
add_body('Live CO₂e Preview Panel: updates in real-time as Activity Value and EF are selected. Shows formula, raw kgCO₂e, and final tCO₂e.')
add_body('HelpTooltip icons appear on Category, Activity Value, Unit, EF, and Data Quality fields — appear on hover only (CSS-only, no JS state).')

add_heading('CSV Bulk Upload (Tab 2)', 2)
add_bullet('Drag-and-drop or file browse. CSV must contain: category_id, period_start, period_end, activity_value, activity_unit, ef_id.')
add_bullet('Optional columns: data_quality (default B), notes.')
add_bullet('Backend processes row-by-row; invalid rows are skipped and returned in errors list.')
add_bullet('Response shows: created count, error list with row numbers, total rows parsed.')
add_bullet('Download Template button fetches the standard CSV template from the API.')

add_heading('Approval Workflow', 2)
add_bullet('Record is created with status="submitted" which triggers manager notification.')
add_bullet('Manager sees pending badge on dashboard + /emissions table filtered to "submitted" status.')
add_bullet('Manager clicks a record → views full calculation trace and EF details.')
add_bullet('Manager clicks Approve → status="approved", approved_by/approved_at stamped, vendor notified in-app + email.')
add_bullet('Manager clicks Reject (with optional reason) → status="rejected", rejection_reason stored, vendor notified in-app + email with reason shown.')

add_heading('Period Lock Guard', 2)
add_body(
    'Before any emission record can be created or status-updated, the backend checks if a ReportingPeriod '
    'overlapping the record\'s dates has is_locked=True. If so, it returns HTTP 423 Locked and the '
    'operation is blocked. This prevents retroactive data manipulation after period close.'
)

page_break()

# ═══════════════════════════════════════════════════════════════════════════════
# 10–14. SERVICES, SECURITY, GEO
# ═══════════════════════════════════════════════════════════════════════════════
add_heading('10. Audit Logging System', 1)
add_body('Every significant action is logged automatically via log_action() in audit_service.py.')
add_table(
    ['Action Code', 'Trigger'],
    [
        ['CREATE_USER', 'Admin creates a new user account'],
        ['UPDATE_USER', 'Admin changes role / region / active status'],
        ['DELETE_USER', 'Soft-delete of a user'],
        ['CREATE_EMISSION_RECORD', 'Vendor submits a manual record'],
        ['CSV_UPLOAD', 'Vendor uploads bulk CSV'],
        ['STATUS_UPDATE', 'Manager approves or rejects a record'],
        ['CREATE_EF', 'Admin adds a new emission factor'],
        ['DEACTIVATE_EF', 'Admin soft-deletes an EF'],
        ['LOCK_PERIOD', 'Admin locks a reporting period'],
    ],
    col_widths=[2.5, 4.0]
)
add_body('Each log entry stores: who, what, which table, which record ID, JSON before/after values, description, IP address, timestamp.')

add_heading('11. Notification System', 1)
add_body('In-app notifications created via notify() in notification_service.py.')
add_table(
    ['Type', 'Sent When', 'Recipient'],
    [
        ['record_submitted', 'Vendor submits a record', 'All managers in vendor\'s region'],
        ['record_approved', 'Manager approves a record', 'The submitting vendor'],
        ['record_rejected', 'Manager rejects a record', 'The submitting vendor'],
        ['reminder', 'Bulk reminder sent', 'Specific vendor(s)'],
        ['system', 'Platform-level event', 'Any user'],
    ],
    col_widths=[1.8, 2.5, 2.2]
)
add_body('Frontend: bell icon shows unread count badge. Dropdown lists messages. Click marks read. "Mark all read" button available.')

add_heading('12. Email Service', 1)
add_body('File: backend/app/services/email_service.py  |  SMTP via Gmail (STARTTLS, port 587).')
add_body('Dev Mode: If SMTP_USER is empty, emails print to the Docker console — no configuration needed for local development.')
add_table(
    ['Function', 'Sent When', 'Content'],
    [
        ['send_vendor_invitation()', 'Vendor is invited', 'Login URL, email address, temp password (48h expiry), region. Styled HTML version included.'],
        ['send_record_status_email()', 'Record approved or rejected', 'Outcome + rejection reason if rejected. Link to /submit for resubmission.'],
        ['send_weekly_digest()', 'Scheduled (function ready, scheduler not wired)', 'Manager digest: total CO₂e, record count, pending count per region.'],
    ],
    col_widths=[2.0, 2.0, 2.5]
)

add_heading('13. Reporting & Exports', 1)
add_table(
    ['Export', 'Endpoint', 'Format', 'Description'],
    [
        ['Excel Report', '/reports/download-excel', '.xlsx', 'All visible records + summary sheet. Filterable by year/region.'],
        ['CSV Template', '/reports/csv-template', '.csv', 'Blank template with exact column headers for bulk upload.'],
        ['Vendor CSV', '/vendor/export-csv', '.csv', 'Vendor\'s own records. Role-gated to vendor.'],
        ['BRSR Export', '/vendor/brsr-export', '.csv', 'BRSR format for Indian annual reporting compliance.'],
        ['Audit Log CSV', '/audit/logs/export-csv', '.csv', 'Up to 5,000 most recent audit entries. Admin/Auditor only.'],
    ],
    col_widths=[1.5, 2.2, 0.7, 2.1]
)

add_heading('14. Authentication & Security', 1)
add_table(
    ['Aspect', 'Implementation'],
    [
        ['Algorithm', 'HS256 (JWT) via python-jose'],
        ['Payload', '{sub: user_id, exp: expiry_timestamp}'],
        ['Token expiry', 'Configurable via ACCESS_TOKEN_EXPIRE_MINUTES (default: 60 min)'],
        ['Password hashing', 'bcrypt via passlib. Workaround applied for bcrypt 4.x / passlib 1.7.4 compatibility.'],
        ['Token storage', 'localStorage on frontend. Axios config attaches Bearer header to every request.'],
        ['401 handling', 'Axios interceptor clears localStorage and redirects to /login on any 401 response.'],
        ['App mount refresh', 'GET /auth/me called on every app load to validate token and refresh user fields.'],
        ['Manager region guard', 'Manager endpoints additionally check that record.region == manager.region or reject 403.'],
        ['Self-protection', 'Admin cannot deactivate their own account or change their own role via the API.'],
    ],
    col_widths=[2.0, 4.5]
)

page_break()

add_heading('15. India Geolocation Support', 1)
add_body('File: frontend/src/utils/indiaGeo.ts — Single source of truth for Indian geographic data.')
add_table(
    ['Feature', 'Details'],
    [
        ['States by region', 'All 28 states + 8 UTs grouped into platform regions (north/south/east/west/central).'],
        ['Cities per state', '50+ major cities mapped per state (e.g., Maharashtra: Mumbai, Pune, Nagpur, Nashik, Aurangabad, Thane…)'],
        ['PIN code pre-fill', 'CITY_PINCODE map provides representative pincode when city is selected; user can override.'],
        ['verifyPincode()', 'Calls https://api.postalpincode.in/pincode/{pin}. Returns {valid, city, state} or error.'],
        ['Onboarding integration', 'State dropdown → city dropdown → PIN code auto-fill → async verification with live spinner.'],
    ],
    col_widths=[2.0, 4.5]
)

add_heading('16. Unit System', 1)
add_body('The unit system is consistent across onboarding (volume_unit) and data submission (activity_unit). Both pages use the same list.')
add_table(
    ['Unit', 'Typical Use Case'],
    [
        ['tonnes', 'Raw materials, waste, freight weight'],
        ['kg', 'Smaller material quantities'],
        ['litres', 'Liquid fuels (diesel, petrol)'],
        ['kL (kilolitres)', 'Larger liquid volumes'],
        ['kWh', 'Electricity consumption'],
        ['MWh', 'Large-scale electricity'],
        ['km', 'Distance travelled'],
        ['tonne-km', 'Freight transport (weight × distance)'],
        ['passenger-km', 'Business / employee travel'],
        ['vehicle-km', 'Transport fleet operations'],
        ['units / pieces', 'Discrete manufactured goods'],
        ['INR (spend-based)', 'Spend-based estimation (Category 1, 13)'],
        ['INR (invested)', 'Investment-based estimation (Category 14)'],
        ['USD (spend-based)', 'International spend'],
        ['nights', 'Hotel stays (Business Travel, Cat 6)'],
        ['Custom (Other)', 'Vendor specifies free-text unit; stored verbatim'],
    ],
    col_widths=[2.2, 4.3]
)

page_break()

add_heading('17. Bugs Fixed in This Development Session', 1)
add_table(
    ['Bug', 'Root Cause', 'Fix Applied'],
    [
        ['Activity Calculator page crashed on load',
         'SCOPE3_CATEGORIES was referenced but not imported in ActivityCalculator.tsx.',
         'Added import from constants module.'],
        ['Vendor list returned 422 / empty',
         'FastAPI route ordering: /users/vendors registered after /{user_id}; "vendors" was parsed as a numeric ID.',
         'Moved /vendors and /vendors/{id} routes above /{user_id} in users.py.'],
        ['Dashboard showed no seeded data',
         'Default year state was current system year (2026); all seeded data is for FY2024.',
         'Changed default year state to "2024" in DashboardPage.tsx.'],
        ['Vendor password change failed at runtime',
         'ChangePasswordPage called authApi.changePassword() — method does not exist; correct one is profileApi.changePassword() with different signature.',
         'Changed import to profileApi, fixed call: profileApi.changePassword({current_password, new_password}).'],
        ['Onboarding could proceed with invalid PIN',
         'nextStep() did not check pincodeStatus before navigating to the next step.',
         'Added guard: if step === 1 and pincodeStatus === "error" or API still checking, block with toast.'],
        ['Profile update not reflected in sidebar/header',
         'onVendorSave only updated local vendorProfile state; global authStore was not updated.',
         'Added updateUser({...user, full_name: data.contact_name}) after save, causing immediate re-render.'],
        ['SubmitDataPage unit dropdown empty before category selected',
         'No fallback unit list when category_id was null. Also "other" option re-registered activity_unit field, overwriting the dropdown value.',
         'Added ALL_UNITS fallback; separated custom unit into custom_unit field, merged into activity_unit on submit.'],
        ['HelpTooltip required click to open and had a close button',
         'Implemented with useState + click handler. Disruptive UX during data entry.',
         'Rewritten as pure CSS hover tooltip using group/group-hover Tailwind classes. No JS state, no close button.'],
    ],
    col_widths=[1.7, 2.3, 2.5]
)

# ── Save ─────────────────────────────────────────────────────────────────────
out_path = r'c:\Users\arpit\Desktop\Code\College\DL\CP\Phase 1\scope3-platform-v5\StratXG_Platform_Documentation.docx'
doc.save(out_path)
print(f'Saved → {out_path}')
