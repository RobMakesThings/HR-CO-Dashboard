from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'admin')}"}


def test_list_products():
    r = client.get("/api/products", params={"page": 1, "pageSize": 5}, headers=H)
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 5


def test_generate_product():
    r = client.get("/api/products/generate", headers=H)
    assert r.status_code == 200
    assert r.json()["product_name"] and r.json()["unit_price"] > 0


def test_product_crud_roundtrip():
    r = client.post(
        "/api/products", json={"product_name": "Widget 9000", "unit_price": 42.5},
        headers=H,
    )
    assert r.status_code == 201, r.text
    pid = r.json()["product_id"]
    g = client.get(f"/api/products/{pid}", headers=H)
    assert g.json()["product_name"] == "Widget 9000"
    u = client.put(f"/api/products/{pid}", json={"unit_price": 99.99}, headers=H)
    assert u.json()["unit_price"] == 99.99
    d = client.delete(f"/api/products/{pid}", headers=H)
    assert d.status_code == 200
