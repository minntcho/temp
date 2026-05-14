"""기초 ESG 탄소배출량 파이프라인 뼈대.

기능
1) 가상의 엑셀 데이터 생성
2) 엑셀 입력 데이터 로드
3) 전처리(preprocess)
4) 간단한 데이터 마이닝(mining)
5) 탄소배출량 산정(estimation)

실행 예시
---------
# 1) 샘플 파일 생성
python esg_excel_skeleton.py --generate --excel-path ./mock_esg_data.xlsx

# 2) 파이프라인 실행
python esg_excel_skeleton.py --excel-path ./mock_esg_data.xlsx
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class PipelineResult:
    activity_raw: pd.DataFrame
    activity_clean: pd.DataFrame
    emission_factors: pd.DataFrame
    estimated: pd.DataFrame
    monthly_summary: pd.DataFrame
    anomalies: pd.DataFrame


def create_mock_excel(excel_path: Path) -> None:
    """가상 ESG 데이터(2개 시트)를 가진 엑셀 파일을 생성한다."""
    activity = pd.DataFrame(
        [
            ["2026-01-10", "A-100", "electricity", "kWh", 1200],
            ["2026-01-11", "A-100", "diesel", "L", 85],
            ["2026-01-15", "B-200", "electricity", "kWh", 980],
            ["2026-02-02", "B-200", "diesel", "L", 75],
            ["2026-02-10", "C-300", "electricity", "kWh", 3000],  # 의도적 이상치
            ["2026-02-15", "C-300", "diesel", "L", 50],
            ["2026-03-01", "A-100", "electricity", "kWh", 1100],
            ["2026-03-12", "B-200", "diesel", "L", None],
        ],
        columns=["date", "product_id", "activity_type", "unit", "amount"],
    )

    factors = pd.DataFrame(
        [
            ["electricity", "kWh", 0.00045, "kgCO2e/kWh"],
            ["diesel", "L", 2.68000, "kgCO2e/L"],
        ],
        columns=["activity_type", "unit", "emission_factor", "factor_unit"],
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        activity.to_excel(writer, sheet_name="activity", index=False)
        factors.to_excel(writer, sheet_name="emission_factors", index=False)



def load_excel(excel_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """엑셀의 activity / emission_factors 시트를 로드한다."""
    activity = pd.read_excel(excel_path, sheet_name="activity")
    factors = pd.read_excel(excel_path, sheet_name="emission_factors")
    return activity, factors



def preprocess_activity(activity: pd.DataFrame) -> pd.DataFrame:
    """결측/형식/중복 등 기본 전처리를 수행한다."""
    df = activity.copy()

    # 날짜/수치형 정규화
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # 필수값 결측 제거
    df = df.dropna(subset=["date", "product_id", "activity_type", "unit"]).copy()

    # amount 결측은 0으로 보정 (정책에 따라 변경 가능)
    df["amount"] = df["amount"].fillna(0)

    # 중복 제거
    df = df.drop_duplicates()

    return df



def estimate_emissions(activity_clean: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """활동량과 배출계수를 조인하여 배출량(kgCO2e)을 계산한다."""
    merged = activity_clean.merge(
        factors,
        on=["activity_type", "unit"],
        how="left",
    )

    # 계수 미매핑은 0 처리 + 플래그 지정
    merged["factor_missing"] = merged["emission_factor"].isna()
    merged["emission_factor"] = merged["emission_factor"].fillna(0)

    merged["emission_kgco2e"] = merged["amount"] * merged["emission_factor"]
    merged["month"] = merged["date"].dt.to_period("M").astype(str)

    return merged



def mine_data(estimated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """간단한 마이닝 결과(월별 합계, 이상치 탐지)를 반환한다."""
    # 월/제품별 배출량 요약
    monthly_summary = (
        estimated.groupby(["month", "product_id"], as_index=False)["emission_kgco2e"].sum()
        .sort_values(["month", "product_id"])
    )

    # activity_type별 amount 기준 IQR 이상치 탐지(아주 기초)
    rows = []
    for activity_type, group in estimated.groupby("activity_type"):
        q1 = group["amount"].quantile(0.25)
        q3 = group["amount"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        flagged = group[(group["amount"] < lower) | (group["amount"] > upper)].copy()
        if not flagged.empty:
            flagged["outlier_rule"] = f"IQR({activity_type}): amount<{lower:.2f} or >{upper:.2f}"
            rows.append(flagged)

    anomalies = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=list(estimated.columns) + ["outlier_rule"])

    return monthly_summary, anomalies



def run_pipeline(excel_path: Path) -> PipelineResult:
    activity_raw, factors = load_excel(excel_path)
    activity_clean = preprocess_activity(activity_raw)
    estimated = estimate_emissions(activity_clean, factors)
    monthly_summary, anomalies = mine_data(estimated)

    return PipelineResult(
        activity_raw=activity_raw,
        activity_clean=activity_clean,
        emission_factors=factors,
        estimated=estimated,
        monthly_summary=monthly_summary,
        anomalies=anomalies,
    )



def main() -> None:
    parser = argparse.ArgumentParser(description="기초 ESG 엑셀 파이프라인")
    parser.add_argument("--excel-path", type=Path, default=Path("mock_esg_data.xlsx"))
    parser.add_argument("--generate", action="store_true", help="가상 엑셀 파일 생성")
    args = parser.parse_args()

    if args.generate:
        create_mock_excel(args.excel_path)
        print(f"[OK] Mock excel created: {args.excel_path}")
        return

    result = run_pipeline(args.excel_path)

    print("\n=== [1] Raw rows ===")
    print(len(result.activity_raw))

    print("\n=== [2] Cleaned data ===")
    print(result.activity_clean.head().to_string(index=False))

    print("\n=== [3] Estimated emissions ===")
    print(
        result.estimated[
            ["date", "product_id", "activity_type", "amount", "emission_factor", "emission_kgco2e", "factor_missing"]
        ].to_string(index=False)
    )

    print("\n=== [4] Monthly summary ===")
    print(result.monthly_summary.to_string(index=False))

    print("\n=== [5] Anomalies ===")
    if result.anomalies.empty:
        print("No anomalies detected")
    else:
        print(result.anomalies[["date", "product_id", "activity_type", "amount", "outlier_rule"]].to_string(index=False))


if __name__ == "__main__":
    main()
