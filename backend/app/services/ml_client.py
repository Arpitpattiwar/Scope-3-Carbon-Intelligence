from typing import Any

import httpx

from app.core.config import settings


ANOMALY_SUPPORTED_CATEGORIES = {1, 3, 4, 5, 6, 7}

_ACTIVITY_UNIT_CODES = {
    "tonne": 0,
    "tonnes": 0,
    "ton": 0,
    "tons": 0,
    "tonne-km": 1,
    "tonne km": 1,
    "pass-km": 2,
    "passenger-km": 2,
    "passenger km": 2,
    "vehicle-km": 2,
    "vehicle km": 2,
    "kwh": 3,
    "litre": 4,
    "liter": 4,
    "l": 4,
    "inr": 5,
    "kg": 6,
    "kilogram": 6,
    "kilograms": 6,
    "km": 7,
}

_DATA_QUALITY_CODES = {
    "a": 0,
    "b": 1,
    "c": 2,
}

_REGION_CODES = {
    "north": 0,
    "south": 1,
    "east": 2,
    "west": 3,
    "central": 4,
    "all": 0,
}


class MLServiceError(RuntimeError):
    """Raised when the backend cannot complete a request against the ML service."""


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _normalise_activity_unit(activity_unit: Any) -> int:
    key = str(_enum_value(activity_unit)).strip().lower()
    if key not in _ACTIVITY_UNIT_CODES:
        raise ValueError(f"Unsupported activity unit for anomaly scoring: {activity_unit}")
    return _ACTIVITY_UNIT_CODES[key]


def _normalise_data_quality(data_quality: Any) -> int:
    if isinstance(data_quality, int):
        if data_quality in (0, 1, 2):
            return data_quality
        raise ValueError(f"Unsupported data quality for anomaly scoring: {data_quality}")
    key = str(_enum_value(data_quality)).strip().lower()
    return _DATA_QUALITY_CODES.get(key, 1)


def _normalise_region(region: Any) -> int:
    if isinstance(region, int):
        if 0 <= region <= 4:
            return region
        raise ValueError(f"Unsupported region code for anomaly scoring: {region}")
    key = str(_enum_value(region)).strip().lower()
    return _REGION_CODES.get(key, 0)


def _request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{settings.ml_service_base_url}{path}"
    try:
        with httpx.Client(timeout=settings.ML_SERVICE_TIMEOUT_SECONDS) as client:
            response = client.request(method, url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        raise MLServiceError(f"ML service returned {exc.response.status_code}: {detail}") from exc
    except httpx.RequestError as exc:
        raise MLServiceError(f"Unable to reach ML service at {url}: {exc}") from exc


def get_ml_health() -> dict[str, Any]:
    return _request_json("GET", "/health")


def build_anomaly_payload(
    *,
    category_id: int,
    activity_value: float,
    activity_unit: Any,
    ef_value: float,
    calculated_co2e: float,
    data_quality: Any,
    region: Any,
) -> dict[str, Any]:
    if category_id not in ANOMALY_SUPPORTED_CATEGORIES:
        raise ValueError(f"Category {category_id} is not supported by the anomaly model yet")

    return {
        "category_id": category_id,
        "activity_value": float(activity_value),
        "activity_unit": _normalise_activity_unit(activity_unit),
        "ef_value": float(ef_value),
        "calculated_co2e": float(calculated_co2e),
        "data_quality": _normalise_data_quality(data_quality),
        "region": _normalise_region(region),
    }


def score_anomaly(record: dict[str, Any]) -> dict[str, Any]:
    return _request_json("POST", "/inference/anomaly", record)


def estimate_spend(
    *,
    spend_inr: float,
    nic_4digit: int,
    region: str,
    year: int,
) -> dict[str, Any]:
    return _request_json(
        "POST",
        "/inference/spend",
        {
            "spend_inr": float(spend_inr),
            "nic_4digit": int(nic_4digit),
            "region": str(region),
            "year": int(year),
        },
    )


def forecast_emissions(*, sector: str, history: list[float]) -> dict[str, Any]:
    return _request_json(
        "POST",
        "/inference/forecast",
        {
            "sector": sector,
            "history": history,
        },
    )
