"""
Database Seeder — Seeds demo data including realistic emission records.
"""
from sqlalchemy.orm import Session
from app.models.user import (
    User, EmissionFactor, ReportingPeriod, VendorProfile, EmissionRecord
)
from app.core.security import get_password_hash
from datetime import date, datetime


def seed_admin(db: Session):
    if db.query(User).filter(User.email == "admin@stratxg.com").first():
        return

    admin = User(email="admin@stratxg.com", full_name="Platform Admin",
                 role="admin", region="all",
                 password_hash=get_password_hash("Admin@1234"),
                 is_active=True, onboarding_complete=True)
    db.add(admin)

    manager = User(email="manager.north@stratxg.com",
                   full_name="North Region Manager", role="manager", region="north",
                   password_hash=get_password_hash("Manager@1234"),
                   is_active=True, onboarding_complete=True)
    db.add(manager)

    manager_south = User(email="manager.south@stratxg.com",
                         full_name="South Region Manager", role="manager", region="south",
                         password_hash=get_password_hash("Manager@1234"),
                         is_active=True, onboarding_complete=True)
    db.add(manager_south)

    auditor = User(email="auditor@stratxg.com", full_name="External Auditor",
                   role="auditor", password_hash=get_password_hash("Auditor@1234"),
                   is_active=True, onboarding_complete=True)
    db.add(auditor)

    # Demo vendors
    vendor1 = User(email="vendor@acmesupplies.com", full_name="Rahul Sharma",
                   role="vendor", region="north",
                   password_hash=get_password_hash("Vendor@1234"),
                   is_active=True, onboarding_complete=True)
    db.add(vendor1)
    db.flush()

    profile1 = VendorProfile(
        user_id=vendor1.id, company_name="Acme Supplies Pvt Ltd",
        trade_name="Acme", gst_number="27AABCA1234B1Z5", pan_number="AABCA1234B",
        state="Delhi", city="New Delhi", region="north", pin_code="110001",
        nic_code="46610", material_category=1,
        material_name="Industrial Raw Materials (Steel, Aluminium)",
        supply_frequency="monthly", avg_annual_volume=5000, volume_unit="tonnes",
        has_own_carbon_system=False, contact_name="Rahul Sharma",
        contact_designation="ESG Manager", contact_phone="+91 9876543210",
        onboarded_at=datetime(2024, 5, 1),
    )
    db.add(profile1)

    vendor2 = User(email="vendor@greentrans.com", full_name="Priya Menon",
                   role="vendor", region="south",
                   password_hash=get_password_hash("Vendor@1234"),
                   is_active=True, onboarding_complete=True)
    db.add(vendor2)
    db.flush()

    profile2 = VendorProfile(
        user_id=vendor2.id, company_name="GreenTrans Logistics",
        gst_number="33AADCG5678C1Z2", state="Tamil Nadu", city="Chennai",
        region="south", nic_code="49100", material_category=4,
        material_name="Road freight — diesel HGV",
        supply_frequency="weekly", avg_annual_volume=120000, volume_unit="tonne-km",
        has_own_carbon_system=True, contact_name="Priya Menon",
        contact_designation="Operations Head", contact_phone="+91 9123456789",
        onboarded_at=datetime(2024, 6, 1),
    )
    db.add(profile2)

    vendor3 = User(email="vendor@wastecare.com", full_name="Amit Patel",
                   role="vendor", region="north",
                   password_hash=get_password_hash("Vendor@1234"),
                   is_active=True, onboarding_complete=True)
    db.add(vendor3)
    db.flush()

    profile3 = VendorProfile(
        user_id=vendor3.id, company_name="WasteCare Solutions",
        gst_number="24AACFW9012D1Z3", state="Gujarat", city="Ahmedabad",
        region="north", nic_code="38110", material_category=5,
        material_name="Industrial waste disposal & recycling",
        supply_frequency="monthly", avg_annual_volume=800, volume_unit="tonnes",
        has_own_carbon_system=False, contact_name="Amit Patel",
        contact_designation="Director", contact_phone="+91 9988776655",
        onboarded_at=datetime(2024, 7, 1),
    )
    db.add(profile3)

    db.commit()
    print("✅ Seeded demo users and vendor profiles")
    return profile1, profile2, profile3


def seed_emission_factors(db: Session):
    if db.query(EmissionFactor).count() > 0:
        return

    factors = [
        # Cat 1 — Purchased Goods & Services
        dict(source="DEFRA", category_id=1, subcategory="Raw Materials",
             material_type="Steel", factor_value=1890, unit="kgCO2e/tonne",
             region="global", version_tag="DEFRA_2024_v1", valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=1, subcategory="Raw Materials",
             material_type="Aluminium", factor_value=6700, unit="kgCO2e/tonne",
             region="global", version_tag="DEFRA_2024_v1", valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=1, subcategory="Raw Materials",
             material_type="Plastic (general)", factor_value=3140, unit="kgCO2e/tonne",
             region="global", version_tag="DEFRA_2024_v1", valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=1, subcategory="Spend-based",
             material_type="Manufacturing (generic)", factor_value=0.43, unit="kgCO2e/INR",
             region="India", version_tag="DEFRA_2024_v1", valid_from=date(2024, 1, 1),
             notes="Spend-based estimate for Indian manufacturing sector"),
        # Cat 2 — Capital Goods
        dict(source="IPCC", category_id=2, subcategory="Machinery & Equipment",
             material_type="Industrial machinery", factor_value=2100, unit="kgCO2e/tonne",
             region="global", version_tag="IPCC_AR6_v1", valid_from=date(2023, 1, 1),
             source_url="https://www.ipcc.ch/assessment-report/ar6/"),
        dict(source="IPCC", category_id=2, subcategory="Buildings",
             material_type="Concrete structure", factor_value=410, unit="kgCO2e/tonne",
             region="global", version_tag="IPCC_AR6_v1", valid_from=date(2023, 1, 1)),
        # Cat 3 — Fuel & Energy
        dict(source="DEFRA", category_id=3, subcategory="Electricity T&D losses",
             material_type="Grid electricity India", factor_value=0.82, unit="kgCO2e/kWh",
             region="India", version_tag="CPCB_2023_v1", valid_from=date(2023, 1, 1),
             source_url="https://cpcb.nic.in/", notes="India national grid average"),
        dict(source="DEFRA", category_id=3, subcategory="Fuel upstream",
             material_type="Diesel (upstream)", factor_value=0.621, unit="kgCO2e/litre",
             region="global", version_tag="DEFRA_2024_v1", valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        # Cat 4 — Upstream Transport
        dict(source="DEFRA", category_id=4, subcategory="Road freight",
             material_type="HGV (diesel) - average laden", factor_value=0.112,
             unit="kgCO2e/tonne-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=4, subcategory="Rail freight",
             material_type="Rail freight (diesel)", factor_value=0.028,
             unit="kgCO2e/tonne-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=4, subcategory="Sea freight",
             material_type="Container ship (average)", factor_value=0.016,
             unit="kgCO2e/tonne-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=4, subcategory="Air freight",
             material_type="Air freight", factor_value=1.17,
             unit="kgCO2e/tonne-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        # Cat 5 — Waste
        dict(source="DEFRA", category_id=5, subcategory="Waste to landfill",
             material_type="Mixed waste - landfill", factor_value=467,
             unit="kgCO2e/tonne", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=5, subcategory="Incineration",
             material_type="Mixed waste - incineration", factor_value=210,
             unit="kgCO2e/tonne", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        dict(source="DEFRA", category_id=5, subcategory="Recycling",
             material_type="Mixed waste - recycled", factor_value=21,
             unit="kgCO2e/tonne", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        # Cat 6 — Business Travel
        dict(source="DEFRA", category_id=6, subcategory="Air travel",
             material_type="Domestic flights (India)", factor_value=0.255,
             unit="kgCO2e/passenger-km", region="India", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        dict(source="DEFRA", category_id=6, subcategory="Air travel",
             material_type="International flights (economy)", factor_value=0.195,
             unit="kgCO2e/passenger-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=6, subcategory="Rail travel",
             material_type="Indian Railways (average)", factor_value=0.041,
             unit="kgCO2e/passenger-km", region="India", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1), notes="Indian Railways grid mix"),
        dict(source="DEFRA", category_id=6, subcategory="Car travel",
             material_type="Petrol car (average)", factor_value=0.192,
             unit="kgCO2e/vehicle-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=6, subcategory="Hotel stays",
             material_type="Hotel night (India)", factor_value=31.2,
             unit="kgCO2e/night", region="India", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        # Cat 7 — Employee Commuting
        dict(source="DEFRA", category_id=7, subcategory="Commuting by car",
             material_type="Petrol car commute", factor_value=0.192,
             unit="kgCO2e/vehicle-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        dict(source="DEFRA", category_id=7, subcategory="Commuting by bus",
             material_type="Bus commute (India)", factor_value=0.089,
             unit="kgCO2e/passenger-km", region="India", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        dict(source="DEFRA", category_id=7, subcategory="Commuting by metro/rail",
             material_type="Metro (India)", factor_value=0.031,
             unit="kgCO2e/passenger-km", region="India", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        # Cat 8 — Downstream Transport
        dict(source="DEFRA", category_id=8, subcategory="Road freight",
             material_type="LCV (diesel) delivery", factor_value=0.245,
             unit="kgCO2e/tonne-km", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1),
             source_url="https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024"),
        # Cat 9
        dict(source="IPCC", category_id=9, subcategory="Industrial processing",
             material_type="Energy-intensive processing (average)", factor_value=0.82,
             unit="kgCO2e/kWh", region="India", version_tag="IPCC_AR6_v1",
             valid_from=date(2023, 1, 1)),
        # Cat 10
        dict(source="IPCC", category_id=10, subcategory="Electrical products",
             material_type="Consumer electronics (lifetime)", factor_value=150,
             unit="kgCO2e/unit", region="global", version_tag="IPCC_AR6_v1",
             valid_from=date(2023, 1, 1)),
        dict(source="IPCC", category_id=10, subcategory="Industrial products",
             material_type="Industrial equipment (lifetime)", factor_value=2400,
             unit="kgCO2e/unit", region="global", version_tag="IPCC_AR6_v1",
             valid_from=date(2023, 1, 1)),
        # Cat 11
        dict(source="DEFRA", category_id=11, subcategory="Electronic waste",
             material_type="E-waste landfill", factor_value=890,
             unit="kgCO2e/tonne", region="global", version_tag="DEFRA_2024_v1",
             valid_from=date(2024, 1, 1)),
        # Cat 12
        dict(source="DEFRA", category_id=12, subcategory="Office buildings",
             material_type="Office energy use (India)", factor_value=0.82,
             unit="kgCO2e/kWh", region="India", version_tag="CPCB_2023_v1",
             valid_from=date(2023, 1, 1)),
        # Cat 13
        dict(source="IPCC", category_id=13, subcategory="Revenue-based",
             material_type="Retail franchise (average)", factor_value=0.38,
             unit="kgCO2e/INR-revenue", region="India", version_tag="IPCC_AR6_v1",
             valid_from=date(2023, 1, 1),
             notes="Spend-based proxy for franchise emissions"),
        # Cat 14
        dict(source="IPCC", category_id=14, subcategory="Equity investments",
             material_type="Manufacturing sector (PCAF)", factor_value=0.52,
             unit="kgCO2e/INR-invested", region="India", version_tag="PCAF_2023_v1",
             valid_from=date(2023, 1, 1),
             notes="PCAF-aligned financial emissions intensity"),
        # Cat 15
        dict(source="IPCC", category_id=15, subcategory="Custom",
             material_type="Generic / industry-specific", factor_value=1.0,
             unit="kgCO2e/unit", region="global", version_tag="IPCC_AR6_v1",
             valid_from=date(2023, 1, 1),
             notes="Placeholder — replace with specific factor"),
    ]

    ef_objects = []
    for f in factors:
        ef = EmissionFactor(**f, is_active=True)
        db.add(ef)
        ef_objects.append(ef)

    db.commit()
    print(f"✅ Seeded {len(factors)} emission factors")
    return ef_objects


def seed_reporting_period(db: Session):
    if db.query(ReportingPeriod).count() > 0:
        return
    db.add(ReportingPeriod(label="FY2024-25", period_start=date(2024, 4, 1),
                           period_end=date(2025, 3, 31), is_locked=False))
    db.commit()
    print("✅ Seeded reporting period FY2024-25")


def seed_emission_records(db: Session):
    if db.query(EmissionRecord).count() > 0:
        return

    # Get vendor profiles
    v1 = db.query(VendorProfile).join(User).filter(
        User.email == "vendor@acmesupplies.com").first()
    v2 = db.query(VendorProfile).join(User).filter(
        User.email == "vendor@greentrans.com").first()
    v3 = db.query(VendorProfile).join(User).filter(
        User.email == "vendor@wastecare.com").first()

    u1 = db.query(User).filter(User.email == "vendor@acmesupplies.com").first()
    u2 = db.query(User).filter(User.email == "vendor@greentrans.com").first()
    u3 = db.query(User).filter(User.email == "vendor@wastecare.com").first()

    if not (v1 and v2 and v3 and u1 and u2 and u3):
        print("⚠️  Skipping emission records seed — vendor profiles not found")
        return

    # Get commonly used emission factors
    ef_steel = db.query(EmissionFactor).filter(
        EmissionFactor.material_type == "Steel").first()
    ef_road = db.query(EmissionFactor).filter(
        EmissionFactor.material_type == "HGV (diesel) - average laden").first()
    ef_landfill = db.query(EmissionFactor).filter(
        EmissionFactor.material_type == "Mixed waste - landfill").first()
    ef_recycle = db.query(EmissionFactor).filter(
        EmissionFactor.material_type == "Mixed waste - recycled").first()
    ef_aluminium = db.query(EmissionFactor).filter(
        EmissionFactor.material_type == "Aluminium").first()

    if not all([ef_steel, ef_road, ef_landfill, ef_recycle, ef_aluminium]):
        print("⚠️  Skipping emission records seed — emission factors not found")
        return

    def make_record(vendor_profile, submitted_by_user, category_id, period_start,
                    period_end, activity_value, activity_unit, ef, data_quality,
                    status="approved"):
        co2e = (activity_value * ef.factor_value) / 1000
        return EmissionRecord(
            vendor_id=vendor_profile.id,
            submitted_by=submitted_by_user.id,
            category_id=category_id,
            period_start=period_start,
            period_end=period_end,
            activity_value=activity_value,
            activity_unit=activity_unit,
            ef_id=ef.id,
            calculated_co2e=round(co2e, 4),
            data_quality=data_quality,
            input_method="manual",
            region=submitted_by_user.region,
            status=status,
            is_ai_estimated=False,
            submitted_at=datetime(2024, period_start.month + 1 if period_start.month < 12 else 1, 10),
        )

    records = [
        # Acme — Cat 1 Purchased Goods (steel) — Q1-Q4 FY24
        make_record(v1, u1, 1, date(2024, 4, 1),  date(2024, 6, 30),  1200, "tonne", ef_steel, "A"),
        make_record(v1, u1, 1, date(2024, 7, 1),  date(2024, 9, 30),  1350, "tonne", ef_steel, "A"),
        make_record(v1, u1, 1, date(2024, 10, 1), date(2024, 12, 31), 1100, "tonne", ef_steel, "B"),
        make_record(v1, u1, 1, date(2025, 1, 1),  date(2025, 3, 31),  1450, "tonne", ef_steel, "A"),
        # Acme — Cat 1 Aluminium
        make_record(v1, u1, 1, date(2024, 4, 1),  date(2024, 9, 30),  180,  "tonne", ef_aluminium, "B"),
        make_record(v1, u1, 1, date(2024, 10, 1), date(2025, 3, 31),  210,  "tonne", ef_aluminium, "B"),
        # GreenTrans — Cat 4 Transport — monthly
        make_record(v2, u2, 4, date(2024, 4, 1),  date(2024, 4, 30),  85000,  "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 5, 1),  date(2024, 5, 31),  92000,  "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 6, 1),  date(2024, 6, 30),  78000,  "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 7, 1),  date(2024, 7, 31),  105000, "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 8, 1),  date(2024, 8, 31),  98000,  "tonne-km", ef_road, "B"),
        make_record(v2, u2, 4, date(2024, 9, 1),  date(2024, 9, 30),  88000,  "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 10, 1), date(2024, 10, 31), 110000, "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 11, 1), date(2024, 11, 30), 95000,  "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2024, 12, 1), date(2024, 12, 31), 102000, "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2025, 1, 1),  date(2025, 1, 31),  89000,  "tonne-km", ef_road, "B"),
        make_record(v2, u2, 4, date(2025, 2, 1),  date(2025, 2, 28),  76000,  "tonne-km", ef_road, "A"),
        make_record(v2, u2, 4, date(2025, 3, 1),  date(2025, 3, 31),  93000,  "tonne-km", ef_road, "A"),
        # WasteCare — Cat 5 Waste — quarterly
        make_record(v3, u3, 5, date(2024, 4, 1),  date(2024, 6, 30),  185, "tonne", ef_landfill, "B"),
        make_record(v3, u3, 5, date(2024, 7, 1),  date(2024, 9, 30),  210, "tonne", ef_landfill, "B"),
        make_record(v3, u3, 5, date(2024, 10, 1), date(2024, 12, 31), 195, "tonne", ef_landfill, "A"),
        make_record(v3, u3, 5, date(2025, 1, 1),  date(2025, 3, 31),  220, "tonne", ef_landfill, "A"),
        make_record(v3, u3, 5, date(2024, 4, 1),  date(2024, 9, 30),  95,  "tonne", ef_recycle,  "A"),
        make_record(v3, u3, 5, date(2024, 10, 1), date(2025, 3, 31),  115, "tonne", ef_recycle,  "A"),
        # One pending record for demo
        make_record(v1, u1, 1, date(2025, 4, 1), date(2025, 6, 30), 1300, "tonne",
                    ef_steel, "B", status="submitted"),
    ]

    for r in records:
        db.add(r)

    db.commit()
    print(f"✅ Seeded {len(records)} emission records")


def run_all_seeds(db: Session):
    seed_admin(db)
    seed_emission_factors(db)
    seed_reporting_period(db)
    seed_emission_records(db)
    print("✅ All seeds complete")
