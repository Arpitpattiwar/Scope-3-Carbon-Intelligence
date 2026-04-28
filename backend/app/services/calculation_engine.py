"""
Emission Calculation Engine
============================
Core formula: CO2e (tCO2e) = Activity Data × Emission Factor

Phase 1: Pure rule-based calculation with full traceability.
Phase 2: AI estimation engine plugs in via estimate_missing_data()
         without changing this module's interface.
"""

from typing import Optional, Dict, Any
from app.core.config import settings


# GHG Protocol Category names — single source of truth
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


def calculate_co2e(
    activity_value: float,
    ef_value: float,
    activity_unit: str,
    ef_unit: str,
) -> Dict[str, Any]:
    """
    Core calculation: CO2e = Activity × EF
    Returns result dict with full trace for audit.
    """
    if activity_value < 0:
        raise ValueError("Activity value cannot be negative")
    if ef_value <= 0:
        raise ValueError("Emission factor must be positive")

    # Convert to tCO2e (EF is in kgCO2e per unit → divide by 1000)
    raw_co2e_kg = activity_value * ef_value
    co2e_tonnes = raw_co2e_kg / 1000

    return {
        "calculated_co2e": round(co2e_tonnes, 6),
        "calculation_trace": {
            "formula": "CO2e (tCO2e) = Activity Data × Emission Factor / 1000",
            "activity_value": activity_value,
            "activity_unit": activity_unit,
            "ef_value": ef_value,
            "ef_unit": ef_unit,
            "raw_co2e_kg": round(raw_co2e_kg, 4),
            "co2e_tonnes": round(co2e_tonnes, 6),
            "steps": [
                f"Step 1: Activity = {activity_value} {activity_unit}",
                f"Step 2: EF = {ef_value} {ef_unit}",
                f"Step 3: Raw CO2e = {activity_value} × {ef_value} = {raw_co2e_kg:.4f} kgCO2e",
                f"Step 4: Convert to tonnes = {raw_co2e_kg:.4f} / 1000 = {co2e_tonnes:.6f} tCO2e",
            ],
        },
    }


def get_category_name(category_id: int) -> str:
    return SCOPE3_CATEGORIES.get(category_id, f"Category {category_id}")


def estimate_missing_data(
    category_id: int,
    available_data: Dict[str, Any],
    vendor_profile: Optional[Dict] = None,
) -> Optional[Dict[str, Any]]:
    """
    Phase 2 hook: AI estimation for missing primary data.

    In Phase 1: returns None (no estimation).
    In Phase 2: import and call the AI estimation service here.

    Returns:
        dict with keys: estimated_value, confidence_score, explanation,
                        model_used, inputs_used, methodology_reference
        or None if estimation not available/enabled.
    """
    if not settings.AI_ESTIMATION_ENABLED:
        return None

    # Phase 2 implementation:
    # from app.services.ai_estimation import AIEstimationService
    # service = AIEstimationService()
    # return service.estimate(category_id, available_data, vendor_profile)

    return None


def validate_activity_data(
    category_id: int,
    activity_value: float,
    activity_unit: str,
) -> Dict[str, Any]:
    """
    Basic validation + outlier detection.
    Returns {"valid": bool, "warnings": list, "errors": list}
    """
    warnings = []
    errors = []

    if activity_value <= 0:
        errors.append("Activity value must be greater than 0")

    # Category-specific sanity checks
    if category_id == 6 and activity_value > 1_000_000:
        warnings.append("Business travel distance seems unusually high (>1M km). Please verify.")

    if category_id == 1 and activity_value > 1_000_000_000:
        warnings.append("Spend value >1B — please verify units (should be INR).")

    return {
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
    }
