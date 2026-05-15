# Synthetic ESG Data Generator

대규모 배터리 제조사를 모티프로 한 **fictional synthetic ESG 데이터 생성기**입니다.

이 레포는 실제 기업 데이터를 담거나 재현하지 않습니다. 목적은 ESG 데이터 처리 시스템을 만들기 전에, 여러 원천 시스템에서 온 것처럼 보이는 raw source 데이터와 비교용 truth 데이터를 안정적으로 만들어 주는 것입니다.

한 번 실행하면 다음과 같은 산출물이 생깁니다.

- `master/`: 조직, 사업장, 생산 라인, 제품, 협력사, 계량기, 배출계수 같은 기준 정보
- `raw_sources/`: ERP, MES, EMS, 협력사 제출 파일, 수기 업로드, 현장 메모, 이메일 덤프 형태의 원천 데이터
- `truth/`: 생성기가 내부적으로 알고 있는 정답 활동량, 배출량, source-to-truth 매핑, 주입된 이상치 라벨
- `manifest.json`: 실행 설정, 출력 계약, seed, 재현성 hash
- `generation_report.json`: record count, 품질 체크, 분포 통계
- 선택적으로 `reports/distribution_dashboard.html`: Plotly 기반 시각화 리포트

## What This Is For

이 프로젝트는 ESG 데이터 파이프라인을 검증하기 위한 테스트 데이터 팩토리입니다.

예를 들어 다음을 확인할 수 있습니다.

- raw source 파일을 canonical activity로 복원할 수 있는지
- 결측, 중복, 단위 오류, 기간 오류, site alias, outlier를 처리할 수 있는지
- truth label과 비교해 처리 결과를 평가할 수 있는지
- seed/profile이 같을 때 같은 설정 hash와 재현 가능한 출력을 얻을 수 있는지
- smoke 규모부터 enterprise 규모까지 생성 계약이 유지되는지

## What This Is Not

이 레포는 아래 역할을 하지 않습니다.

- 실제 LG Energy Solution 또는 실제 기업 데이터 재현
- ESG 정규화/보정/분석 파이프라인 구현
- 실제 배출량 산정 시스템 구현
- FastAPI 같은 운영 API 서버 제공
- 머신러닝 기반 이상치 탐지
- raw source를 처리한 결과물을 truth로 둔갑시키기

`truth/`는 생성기가 알고 있는 평가용 정답입니다. downstream 시스템은 `raw_sources/`만 보고 결과를 만들고, 평가할 때만 `truth/`와 비교하는 구조를 의도합니다.

## Quick Start

Python 의존성을 먼저 설치합니다.

```bash
python -m pip install -r requirements.txt
```

가장 작은 smoke profile 실행:

```bash
python -m synthetic_esg generate \
  --profile profiles/lges_smoke.yaml \
  --out-dir ./out/smoke \
  --seed 1
```

생성된 run에서 Plotly HTML 리포트 만들기:

```bash
python -m synthetic_esg visualize \
  --run-dir ./out/smoke
```

리포트는 기본적으로 다음 위치에 생성됩니다.

```text
out/smoke/reports/distribution_dashboard.html
```

## Larger Runs

`profiles/lges_enterprise.yaml`와 CLI override를 조합하면 더 큰 규모의 데이터를 만들 수 있습니다.

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

현재 CLI preset은 `smoke`, `enterprise`를 기본 지원합니다. `profiles/experimental/` 아래의 `large`, `stress` profile은 더 큰 부하 실험 후보이며, 기본 preset으로 취급하지 않습니다.

## Web Run Dashboard

`web/`에는 Next.js 기반 run dashboard가 있습니다. 지금은 smoke profile 실행을 브라우저에서 만들고, 실행 이력을 `out/web-runs/<run-id>/` 단위로 다시 열어볼 수 있게 해줍니다.

```bash
cd web
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:3000`을 열고 `Run smoke`를 실행하면 다음 흐름이 자동으로 돌게 됩니다.

1. `python -m synthetic_esg generate --profile profiles/lges_smoke.yaml ...`
2. `python -m synthetic_esg visualize --run-dir ...`
3. `web_run.json`, `manifest.json`, `generation_report.json`, raw/master/truth 데이터, Plotly HTML 리포트 저장

Python 실행 파일을 명시해야 하는 환경에서는 `SYNTHETIC_ESG_PYTHON`에 Python 경로를 지정할 수 있습니다.

```bash
SYNTHETIC_ESG_PYTHON=/path/to/python npm run dev
```

## Output Layout

일반적인 생성 결과는 아래처럼 생깁니다.

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

  reports/
    distribution_dashboard.html
```

정확한 출력 계약은 `synthetic_esg/generators/scaffold.py`가 기준입니다. README의 layout은 빠르게 이해하기 위한 예시입니다.

## Profiles

프로필은 생성 규모, 기간, activity type, source mix, noise rate, output option을 지정합니다.

- `profiles/lges_smoke.yaml`: 빠른 개발/검증용 작은 데이터
- `profiles/lges_enterprise.yaml`: 대규모 생성 기준선
- `profiles/experimental/lges_large.yaml`: 큰 규모 실험 후보
- `profiles/experimental/lges_stress.yaml`: stress 성격의 실험 후보

현재 profile parser는 단순 YAML subset만 지원합니다. 복잡한 YAML 기능이 필요한 경우 parser를 먼저 확장해야 합니다.

## Architecture Notes

아키텍처 흐름과 SSOT 경계는 `docs/ARCHITECTURE.md`에 Mermaid diagram으로 정리되어 있습니다.

중요한 기준은 다음과 같습니다.

- 프로젝트 목적과 비목적: `README.md`
- agent 작업 규칙: `AGENTS.md`
- 아키텍처 오리엔테이션: `docs/ARCHITECTURE.md`
- 출력 계약: `synthetic_esg/generators/scaffold.py`
- 계약 검증: `tests/`

Mermaid diagram은 현재 구조를 이해하기 위한 지도이지, 설계를 고정하는 계약은 아닙니다. 코드/테스트/README와 다르면 diagram이 낡은 것으로 보고 업데이트해야 합니다.

## Testing

Python 테스트는 표준 라이브러리 `unittest` 기반입니다.

```bash
python -m unittest discover -s tests -p "test_*.py" -q
```

웹 대시보드 테스트:

```bash
cd web
npm test
```

새 agent 환경에서는 `pytest`가 설치되어 있다고 가정하지 마세요. 자세한 agent bootstrap 규칙은 `AGENTS.md`에 있습니다.

## Archived Consumer Examples

`archive/consumer_examples/`에는 예전 처리/정규화/엑셀 예제가 보관되어 있습니다. 이 코드는 메인 기능이 아니라, 생성된 데이터를 downstream 시스템이 어떻게 소비할 수 있는지 보여주는 참고 자료입니다.
