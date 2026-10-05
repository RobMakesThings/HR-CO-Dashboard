from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'admin')}"}


def test_list_employees_returns_joined_fields():
    r = client.get("/api/employees", params={"page": 1, "pageSize": 5}, headers=H)
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert "department_name" in item and "job_title" in item


def test_generate_employee_is_valid():
    r = client.get("/api/employees/generate", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert "@" in data["email"] and data["last_name"]
    assert data["department_id"] and data["job_id"]


def test_employee_crud_roundtrip():
    email = f"e{__import__('time').time_ns() % 1000000}@x.com"
    r = client.post(
        "/api/employees",
        json={
            "first_name": "Test", "last_name": "Crud", "email": email,
            "phone_number": "555.123.4567", "hire_date": "2024-01-15",
            "job_id": "IT_PROG", "salary": 6000, "commission_pct": None,
            "manager_id": 100, "department_id": 60,
        },
        headers=H,
    )
    assert r.status_code == 201, r.text
    eid = r.json()["employee_id"]
    u = client.put(f"/api/employees/{eid}", json={"salary": 6500}, headers=H)
    assert u.status_code == 200 and u.json()["salary"] == 6500
    d = client.delete(f"/api/employees/{eid}", headers=H)
    assert d.status_code == 200
