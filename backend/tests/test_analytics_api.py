from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'viewer')}"}


def test_revenue_over_time_shape():
    r = client.get(
        "/api/analytics/revenue-over-time",
        params={"granularity": "month", "from": "2025-01-01", "to": "2026-12-31"},
        headers=H,
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["points"], list)
    if body["points"]:
        assert "period" in body["points"][0] and "revenue" in body["points"][0]


def test_orders_by_status():
    r = client.get("/api/analytics/orders-by-status", params={"from": "2025-01-01", "to": "2026-12-31"}, headers=H)
    assert r.status_code == 200
    assert "series" in r.json()


def test_hr_analytics():
    assert client.get("/api/analytics/headcount-by-dept", headers=H).status_code == 200
    assert client.get("/api/analytics/salary-stats", headers=H).status_code == 200
    assert client.get("/api/analytics/hires-over-time", headers=H).status_code == 200
