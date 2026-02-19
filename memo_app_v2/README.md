# memo_app_v2

새로 만든 FastAPI 기반 로그인 + 개인 메모 프로젝트입니다.

## 실행
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## 주요 기능
- 회원가입 / 로그인 / 로그아웃
- 인증 사용자 메모 CRUD
- 메모 소유권 검증
- 소프트 삭제
