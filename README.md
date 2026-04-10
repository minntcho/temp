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
# 자동 merged 승격이 필요하면:
python process_esg_dummy_data.py --in-dir ./dummy_esg --out-dir ./dummy_esg --auto-merge
# 설명가능 trace 로그를 남기려면:
python process_esg_dummy_data.py --in-dir ./dummy_esg --out-dir ./dummy_esg --trace
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

## 처리기 추가 산출물 (commit/merge lifecycle)
- `commit_table.csv` (commit snapshot)
- `event_log.csv` (상태 전이 이벤트 로그)
- `canonical_activity_emissions.csv` (`--auto-merge` 사용 시 생성)
- `trace_log.jsonl` (`--trace` 사용 시 생성, 레코드별 의사결정 근거)

## 엑셀 파이프라인 실행 (선택)
```bash
python esg_excel_skeleton.py --generate --excel-path ./mock_esg_data.xlsx
python esg_excel_skeleton.py --excel-path ./mock_esg_data.xlsx
```

## 문서
- `docs/MVP_SPEC.md`: E-domain 구조화 Agent MVP 명세서
