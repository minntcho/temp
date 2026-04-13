"""FastAPI 기반 ESG 탄소배출량 분석 서버."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from carbon_core import analyze_payload, build_template_excel, enrich_keywords


class ActivityRecord(BaseModel):
    date: str | None = None
    product_id: str
    site_id: str | None = None
    activity_type: str | None = None
    amount: float
    unit: str
    description: str | None = None


class FactorRecord(BaseModel):
    activity_type: str
    unit: str
    emission_factor: float
    factor_unit: str = "kgCO2e/unit"


class EmissionRequest(BaseModel):
    activities: list[ActivityRecord]
    factors: list[FactorRecord]
    run_outlier_detection: bool = True


class KeywordRequest(BaseModel):
    records: list[dict[str, Any]] = Field(default_factory=list)
    text_fields: list[str] = Field(default_factory=lambda: ["description", "memo", "activity_name"])


app = FastAPI(title="ESG Carbon Management API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/keywords/classify")
def classify_keywords(req: KeywordRequest) -> dict[str, Any]:
    return {"records": enrich_keywords(req.records, req.text_fields)}


@app.post("/v1/emissions/calculate")
def calculate_emissions(req: EmissionRequest) -> dict[str, Any]:
    return analyze_payload(
        activities=[r.model_dump() for r in req.activities],
        factors=[r.model_dump() for r in req.factors],
        run_outlier_detection=req.run_outlier_detection,
    )


@app.get("/v1/excel/template")
def download_template() -> StreamingResponse:
    payload = build_template_excel()
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=esg_template.xlsx"},
    )


@app.post("/v1/excel/analyze")
async def analyze_excel(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Only xlsx/xlsm files are supported")

    content = await file.read()
    with BytesIO(content) as buf:
        activity_df = pd.read_excel(buf, sheet_name="activity")
        buf.seek(0)
        factor_df = pd.read_excel(buf, sheet_name="emission_factors")

    return analyze_payload(
        activities=activity_df.to_dict(orient="records"),
        factors=factor_df.to_dict(orient="records"),
        run_outlier_detection=True,
    )
