# temp

기초 ESG 데이터 파이프라인 실험용 저장소입니다.

## 포함 파일
- `generate_esg_dummy_data.py`: **생성 전용** 더미 데이터 생성기 (마스터 + `activity_raw`)
- `process_esg_dummy_data.py`: **처리 전용** 정책 실행기 (표준화 + 배출량 계산)
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

생성 파일:
- `legal_entities.csv`
- `sites.csv`
- `products.csv`
- `suppliers.csv`
- `reporting_calendar.csv`
- `unit_conversions.csv`
- `emission_factors.csv`
- `activity_raw.csv`
- `metadata.json`

## 2) 정책 처리 (Processing only)
```bash
python process_esg_dummy_data.py --in-dir ./dummy_esg --out-dir ./dummy_esg
```

처리 파일:
- `activity_normalized.csv`
- `activity_emissions.csv`
- `processing_report.json`

## 엑셀 파이프라인 실행 (선택)
```bash
python esg_excel_skeleton.py --generate --excel-path ./mock_esg_data.xlsx
python esg_excel_skeleton.py --excel-path ./mock_esg_data.xlsx
```
