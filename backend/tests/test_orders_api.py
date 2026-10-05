from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'admin')}"}


def test_list_orders():
    r = client.get("/api/orders", params={"page": 1, "pageSize": 5}, headers=H)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) <= 5
    assert "customer_name" in items[0] and "total" in items[0]


def test_generate_order_payload():
    r = client.get("/api/orders/generate", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert data["customer_id"] and data["items"]


def test_order_crud_roundtrip():
    payload = client.get("/api/orders/generate", headers=H).json()
    payload["order_status"] = "COMPLETE"
    r = client.post("/api/orders", json=payload, headers=H)
    assert r.status_code == 201, r.text
    oid = r.json()["order_id"]
    # detail includes items
    d = client.get(f"/api/orders/{oid}", headers=H)
    assert d.status_code == 200 and len(d.json()["items"]) == len(payload["items"])
    # update: change status
    u = client.put(f"/api/orders/{oid}", json={"order_status": "CANCELLED"}, headers=H)
    assert u.status_code == 200 and u.json()["order_status"] == "CANCELLED"
    # delete
    rm = client.delete(f"/api/orders/{oid}", headers=H)
    assert rm.status_code == 200
    assert client.get(f"/api/orders/{oid}", headers=H).status_code == 404
