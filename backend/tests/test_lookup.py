from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'viewer')}"}


def test_lookup_departments():
    r = client.get("/api/lookup/departments", headers=H)
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_lookup_requires_auth():
    r = client.get("/api/lookup/departments")
    assert r.status_code == 401


def test_lookup_stores_and_statuses():
    assert client.get("/api/lookup/stores", headers=H).status_code == 200
    assert client.get("/api/lookup/order-statuses", headers=H).status_code == 200
