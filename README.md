# temp

기초 **E(Environment, 환경)** 데이터 파이프라인 실험용 저장소입니다.

## 포함 파일
- `generate_esg_dummy_data.py`: **E 도메인 생성 전용** 더미 데이터 생성기 (마스터 + `activity_raw`)
- `process_esg_dummy_data.py`: **E 도메인 처리 전용** 정책 실행기 (표준화 + 배출량 계산)
- `generate_multisource_esg_raw.py`: E 데이터 출처별 원형(정형/반정형/비정형) 원시데이터 생성기
- `normalize_multisource_esg.py`: E 다중 출처 원시데이터를 공통 staging 스키마로 정규화
- `esg_excel_skeleton.py`: 엑셀 기반 전처리/산정/마이닝 뼈대 코드
- `requirements.txt`: 엑셀 파이프라인 실행용 의존성

## 1) 더미 데이터 생성 (Generation only)
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

## 2) 정책 처리 (Processing only)
```bash
python process_esg_dummy_data.py --in-dir ./dummy_esg --out-dir ./dummy_esg
```

## 3) 다중 출처 원시데이터 생성 (정형+반정형+비정형)
```bash
python generate_multisource_esg_raw.py --out-dir ./raw_multisource --rows 80 --seed 7
```

생성 파일:
- `erp_energy.csv` (정형)
- `supplier_fuel_sheet.csv` (반정형)
- `field_notes.txt` (비정형)
- `email_dump.jsonl` (비정형)
- `source_manifest.json`

## 4) 다중 출처 정규화 (LLM 대체용 규칙 파서 베이스라인)
```bash
python normalize_multisource_esg.py --in-dir ./raw_multisource --out-dir ./raw_multisource
```

출력 파일:
- `unified_raw_staging.csv`
- `parse_report.json`

## 엑셀 파이프라인 실행 (선택)
```bash
python esg_excel_skeleton.py --generate --excel-path ./mock_esg_data.xlsx
python esg_excel_skeleton.py --excel-path ./mock_esg_data.xlsx
```

## 5) FastAPI 기반 탄소배출량 분석 서버 (요구사항 반영)
아래 기능을 포함합니다.
- 제품별 탄소배출량 자동 계산 (`/v1/emissions/calculate`)
- 키워드 기반 activity 자동 분류 (`/v1/keywords/classify`)
- scikit-learn 이상치 탐지(IsolationForest) + 데이터 검증
- 엑셀 템플릿 다운로드 (`/v1/excel/template`)
- 엑셀 업로드 분석 (`/v1/excel/analyze`, 시트: `activity`, `emission_factors`)

```bash
uvicorn carbon_api:app --reload --port 8000
```

예시 요청:
```bash
curl -X POST http://127.0.0.1:8000/v1/emissions/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "activities": [
      {"product_id":"PRD-001","activity_type":"electricity","amount":1200,"unit":"kWh","description":"1월 전력"},
      {"product_id":"PRD-001","activity_type":"diesel","amount":80,"unit":"L","description":"디젤 사용"}
    ],
    "factors": [
      {"activity_type":"electricity","unit":"kWh","emission_factor":0.45},
      {"activity_type":"diesel","unit":"L","emission_factor":2.68}
    ],
    "run_outlier_detection": true
  }'
```
