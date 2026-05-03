from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from serving.inference import (
    health_check,
    predict_anomaly,
    predict_forecast,
    predict_spend,
)


app = FastAPI(
    title="Scope 3 ML Service",
    description="Inference-only service for anomaly detection, forecasting, and spend estimation.",
    version="0.1.0",
)


class AnomalyInferenceRequest(BaseModel):
    category_id: int = Field(ge=1, le=15)
    activity_value: float = Field(gt=0)
    activity_unit: int
    ef_value: float = Field(gt=0)
    calculated_co2e: Optional[float] = None
    data_quality: int = Field(default=1, ge=0, le=2)
    region: int = Field(default=0, ge=0, le=4)


class ForecastInferenceRequest(BaseModel):
    sector: str
    history: list[float] = Field(min_length=12)


class SpendInferenceRequest(BaseModel):
    spend_inr: float = Field(gt=0)
    nic_4digit: int = Field(gt=0)
    region: str
    year: int = Field(default=2023, ge=2000, le=2100)


@app.get("/health")
def get_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ml-service",
        "models": health_check(),
    }


@app.post("/inference/anomaly")
def run_anomaly_inference(body: AnomalyInferenceRequest) -> dict[str, Any]:
    try:
        return predict_anomaly(body.model_dump(exclude_none=True))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Anomaly inference failed: {exc}") from exc


@app.post("/inference/forecast")
def run_forecast_inference(body: ForecastInferenceRequest) -> dict[str, Any]:
    try:
        return predict_forecast(body.sector, body.history)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Forecast inference failed: {exc}") from exc


@app.post("/inference/spend")
def run_spend_inference(body: SpendInferenceRequest) -> dict[str, Any]:
    try:
        return predict_spend(
            spend_inr=body.spend_inr,
            nic_4digit=body.nic_4digit,
            region=body.region,
            year=body.year,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Spend inference failed: {exc}") from exc
