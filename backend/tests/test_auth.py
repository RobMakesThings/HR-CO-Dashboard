from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)


def _auth_headers(role: str) -> dict:
    return {"Authorization": f"Bearer {create_token(1, 'u', role)}"}


def test_login_rejects_bad_credentials():
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_login_admin_succeeds():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert r.json()["access_token"]


def test_users_requires_auth():
    r = client.get("/api/users")
    assert r.status_code == 401


def test_viewer_cannot_create_user():
    r = client.post(
        "/api/users",
        json={"username": "x", "password": "secret1", "role": "viewer"},
        headers=_auth_headers("viewer"),
    )
    assert r.status_code == 403


def test_admin_can_list_users():
    r = client.get("/api/users", headers=_auth_headers("admin"))
    assert r.status_code == 200
    usernames = [u["username"] for u in r.json()]
    assert "admin" in usernames and "user" in usernames
