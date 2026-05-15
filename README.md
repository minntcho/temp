# LGES-scale Synthetic ESG Data Generator

이 저장소는 대기업 배터리 제조사를 가정한 ESG/탄소 원천 데이터를 대량 생성하기 위한 synthetic data factory입니다.

본 저장소의 목적은 데이터 처리, 정규화, 분석, 배출량 계산이 아니라, 그러한 시스템을 테스트하기 위한 대량의 raw source data와 ground truth를 생성하는 것입니다.

This repository generates fictional synthetic ESG data inspired by a large battery manufacturer. It does not contain or represent real LG Energy Solution data.

## Goals

- 대기업 기준정보 생성
- 대량 활동 데이터 생성
- 출처별 raw 데이터 생성
- 결측, 중복, 오류, 이상치 주입
- ground truth 라벨 생성
- 생성 리포트와 manifest 생성

## Non-goals

- ESG 데이터 정규화 파이프라인 구현
- 실제 탄소배출량 산정 시스템 구현
- FastAPI 또는 웹서비스 구현
- 머신러닝 기반 이상치 탐지
- staging/canonical 변환기를 메인 기능으로 제공
- 실제 기업 데이터 재현

## Data Contract

생성 결과는 세 종류의 산출물로 나뉩니다.

### Master Data

조직, 사업장, 생산 라인, 제품, 협력사, 계량기, 배출계수, 단위변환표 같은 기준정보입니다.

### Raw Source Data

ERP, MES, EMS, 협력사 제출 파일, 수기 업로드, 메일, 현장 메모처럼 실제 시스템마다 다른 형태로 관측된 원천 데이터입니다. 이 데이터에는 의도적으로 결측, 단위 오류, 중복, 기간 오류, 사업장 alias, 이상치가 포함될 수 있습니다.

### Truth / Label Data

합성 생성기가 내부적으로 알고 있는 정답 데이터입니다. `truth/`는 처리 결과가 아니라 평가용 라벨입니다. 다른 처리 시스템은 `raw_sources/`를 복원한 뒤 `truth/`와 비교해 품질을 측정할 수 있습니다.

## Quick Start

```bash
python -m synthetic_esg generate \
  --profile profiles/lges_smoke.yaml \
  --out-dir ./out/smoke \
  --seed 1
```

## Web Run Dashboard

Next.js 대시보드는 `web/` 아래에 있으며, smoke profile 실행 이력을 `out/web-runs/<run-id>/` 단위로 보관합니다. 각 run 폴더에는 `web_run.json`, `manifest.json`, `generation_report.json`, 생성 데이터 폴더, Plotly HTML 리포트가 함께 남습니다.

```bash
cd web
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:3000`을 열고 `Run smoke`를 실행하면 `profiles/lges_smoke.yaml` 기준 synthetic ESG 데이터와 `reports/distribution_dashboard.html`이 생성됩니다. Python 실행 파일을 명시해야 하는 환경에서는 `SYNTHETIC_ESG_PYTHON`에 Python 경로를 지정합니다.

대기업 규모 override 예시:

```bash
python -m synthetic_esg generate \
  --profile profiles/lges_enterprise.yaml \
  --scale enterprise \
  --months 36 \
  --sites 80 \
  --lines 500 \
  --products 300 \
  --suppliers 2000 \
  --meters 5000 \
  --out-dir ./out/lges_enterprise \
  --seed 42
```

## Profiles

기본 지원 프로필은 빠른 개발 검증용 `profiles/lges_smoke.yaml`과 대기업 규모 기준선인 `profiles/lges_enterprise.yaml`입니다.

`profiles/experimental/` 아래의 `lges_large.yaml`, `lges_stress.yaml`은 대량/부하 검증용 후보 프로필입니다. 현재는 기본 테스트와 CLI scale preset에서 제외하며, row-generation 성능 최적화와 장기 실행 검증이 준비된 뒤 정식 경로로 올립니다.

## Target Output Layout

```text
out/lges_2026_seed42/
  manifest.json
  generation_report.json

  master/
    legal_entities.csv
    business_units.csv
    sites.csv
    production_lines.csv
    products.csv
    suppliers.csv
    meters.csv
    reporting_calendar.csv
    emission_factors.csv
    unit_conversions.csv

  truth/
    canonical_activity.csv
    canonical_emissions.csv
    source_to_truth_map.csv
    injected_anomalies.csv

  raw_sources/
    erp/
      erp_energy_2026_01.csv
    mes/
      mes_production_2026_01.csv
    ems/
      meter_readings_2026_01.jsonl
    suppliers/
      supplier_energy_report_batch_001.csv
    manual/
      manual_upload_001.csv
    field_notes/
      field_notes_2026_01.txt
    emails/
      email_dump_2026_01.jsonl
```

## Archived Consumer Examples

이전의 처리, 정규화, 엑셀 파이프라인 예제는 `archive/consumer_examples/`로 이동했습니다. 해당 코드는 이 저장소의 핵심 기능이 아니라, 생성된 데이터를 소비하는 외부 시스템이 어떤 일을 할 수 있는지 보여주는 참고 자료입니다.

## Roadmap

1. Phase 1: README에서 generation-only 목적을 확정하고 consumer example을 archive로 이동
2. Phase 2: `synthetic_esg` 패키지 골격과 `python -m synthetic_esg generate` CLI 추가
3. Phase 3: `profiles/*.yaml` 기반 scale, source mix, noise rate 제어
4. Phase 4: `master/`, `raw_sources/`, `truth/`, `manifest.json` 출력 구조 고정
5. Phase 5: seed 재현성, truth consistency, noise rate 테스트 추가
6. Phase 6: smoke, enterprise profile과 chunk writer 지원
7. Phase 7: master/truth/raw source row generation 고도화 및 source mix 기반 partitioning
8. Later: large, stress profile을 성능 검증 경로로 승격
