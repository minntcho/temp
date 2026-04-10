# temp

기초 ESG 데이터 파이프라인 실험용 저장소입니다.

## 포함 파일
- `generate_esg_dummy_data.py`: boundary-aware 원시/표준화/배출량 계산 계층을 포함한 ESG 더미 데이터 생성기
- `esg_excel_skeleton.py`: 엑셀 기반 전처리/산정/마이닝 뼈대 코드
- `requirements.txt`: 엑셀 파이프라인 실행용 의존성

## ESG 더미 데이터 생성 (권장 시작점)
```bash
python generate_esg_dummy_data.py \
  --out-dir ./dummy_esg \
  --rows 1000 \
  --num-entities 5 \
  --num-sites 20 \
  --num-products 60 \
  --num-suppliers 30 \
  --anomaly-rate 0.03 \
  --seed 42
```

생성 결과:
- `dummy_esg/legal_entities.csv`
- `dummy_esg/sites.csv`
- `dummy_esg/products.csv`
- `dummy_esg/suppliers.csv`
- `dummy_esg/reporting_calendar.csv`
- `dummy_esg/unit_conversions.csv`
- `dummy_esg/emission_factors.csv` (`factor_id` 포함)
- `dummy_esg/activity_raw.csv`
- `dummy_esg/activity_normalized.csv`
- `dummy_esg/activity_emissions.csv`
- `dummy_esg/metadata.json`

핵심 계층:
- Raw: `raw_unit`, `raw_amount`
- Normalized: `standardized_unit`, `standardized_amount`, `conversion_status`
- Emissions: `factor_id`, `co2e_kg`, `calculation_status`

## 엑셀 파이프라인 실행 (선택)
```bash
python esg_excel_skeleton.py --generate --excel-path ./mock_esg_data.xlsx
python esg_excel_skeleton.py --excel-path ./mock_esg_data.xlsx
```
