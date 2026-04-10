# E-domain ESG 구조화 Agent MVP 명세서

## 1) 목적
중구난방 E(Environment) 원시데이터(정형/반정형/비정형)를 입력받아,
반복적 구조 복원(가설-검증 루프)을 통해 계산 가능한 내부 스키마로 변환한다.

---

## 2) 범위 (In/Out)

### In Scope (MVP)
- E 도메인만 대상 (electricity, diesel, natural_gas, steam)
- 입력 포맷:
  - CSV (`erp_energy.csv`, `supplier_fuel_sheet.csv`)
  - TXT (`field_notes.txt`)
  - JSONL (`email_dump.jsonl`)
- 표준화 대상 필드:
  - `site`, `period`, `activity_type`, `raw_amount`, `raw_unit`
- 산출물:
  - `unified_raw_staging.csv`
  - `activity_normalized.csv`
  - `activity_emissions.csv`
  - `parse_report.json`, `processing_report.json`

### Out of Scope (MVP 제외)
- S/G 독립 도메인 지표
- PDF/OCR 파싱
- 완전 자동 의사결정(사람 검토 없는 100% 확정)

---

## 3) 사용자 시나리오
1. 운영자가 여러 출처 파일을 업로드/배치한다.
2. 시스템이 구조 복원 및 key-value 후보화를 수행한다.
3. 규칙/임베딩 기반 매핑 점수로 자동 확정/검토/거부를 분기한다.
4. 단위 표준화 + factor 적용으로 배출량을 계산한다.
5. 실패/제외/성공 리포트를 확인하고 재처리한다.

---

## 4) 아키텍처 (MVP)
1. **Source Layer**: 출처별 원형 데이터 생성/수집
2. **Structure Recovery Layer**: row/col 정리, 헤더/레코드 경계 감지
3. **Candidate Layer**: key 후보, value 후보 추출
4. **Mapping Loop Layer**: 가설-파싱-검증-수정 반복
5. **Standardization Layer**: 단위 환산 및 값 정규화
6. **Calculation Layer**: factor 매칭, `co2e_kg` 계산

---

## 5) 데이터 계약 (최소 스키마)

### 5.1 unified_raw_staging.csv
- `source_type`
- `source_ref`
- `raw_text`
- `site`
- `period` (`YYYY-MM`)
- `activity_type`
- `raw_amount`
- `raw_unit`
- `standardized_amount`
- `standardized_unit`
- `parse_method`
- `confidence` (0~1)
- `status` (`ok`/`failed`)
- `note`

### 5.2 activity_normalized.csv
- `activity_id`
- `activity_type`
- `raw_unit`
- `raw_amount`
- `standardized_unit`
- `standardized_amount`
- `conversion_id`
- `conversion_status` (`converted`/`already_standard`/`failed`)
- `conversion_note`

### 5.3 activity_emissions.csv
- `activity_id`
- `factor_id`
- `standardized_amount`
- `standardized_unit`
- `applied_factor`
- `factor_unit`
- `co2e_kg`
- `scope_category`
- `calculation_status` (`success`/`failed`/`excluded`)
- `excluded_from_reporting`
- `exclusion_reason`
- `calculation_version`
- `calculated_at`

---

## 6) 반복 루프(핵심 알고리즘)

### 6.1 루프 절차
1. key 후보 생성 (문자열/임베딩/위치 기반)
2. value 파싱 (수치/단위/기간 추출)
3. 검증 점수 계산
   - Key Match Score
   - Value Fit Score
   - Pair Consistency Score
4. 후보 갱신
5. 종료조건 체크

### 6.2 종료조건
- 매핑 변화율 < `delta_threshold`
- 점수 개선폭 < `epsilon`
- 상태 진동(A↔B) 감지
- `max_iter` 도달

---

## 7) 점수 및 의사결정

### 7.1 점수식 (MVP)
`final_score = 0.5 * key_score + 0.3 * value_score + 0.2 * consistency_score`

### 7.2 임계치
- `>= 0.80`: 자동 확정
- `0.55 ~ 0.79`: 검토 큐
- `< 0.55`: 거부/미매핑

---

## 8) 검증 규칙 (MVP)
- 타입 검증: amount 숫자형
- 단위 검증: unit 변환 규칙 존재 여부
- 범위 검증: 음수 금지(기본)
- 기간 검증: `YYYY-MM` 포맷
- 활동-단위 호환 검증

---

## 9) 품질 지표 (MVP KPI)
- Parse Success Rate (`status=ok` 비율) >= 90%
- Normalization Success Rate >= 95%
- Calculation Success Rate >= 95%
- Manual Review Ratio <= 30%

---

## 10) 수용 기준 (Acceptance Criteria)
- 다중 출처 입력 4종에서 staging 생성 성공
- 단위 변환 실패/성공이 리포트에 분리 기록
- factor 매칭 성공/실패/제외가 계산 결과에 기록
- 같은 입력 + 같은 seed 재실행 시 결과 재현성 확보

---

## 11) 운영/로깅 요구
- 각 레코드에 `source_ref`, `parse_method`, `confidence` 저장
- 실패 사유 코드(`note`, `exclusion_reason`) 저장
- 처리 요약 리포트(JSON) 자동 생성

### 11.1 Commit / Merge 분리 원칙 (MVP 필수)
- 자동 승인 결과는 `committed` 상태로 기록하고 즉시 canonical 반영하지 않는다.
- `merged`는 별도 정책 사건(사람 승인 또는 명시적 자동 머지 플래그)으로 승격한다.
- 공식 계산/리포트 반영은 `merged` 상태 레코드만 대상으로 한다.

### 11.2 최소 Ledger 스키마
- `event_log`:
  - `event_id`, `record_id`, `event_type`, `from_status`, `to_status`
  - `score`, `reason_code`, `actor`, `created_at`
- `commit_table`:
  - `commit_id`, `record_id`, `parent_commit_id`
  - `score`, `reason_code`, `rule_version`, `model_version`
  - `created_by`, `created_at`, `to_status`

### 11.3 Explainable Trace (디버깅/가시화용)
- 레코드 단위 처리 근거를 `trace_log.jsonl`로 남긴다.
- 최소 필드:
  - `trace_id`, `record_id`, `timestamp`
  - `normalization` (`conversion_status`, `raw_unit`, `standardized_unit`, `conversion_note`)
  - `calculation` (`calculation_status`, `factor_id`, `co2e_kg`, `exclusion_reason`)
  - `decision` (`final_status`, `score`, `reason_code`, `auto_merge`)

---

## 12) 릴리스 계획

### Sprint 1
- 구조 복원 + staging 정규화 안정화
- parse report 고도화

### Sprint 2
- 반복 루프 점수화 및 자동/검토/거부 분기
- 계산 계층과 검토 큐 연동

### Sprint 3
- 규칙 튜닝 + 평가셋 기반 성능 측정
- 운영 문서화

---

## 13) 실행 모드
- 분리 실행 모드:
  - raw/master 생성 → 정규화/계산
  - multisource 생성 → staging 정규화
- 단일 실행 모드(권장):
  - `run_esg_unified_pipeline.py`로 정형+반정형+비정형 소스를 한 번에 병합 처리
