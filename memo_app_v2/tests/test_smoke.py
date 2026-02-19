from fastapi.testclient import TestClient

from app.main import app


def test_home():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200


def test_auth_and_memo_flow():
    client = TestClient(app)

    r1 = client.post("/user/register", json={"username": "u1", "email": "u1@example.com", "password": "1234"})
    assert r1.status_code == 200

    r2 = client.post("/user/login", json={"email": "u1@example.com", "password": "1234"})
    assert r2.status_code == 200

    r3 = client.post("/memo", json={"title": "t", "content": "c"})
    assert r3.status_code == 200

    r4 = client.get("/memo/list")
    assert r4.status_code == 200
    assert len(r4.json()) >= 1
