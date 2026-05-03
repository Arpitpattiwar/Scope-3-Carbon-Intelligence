"""
Emission Calculation Engine — v8
=================================
Core: CO2e (tCO2e) = Activity Data x Emission Factor / 1000

New in v8:
  - Unit normalisation (kg→tonne, g→tonne, kWh→MWh conversions)
  - Unit compatibility check (EF denominator vs activity unit)
  - Parametric activity calculation per Scope 3 category
"""

from typing import Optional, Dict, Any, List, Tuple
from app.core.config import settings

SCOPE3_CATEGORIES = {
    1: "Purchased Goods & Services",
    2: "Capital Goods",
    3: "Fuel & Energy Related Activities",
    4: "Upstream Transport & Distribution",
    5: "Waste Generated in Operations",
    6: "Business Travel",
    7: "Employee Commuting",
    8: "Downstream Transport & Distribution",
    9: "Processing of Sold Products",
    10: "Use of Sold Products",
    11: "End-of-Life Treatment of Sold Products",
    12: "Leased Assets",
    13: "Franchises",
    14: "Investments",
    15: "Other (Custom)",
}

# ── Unit normalisation ────────────────────────────────────────────────────────
# Maps input unit → (canonical unit, multiplier)
# activity_value_canonical = activity_value * multiplier
UNIT_CONVERSIONS: Dict[str, Tuple[str, float]] = {
    # Mass
    "g":         ("tonne", 1e-6),
    "gram":      ("tonne", 1e-6),
    "kg":        ("tonne", 0.001),
    "kilogram":  ("tonne", 0.001),
    "tonne":     ("tonne", 1.0),
    "tonnes":    ("tonne", 1.0),
    "ton":       ("tonne", 1.0),
    "mt":        ("tonne", 1.0),
    # Energy
    "wh":        ("kwh",   0.001),
    "kwh":       ("kwh",   1.0),
    "kilowatt-hour": ("kwh", 1.0),
    "mwh":       ("kwh",   1000.0),
    "megawatt-hour": ("kwh", 1000.0),
    "gj":        ("kwh",   277.778),
    # Volume (liquid)
    "ml":        ("litre", 0.001),
    "litre":     ("litre", 1.0),
    "litres":    ("litre", 1.0),
    "liter":     ("litre", 1.0),
    "l":         ("litre", 1.0),
    "kl":        ("litre", 1000.0),
    "kl (kilolitres)": ("litre", 1000.0),
    "kilolitre": ("litre", 1000.0),
    # Distance / composite
    "km":               ("km",          1.0),
    "kilometre":        ("km",          1.0),
    "kilometer":        ("km",          1.0),
    "tonne-km":         ("tonne-km",    1.0),
    "passenger-km":     ("passenger-km",1.0),
    "vehicle-km":       ("vehicle-km",  1.0),
    # Nights
    "night":     ("night", 1.0),
    "nights":    ("night", 1.0),
    # Spend
    "inr (spend-based)": ("inr", 1.0),
    "inr (invested)":    ("inr", 1.0),
    "inr":               ("inr", 1.0),
    "usd (spend-based)": ("usd", 1.0),
    "usd":               ("usd", 1.0),
    # Count
    "units":     ("unit",  1.0),
    "unit":      ("unit",  1.0),
    "pieces":    ("unit",  1.0),
}

# EF unit denominator → canonical unit (extract denominator from "kgCO2e/X")
EF_UNIT_DENOMINATORS: Dict[str, str] = {
    "kgco2e/tonne":        "tonne",
    "kgco2e/kg":           "tonne",   # EF in per-kg, activity must be in kg→tonne
    "kgco2e/kwh":          "kwh",
    "kgco2e/litre":        "litre",
    "kgco2e/tonne-km":     "tonne-km",
    "kgco2e/passenger-km": "passenger-km",
    "kgco2e/vehicle-km":   "vehicle-km",
    "kgco2e/night":        "night",
    "kgco2e/unit":         "unit",
    "kgco2e/inr":          "inr",
    "kgco2e/inr-revenue":  "inr",
    "kgco2e/inr-invested": "inr",
}

# Compatible canonical unit pairs (activity_canonical → set of compatible EF denominators)
COMPATIBLE_UNITS: Dict[str, set] = {
    "tonne":        {"tonne"},
    "kwh":          {"kwh"},
    "litre":        {"litre"},
    "tonne-km":     {"tonne-km"},
    "passenger-km": {"passenger-km"},
    "vehicle-km":   {"vehicle-km"},
    "night":        {"night"},
    "unit":         {"unit"},
    "inr":          {"inr"},
    "km":           {"km"},
}


def normalise_unit(value: float, unit: str) -> Tuple[float, str]:
    """Convert value+unit to canonical form. Returns (normalised_value, canonical_unit)."""
    key = unit.lower().strip()
    if key in UNIT_CONVERSIONS:
        canon_unit, mult = UNIT_CONVERSIONS[key]
        return value * mult, canon_unit
    return value, key   # unknown unit — pass through unchanged


def check_unit_compatibility(activity_unit: str, ef_unit: str) -> Dict[str, Any]:
    """
    Check whether activity_unit is compatible with the EF denominator.
    Returns {compatible: bool, warning: str|None, suggestion: str|None}.
    """
    _, act_canon = normalise_unit(1.0, activity_unit)
    ef_key = ef_unit.lower().strip()
    ef_denom = EF_UNIT_DENOMINATORS.get(ef_key)

    if ef_denom is None:
        # Unknown EF unit format — can't check, pass through
        return {"compatible": True, "warning": None, "suggestion": None}

    compatible_set = COMPATIBLE_UNITS.get(act_canon, {act_canon})
    if ef_denom in compatible_set or act_canon == ef_denom:
        return {"compatible": True, "warning": None, "suggestion": None}

    return {
        "compatible": False,
        "warning": (
            f"Unit mismatch: activity is in '{activity_unit}' "
            f"(canonical: {act_canon}) but emission factor expects '{ef_denom}'. "
            "CO₂e may be miscalculated."
        ),
        "suggestion": f"Convert your activity value to {ef_denom} before submitting.",
    }


# ── Parametric calculation ────────────────────────────────────────────────────

PARAMETRIC_SCHEMAS: Dict[int, Dict] = {
    1: {
        "label": "Purchased Goods & Services",
        "fields": [
            {"key": "quantity",      "label": "Quantity",      "unit_key": "quantity_unit",
             "units": ["tonnes", "kg"], "placeholder": "e.g. 500"},
            {"key": "quantity_unit", "label": "Unit",          "type": "select",
             "options": ["tonnes", "kg"]},
        ],
        "formula": "quantity in tonnes",
        "output_unit": "tonne",
    },
    4: {
        "label": "Upstream Transport & Distribution",
        "fields": [
            {"key": "distance_km",     "label": "Total distance (km)",
             "placeholder": "e.g. 1200", "help": "One-way distance per shipment × number of shipments"},
            {"key": "weight_tonnes",   "label": "Shipment weight (tonnes)",
             "placeholder": "e.g. 25",  "help": "Total weight of goods transported"},
        ],
        "formula": "distance_km × weight_tonnes",
        "output_unit": "tonne-km",
    },
    5: {
        "label": "Waste Generated in Operations",
        "fields": [
            {"key": "landfill_tonnes",  "label": "Landfill waste (tonnes)",   "placeholder": "e.g. 10"},
            {"key": "incinerate_tonnes","label": "Incinerated waste (tonnes)", "placeholder": "e.g. 5"},
            {"key": "recycle_tonnes",   "label": "Recycled waste (tonnes)",    "placeholder": "e.g. 3"},
        ],
        "formula": "total waste = landfill + incinerated + recycled",
        "output_unit": "tonne",
        "note": "Submit separate records per disposal method for accurate EF matching.",
    },
    6: {
        "label": "Business Travel",
        "fields": [
            {"key": "trips",          "label": "Number of trips",          "placeholder": "e.g. 12"},
            {"key": "avg_distance_km","label": "Average distance per trip (km)", "placeholder": "e.g. 850"},
            {"key": "passengers",     "label": "Passengers per trip",      "placeholder": "e.g. 1"},
        ],
        "formula": "trips × avg_distance_km × passengers",
        "output_unit": "passenger-km",
    },
    7: {
        "label": "Employee Commuting",
        "fields": [
            {"key": "employees",     "label": "Number of employees commuting", "placeholder": "e.g. 200"},
            {"key": "avg_distance_km","label": "Average one-way distance (km)", "placeholder": "e.g. 15"},
            {"key": "working_days",  "label": "Working days in period",         "placeholder": "e.g. 66"},
            {"key": "wfh_pct",       "label": "Work-from-home % (0–100)",       "placeholder": "e.g. 30",
             "help": "Enter 0 if no WFH"},
        ],
        "formula": "employees × avg_distance_km × 2 × working_days × (1 - wfh_pct/100)",
        "output_unit": "vehicle-km",
    },
    8: {
        "label": "Downstream Transport & Distribution",
        "fields": [
            {"key": "distance_km",   "label": "Total distance (km)",       "placeholder": "e.g. 800"},
            {"key": "weight_tonnes", "label": "Shipment weight (tonnes)",   "placeholder": "e.g. 10"},
        ],
        "formula": "distance_km × weight_tonnes",
        "output_unit": "tonne-km",
    },
    3: {
        "label": "Fuel & Energy (not in S1/S2)",
        "fields": [
            {"key": "volume_litres", "label": "Fuel volume consumed (litres)",
             "placeholder": "e.g. 5000", "help": "Total fuel consumed in upstream operations"},
        ],
        "formula": "volume_litres (direct)",
        "output_unit": "litre",
    },
}


def calculate_parametric(category_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate activity_value from raw measurement parameters.
    Returns {activity_value, activity_unit, formula_used, steps}.
    """
    if category_id not in PARAMETRIC_SCHEMAS:
        raise ValueError(
            f"Parametric entry not supported for Category {category_id}. "
            "Use direct entry mode."
        )
    schema = PARAMETRIC_SCHEMAS[category_id]
    steps  = []

    def _get(key, default=0.0):
        return float(params.get(key) or default)

    if category_id == 1:
        q    = _get("quantity")
        unit = params.get("quantity_unit", "tonnes").lower().strip()
        if unit == "kg":
            q_tonnes = q / 1000
            steps.append(f"Convert: {q} kg ÷ 1000 = {q_tonnes:.4f} tonnes")
        else:
            q_tonnes = q
            steps.append(f"Quantity: {q} tonnes")
        return {"activity_value": round(q_tonnes, 4), "activity_unit": "tonne",
                "formula_used": schema["formula"], "steps": steps}

    if category_id in (4, 8):
        d = _get("distance_km"); w = _get("weight_tonnes")
        result = d * w
        steps += [f"Distance: {d} km", f"Weight: {w} tonnes",
                  f"Tonne-km: {d} × {w} = {result:.2f}"]
        return {"activity_value": round(result, 4), "activity_unit": "tonne-km",
                "formula_used": schema["formula"], "steps": steps}

    if category_id == 5:
        l = _get("landfill_tonnes"); i = _get("incinerate_tonnes"); r = _get("recycle_tonnes")
        total = l + i + r
        steps += [f"Landfill: {l}t  Incineration: {i}t  Recycled: {r}t",
                  f"Total: {l}+{i}+{r} = {total:.4f} tonnes"]
        return {"activity_value": round(total, 4), "activity_unit": "tonne",
                "formula_used": schema["formula"], "steps": steps}

    if category_id == 6:
        t = _get("trips"); d = _get("avg_distance_km"); p = _get("passengers", 1)
        result = t * d * p
        steps += [f"Trips: {t}", f"Avg distance: {d} km",
                  f"Passengers: {p}", f"Pax-km: {t}×{d}×{p} = {result:.2f}"]
        return {"activity_value": round(result, 4), "activity_unit": "passenger-km",
                "formula_used": schema["formula"], "steps": steps}

    if category_id == 7:
        e = _get("employees"); d = _get("avg_distance_km")
        wd = _get("working_days"); wfh = _get("wfh_pct")
        wfh_factor = 1 - (wfh / 100)
        result = e * d * 2 * wd * wfh_factor
        steps += [f"Employees: {e}  Distance one-way: {d} km",
                  f"Working days: {wd}  WFH factor: {wfh_factor:.2f}",
                  f"Veh-km: {e}×{d}×2×{wd}×{wfh_factor:.2f} = {result:.2f}"]
        return {"activity_value": round(result, 4), "activity_unit": "vehicle-km",
                "formula_used": schema["formula"], "steps": steps}

    if category_id == 3:
        v = _get("volume_litres")
        steps.append(f"Volume: {v} litres")
        return {"activity_value": round(v, 4), "activity_unit": "litre",
                "formula_used": schema["formula"], "steps": steps}

    raise ValueError(f"Parametric logic not implemented for category {category_id}")


# ── Core calculation ──────────────────────────────────────────────────────────

def calculate_co2e(
    activity_value: float,
    ef_value: float,
    activity_unit: str,
    ef_unit: str,
    auto_convert: bool = True,
) -> Dict[str, Any]:
    if activity_value < 0:
        raise ValueError("Activity value cannot be negative")
    if ef_value <= 0:
        raise ValueError("Emission factor must be positive")

    unit_check = check_unit_compatibility(activity_unit, ef_unit)
    steps = []

    # Normalise unit if auto_convert is on
    if auto_convert:
        norm_value, norm_unit = normalise_unit(activity_value, activity_unit)
        if norm_value != activity_value:
            steps.append(
                f"Unit conversion: {activity_value} {activity_unit} "
                f"→ {norm_value:.6g} {norm_unit}"
            )
    else:
        norm_value = activity_value
        norm_unit  = activity_unit

    raw_co2e_kg = norm_value * ef_value
    co2e_tonnes = raw_co2e_kg / 1000

    steps += [
        f"Step 1: Activity = {activity_value} {activity_unit}"
        + (f" → {norm_value:.6g} {norm_unit}" if norm_value != activity_value else ""),
        f"Step 2: EF = {ef_value} {ef_unit}",
        f"Step 3: Raw CO₂e = {norm_value:.6g} × {ef_value} = {raw_co2e_kg:.4f} kgCO₂e",
        f"Step 4: Convert to tonnes = {raw_co2e_kg:.4f} / 1000 = {co2e_tonnes:.6f} tCO₂e",
    ]

    return {
        "calculated_co2e": round(co2e_tonnes, 6),
        "unit_check": unit_check,
        "calculation_trace": {
            "formula": "CO₂e (tCO₂e) = Activity Data × Emission Factor / 1000",
            "activity_value":     activity_value,
            "activity_unit":      activity_unit,
            "normalised_value":   norm_value,
            "normalised_unit":    norm_unit,
            "ef_value":           ef_value,
            "ef_unit":            ef_unit,
            "raw_co2e_kg":        round(raw_co2e_kg, 4),
            "co2e_tonnes":        round(co2e_tonnes, 6),
            "unit_warning":       unit_check.get("warning"),
            "steps":              steps,
        },
    }


def get_category_name(category_id: int) -> str:
    return SCOPE3_CATEGORIES.get(category_id, f"Category {category_id}")


def estimate_missing_data(
    category_id: int,
    available_data: Dict[str, Any],
    vendor_profile: Optional[Dict] = None,
) -> Optional[Dict[str, Any]]:
    if not settings.AI_ESTIMATION_ENABLED:
        return None
    from app.services.ai_estimation import estimate_spend_based_emissions
    return estimate_spend_based_emissions(category_id, available_data, vendor_profile)


def validate_activity_data(
    category_id: int,
    activity_value: float,
    activity_unit: str,
) -> Dict[str, Any]:
    warnings = []
    errors   = []
    if activity_value <= 0:
        errors.append("Activity value must be greater than 0")
    if category_id == 6 and activity_value > 1_000_000:
        warnings.append("Business travel >1M km — please verify units.")
    if category_id == 1 and activity_value > 1_000_000_000:
        warnings.append("Spend >1B INR — please verify units.")
    return {"valid": len(errors) == 0, "warnings": warnings, "errors": errors}


def get_parametric_schema(category_id: int) -> Optional[Dict]:
    """Return the parametric entry schema for a category, or None if not supported."""
    return PARAMETRIC_SCHEMAS.get(category_id)
