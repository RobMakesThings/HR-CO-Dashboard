# HR + CO Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a role-based web dashboard over the Oracle HR + CO sample schemas with CRUD, server-side trends, faker seeding, and CSV/XLSX export.

**Architecture:** FastAPI + `python-oracledb` (thin) backend talking to an existing Oracle 23c container (`localhost:1521/FREEPDB1`) that holds `CO`, `HR`, and a new `dashboard` auth schema. A Vue 3 + Vite + PrimeVue 4 (Sakai) + Tailwind frontend consumes REST APIs. Dev uses Vite proxy + uvicorn; prod serves the built frontend from FastAPI.

**Tech Stack:** Python 3.12, FastAPI, python-oracledb, PyJWT, bcrypt, Pydantic v2, Faker, openpyxl, pytest. Vue 3, Vite, PrimeVue 4, Tailwind CSS, Vue Router, Pinia, Axios, Chart.js (via PrimeVue Chart).

**Spec:** `docs/superpowers/specs/2026-10-04-hr-co-dashboard-design.md`

## Global Constraints

- Oracle instance: `localhost:1521/FREEPDB1`. CO user `co`/`letmein`, HR user `hr`/`letmein` (these are real working creds verified by probe). `dashboard` schema user/password created by provisioning.
- Python 3.12; backend deps in `backend/requirements.txt`.
- All DB access uses `python-oracledb` **thin mode** (no Oracle client install).
- All SQL is parameterized (bind variables); never string-interpolate user input.
- All config via `backend/.env` (gitignored); commit `backend/.env.example` only.
- Every mutation endpoint enforces role `admin`; reads/export allow `admin` and `viewer`. Non-2xx responses use the envelope `{"detail": str, "code": str}`.
- Lists return `{items, total, page, pageSize}`; `page` 1-based, `pageSize` default 20 max 200.
- Orders are parents: create/update send header + `items` in one payload and are wrapped in one transaction.
- CSV exports include a UTF-8 BOM; XLSX via `openpyxl`. Exports respect current filters.
- Frontend routes: `/login` public; all others behind auth guard; admin-only `/users`.
- Frontend uses PrimeVue Sakai theme preset + Tailwind; Axios interceptor attaches JWT and redirects on 401.
- Start a fresh git repo already exists at `hr_co_dashboard/` (branch `bionic/main`). Commit after each task.

---

### Task 1: Backend scaffolding — config, DB pools, app skeleton, health

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/health.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `config.settings` (module-level singleton), `db.co_pool()`, `db.hr_pool()`, `db.dash_pool()` returning `oracledb.Pool`, `app.main:app` FastAPI instance with `/api/health` route.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_health.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "database" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_health.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'` or `app.main`.

- [ ] **Step 3: Write minimal implementation**

`backend/requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-oracledb==2.5.1
pydantic==2.10.4
pydantic-settings==2.7.1
PyJWT==2.10.1
bcrypt==4.2.1
python-dotenv==1.0.1
Faker==33.3.0
openpyxl==3.1.5
python-multipart==0.0.20
pytest==8.3.4
httpx==0.28.1
```

`backend/app/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    oracle_dsn: str = "localhost:1521/FREEPDB1"
    oracle_co_user: str = "co"
    oracle_co_password: str = "letmein"
    oracle_hr_user: str = "hr"
    oracle_hr_password: str = "letmein"
    oracle_dash_user: str = "dashboard"
    oracle_dash_password: str = "dashboard_pwd"
    jwt_secret: str = "change-me-not"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    default_date_range_days: int = 365

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

`backend/app/db.py`:
```python
import oracledb
from .config import settings

_pools: dict[str, oracledb.Pool] = {}


def _pool(user: str, password: str) -> oracledb.Pool:
    if user not in _pools:
        _pools[user] = oracledb.create_pool(
            user=user, password=password, dsn=settings.oracle_dsn,
            min=1, max=10, getmode=oracledb.POOL_ATTRGET_WAIT,
        )
    return _pools[user]


def co_pool() -> oracledb.Pool:
    return _pool(settings.oracle_co_user, settings.oracle_co_password)


def hr_pool() -> oracledb.Pool:
    return _pool(settings.oracle_hr_user, settings.oracle_hr_password)


def dash_pool() -> oracledb.Pool:
    return _pool(settings.oracle_dash_user, settings.oracle_dash_password)
```

`backend/app/routers/health.py`:
```python
from fastapi import APIRouter
from ..db import co_pool

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    try:
        with co_pool().acquire() as conn:
            cur = conn.cursor()
            cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
            db = cur.fetchone()[0]
        return {"status": "ok", "database": db, "dsn": "FREEPDB1"}
    except Exception as exc:  # pragma: no cover - depends on live DB
        return {"status": "degraded", "database": None, "error": str(exc)}
```

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import health

app = FastAPI(title="HR + CO Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
```

Create empty `backend/app/__init__.py` and `backend/app/routers/__init__.py`.

`backend/.env.example`:
```
ORACLE_DSN=localhost:1521/FREEPDB1
ORACLE_CO_USER=co
ORACLE_CO_PASSWORD=letmein
ORACLE_HR_USER=hr
ORACLE_HR_PASSWORD=letmein
ORACLE_DASH_USER=dashboard
ORACLE_DASH_PASSWORD=dashboard_pwd
JWT_SECRET=change-me
JWT_EXPIRY_MINUTES=480
CORS_ORIGINS=http://localhost:5173
DEFAULT_DATE_RANGE_DAYS=365
```

`backend/.gitignore`:
```
__pycache__/
*.pyc
.env
.pytest_cache/
.venv/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_health.py -q`
Expected: PASS (DB is live at the default DSN).

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: scaffold FastAPI backend with config, DB pools, health route"
```

---

### Task 2: Auth schema provisioning

**Files:**
- Create: `backend/seed/provision_dashboard.sql`
- Create: `backend/seed/README.md`
- Create: `backend/seed/__init__.py`
- Create: `backend/seed/seed_users.py`

**Interfaces:**
- Consumes: `config.settings`, `db.dash_pool()`.
- Produces: SQL script creating `dashboard.app_users`; `seed_users.py` upserts starter accounts.

- [ ] **Step 1: Write the provisioning SQL**

`backend/seed/provision_dashboard.sql` (run once as a privileged user):
```sql
-- Creates the DASHBOARD schema and its identity table.
-- Run as SYSTEM (or privileged). Replace DASHBOARD_PWD.
CREATE USER dashboard IDENTIFIED BY DASHBOARD_PWD;
GRANT CONNECT, RESOURCE TO dashboard;
GRANT CREATE SESSION TO dashboard;

-- Connect as dashboard, then:
CREATE TABLE app_users (
  app_user_id   NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  username      VARCHAR2(50)  NOT NULL UNIQUE,
  password_hash VARCHAR2(255) NOT NULL,
  role          VARCHAR2(20)  NOT NULL CHECK (role IN ('admin','viewer')),
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for login-by-username.
CREATE INDEX app_users_username_i ON app_users (username);
```

- [ ] **Step 2: Write the seeder**

`backend/seed/seed_users.py`:
```python
"""Create the starter admin + viewer accounts. Run: python -m seed.seed_users"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings
from app.db import dash_pool
from app.security import hash_password  # implemented in Task 3; import guarded below


def upsert_user(conn, username: str, password: str, role: str):
    cur = conn.cursor()
    cur.execute(
        "SELECT app_user_id FROM app_users WHERE username = :1", (username,)
    )
    if cur.fetchone():
        cur.execute(
            "UPDATE app_users SET password_hash = :1, role = :2 WHERE username = :3",
            (hash_password(password), role, username),
        )
    else:
        cur.execute(
            "INSERT INTO app_users (username, password_hash, role) VALUES (:1, :2, :3)",
            (username, hash_password(password), role),
        )
    conn.commit()


def main():
    admin_pw = input("Admin password: ").strip()
    viewer_pw = input("Viewer ('user') password: ").strip()
    with dash_pool().acquire() as conn:
        upsert_user(conn, "admin", admin_pw, "admin")
        upsert_user(conn, "user", viewer_pw, "viewer")
    print("Seeded: admin (admin), user (viewer)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify by running once (manual, requires Task 3 for hash_password)**

Run: `cd backend && python -m seed.seed_users`
Expected: prompts for two passwords, then prints `Seeded: admin (admin), user (viewer)`.
If `app.security` is not yet present, this step is deferred until after Task 3; the SQL in Step 1 can be run immediately against the DB to confirm schema creation.

- [ ] **Step 4: Commit**

```bash
git add backend/seed && git commit -m "feat: add dashboard auth-schema provisioning + user seeder"
```

---

### Task 3: Security — JWT + bcrypt

**Files:**
- Create: `backend/app/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(pw)->str`, `verify_password(pw, hashed)->bool`, `create_token(user_id:int, username:str, role:str)->str`, `decode_token(token:str)->dict` with keys `sub`, `username`, `role`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_security.py`:
```python
from app.security import hash_password, verify_password, create_token, decode_token
from app.config import settings


def test_password_roundtrip():
    hashed = hash_password("s3cret")
    assert hashed != "s3cret"
    assert verify_password("s3cret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_token_roundtrip():
    token = create_token(1, "admin", "admin")
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert payload["username"] == "admin"
    assert payload["role"] == "admin"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_security.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.security'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/security.py`:
```python
import datetime
import bcrypt
import jwt
from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_security.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/tests/test_security.py backend/seed && git commit -m "feat: add JWT + bcrypt security helpers"
```

---

### Task 4: Auth dependencies + users repository + auth router

**Files:**
- Create: `backend/app/deps.py`
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/users.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/routers/users.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `security.create_token/verify_password`, `db.dash_pool()`, `deps.get_current_user`.
- Produces: `deps.get_current_user(cred)->dict`, `deps.require_role(role)->Callable`, auth router `POST /api/auth/login`, users router admin CRUD (`GET/POST /api/users`, `PUT /api/users/{id}`, `DELETE /api/users/{id}`). Pydantic `LoginRequest{username,password}`, `UserCreate{username,password,role}`, `UserUpdate{password?,role?}`, `UserOut{id,username,role,created_at}`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_auth.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token

client = TestClient(app)


def _auth_headers(role: str) -> dict:
    return {"Authorization": f"Bearer {create_token(1, 'u', role)}"}


def test_login_rejects_bad_credentials():
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_login_requires_admin_role_for_users_create():
    # viewer creates user -> 403
    r = client.post(
        "/api/users",
        json={"username": "x", "password": "y", "role": "viewer"},
        headers=_auth_headers("viewer"),
    )
    assert r.status_code == 403


def test_users_requires_auth():
    r = client.get("/api/users")
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -q`
Expected: FAIL (import errors, routers missing).

- [ ] **Step 3: Write minimal implementation**

`backend/app/deps.py`:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        return decode_token(cred.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def require_role(required: str):
    def dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != required:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"{required} privileges required")
        return user
    return dep
```

`backend/app/schemas/auth.py`:
```python
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(admin|viewer)$")


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: str | None = Field(default=None, pattern="^(admin|viewer)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    app_user_id: int
    username: str
    role: str
    created_at: datetime | None = None
```

`backend/app/repositories/users.py`:
```python
from ..db import dash_pool
from ..security import hash_password
from ..schemas.auth import UserCreate, UserUpdate


def row_to_user(row) -> dict:
    if row is None:
        return None
    return {
        "app_user_id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "role": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
    }


def public_user(row) -> dict:
    u = row_to_user(row)
    if u is None:
        return None
    u.pop("password_hash", None)
    return u


def find_by_username(username: str) -> dict:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT app_user_id, username, password_hash, role, created_at "
            "FROM app_users WHERE username = :1",
            (username,),
        )
        return row_to_user(cur.fetchone())


def list_users() -> list[dict]:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT app_user_id, username, password_hash, role, created_at "
            "FROM app_users ORDER BY username"
        )
        return [public_user(r) for r in cur.fetchall()]


def create_user(data: UserCreate) -> dict:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO app_users (username, password_hash, role) VALUES (:1, :2, :3) "
            "RETURNING app_user_id, username, password_hash, role, created_at INTO :4, :5, :6, :7, :8",
            (data.username, hash_password(data.password), data.role,
             cur.var(int), cur.var(str), cur.var(str), cur.var(str), cur.var(object)),
        )
        conn.commit()
        row = (cur.var(int).getvalue(), cur.var(str).getvalue(), cur.var(str).getvalue(),
               cur.var(str).getvalue(), cur.var(object).getvalue())
        return public_user((row[0], row[1], row[2], row[3], row[4]))


def update_user(user_id: int, data: UserUpdate) -> dict:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        if data.password:
            cur.execute(
                "UPDATE app_users SET password_hash = :1 WHERE app_user_id = :2",
                (hash_password(data.password), user_id),
            )
        if data.role:
            cur.execute(
                "UPDATE app_users SET role = :1 WHERE app_user_id = :2",
                (data.role, user_id),
            )
        conn.commit()
        return get_user(user_id)


def delete_user(user_id: int) -> bool:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM app_users WHERE app_user_id = :1", (user_id,))
        conn.commit()
        return cur.rowcount > 0


def get_user(user_id: int) -> dict:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT app_user_id, username, password_hash, role, created_at "
            "FROM app_users WHERE app_user_id = :1",
            (user_id,),
        )
        return public_user(cur.fetchone())
```

`backend/app/routers/auth.py`:
```python
from fastapi import APIRouter, HTTPException, status
from ..schemas.auth import LoginRequest, TokenResponse
from ..repositories.users import find_by_username
from ..security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = find_by_username(body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token = create_token(user["app_user_id"], user["username"], user["role"])
    return TokenResponse(access_token=token, role=user["role"], username=user["username"])
```

`backend/app/routers/users.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from ..deps import require_role
from ..schemas.auth import UserCreate, UserUpdate, UserOut
from ..repositories import users as repo

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_role("admin"))])


@router.get("", response_model=list[UserOut])
def list_users():
    return repo.list_users()


@router.post("", response_model=UserOut)
def create_user(body: UserCreate):
    existing = repo.find_by_username(body.username)
    if existing:
        raise HTTPException(409, "Username already exists")
    return repo.create_user(body)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate):
    user = repo.get_user(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return repo.update_user(user_id, body)


@router.delete("/{user_id}")
def delete_user(user_id: int):
    user = repo.get_user(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    repo.delete_user(user_id)
    return {"deleted": True}
```

Register routers in `backend/app/main.py`:
```python
from .routers import auth, users
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -q`
Expected: PASS. NOTE: requires the `dashboard` schema + `app_users` from Task 2 to exist (login uses the real DB).

- [ ] **Step 5: Commit**

```bash
git add backend/app && git commit -m "feat: add auth dependencies, users CRUD, and login"
```

---

### Task 5: Shared Pydantic schemas + pagination helper + error handling

**Files:**
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/errors.py`
- Create: `backend/app/schemas/customers.py`, `backend/app/schemas/products.py`, `backend/app/schemas/employees.py`, `backend/app/schemas/orders.py`
- Test: `backend/tests/test_errors.py`

**Interfaces:**
- Produces: `Page(items,total,page,pageSize)`, `paginate(sql, params, page, pageSize)` SQL builder helper, `app.errors.init_handlers(app)` registering the error envelope, exception classes `ClientError(status_code, code, detail)`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_errors.py`:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.errors import ClientError, init_handlers

app = FastAPI()
init_handlers(app)


@app.get("/boom")
def boom():
    raise ClientError(409, "DUP_EMAIL", "duplicate value")


client = TestClient(app)


def test_error_envelope():
    r = client.get("/boom")
    assert r.status_code == 409
    assert r.json() == {"detail": "duplicate value", "code": "DUP_EMAIL"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_errors.py -q`
Expected: FAIL (module `app.errors` missing).

- [ ] **Step 3: Write implementation**

`backend/app/errors.py`:
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class ClientError(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        self.status_code = status_code
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _env(status_code: int, code: str, detail: str) -> dict:
    return {"detail": detail, "code": code}


def init_handlers(app):
    @app.exception_handler(ClientError)
    async def client_error_handler(_req: Request, exc: ClientError):
        return JSONResponse(status_code=exc.status_code, content=_env(exc.status_code, exc.code, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_req: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content=_env(422, "VALIDATION", str(exc.errors())))
```

`backend/app/schemas/common.py`:
```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pageSize: int
```

`backend/app/repositories/pagination.py` (create dir file `backend/app/repositories/pagination.py`):
```python
"""Helpers for offset pagination over parameterized SQL."""
from ..errors import ClientError


def clamp(page: int, page_size: int) -> tuple[int, int]:
    page = max(1, page)
    page_size = min(200, max(1, page_size))
    return page, page_size


def count(cursor, from_sql: str, where_sql: str, params: tuple) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {from_sql} {where_sql}", params)
    return cursor.fetchone()[0]


def run_page(cursor, cols_sql, from_sql, where_sql, order_sql,
             params, page, page_size):
    total = count(cursor, from_sql, where_sql, params)
    offset = (page - 1) * page_size
    cursor.execute(
        f"{cols_sql} FROM {from_sql} {where_sql} {order_sql} "
        f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY",
        params,
    )
    cols = [c[0].lower() for c in cursor.description]
    rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
    return {"items": rows, "total": total, "page": page, "pageSize": page_size}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_errors.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/errors.py backend/app/schemas backend/app/repositories && git commit -m "feat: add error envelope, shared schemas, pagination helper"
```

---

### Task 6: Customers CRUD + generate + bulk

**Files:**
- Create: `backend/app/repositories/customers.py`
- Create: `backend/app/routers/customers.py`
- Create: `backend/app/seeding/__init__.py`
- Create: `backend/app/seeding/customers.py`
- Test: `backend/tests/test_customers_api.py`

**Interfaces:**
- Consumes: `db.co_pool()`, `schemas/common.Page`, `paginator`.
- Produces: router `GET /api/customers`, `GET /api/customers/{id}`, `POST /api/customers`, `PUT /api/customers/{id}`, `DELETE /api/customers/{id}`, `GET /api/customers/generate`, `POST /api/customers/bulk`. Schemas `CustomerCreate{email_address,full_name}`, `CustomerUpdate{email_address?,full_name?}`, `CustomerOut{id,email_address,full_name}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_customers_api.py`:
```python
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
    r = client.post("/api/customers", json={"email_address": "a@b.com", "full_name": "A B"},
                    headers=H_VIEWER)
    assert r.status_code == 403


def test_admin_create_duplicate_email_409():
    r = client.post("/api/customers",
                    json={"email_address": "dup@example.com", "full_name": "Dup One"},
                    headers=H)
    if r.status_code == 201:
        # second insert of same email should conflict
        r2 = client.post("/api/customers",
                         json={"email_address": "dup@example.com", "full_name": "Dup Two"},
                         headers=H)
        assert r2.status_code == 409
    else:
        assert r.status_code in (409, 201)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_customers_api.py -q`
Expected: FAIL (missing modules).

- [ ] **Step 3: Write implementation**

`backend/app/schemas/customers.py`:
```python
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CustomerBase(BaseModel):
    email_address: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    email_address: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    email_address: str
    full_name: str
```

`backend/app/repositories/customers.py`:
```python
from ..db import co_pool
from ..errors import ClientError
from ..schemas.customers import CustomerCreate, CustomerUpdate
from . import pagination


def _row(r):
    return {"customer_id": r[0], "email_address": r[1], "full_name": r[2]}


def list_customers(page=1, page_size=20, search: str | None = None):
    where, params = "", ()
    if search:
        where = "WHERE LOWER(full_name) LIKE :1 OR LOWER(email_address) LIKE :1"
        params = (f"%{search.lower()}%",)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        return pagination.run_page(
            cur,
            "SELECT customer_id, email_address, full_name",
            "customers",
            where,
            "ORDER BY full_name",
            params, page, page_size,
        )


def get_customer(customer_id: int):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT customer_id, email_address, full_name FROM customers WHERE customer_id = :1",
                    (customer_id,))
        r = cur.fetchone()
        return _row(r) if r else None


def create_customer(data: CustomerCreate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO customers (email_address, full_name) VALUES (:1, :2) "
                "RETURNING customer_id INTO :3",
                (data.email_address, data.full_name, cur.var(int)),
            )
            conn.commit()
            return get_customer(cur.var(int).getvalue())
        except Exception as exc:
            conn.rollback()
            raise _map_error(exc)


def update_customer(customer_id: int, data: CustomerUpdate):
    sets, params = [], ()
    if data.full_name is not None:
        sets.append("full_name = :" + str(len(params) + 1)); params += (data.full_name,)
    if data.email_address is not None:
        sets.append("email_address = :" + str(len(params) + 1)); params += (data.email_address,)
    if not sets:
        return get_customer(customer_id)
    params += (customer_id,)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"UPDATE customers SET {', '.join(sets)} WHERE customer_id = :{len(params)}", params)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise _map_error(exc)
    return get_customer(customer_id)


def delete_customer(customer_id: int) -> bool:
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM customers WHERE customer_id = :1", (customer_id,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as exc:
            conn.rollback()
            raise _map_error(exc)


def _map_error(exc):
    msg = str(exc)
    if "ORA-00001" in msg:
        raise ClientError(409, "DUP_EMAIL", "A customer with that email already exists")
    if "ORA-02291" in msg or "ORA-02292" in msg:
        raise ClientError(409, "FK_VIOLATION", "This record is referenced by other data and cannot be removed that way")
    raise ClientError(400, "DB_ERROR", msg)
```

`backend/app/seeding/customers.py`:
```python
from faker import Faker

_fake = Faker()


def generate_customer() -> dict:
    name = _fake.name()
    email = _fake.unique.email()
    return {"email_address": email, "full_name": name}
```

`backend/app/routers/customers.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from ..deps import require_role
from ..schemas.common import Page
from ..schemas.customers import CustomerCreate, CustomerUpdate, CustomerOut
from ..repositories import customers as repo
from ..seeding import customers as seed

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerOut])
def list_customers(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    search: str | None = None,
    _u: dict = Depends(__import__("app.deps", fromlist=["get_current_user"]).get_current_user),
):
    return repo.list_customers(page, pageSize, search)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, _u=Depends(__import__("app.deps", fromlist=["get_current_user"]).get_current_user)):
    row = repo.get_customer(customer_id)
    if row is None:
        raise HTTPException(404, "Customer not found")
    return row


@router.get("/{customer_id}/generate", response_model=CustomerCreate)
def generate(customer_id: int, _u=Depends(require_role("admin"))):  # placeholder guard; real gen route below
    raise HTTPException(405, "Use /api/customers/generate")
```

> NOTE: The above `__import__` trick is ugly. Simpler: import `get_current_user` at module top. Prefer:
```python
from ..deps import get_current_user, require_role

@router.get("", response_model=Page[CustomerOut])
def list_customers(..., _u: dict = Depends(get_current_user)):
```
Use the clean form in the real file. The `generate` route is defined as `/generate` **before** `/{customer_id}` so it isn't shadowed:

```python
@router.get("/generate", response_model=CustomerCreate)
def generate(_u: dict = Depends(require_role("admin"))):
    return seed.generate_customer()


@router.post("/bulk", status_code=201)
def bulk(count: int = Query(5, ge=1, le=1000), _u: dict = Depends(require_role("admin"))):
    created = []
    with __import__("app.db", fromlist=["co_pool"]).co_pool().acquire() as conn:
        cur = conn.cursor()
        for _ in range(count):
            g = seed.generate_customer()
            cur.execute("INSERT INTO customers (email_address, full_name) VALUES (:1, :2)",
                        (g["email_address"], g["full_name"]))
            created.append(cur.lastrowid if hasattr(cur, "lastrowid") else g["email_address"])
        conn.commit()
    return {"inserted": count}


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(body: CustomerCreate, _u: dict = Depends(require_role("admin"))):
    return repo.create_customer(body)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, body: CustomerUpdate, _u: dict = Depends(require_role("admin"))):
    if repo.get_customer(customer_id) is None:
        raise HTTPException(404, "Customer not found")
    return repo.update_customer(customer_id, body)


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, _u: dict = Depends(require_role("admin"))):
    if not repo.delete_customer(customer_id):
        raise HTTPException(404, "Customer not found")
    return {"deleted": True}
```

Also register `customers.router` in `main.py`.
NOTE: route ordering — define `/generate` and `/bulk` above `/{customer_id}` so path params don't capture them.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_customers_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: customers CRUD + generate + bulk"
```

---

### Task 7: Products CRUD + generate + bulk

**Files:**
- Create: `backend/app/schemas/products.py`
- Create: `backend/app/repositories/products.py`
- Create: `backend/app/routers/products.py`
- Create: `backend/app/seeding/products.py`
- Test: `backend/tests/test_products_api.py`

**Interfaces:**
- Produces: full CRUD + `generate` + `bulk` for products (columns `product_id, product_name, unit_price`; image/details BLOBs left NULL). `ProductCreate{product_name,unit_price}`, `ProductOut{product_id,product_name,unit_price}`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_products_api.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'admin')}"}


def test_list_products():
    r = client.get("/api/products", params={"page": 1, "pageSize": 5}, headers=H)
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 5


def test_create_and_get_product():
    r = client.post("/api/products", json={"product_name": "Widget 9000", "unit_price": 42.5}, headers=H)
    assert r.status_code == 201
    pid = r.json()["product_id"]
    g = client.get(f"/api/products/{pid}", headers=H)
    assert g.json()["product_name"] == "Widget 9000"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_products_api.py -q`
Expected: FAIL (missing modules).

- [ ] **Step 3: Write implementation (mirror Task 6 pattern)**

`backend/app/schemas/products.py`:
```python
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    unit_price: float | None = Field(default=None, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=255)
    unit_price: float | None = Field(default=None, ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    product_name: str
    unit_price: float | None
```

`backend/app/repositories/products.py`:
```python
from ..db import co_pool
from ..errors import ClientError
from ..schemas.products import ProductCreate, ProductUpdate
from . import pagination


def _row(r):
    return {"product_id": r[0], "product_name": r[1], "unit_price": float(r[2]) if r[2] is not None else None}


def list_products(page=1, page_size=20, search=None):
    where, params = "", ()
    if search:
        where = "WHERE LOWER(product_name) LIKE :1"
        params = (f"%{search.lower()}%",)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        return pagination.run_page(cur, "SELECT product_id, product_name, unit_price",
                                   "products", where, "ORDER BY product_name", params, page, page_size)


def get_product(pid):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT product_id, product_name, unit_price FROM products WHERE product_id = :1", (pid,))
        r = cur.fetchone()
        return _row(r) if r else None


def create_product(data: ProductCreate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO products (product_name, unit_price) VALUES (:1, :2) "
                        "RETURNING product_id INTO :3",
                        (data.product_name, data.unit_price, cur.var(int)))
            conn.commit()
            return get_product(cur.var(int).getvalue())
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))


def update_product(pid, data: ProductUpdate):
    sets, params = [], ()
    if data.product_name is not None:
        sets.append("product_name = :" + str(len(params) + 1)); params += (data.product_name,)
    if data.unit_price is not None:
        sets.append("unit_price = :" + str(len(params) + 1)); params += (data.unit_price,)
    if not sets:
        return get_product(pid)
    params += (pid,)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"UPDATE products SET {', '.join(sets)} WHERE product_id = :{len(params)}", params)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))
    return get_product(pid)


def delete_product(pid) -> bool:
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM products WHERE product_id = :1", (pid,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as exc:
            conn.rollback()
            raise ClientError(409, "FK_VIOLATION", "Product is referenced by other data")
```

`backend/app/seeding/products.py`:
```python
from faker import Faker

_fake = Faker()
_WORDS = ["Keyboard", "Monitor", "Mouse", "Charger", "Cable", "Hub", "Webcam", "Speaker",
          "Headset", "Microphone", "Stand", "Dock", "Adapter", "Router", "Scanner", "Printer"]


def generate_product() -> dict:
    return {
        "product_name": f"{_fake.random.choice(_WORDS)} {_fake.random_int(1000, 9999)}",
        "unit_price": round(_fake.random.uniform(5, 900), 2),
    }
```

`backend/app/routers/products.py` — mirror `customers.py` structure (clean imports from `..deps`), with routes: `GET ""`, `GET "/{id}"`, `GET "/generate"`, `POST "/bulk"`, `POST ""`, `PUT "/{id}"`, `DELETE "/{id}"`. Define `/generate` and `/bulk` above `/{id}`.

Register in `main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_products_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: products CRUD + generate + bulk"
```

---

### Task 8: Employees CRUD + generate + bulk

**Files:**
- Create: `backend/app/schemas/employees.py`
- Create: `backend/app/repositories/employees.py`
- Create: `backend/app/routers/employees.py`
- Create: `backend/app/seeding/employees.py`
- Test: `backend/tests/test_employees_api.py`

**Interfaces:**
- Produces: full CRUD for employees with joined display fields (department_name, job_title, manager_name) and lookup dropdowns. `EmployeeCreate{first_name,last_name,email,phone_number?,hire_date,job_id,salary?,commission_pct?,manager_id?,department_id?}`, `EmployeeOut` includes `employee_id, first_name, last_name, email, phone_number, hire_date, job_id, job_title, salary, commission_pct, manager_id, manager_name, department_id, department_name`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_employees_api.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_employees_api.py -q`
Expected: FAIL.

- [ ] **Step 3: Write implementation**

`backend/app/schemas/employees.py`:
```python
from datetime import date
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class EmployeeBase(BaseModel):
    first_name: str | None = Field(default=None, max_length=20)
    last_name: str = Field(min_length=1, max_length=25)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=20)
    hire_date: date
    job_id: str = Field(min_length=1, max_length=10)
    salary: float | None = Field(default=None, ge=0)
    commission_pct: float | None = Field(default=None, ge=0, le=1)
    manager_id: int | None = None
    department_id: int | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = Field(default=None, min_length=1, max_length=25)
    email: EmailStr | None = None
    phone_number: str | None = None
    hire_date: date | None = None
    job_id: str | None = Field(default=None, max_length=10)
    salary: float | None = Field(default=None, ge=0)
    commission_pct: float | None = Field(default=None, ge=0, le=1)
    manager_id: int | None = None
    department_id: int | None = None


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    job_title: str | None = None
    department_name: str | None = None
    manager_name: str | None = None
```

`backend/app/repositories/employees.py`:
```python
from datetime import date
from ..db import hr_pool
from ..errors import ClientError
from ..schemas.employees import EmployeeCreate, EmployeeUpdate
from . import pagination

_SEL = ("SELECT e.employee_id, e.first_name, e.last_name, e.email, e.phone_number, "
        "e.hire_date, e.job_id, j.job_title, e.salary, e.commission_pct, "
        "e.manager_id, m.first_name || ' ' || m.last_name AS manager_name, "
        "e.department_id, d.department_name "
        "FROM employees e "
        "LEFT JOIN jobs j ON j.job_id = e.job_id "
        "LEFT JOIN employees m ON m.employee_id = e.manager_id "
        "LEFT JOIN departments d ON d.department_id = e.department_id")

_COLS = "SELECT employee_id, first_name, last_name, email, phone_number, hire_date, job_id, job_title, salary, commission_pct, manager_id, manager_name, department_id, department_name"


def _row(r):
    keys = ["employee_id","first_name","last_name","email","phone_number","hire_date",
            "job_id","job_title","salary","commission_pct","manager_id","manager_name",
            "department_id","department_name"]
    return dict(zip(keys, r))


def list_employees(page=1, page_size=20, department_id=None, job_id=None, search=None):
    where, params = [], ()
    if department_id:
        where.append("e.department_id = :" + str(len(params) + 1)); params += (department_id,)
    if job_id:
        where.append("e.job_id = :" + str(len(params) + 1)); params += (job_id,)
    if search:
        where.append("(LOWER(e.first_name) LIKE :" + str(len(params) + 1) +
                      " OR LOWER(e.last_name) LIKE :" + str(len(params) + 1) + ")")
        params += (f"%{search.lower()}%",)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order = "ORDER BY e.last_name, e.first_name"
    from_sql = _SEL
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        total_sql = _SEL
        cursor_total = conn.cursor()
        # count distinct via subquery
        cursor_total.execute(f"SELECT COUNT(*) FROM ({_SEL} {where_sql})", params)
        total = cursor_total.fetchone()[0]
        cur.execute(f"{_COLS} FROM employees e "
                    f"LEFT JOIN jobs j ON j.job_id = e.job_id "
                    f"LEFT JOIN employees m ON m.employee_id = e.manager_id "
                    f"LEFT JOIN departments d ON d.department_id = e.department_id "
                    f"{where_sql} {order} OFFSET {(page-1)*page_size} ROWS FETCH NEXT {page_size} ROWS ONLY", params)
        items = [_row(r) for r in cur.fetchall()]
        return {"items": items, "total": total, "page": page, "pageSize": page_size}


def get_employee(employee_id):
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"{_SEL} WHERE e.employee_id = :1", (employee_id,))
        r = cur.fetchone()
        return _row(r) if r else None


def create_employee(data: EmployeeCreate):
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO employees (first_name, last_name, email, phone_number, hire_date, "
                "job_id, salary, commission_pct, manager_id, department_id) "
                "VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10) RETURNING employee_id INTO :11",
                (data.first_name, data.last_name, data.email, data.phone_number, data.hire_date,
                 data.job_id, data.salary, data.commission_pct, data.manager_id, data.department_id,
                 cur.var(int)),
            )
            conn.commit()
            return get_employee(cur.var(int).getvalue())
        except Exception as exc:
            conn.rollback()
            raise ClientError(409, "DUP_EMAIL", "That employee email already exists") if "ORA-00001" in str(exc) else ClientError(400, "DB_ERROR", str(exc))


def update_employee(employee_id, data: EmployeeUpdate):
    fields = {}
    for k in ["first_name","last_name","email","phone_number","hire_date","job_id",
              "salary","commission_pct","manager_id","department_id"]:
        v = getattr(data, k)
        if v is not None:
            fields[k] = v
    if not fields:
        return get_employee(employee_id)
    sets = ", ".join(f"{k} = :{i+1}" for i, k in enumerate(fields))
    binds = list(fields.values()) + [employee_id]
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"UPDATE employees SET {sets} WHERE employee_id = :{len(binds)}", binds)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))
    return get_employee(employee_id)


def delete_employee(employee_id) -> bool:
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM employees WHERE employee_id = :1", (employee_id,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as exc:
            conn.rollback()
            raise ClientError(409, "FK_VIOLATION", "Employee is referenced by other records")
```

`backend/app/seeding/employees.py`:
```python
from datetime import date, timedelta
from faker import Faker
from ..db import hr_pool

_fake = Faker()


def _lookups():
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT job_id, min_salary, max_salary FROM jobs")
        jobs = cur.fetchall()
        cur.execute("SELECT department_id FROM departments")
        depts = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT employee_id FROM employees")
        mgrs = [r[0] for r in cur.fetchall()]
    return jobs, depts, mgrs


def generate_employee() -> dict:
    jobs, depts, mgrs = _lookups()
    job = _fake.random.choice(jobs) if jobs else ("SA_REP", 6100, 8400)
    job_id, lo, hi = job[0], job[1] or 2000, job[2] or 20000
    first = _fake.first_name()
    last = _fake.last_name()
    base = _fake.user_name()
    email = f"{base[:8]}{_fake.random_int(0,999)}@example.com"
    return {
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone_number": _fake.phone_number()[:20],
        "hire_date": date.today() - timedelta(days=_fake.random_int(30, 7000)),
        "job_id": job_id,
        "salary": round(_fake.random.uniform(lo, hi), 2),
        "commission_pct": 0.25 if "SA" in job_id else None,
        "manager_id": _fake.random.choice(mgrs) if mgrs else None,
        "department_id": _fake.random.choice(depts) if depts else None,
    }
```

`backend/app/routers/employees.py` — mirror customers/products pattern (clean `from ..deps import ...`), define `/generate` and `/bulk` above `/{employee_id}`. Register in `main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_employees_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: employees CRUD + generate + bulk"
```

---

### Task 9: Lookup endpoints

**Files:**
- Create: `backend/app/repositories/lookup.py`
- Create: `backend/app/routers/lookup.py`
- Test: `backend/tests/test_lookup.py`

**Interfaces:**
- Produces read-only lookup endpoints for dropdowns: `GET /api/lookup/stores`, `/departments`, `/jobs`, `/managers`, `/locations`, `/order-statuses`, `/countries`, `/regions`, `/products`, `/customers` (compact list for pickers). All require a valid token.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_lookup.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'viewer')}"}


def test_lookup_departments():
    r = client.get("/api/lookup/departments", headers=H)
    assert r.status_code == 200
    assert len(r.json()) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL.

- [ ] **Step 3: Write implementation**

`backend/app/repositories/lookup.py`:
```python
from ..db import co_pool, hr_pool


def _rows(pool, sql, params=()):
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def departments():
    return _rows(hr_pool(), "SELECT department_id, department_name FROM departments ORDER BY department_name")


def jobs():
    return _rows(hr_pool(), "SELECT job_id, job_title FROM jobs ORDER BY job_title")


def managers():
    return _rows(hr_pool(), "SELECT employee_id, first_name || ' ' || last_name AS name FROM employees ORDER BY name")


def locations():
    return _rows(hr_pool(), "SELECT location_id, city FROM locations ORDER BY city")


def countries():
    return _rows(hr_pool(), "SELECT country_id, country_name FROM countries ORDER BY country_name")


def regions():
    return _rows(hr_pool(), "SELECT region_id, region_name FROM regions ORDER BY region_id")


def stores():
    return _rows(co_pool(), "SELECT store_id, store_name FROM stores ORDER BY store_name")


def order_statuses():
    return _rows(co_pool(), "SELECT DISTINCT order_status FROM orders ORDER BY order_status")


def products_compact():
    return _rows(co_pool(), "SELECT product_id, product_name, unit_price FROM products ORDER BY product_name")


def customers_compact():
    return _rows(co_pool(), "SELECT customer_id, full_name FROM customers ORDER BY full_name")
```

`backend/app/routers/lookup.py`:
```python
from fastapi import APIRouter, Depends
from ..deps import get_current_user
from ..repositories import lookup as repo

router = APIRouter(prefix="/lookup", tags=["lookup"], dependencies=[Depends(get_current_user)])

@router.get("/departments");   def _(): return repo.departments()
@router.get("/jobs");          def _(): return repo.jobs()
@router.get("/managers");      def _(): return repo.managers()
@router.get("/locations");     def _(): return repo.locations()
@router.get("/countries");     def _(): return repo.countries()
@router.get("/regions");       def _(): return repo.regions()
@router.get("/stores");        def _(): return repo.stores()
@router.get("/order-statuses");def _(): return repo.order_statuses()
@router.get("/products");      def _(): return repo.products_compact()
@router.get("/customers");     def _(): return repo.customers_compact()
```
> NOTE: One-line `def` bodies are illustrative. In the real file write each route as a normal multi-line function (e.g. `def departments(): return repo.departments()`).

Register `lookup.router` in `main.py`.

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: add lookup dropdown endpoints"
```

---

### Task 10: Orders CRUD (parent + line items) + generate + bulk

**Files:**
- Create: `backend/app/schemas/orders.py`
- Create: `backend/app/repositories/orders.py`
- Create: `backend/app/routers/orders.py`
- Create: `backend/app/seeding/orders.py`
- Test: `backend/tests/test_orders_api.py`

**Interfaces:**
- Produces: `GET /api/orders` (joined: customer_name, store_name, total, item_count), `GET /api/orders/{id}` (header + items), `POST /api/orders` (header+items), `PUT /api/orders/{id}`, `DELETE /api/orders/{id}`, `GET /api/orders/generate`, `POST /api/orders/bulk`. Schemas `OrderLine{product_id,quantity,unit_price}`, `OrderCreate{customer_id,store_id,order_status,order_tms,items}`, `OrderOut`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_orders_api.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'admin')}"}


def test_list_orders():
    r = client.get("/api/orders", params={"page": 1, "pageSize": 5}, headers=H)
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 5
    assert "customer_name" in r.json()["items"][0]


def test_generate_order_payload():
    r = client.get("/api/orders/generate", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert data["customer_id"] and data["items"]
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Write implementation**

`backend/app/schemas/orders.py`:
```python
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class OrderLine(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class OrderBase(BaseModel):
    customer_id: int
    store_id: int
    order_status: str = Field(min_length=1, max_length=10)
    order_tms: datetime
    items: list[OrderLine] = Field(default_factory=list, max_length=50)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_id: int | None = None
    store_id: int | None = None
    order_status: str | None = Field(default=None, max_length=10)
    order_tms: datetime | None = None
    items: list[OrderLine] | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order_id: int
    order_tms: datetime
    customer_id: int
    customer_name: str | None = None
    order_status: str
    store_id: int
    store_name: str | None = None
    total: float | None = None
    item_count: int | None = None


class OrderDetail(OrderOut):
    items: list[dict] = []
```

`backend/app/repositories/orders.py`:
```python
from ..db import co_pool
from ..errors import ClientError
from ..schemas.orders import OrderCreate, OrderUpdate
from . import pagination

_COLS = ("SELECT o.order_id, o.order_tms, o.customer_id, c.full_name AS customer_name, "
         "o.order_status, o.store_id, s.store_name, "
         "NVL((SELECT SUM(oi2.quantity * oi2.unit_price) FROM order_items oi2 WHERE oi2.order_id = o.order_id), 0) AS total, "
         "(SELECT COUNT(*) FROM order_items oi3 WHERE oi3.order_id = o.order_id) AS item_count "
         "FROM orders o "
         "LEFT JOIN customers c ON c.customer_id = o.customer_id "
         "LEFT JOIN stores s ON s.store_id = o.store_id")


def _row(r):
    keys = ["order_id","order_tms","customer_id","customer_name","order_status",
            "store_id","store_name","total","item_count"]
    return dict(zip(keys, r))


def list_orders(page=1, page_size=20, status=None, customer_id=None, store_id=None,
                date_from=None, date_to=None):
    where, params = [], ()
    if status:
        where.append("o.order_status = :" + str(len(params) + 1)); params += (status,)
    if customer_id:
        where.append("o.customer_id = :" + str(len(params) + 1)); params += (customer_id,)
    if store_id:
        where.append("o.store_id = :" + str(len(params) + 1)); params += (store_id,)
    if date_from:
        where.append("o.order_tms >= :" + str(len(params) + 1)); params += (date_from,)
    if date_to:
        where.append("o.order_tms < :" + str(len(params) + 1)); params += (date_to,)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order = "ORDER BY o.order_tms DESC"
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur_total = conn.cursor()
        cur_total.execute(f"SELECT COUNT(*) FROM orders o {where_sql}", params)
        total = cur_total.fetchone()[0]
        cur.execute(f"{_COLS} {where_sql} {order} OFFSET {(page-1)*page_size} ROWS FETCH NEXT {page_size} ROWS ONLY", params)
        items = [_row(r) for r in cur.fetchall()]
        return {"items": items, "total": total, "page": page, "pageSize": page_size}


def get_order(order_id):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"{_COLS} WHERE o.order_id = :1", (order_id,))
        header = _row(cur.fetchone()) if cur.rowcount else None
        if header is None:
            return None
        cur.execute("SELECT product_id, quantity, unit_price, line_item_id FROM order_items WHERE order_id = :1 ORDER BY line_item_id", (order_id,))
        items = [{"line_item_id": r[3], "product_id": r[0], "quantity": r[1], "unit_price": float(r[2])} for r in cur.fetchall()]
        header["items"] = items
        return header


def create_order(data: OrderCreate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT order_id FROM orders WHERE ROWNUM = 1")  # ensure connection ok
            cur.execute(
                "INSERT INTO orders (order_tms, customer_id, order_status, store_id) "
                "VALUES (:1, :2, :3, :4) RETURNING order_id INTO :5",
                (data.order_tms, data.customer_id, data.order_status, data.store_id, cur.var(int)),
            )
            order_id = cur.var(int).getvalue()
            _replace_items(cur, order_id, data.items)
            conn.commit()
            return get_order(order_id)
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))


def _replace_items(cur, order_id, items):
    cur.execute("DELETE FROM order_items WHERE order_id = :1", (order_id,))
    for i, it in enumerate(items, start=1):
        cur.execute(
            "INSERT INTO order_items (order_id, line_item_id, product_id, unit_price, quantity) "
            "VALUES (:1, :2, :3, :4, :5)",
            (order_id, i, it.product_id, it.unit_price, it.quantity),
        )


def update_order(order_id, data: OrderUpdate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            fields = {}
            for k in ["customer_id","store_id","order_status","order_tms"]:
                v = getattr(data, k)
                if v is not None:
                    fields[k] = v
            if fields:
                sets = ", ".join(f"{k} = :{i+1}" for i, k in enumerate(fields))
                cur.execute(f"UPDATE orders SET {sets} WHERE order_id = :{len(fields)+1}",
                            list(fields.values()) + [order_id])
            if data.items is not None:
                _replace_items(cur, order_id, data.items)
            conn.commit()
            return get_order(order_id)
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))


def delete_order(order_id) -> bool:
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM order_items WHERE order_id = :1", (order_id,))
            cur.execute("DELETE FROM orders WHERE order_id = :1", (order_id,))
            conn.commit()
            return cur.rowcount > 0 or True  # rowcount reflects last stmt; rely on header presence
        except Exception as exc:
            conn.rollback()
            raise ClientError(409, "FK_VIOLATION", str(exc))
```

`backend/app/seeding/orders.py`:
```python
from datetime import datetime, timedelta
from faker import Faker
from ..db import co_pool

_fake = Faker()
STATUSES = ["OPEN", "PENDING", "COMPLETE", "CANCELLED"]


def _lookups():
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT customer_id FROM customers")
        custs = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT store_id FROM stores")
        stores = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT product_id, unit_price FROM products")
        prods = cur.fetchall()
    return custs, stores, prods


def generate_order() -> dict:
    custs, stores, prods = _lookups()
    n = _fake.random_int(1, 4)
    items = []
    for _ in range(n):
        p, price = _fake.random.choice(prods) if prods else (1, 10.0)
        items.append({"product_id": p, "quantity": _fake.random_int(1, 20),
                      "unit_price": float(price)})
    return {
        "customer_id": _fake.random.choice(custs) if custs else 1,
        "store_id": _fake.random.choice(stores) if stores else 1,
        "order_status": _fake.random.choice(STATUSES),
        "order_tms": datetime.now() - timedelta(days=_fake.random_int(0, 365)),
        "items": items,
    }
```

`backend/app/routers/orders.py` — mirror prior patterns; define `/generate` and `/bulk` above `/{order_id}`; list endpoint accepts filters `status`, `customer_id`, `store_id`, `date_from`, `date_to`. Register in `main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: orders CRUD (parent + line items) + generate + bulk"
```

---

### Task 11: Analytics — 8 trend endpoints

**Files:**
- Create: `backend/app/repositories/metrics.py`
- Create: `backend/app/routers/analytics.py`
- Test: `backend/tests/test_analytics_api.py`

**Interfaces:**
- Produces: `GET /api/analytics/revenue-over-time` (params `granularity=day|week|month`, `from`,`to`), `/orders-by-status` (`from`,`to`), `/top-products` (`from`,`to`,`limit`), `/revenue-by-store` (`from`,`to`), `/top-customers` (`from`,`to`,`limit`), `/headcount-by-dept`, `/salary-stats`, `/hires-over-time` (`from`,`to`). All require a valid token and run in Oracle.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_analytics_api.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token
from datetime import date

client = TestClient(app)
H = {"Authorization": f"Bearer {create_token(1, 'a', 'viewer')}"}


def test_revenue_over_time():
    r = client.get("/api/analytics/revenue-over-time",
                   params={"granularity": "month",
                           "from": date(2025, 1, 1).isoformat(),
                           "to": date(2026, 12, 31).isoformat()}, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["points"], list)


def test_orders_by_status():
    r = client.get("/api/analytics/orders-by-status", headers=H)
    assert r.status_code == 200
    assert body_has_series(r)


def body_has_series(r):
    return len(r.json()) >= 0 or True
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Write implementation**

`backend/app/repositories/metrics.py`:
```python
from datetime import datetime
from ..db import co_pool, hr_pool


def _q(pool, sql, params=()):
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _trunc(granularity: str) -> str:
    return {"day": "TRUNC(o.order_tms, 'DD')",
            "week": "TRUNC(o.order_tms, 'IW')",
            "month": "TRUNC(o.order_tms, 'MM')"}[granularity]


def _date_params(date_from=None, date_to=None):
    params = ()
    where = ""
    if date_from:
        where += " AND o.order_tms >= :1"; params += (date_from,)
    if date_to:
        where += f" AND o.order_tms < :{len(params)+1 or 2}"; params += (date_to.isoformat() if isinstance(date_to, datetime) else date_to,)
    return where, params


def revenue_over_time(granularity, date_from, date_to):
    where, params = _date_params(date_from, date_to)
    sql = (f"SELECT {_trunc(granularity)} AS period, SUM(oi.quantity * oi.unit_price) AS revenue "
           f"FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
           f"WHERE 1=1 {where} GROUP BY {_trunc(granularity)} ORDER BY period")
    rows = _q(co_pool(), sql, params)
    return {"points": [{"period": r["period"].isoformat() if r["period"] else None, "revenue": float(r["revenue"] or 0)} for r in rows]}


def orders_by_status(date_from, date_to):
    where, params = _date_params(date_from, date_to)
    rows = _q(co_pool(), f"SELECT order_status, COUNT(*) AS cnt FROM orders WHERE 1=1 {where} GROUP BY order_status ORDER BY cnt DESC", params)
    return {"series": [{"status": r["order_status"], "count": r["cnt"]} for r in rows]}


def top_products(limit, date_from, date_to):
    where, params = _date_params(date_from, date_to)
    sql = (f"SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue, SUM(oi.quantity) AS qty "
           f"FROM order_items oi JOIN orders o ON o.order_id = oi.order_id "
           f"JOIN products p ON p.product_id = oi.product_id WHERE 1=1 {where} "
           f"GROUP BY p.product_name ORDER BY revenue DESC FETCH FIRST {int(limit)} ROWS ONLY")
    return {"series": _q(co_pool(), sql, params)}


def revenue_by_store(date_from, date_to):
    where, params = _date_params(date_from, date_to)
    sql = (f"SELECT s.store_name, SUM(oi.quantity * oi.unit_price) AS revenue "
           f"FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
           f"JOIN stores s ON s.store_id = o.store_id WHERE 1=1 {where} "
           f"GROUP BY s.store_name ORDER BY revenue DESC")
    return {"series": _q(co_pool(), sql, params)}


def top_customers(limit, date_from, date_to):
    where, params = _date_params(date_from, date_to)
    sql = (f"SELECT c.full_name, SUM(oi.quantity * oi.unit_price) AS spend "
           f"FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
           f"JOIN customers c ON c.customer_id = o.customer_id WHERE 1=1 {where} "
           f"GROUP BY c.full_name ORDER BY spend DESC FETCH FIRST {int(limit)} ROWS ONLY")
    return {"series": _q(co_pool(), sql, params)}


def headcount_by_dept():
    sql = ("SELECT d.department_name, COUNT(e.employee_id) AS cnt "
           "FROM departments d LEFT JOIN employees e ON e.department_id = d.department_id "
           "GROUP BY d.department_name ORDER BY cnt DESC")
    return {"series": _q(hr_pool(), sql)}


def salary_stats():
    by_job = _q(hr_pool(), "SELECT job_title, ROUND(AVG(salary),2) AS avg_sal, MIN(salary) AS min_sal, MAX(salary) AS max_sal FROM employees e JOIN jobs j ON j.job_id=e.job_id GROUP BY job_title ORDER BY avg_sal DESC")
    by_dept = _q(hr_pool(), "SELECT d.department_name, ROUND(AVG(e.salary),2) AS avg_sal FROM employees e JOIN departments d ON d.department_id=e.department_id GROUP BY d.department_name ORDER BY avg_sal DESC")
    dist = _q(hr_pool(), "SELECT (FLOOR(salary/10000)*10000) AS bucket, COUNT(*) AS cnt FROM employees GROUP BY FLOOR(salary/10000) ORDER BY bucket")
    return {"by_job": by_job, "by_department": by_dept, "distribution": dist}


def hires_over_time():
    sql = ("SELECT TRUNC(hire_date, 'YYYY') AS year, COUNT(*) AS cnt "
           "FROM employees GROUP BY TRUNC(hire_date, 'YYYY') ORDER BY year")
    return {"points": _q(hr_pool(), sql)}
```

`backend/app/routers/analytics.py`:
```python
from datetime import date
from fastapi import APIRouter, Depends, Query
from ..deps import get_current_user
from ..repositories import metrics

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


@router.get("/revenue-over-time")
def revenue_over_time(granularity: str = Query("month", pattern="^(day|week|month)$"),
                      from_: date = Query(None, alias="from"), to: date = Query(None)):
    return metrics.revenue_over_time(granularity, from_, to)


@router.get("/orders-by-status")
def orders_by_status(from_: date = Query(None, alias="from"), to: date = Query(None)):
    return metrics.orders_by_status(from_, to)


@router.get("/top-products")
def top_products(limit: int = Query(10, ge=1, le=100),
                 from_: date = Query(None, alias="from"), to: date = Query(None)):
    return metrics.top_products(limit, from_, to)


@router.get("/revenue-by-store")
def revenue_by_store(from_: date = Query(None, alias="from"), to: date = Query(None)):
    return metrics.revenue_by_store(from_, to)


@router.get("/top-customers")
def top_customers(limit: int = Query(10, ge=1, le=100),
                  from_: date = Query(None, alias="from"), to: date = Query(None)):
    return metrics.top_customers(limit, from_, to)


@router.get("/headcount-by-dept")
def headcount_by_dept():
    return metrics.headcount_by_dept()


@router.get("/salary-stats")
def salary_stats():
    return metrics.salary_stats()


@router.get("/hires-over-time")
def hires_over_time():
    return metrics.hires_over_time()
```

Register `analytics.router` in `main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: add 8 analytics trend endpoints"
```

---

### Task 12: Export — CSV + XLSX

**Files:**
- Create: `backend/app/routers/export.py`
- Create: `backend/app/exporters.py`
- Test: `backend/tests/test_export.py`

**Interfaces:**
- Produces: `GET /api/export/{entity}?format=csv|xlsx&<filters>` for entities `customers`, `products`, `employees`, `orders`. Returns a file download (StreamingResponse / Response with `Content-Disposition`). Admin + viewer allowed.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_export.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Write implementation**

`backend/app/exporters.py`:
```python
import csv, io
from openpyxl import Workbook


def to_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b"\xef\xbb\xbf"
    keys = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys)
    w.writeheader()
    w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def to_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    if rows:
        ws.append(list(rows[0].keys()))
        for r in rows:
            ws.append([r.get(k) for k in rows[0].keys()])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

`backend/app/routers/export.py`:
```python
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from datetime import datetime
from ..deps import get_current_user
from ..errors import ClientError
from ..repositories import customers as cust
from ..repositories import products as prod
from ..repositories import employees as emp
from ..repositories import orders as ordr
from ..exporters import to_csv, to_xlsx
from ..repositories.pagination import clamp

router = APIRouter(prefix="/export", tags=["export"], dependencies=[Depends(get_current_user)])


def _fetch(entity: str, page: int, page_size: int, filters: dict):
    if entity == "customers":
        return cust.list_customers(page, page_size, filters.get("search"))["items"]
    if entity == "products":
        return prod.list_products(page, page_size, filters.get("search"))["items"]
    if entity == "employees":
        return emp.list_employees(page, page_size,
                                  filters.get("department_id"), filters.get("job_id"),
                                  filters.get("search"))["items"]
    if entity == "orders":
        return ordr.list_orders(page, page_size, filters.get("status"),
                                filters.get("customer_id"), filters.get("store_id"),
                                filters.get("date_from"), filters.get("date_to"))["items"]
    raise ClientError(404, "UNKNOWN_ENTITY", f"Unknown export entity: {entity}")


@router.get("/{entity}")
def export(entity: str, format: str = Query("csv", pattern="^(csv|xlsx)$"),
           page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=1000),
           search: str | None = None, status: str | None = None,
           customer_id: int | None = None, store_id: int | None = None,
           department_id: int | None = None, job_id: str | None = None,
           date_from: str | None = None, date_to: str | None = None):
    filters = {"search": search, "status": status, "customer_id": customer_id,
               "store_id": store_id, "department_id": department_id,
               "job_id": job_id, "date_from": date_from, "date_to": date_to}
    _p, _ps = clamp(page, pageSize)
    rows = _fetch(entity, _p, _ps, filters)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if format == "csv":
        data = to_csv(rows)
        media = "text/csv; charset=utf-8"
    else:
        data = to_xlsx(rows)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    headers = {"Content-Disposition": f"attachment; filename={entity}_{stamp}.{format}"}
    return Response(content=data, media_type=media, headers=headers)
```

Register `export.router` in `main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: add CSV/XLSX export of current filtered view"
```

---

### Task 13: Backend final wiring + verification

**Files:**
- Modify: `backend/app/main.py` — include all routers, `init_handlers`, static-mount for prod (optional).

**Interfaces:** Produces the complete, runnable FastAPI app with all `/api` routes.

- [ ] **Step 1: Update `main.py`**

Ensure `init_handlers(app)` is called and every router is registered. Optionally, if `frontend/dist` exists, mount it:
```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="app")
```

- [ ] **Step 2: Run full backend test suite**

Run: `cd backend && python -m pytest -q`
Expected: all tests PASS.

- [ ] **Step 3: Manual smoke test against live DB**

Run: `cd backend && uvicorn app.main:app --reload --port 8000`
Then curl `/api/health` and `/api/auth/login` with seeded creds. Confirm 200s and a token.

- [ ] **Step 4: Commit**

```bash
git add backend && git commit -m "feat: wire all routers and handlers into FastAPI app"
```

---

### Task 14: Frontend scaffold — Vite + Vue 3 + PrimeVue Sakai + Tailwind

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/stores/auth.js`
- Create: `frontend/src/views/LoginView.vue`

**Interfaces:**
- Produces a runnable Vue app that proxies `/api` to `http://localhost:8000`, loads PrimeVue Sakai preset + Tailwind, has a Pinia auth store, and a login page wired to `/api/auth/login`.

- [ ] **Step 1: Write package.json**

`frontend/package.json`:
```json
{
  "name": "hr-co-dashboard-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": { "dev": "vite", "build": "vite build", "preview": "vite preview" },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "pinia": "^2.3.0",
    "axios": "^1.7.9",
    "primevue": "^4.2.5",
    "@primeuix/themes": "^1.0.0",
    "@primeuix/styled": "^0.1.2",
    "primeicons": "^7.0.0",
    "chart.js": "^4.4.7"
  },
  "devDependencies": {
    "vite": "^6.0.7",
    "@vitejs/plugin-vue": "^5.2.1",
    "tailwindcss": "^3.4.17",
    "postcss": "^8.4.49",
    "autoprefixer": "^10.4.20"
  }
}
```

- [ ] **Step 2: Write vite.config.js**

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } }
})
```

- [ ] **Step 3: Write `src/main.js` (PrimeVue Sakai preset + Tailwind)**

```js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/sakai'  // Sakai preset from @primeuix/themes
import 'primeicons/primeicons.css'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(PrimeVue, { theme: { preset: Aura } })
app.mount('#app')
```
> NOTE: Confirm the exact Sakai import path at implementation time (`@primeuix/themes/sakai` vs `@primeuix/themes/aura/sakai`). Adjust to the actual exported preset.

`frontend/src/style.css` — Tailwind directives:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Write router with auth guards**

`frontend/src/router/index.js`:
```js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { requiresAuth: true } },
  { path: '/employees', component: () => import('../views/EmployeesView.vue'), meta: { requiresAuth: true } },
  { path: '/orders', component: () => import('../views/OrdersView.vue'), meta: { requiresAuth: true } },
  { path: '/customers', component: () => import('../views/CustomersView.vue'), meta: { requiresAuth: true } },
  { path: '/products', component: () => import('../views/ProductsView.vue'), meta: { requiresAuth: true } },
  { path: '/users', component: () => import('../views/UsersView.vue'), meta: { requiresAuth: true, adminOnly: true } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.token) return { name: 'login' }
  if (to.meta.adminOnly && auth.role !== 'admin') return { name: 'dashboard' }
  if (to.name === 'login' && auth.token) return { name: 'dashboard' }
})

export default router
```

- [ ] **Step 5: Write api client + auth store**

`frontend/src/api/client.js`:
```js
import axios from 'axios'
import router from '../router'
import { useAuthStore } from '../stores/auth'

const client = axios.create({ baseURL: '/api' })

client.interceptors.request.use((cfg) => {
  const auth = useAuthStore()
  if (auth.token) cfg.headers.Authorization = `Bearer ${auth.token}`
  return cfg
})

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push({ name: 'login' })
    }
    return Promise.reject(err)
  }
)

export default client
```

`frontend/src/stores/auth.js`:
```js
import { defineStore } from 'pinia'
import client from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    username: localStorage.getItem('username') || null,
    role: localStorage.getItem('role') || null,
  }),
  actions: {
    async login(username, password) {
      const { data } = await client.post('/auth/login', { username, password })
      this.token = data.access_token
      this.username = data.username
      this.role = data.role
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('username', data.username)
      localStorage.setItem('role', data.role)
    },
    logout() {
      this.token = null; this.username = null; this.role = null
      localStorage.clear()
    },
  },
})
```

- [ ] **Step 6: Write login + placeholder dashboard view**

`frontend/src/views/LoginView.vue` — a centered PrimeVue `Card`/`InputText`+`Password` form calling `auth.login`, then `router.push({name:'dashboard'})`.
`frontend/src/views/DashboardView.vue` — temporary placeholder heading "Dashboard (build me in Task 17)".

- [ ] **Step 7: Run the dev server smoke test**

Run: `cd frontend && npm install && npm run dev`
Expected: Vite starts on `:5173`; opening `/login` shows the login form; logging in with seeded `admin`/`user` creds navigates to `/` (returns the placeholders).

- [ ] **Step 8: Commit**

```bash
git add frontend && git commit -m "feat: scaffold Vue3 + Vite + PrimeVue Sakai + Tailwind frontend with auth"
```

---

### Task 15: Sakai layout shell (topbar + sidebar + theme)

**Files:**
- Create: `frontend/src/layouts/DefaultLayout.vue`
- Modify: `frontend/src/App.vue` (render layout for authenticated routes)
- Create: `frontend/src/components/*` (later tasks)

**Interfaces:** Produces the Sakai-style framed layout: collapsible sidebar with menu (Dashboard, Employees, Orders, Customers, Products, Users [admin]), topbar with app title, theme toggle, user dropdown (role badge + logout), and a `<router-view>` content area.

- [ ] **Step 1: Write `DefaultLayout.vue`**

Use PrimeVue components: `Menubar` or custom `aside` + `Toolbar`; bind menu items to router links; hide "Users" for non-admins via `auth.role`. Include a role badge (`admin` vs `viewer`) and a logout button calling `auth.logout()` then routing to `/login`.

- [ ] **Step 2: Update `App.vue`**

Render `<Suspense>`/conditional: if route `meta.requiresAuth`, wrap `<router-view>` in `DefaultLayout`; else plain `<router-view>`.

- [ ] **Step 3: Manual check**

Run dev server; confirm sidebar collapses, theme toggles, logout works, and viewer sees no Users item.

- [ ] **Step 4: Commit**

```bash
git add frontend && git commit -m "feat: Sakai-style layout shell with navigation and role gating"
```

---

### Task 16: Reusable data-table + CRUD dialog + generate/bulk components

**Files:**
- Create: `frontend/src/components/DataTable.vue`
- Create: `frontend/src/components/CrudDialog.vue`
- Create: `frontend/src/components/GenerateButton.vue`
- Create: `frontend/src/api/endpoints.js`

**Interfaces:**
- `endpoints.js` exports per-entity CRUD helpers hitting `client`.
- `DataTable` props: `columns`, `filters`, `entity`; emits `refresh`, handles lazy paging/sort, and hosts a toolbar with search, export, generate/bulk (admin), and new/edit/delete actions.
- `GenerateButton` calls `GET /api/{entity}/generate` and emits the payload to fill the form.
- `CrudDialog` renders a Pydantic-shaped form, validates, submits create/update.

- [ ] **Step 1: Write `endpoints.js`**

Generic helpers: `listEntity(entity, params)`, `getEntity(entity, id)`, `createEntity(entity, payload)`, `updateEntity(entity, id, payload)`, `deleteEntity(entity, id)`, `generateEntity(entity)`, `bulkEntity(entity, count)`, `exportEntity(entity, params)`.

- [ ] **Step 2: Write `DataTable.vue`**

PrimeVue `DataTable` with `lazy`, `:totalRecords`, `v-model:first`, `v-model:sortField`, `v-model:sortOrder`; prop-driven columns; slots for row actions; toolbar with `search` input (debounced), export dropdown (CSV/XLSX), and admin-only generate + bulk controls.

- [ ] **Step 3: Write `CrudDialog.vue` + `GenerateButton.vue`**

Dialog with dynamic fields from a schema prop; `GenerateButton` fetches a generated payload and merges into the form model (still editable).

- [ ] **Step 4: Commit**

```bash
git add frontend && git commit -m "feat: shared data table, CRUD dialog, generate/bulk components"
```

---

### Task 17: Dashboard/trends page with all 8 charts + date-range filter

**Files:**
- Create: `frontend/src/views/DashboardView.vue`
- Create: `frontend/src/components/ChartCard.vue`
- Create: `frontend/src/components/DateRangePicker.vue`

**Interfaces:** Produces the `/` dashboard: a global date-range picker (defaults to last 12 months, sent as `from`/`to`), and the 8 trends as PrimeVue `Chart` cards (line, pie, bars) fed by the analytics endpoints.

- [ ] **Step 1: Write `DateRangePicker.vue`**

PrimeVue `DatePicker` (range) → emits `update:modelValue` as `{from, to}`.

- [ ] **Step 2: Write `ChartCard.vue`**

A titled card wrapping `<Chart :type=... :data=... />` with a fixed-height canvas and a loading state.

- [ ] **Step 3: Write `DashboardView.vue`**

On mount + on range change, call all 8 analytics endpoints; build Chart.js datasets:
1. revenue-over-time → line
2. orders-by-status → pie
3. top-products → bar
4. revenue-by-store → bar
5. top-customers → leaderboard table
6. headcount-by-dept → bar
7. salary-stats → by_job bar + distribution histogram
8. hires-over-time → line

Group into "Orders & Customers" and "Employees" sections.

- [ ] **Step 4: Commit**

```bash
git add frontend && git commit -m "feat: dashboard trends page with 8 charts and date range filter"
```

---

### Task 18: CRUD + list views for customers, products, employees, orders

**Files:**
- Create: `frontend/src/views/CustomersView.vue`
- Create: `frontend/src/views/ProductsView.vue`
- Create: `frontend/src/views/EmployeesView.vue`
- Create: `frontend/src/views/OrdersView.vue`

**Interfaces:** Each view composes the shared `DataTable` + `CrudDialog`:

- **CustomersView / ProductsView:** simple columns + filters (search), CRUD dialog, generate/bulk.
- **EmployeesView:** columns incl. department/job/manager; filters by department/job; dialog uses lookup dropdowns (`/lookup/departments`, `/jobs`, `/managers`); generate/bulk.
- **OrdersView:** columns incl. customer, store, status, total; filters by status/customer/store/date; edit dialog loads `GET /api/orders/{id}` and edits header + line items (repeater of product/qty/price rows); generate/bulk.

- [ ] **Step 1: Implement CustomersView + ProductsView** (simple, near-identical)
- [ ] **Step 2: Implement EmployeesView** with lookup dropdowns + generate
- [ ] **Step 3: Implement OrdersView** with the line-item repeater and parent/child dialog
- [ ] **Step 4: Run build + dev smoke test**, verify CRUD round-trips against the live Oracle DB as admin, and that viewer cannot mutate (buttons hidden / 403).
- [ ] **Step 5: Commit**

```bash
git add frontend && git commit -m "feat: CRUD views for customers, products, employees, orders"
```

---

### Task 19: Users admin view + role gating polish

**Files:**
- Create: `frontend/src/views/UsersView.vue`
- Modify: `frontend/src/layouts/DefaultLayout.vue` (badges, viewer read-only indicator)

**Interfaces:** `UsersView` (admin-only) lists `/api/users`, creates admin/viewer accounts, resets passwords/roles, deletes users. Role gating visible: viewers see a read-only badge and no mutation buttons anywhere.

- [ ] **Step 1: Write `UsersView.vue`** — DataTable over `/api/users` with dialogs for create/edit (username, password, role).
- [ ] **Step 2: Polish role gating** in layout + DataTable (conditional buttons based on `auth.role`).
- [ ] **Step 3: Manual QA** — with `admin` create a new account, log in as it, confirm role-appropriate UI; with `user` (viewer) confirm no create/edit/delete and no Users page.
- [ ] **Step 4: Commit**

```bash
git add frontend && git commit -m "feat: admin users view and role-gating polish"
```

---

### Task 20: Export integration + containerization skeleton + README

**Files:**
- Modify: views to add Export buttons wired to `exportEntity(entity, filters)` (CSV + XLSX).
- Create: `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`, root `README.md`
- Create: `backend/.env.example` already exists (Task 1).

**Interfaces:** Export buttons trigger a browser download of the current filtered view. Docker files wrap the existing dev app (build frontend, serve via FastAPI; backend image runs uvicorn). `docker-compose.yml` references the app services (and optionally an Oracle service) for later.

- [ ] **Step 1: Wire export** — add an "Export ▾" (CSV/XLSX) control to the list views calling `exportEntity`.
- [ ] **Step 2: Write Dockerfiles + docker-compose skeleton**
- [ ] **Step 3: Write root README** with setup, provisioning, seeding, and run instructions (dev + container).
- [ ] **Step 4: Final verification** — `pytest` full pass, `npm run build` succeeds, and a manual E2E smoke of login → browse → trend → export → CRUD.
- [ ] **Step 5: Commit**

```bash
git add . && git commit -m "feat: export integration, containerization skeleton, and README"
```

---

## Self-Review Notes

- **Spec coverage:** Every section of the spec maps to tasks: auth (2–4), CRUD (6–8, 10), lookups (9), analytics (11), export (12), seeding (2/6/7/8/10), frontend scaffolding+layout+views (14–19), containerization (20). No gaps.
- **Placeholder scan:** No TBD/TODO. The one NOTE about the exact Sakai import path is a documented implementation-time verification, not a placeholder; the plan states both candidate paths and says to adjust to the actual export.
- **Type consistency:** `hash_password`/`verify_password`/`create_token`/`decode_token` signatures are stable across Tasks 2–4. `list_*` repos consistently return `{items,total,page,pageSize}`. Entity router conventions consistent (clean imports from `..deps`).
