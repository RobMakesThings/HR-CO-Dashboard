from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'admin', 'admin')}"}
H_VIEWER = {"Authorization": f"Bearer {create_token(2, 'user', 'viewer')}"}


def test_list_customers_paginates():
    r = client.get("/api/customers", params={"page": 1, "pageSize": 5}, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 5
    assert isinstance(body["total"], int)


def test_viewer_cannot_create():
    r = client.post(
        "/api/customers",
        json={"email_address": "a@b.com", "full_name": "A B"},
        headers=H_VIEWER,
    )
    assert r.status_code == 403


def test_admin_can_generate():
    r = client.get("/api/customers/generate", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert "@" in data["email_address"] and data["full_name"]


def test_crud_roundtrip():
    email = f"crud{__import__('time').time_ns()}@example.com"
    # create
    r = client.post(
        "/api/customers", json={"email_address": email, "full_name": "CRUD Test"},
        headers=H,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["customer_id"]
    # duplicate email -> 409
    r2 = client.post(
        "/api/customers", json={"email_address": email, "full_name": "Other"},
        headers=H,
    )
    assert r2.status_code == 409
    # update
    r3 = client.put(
        f"/api/customers/{cid}", json={"full_name": "CRUD Updated"}, headers=H
    )
    assert r3.status_code == 200 and r3.json()["full_name"] == "CRUD Updated"
    # delete
    r4 = client.delete(f"/api/customers/{cid}", headers=H)
    assert r4.status_code == 200
