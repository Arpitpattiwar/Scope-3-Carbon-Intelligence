"""
Scope 3 Platform — Database Seeder (v8)

7 vendors across all 5 regions, 36 monthly periods (Apr 2022 – Mar 2025).
Produces ~292 emission records: enough history for LSTM forecast to activate.

FORCE_RESEED=true  wipes all tables and re-seeds from scratch.
After first clean seed set FORCE_RESEED=false to prevent data loss.
"""
import calendar, os
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.user import (
    User, EmissionFactor, ReportingPeriod,
    VendorProfile, EmissionRecord, EmissionTarget,
)
from app.core.security import get_password_hash


# ── Helpers ───────────────────────────────────────────────────────────────────
def _last(yr, mo):
    return date(yr, mo, calendar.monthrange(yr, mo)[1])

_SEA = {1:0.97,2:0.99,3:1.06,4:0.95,5:1.00,6:1.02,
        7:0.88,8:0.86,9:0.91,10:1.10,11:1.14,12:1.18}

def _act(base, gr, yr, mo, noise=0.04):
    yrs = ((yr-2022)*12+(mo-4))/12.0
    idx = (yr-2022)*12+(mo-4)
    return round(base*(1+gr)**yrs*_SEA[mo]*(1+noise*((idx%7-3)/3)), 1)

def _status(yr, mo, vi):
    pe = _last(yr, mo)
    if pe <= date(2024, 9, 30): return "approved"
    if pe <= date(2024,12,31): return "submitted"
    return "submitted" if vi%2==0 else "draft"


# ── Wipe ──────────────────────────────────────────────────────────────────────
def _wipe(db):
    print("⚠️  FORCE_RESEED — wiping all tables …")
    for t in ["emission_records","emission_targets","ai_estimates",
              "reporting_periods","record_attachments","vendor_profiles",
              "emission_factors","audit_logs","notifications",
              "vendor_invitations","users"]:
        try:
            db.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))
        except Exception:
            db.rollback()
    db.commit()
    print("✅ Wiped")


# ── Users & profiles ──────────────────────────────────────────────────────────
def seed_admin(db):
    if db.query(User).filter(User.email=="admin@stratxg.com").first():
        return

    for kw in [
        dict(email="admin@stratxg.com",full_name="Platform Admin",
             role="admin",region="all",is_active=True,onboarding_complete=True,
             password_hash=get_password_hash("Admin@1234")),
        dict(email="manager.north@stratxg.com",full_name="North Region Manager",
             role="manager",region="north",is_active=True,onboarding_complete=True,
             password_hash=get_password_hash("Manager@1234")),
        dict(email="manager.south@stratxg.com",full_name="South Region Manager",
             role="manager",region="south",is_active=True,onboarding_complete=True,
             password_hash=get_password_hash("Manager@1234")),
        dict(email="auditor@stratxg.com",full_name="External Auditor",
             role="auditor",is_active=True,onboarding_complete=True,
             password_hash=get_password_hash("Auditor@1234")),
    ]:
        db.add(User(**kw))

    _vendors = [
        ("vendor@acmesupplies.com","Rahul Sharma","north"),
        ("vendor@greentrans.com","Priya Menon","south"),
        ("vendor@wastecare.com","Amit Patel","north"),
        ("vendor@energytech.com","Sunita Rao","west"),
        ("vendor@buildcorp.com","Arjun Das","east"),
        ("vendor@travelpro.com","Meera Joshi","central"),
        ("vendor@commuteplus.com","Vikram Singh","west"),
    ]
    _profiles = [
        ("Acme Supplies Pvt Ltd","27AABCA1234B1Z5","AABCA1234B","46610",1,
         "Steel & Aluminium procurement","Delhi","New Delhi",False),
        ("GreenTrans Logistics","33AADCG5678C1Z2","AADCG5678C","49100",4,
         "Road freight — diesel HGV","Tamil Nadu","Chennai",True),
        ("WasteCare Solutions","24AACFW9012D1Z3","AACFW9012D","38110",5,
         "Industrial waste disposal","Gujarat","Ahmedabad",False),
        ("EnergyTech Industries","27AACFE3456F1Z8","AACFE3456F","35119",3,
         "Diesel fuel upstream emissions","Maharashtra","Pune",True),
        ("BuildCorp Limited","19AABCB7890G1Z6","AABCB7890G","41001",2,
         "Concrete & civil construction","West Bengal","Kolkata",False),
        ("TravelPro Services","23AABCT2345H1Z4","AABCT2345H","79110",6,
         "Domestic business travel (air)","Madhya Pradesh","Bhopal",False),
        ("Commuteplus Solutions","27AABCC6789I1Z9","AABCC6789I","45201",7,
         "Employee car commuting","Maharashtra","Nagpur",True),
    ]

    for (email,name,region),(comp,gst,pan,nic,cat,mat,state,city,sys) in zip(_vendors,_profiles):
        u = User(email=email,full_name=name,role="vendor",region=region,
                 is_active=True,onboarding_complete=True,
                 password_hash=get_password_hash("Vendor@1234"))
        db.add(u); db.flush()
        db.add(VendorProfile(
            user_id=u.id,company_name=comp,gst_number=gst,pan_number=pan,
            state=state,city=city,region=region,nic_code=nic,
            material_category=cat,material_name=mat,
            supply_frequency="monthly",avg_annual_volume=5000,volume_unit="tonnes",
            has_own_carbon_system=sys,contact_name=name,
            contact_designation="ESG Manager",contact_phone=f"+91 98{u.id:08d}",
            onboarded_at=datetime(2022,4,1),
        ))
    db.commit()
    print("✅ Seeded 11 users (1 admin, 2 managers, 1 auditor, 7 vendors)")


# ── Emission Factors ──────────────────────────────────────────────────────────
def seed_emission_factors(db):
    if db.query(EmissionFactor).count() > 0:
        return
    factors = [
        dict(source="DEFRA",category_id=1,subcategory="Raw Materials",
             material_type="Steel",factor_value=1890,unit="kgCO2e/tonne",
             region="global",version_tag="DEFRA_2024_v1",valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=1,subcategory="Raw Materials",
             material_type="Aluminium",factor_value=6700,unit="kgCO2e/tonne",
             region="global",version_tag="DEFRA_2024_v1",valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=1,subcategory="Raw Materials",
             material_type="Plastic (general)",factor_value=3140,unit="kgCO2e/tonne",
             region="global",version_tag="DEFRA_2024_v1",valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=1,subcategory="Spend-based",
             material_type="Manufacturing (generic)",factor_value=0.43,unit="kgCO2e/INR",
             region="India",version_tag="DEFRA_2024_v1",valid_from=date(2024,1,1),
             notes="Spend-based estimate for Indian manufacturing sector"),
        dict(source="IPCC",category_id=2,subcategory="Machinery & Equipment",
             material_type="Industrial machinery",factor_value=2100,unit="kgCO2e/tonne",
             region="global",version_tag="IPCC_AR6_v1",valid_from=date(2023,1,1),
             source_url="https://www.ipcc.ch/assessment-report/ar6/"),
        dict(source="IPCC",category_id=2,subcategory="Buildings",
             material_type="Concrete structure",factor_value=410,unit="kgCO2e/tonne",
             region="global",version_tag="IPCC_AR6_v1",valid_from=date(2023,1,1)),
        dict(source="DEFRA",category_id=3,subcategory="Electricity T&D losses",
             material_type="Grid electricity India",factor_value=0.82,unit="kgCO2e/kWh",
             region="India",version_tag="CPCB_2023_v1",valid_from=date(2023,1,1),
             source_url="https://cpcb.nic.in/",notes="India national grid average"),
        dict(source="DEFRA",category_id=3,subcategory="Fuel upstream",
             material_type="Diesel (upstream)",factor_value=0.621,unit="kgCO2e/litre",
             region="global",version_tag="DEFRA_2024_v1",valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=4,subcategory="Road freight",
             material_type="HGV (diesel) - average laden",factor_value=0.112,
             unit="kgCO2e/tonne-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=4,subcategory="Rail freight",
             material_type="Rail freight (diesel)",factor_value=0.028,
             unit="kgCO2e/tonne-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=4,subcategory="Sea freight",
             material_type="Container ship (average)",factor_value=0.016,
             unit="kgCO2e/tonne-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=4,subcategory="Air freight",
             material_type="Air freight",factor_value=1.17,
             unit="kgCO2e/tonne-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=5,subcategory="Waste to landfill",
             material_type="Mixed waste - landfill",factor_value=467,
             unit="kgCO2e/tonne",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=5,subcategory="Incineration",
             material_type="Mixed waste - incineration",factor_value=210,
             unit="kgCO2e/tonne",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=5,subcategory="Recycling",
             material_type="Mixed waste - recycled",factor_value=21,
             unit="kgCO2e/tonne",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=6,subcategory="Air travel",
             material_type="Domestic flights (India)",factor_value=0.255,
             unit="kgCO2e/passenger-km",region="India",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=6,subcategory="Air travel",
             material_type="International flights (economy)",factor_value=0.195,
             unit="kgCO2e/passenger-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=6,subcategory="Rail travel",
             material_type="Indian Railways (average)",factor_value=0.041,
             unit="kgCO2e/passenger-km",region="India",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),notes="Indian Railways grid mix"),
        dict(source="DEFRA",category_id=6,subcategory="Car travel",
             material_type="Petrol car (average)",factor_value=0.192,
             unit="kgCO2e/vehicle-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=6,subcategory="Hotel stays",
             material_type="Hotel night (India)",factor_value=31.2,
             unit="kgCO2e/night",region="India",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=7,subcategory="Commuting by car",
             material_type="Petrol car commute",factor_value=0.192,
             unit="kgCO2e/vehicle-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA",category_id=7,subcategory="Commuting by bus",
             material_type="Bus commute (India)",factor_value=0.089,
             unit="kgCO2e/passenger-km",region="India",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=7,subcategory="Commuting by metro/rail",
             material_type="Metro (India)",factor_value=0.031,
             unit="kgCO2e/passenger-km",region="India",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=8,subcategory="Road freight",
             material_type="LCV (diesel) delivery",factor_value=0.245,
             unit="kgCO2e/tonne-km",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="IPCC",category_id=9,subcategory="Industrial processing",
             material_type="Energy-intensive processing (average)",factor_value=0.82,
             unit="kgCO2e/kWh",region="India",version_tag="IPCC_AR6_v1",
             valid_from=date(2023,1,1)),
        dict(source="IPCC",category_id=10,subcategory="Electrical products",
             material_type="Consumer electronics (lifetime)",factor_value=150,
             unit="kgCO2e/unit",region="global",version_tag="IPCC_AR6_v1",
             valid_from=date(2023,1,1)),
        dict(source="IPCC",category_id=10,subcategory="Industrial products",
             material_type="Industrial equipment (lifetime)",factor_value=2400,
             unit="kgCO2e/unit",region="global",version_tag="IPCC_AR6_v1",
             valid_from=date(2023,1,1)),
        dict(source="DEFRA",category_id=11,subcategory="Electronic waste",
             material_type="E-waste landfill",factor_value=890,
             unit="kgCO2e/tonne",region="global",version_tag="DEFRA_2024_v1",
             valid_from=date(2024,1,1)),
        dict(source="DEFRA",category_id=12,subcategory="Office buildings",
             material_type="Office energy use (India)",factor_value=0.82,
             unit="kgCO2e/kWh",region="India",version_tag="CPCB_2023_v1",
             valid_from=date(2023,1,1)),
        dict(source="IPCC",category_id=13,subcategory="Revenue-based",
             material_type="Retail franchise (average)",factor_value=0.38,
             unit="kgCO2e/INR-revenue",region="India",version_tag="IPCC_AR6_v1",
             valid_from=date(2023,1,1),notes="Spend-based proxy for franchise emissions"),
        dict(source="IPCC",category_id=14,subcategory="Equity investments",
             material_type="Manufacturing sector (PCAF)",factor_value=0.52,
             unit="kgCO2e/INR-invested",region="India",version_tag="PCAF_2023_v1",
             valid_from=date(2023,1,1),notes="PCAF-aligned financial emissions intensity"),
        dict(source="IPCC",category_id=15,subcategory="Custom",
             material_type="Generic / industry-specific",factor_value=1.0,
             unit="kgCO2e/unit",region="global",version_tag="IPCC_AR6_v1",
             valid_from=date(2023,1,1),notes="Placeholder — replace with specific factor"),
    ]
    for f in factors:
        db.add(EmissionFactor(**f, is_active=True))
    db.commit()
    print(f"✅ Seeded {len(factors)} emission factors")


# ── Reporting Periods ─────────────────────────────────────────────────────────
def seed_reporting_periods(db):
    if db.query(ReportingPeriod).count() > 0:
        return
    for label,s,e,locked in [
        ("FY2022-23",date(2022,4,1),date(2023,3,31),True),
        ("FY2023-24",date(2023,4,1),date(2024,3,31),True),
        ("FY2024-25",date(2024,4,1),date(2025,3,31),False),
    ]:
        db.add(ReportingPeriod(label=label,period_start=s,period_end=e,is_locked=locked))
    db.commit()
    print("✅ Seeded 3 reporting periods (FY22-23 & FY23-24 locked; FY24-25 open)")


# ── Emission Records ──────────────────────────────────────────────────────────
def seed_emission_records(db):
    if db.query(EmissionRecord).count() > 0:
        return

    def _u(em): return db.query(User).filter(User.email==em).first()
    def _p(em):
        u=_u(em)
        return db.query(VendorProfile).filter(VendorProfile.user_id==u.id).first() if u else None
    def _ef(mt): return db.query(EmissionFactor).filter(
        EmissionFactor.material_type==mt,EmissionFactor.is_active==True).first()

    admin=_u("admin@stratxg.com")
    mgr_n=_u("manager.north@stratxg.com")
    mgr_s=_u("manager.south@stratxg.com")

    u1,p1=_u("vendor@acmesupplies.com"), _p("vendor@acmesupplies.com")
    u2,p2=_u("vendor@greentrans.com"),   _p("vendor@greentrans.com")
    u3,p3=_u("vendor@wastecare.com"),    _p("vendor@wastecare.com")
    u4,p4=_u("vendor@energytech.com"),   _p("vendor@energytech.com")
    u5,p5=_u("vendor@buildcorp.com"),    _p("vendor@buildcorp.com")
    u6,p6=_u("vendor@travelpro.com"),    _p("vendor@travelpro.com")
    u7,p7=_u("vendor@commuteplus.com"),  _p("vendor@commuteplus.com")

    if not all([p1,p2,p3,p4,p5,p6,p7]):
        print("⚠️  Skipping records — profile lookup failed"); return

    ef_steel=_ef("Steel");       ef_alum=_ef("Aluminium")
    ef_concrete=_ef("Concrete structure"); ef_diesel=_ef("Diesel (upstream)")
    ef_road=_ef("HGV (diesel) - average laden")
    ef_landfill=_ef("Mixed waste - landfill")
    ef_flight=_ef("Domestic flights (India)"); ef_car=_ef("Petrol car commute")

    if not all([ef_steel,ef_alum,ef_concrete,ef_diesel,ef_road,ef_landfill,ef_flight,ef_car]):
        print("⚠️  Skipping records — EF lookup failed"); return

    _app={"north":mgr_n,"south":mgr_s,"east":admin,"west":admin,"central":admin}

    def _make(profile,vu,cat,ps,pe,act,unit,ef,q,vi):
        co2e=round((act*ef.factor_value)/1000,4)
        st=_status(ps.year,ps.month,vi)
        sub_dt=pe+timedelta(days=10)
        sub_at=datetime(sub_dt.year,sub_dt.month,sub_dt.day,9,0,0)
        app_by=None; app_at=None
        if st=="approved":
            ad=pe+timedelta(days=20)
            app_at=datetime(ad.year,ad.month,ad.day,14,0,0)
            rk=vu.region.value if hasattr(vu.region,"value") else str(vu.region)
            apr=_app.get(rk,admin)
            app_by=apr.id if apr else admin.id
        return EmissionRecord(
            vendor_id=profile.id,submitted_by=vu.id,approved_by=app_by,
            category_id=cat,period_start=ps,period_end=pe,
            activity_value=act,activity_unit=unit,ef_id=ef.id,
            calculated_co2e=co2e,data_quality=q,input_method="manual",
            region=vu.region,status=st,is_ai_estimated=False,
            submitted_at=sub_at,approved_at=app_at,
        )

    # 36 months Apr 2022 – Mar 2025
    months=[]
    y,m=2022,4
    for _ in range(36):
        months.append((y,m)); m+=1
        if m>12: m=1; y+=1

    records=[]
    for yr,mo in months:
        ps=date(yr,mo,1); pe=_last(yr,mo)
        q="A" if yr>=2024 else "B"
        records.append(_make(p1,u1,1,ps,pe,_act(800.0, 0.06,yr,mo),"tonne",       ef_steel,   q,0))
        records.append(_make(p1,u1,1,ps,pe,_act(120.0, 0.04,yr,mo),"tonne",       ef_alum,    q,0))
        records.append(_make(p2,u2,4,ps,pe,_act(200000,0.04,yr,mo),"tonne-km",    ef_road,    q,1))
        records.append(_make(p3,u3,5,ps,pe,_act(65.0,  0.03,yr,mo),"tonne",       ef_landfill,q,2))
        records.append(_make(p4,u4,3,ps,pe,_act(75000, 0.02,yr,mo),"litres",      ef_diesel,  q,3))
        records.append(_make(p5,u5,2,ps,pe,_act(400.0, 0.05,yr,mo),"tonne",       ef_concrete,q,4))
        records.append(_make(p6,u6,6,ps,pe,_act(100000,0.07,yr,mo),"passenger-km",ef_flight,  q,5))
        records.append(_make(p7,u7,7,ps,pe,_act(140000,0.03,yr,mo),"vehicle-km",  ef_car,     q,6))

    # 4 rejected anomaly records (July 2024 ×10 activity)
    for vi,(profile,vu,cat,ef,base,unit,gr) in enumerate([
        (p1,u1,1,ef_steel,800.0,"tonne",0.06),
        (p2,u2,4,ef_road,200000,"tonne-km",0.04),
        (p3,u3,5,ef_landfill,65.0,"tonne",0.03),
        (p4,u4,3,ef_diesel,75000,"litres",0.02),
    ]):
        yr,mo=2024,7; ps=date(yr,mo,1); pe=_last(yr,mo)
        act=_act(base*10,gr,yr,mo); co2e=round((act*ef.factor_value)/1000,4)
        sd=pe+timedelta(days=3)
        records.append(EmissionRecord(
            vendor_id=profile.id,submitted_by=vu.id,category_id=cat,
            period_start=ps,period_end=pe,activity_value=act,activity_unit=unit,
            ef_id=ef.id,calculated_co2e=co2e,data_quality="C",input_method="manual",
            region=vu.region,status="rejected",is_ai_estimated=False,
            notes="Submitted with incorrect activity values",
            rejection_reason="Activity value appears inflated by ~10×. Please verify units and resubmit.",
            submitted_at=datetime(sd.year,sd.month,sd.day,9,0,0),
        ))

    # 1 pending high-priority record
    records.append(EmissionRecord(
        vendor_id=p1.id,submitted_by=u1.id,category_id=1,
        period_start=date(2025,1,1),period_end=date(2025,1,31),
        activity_value=1800.0,activity_unit="tonne",ef_id=ef_steel.id,
        calculated_co2e=round((1800.0*ef_steel.factor_value)/1000,4),
        data_quality="A",input_method="manual",region=u1.region,
        status="submitted",is_ai_estimated=False,
        notes="January 2025 steel procurement — urgent approval needed",
        submitted_at=datetime(2025,2,10,9,0,0),
    ))

    for r in records: db.add(r)
    db.commit()
    print(f"✅ Seeded {len(records)} emission records (36 months × 8 streams + extras)")


# ── Targets ───────────────────────────────────────────────────────────────────
def seed_targets(db):
    if db.query(EmissionTarget).count() > 0:
        return
    admin=db.query(User).filter(User.email=="admin@stratxg.com").first()
    if not admin: return
    for t in [
        dict(label="FY2022-23 Baseline",year=2022,target_co2e=38000.0,region=None),
        dict(label="FY2023-24 Target",  year=2023,target_co2e=36100.0,region=None),
        dict(label="FY2024-25 Target",  year=2024,target_co2e=34300.0,region=None),
        dict(label="North 2024 Target", year=2024,target_co2e=14000.0,region="north"),
        dict(label="South 2024 Target", year=2024,target_co2e=5500.0, region="south"),
        dict(label="West 2024 Target",  year=2024,target_co2e=8000.0, region="west"),
    ]:
        db.add(EmissionTarget(created_by=admin.id,**t))
    db.commit()
    print("✅ Seeded 6 emission targets")


# ── Entry Point ───────────────────────────────────────────────────────────────
def run_all_seeds(db: Session):
    force = os.getenv("FORCE_RESEED","false").lower() in ("true","1","yes")
    if force:
        _wipe(db)
    else:
        if db.query(User).count() > 0:
            print("ℹ️  Already seeded — set FORCE_RESEED=true to re-seed")
            return
    seed_admin(db)
    seed_emission_factors(db)
    seed_reporting_periods(db)
    seed_emission_records(db)
    seed_targets(db)
    print("✅ All seeds complete")

# Backward-compat alias
def seed_reporting_period(db): seed_reporting_periods(db)
