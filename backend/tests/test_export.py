from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'viewer')}"}


def test_export_customers_csv():
    r = client.get("/api/export/customers", params={"format": "csv", "pageSize": 5}, headers=H)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert r.content[:3] == b"\xef\xbb\xbf"  # UTF-8 BOM


def test_export_customers_xlsx():
    r = client.get("/api/export/customers", params={"format": "xlsx", "pageSize": 5}, headers=H)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"] or r.content[:2] == b"PK"


def test_export_requires_auth():
    assert client.get("/api/export/customers", params={"format": "csv"}).status_code == 401
