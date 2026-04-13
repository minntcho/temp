"""탄소배출량 계산/검증/키워드 분류 핵심 로직."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from sklearn.ensemble import IsolationForest

KEYWORD_ACTIVITY_MAP: dict[str, str] = {
    "전력": "electricity",
    "electric": "electricity",
    "kwh": "electricity",
    "디젤": "diesel",
    "diesel": "diesel",
    "경유": "diesel",
    "스팀": "steam",
    "steam": "steam",
    "천연가스": "natural_gas",
    "lng": "natural_gas",
    "natural gas": "natural_gas",
    "가스": "natural_gas",
}


def infer_activity_by_keywords(row: dict[str, Any], text_fields: list[str]) -> tuple[str, list[str]]:
    text = " ".join(str(row.get(field, "") or "") for field in text_fields).lower()
    matches: list[tuple[str, str]] = []
    for keyword, activity in KEYWORD_ACTIVITY_MAP.items():
        if keyword in text:
            matches.append((keyword, activity))
    if not matches:
        return "", []
    return matches[0][1], [kw for kw, _ in matches]


def enrich_keywords(records: list[dict[str, Any]], text_fields: list[str]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in records:
        out = dict(row)
        inferred, matched_keywords = infer_activity_by_keywords(row, text_fields)
        if not out.get("activity_type") and inferred:
            out["activity_type"] = inferred
            out["activity_inferred"] = True
        else:
            out["activity_inferred"] = False
        out["matched_keywords"] = matched_keywords
        enriched.append(out)
    return enriched


def validate_activity_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    required_cols = ["product_id", "activity_type", "amount", "unit"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    for col in missing_cols:
        issues.append({"type": "missing_column", "column": col})
    if missing_cols:
        return issues

    for idx, row in df.iterrows():
        if pd.isna(row["product_id"]) or str(row["product_id"]).strip() == "":
            issues.append({"type": "missing_value", "row": int(idx), "column": "product_id"})
        if pd.isna(row["activity_type"]) or str(row["activity_type"]).strip() == "":
            issues.append({"type": "missing_value", "row": int(idx), "column": "activity_type"})
        if pd.isna(row["amount"]):
            issues.append({"type": "missing_value", "row": int(idx), "column": "amount"})
        elif float(row["amount"]) < 0:
            issues.append({"type": "invalid_value", "row": int(idx), "column": "amount", "reason": "negative"})
        if pd.isna(row["unit"]) or str(row["unit"]).strip() == "":
            issues.append({"type": "missing_value", "row": int(idx), "column": "unit"})
    return issues


def calculate_emissions_df(activity_df: pd.DataFrame, factor_df: pd.DataFrame) -> pd.DataFrame:
    merged = activity_df.merge(factor_df, on=["activity_type", "unit"], how="left")
    merged["factor_missing"] = merged["emission_factor"].isna()
    merged["emission_factor"] = merged["emission_factor"].fillna(0)
    merged["emission_kgco2e"] = merged["amount"].astype(float) * merged["emission_factor"].astype(float)
    return merged


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["is_outlier"] = False
    result["outlier_score"] = 0.0
    if "amount" not in result.columns or len(result) < 5:
        return result
    model = IsolationForest(contamination=0.1, random_state=42)
    feature = result[["amount"]].astype(float)
    pred = model.fit_predict(feature)
    score = model.decision_function(feature)
    result["is_outlier"] = pred == -1
    result["outlier_score"] = score
    return result


def summarize_by_product(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("product_id", as_index=False)["emission_kgco2e"]
        .sum()
        .sort_values("emission_kgco2e", ascending=False)
        .rename(columns={"emission_kgco2e": "total_emission_kgco2e"})
    )


def build_template_excel() -> bytes:
    activity_template = pd.DataFrame(
        [
            {
                "date": "2026-01-10",
                "product_id": "PRD-001",
                "site_id": "SITE-001",
                "activity_type": "electricity",
                "amount": 1200,
                "unit": "kWh",
                "description": "1월 전력 사용량",
            }
        ]
    )
    factor_template = pd.DataFrame(
        [
            {"activity_type": "electricity", "unit": "kWh", "emission_factor": 0.45, "factor_unit": "kgCO2e/kWh"},
            {"activity_type": "diesel", "unit": "L", "emission_factor": 2.68, "factor_unit": "kgCO2e/L"},
            {"activity_type": "natural_gas", "unit": "Nm3", "emission_factor": 2.02, "factor_unit": "kgCO2e/Nm3"},
            {"activity_type": "steam", "unit": "ton", "emission_factor": 120.0, "factor_unit": "kgCO2e/ton"},
        ]
    )

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        activity_template.to_excel(writer, sheet_name="activity", index=False)
        factor_template.to_excel(writer, sheet_name="emission_factors", index=False)
    return buf.getvalue()


def analyze_payload(activities: list[dict[str, Any]], factors: list[dict[str, Any]], run_outlier_detection: bool = True) -> dict[str, Any]:
    activity_enriched = enrich_keywords(activities, ["description", "memo", "activity_name"])
    activity_df = pd.DataFrame(activity_enriched)
    factor_df = pd.DataFrame(factors)

    issues = validate_activity_df(activity_df)
    if issues:
        return {"status": "validation_failed", "issues": issues}

    estimated = calculate_emissions_df(activity_df, factor_df)
    if run_outlier_detection:
        estimated = detect_outliers(estimated)

    product_summary = summarize_by_product(estimated)

    return {
        "status": "ok",
        "records": estimated.to_dict(orient="records"),
        "product_summary": product_summary.to_dict(orient="records"),
        "validation_issues": issues,
    }
