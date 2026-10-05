# HR + CO Dashboard

A role-based web dashboard over the Oracle **Human Resources (`HR`)** and
**Customer Orders (`CO`)** sample schemas — browse, create, update and delete
records, view business trends, seed procedural test data, and export the
current filtered view.

- **Backend:** FastAPI + `oracledb` (thin mode, no Oracle client needed)
- **Frontend:** Vue 3 + Vite + PrimeVue 4 (Sakai template) + Tailwind CSS
- **Auth:** JWT + bcrypt, `admin` / `viewer` roles (app-level `dashboard` schema)
- **Data:** Oracle 23c at `localhost:1521/FREEPDB1` (CO + HR + dashboard schemas)

## Layout

```
backend/              FastAPI app (routers, repositories, schemas, seeding, export)
frontend/             Vue 3 SPA (Sakai layout + views + API client)
docs/superpowers/     design spec + implementation plan
Dockerfile            multi-stage build -> single container serving app on :8000
docker-compose.yml    containerization skeleton
```

## Prerequisites

- Python 3.12 (backend)
- Node 20+ / npm (frontend)
- Oracle instance (Docker container works) with CO, HR and the `dashboard`
  schema installed and reachable.

## 1. Provision the auth schema (once, as SYSTEM)

```bash
cd backend
DASH_ADMIN_PASSWORD='...' DASH_USER_PASSWORD='...' python -m seed.provision_dashboard
```

Creates the `dashboard` user, the `app_users` table, and seeds the two starter
accounts (`admin` = admin role, `user` = viewer role). The same command is safe
to re-run to rotate the starter passwords. The standalone SQL is in
`backend/seed/provision_dashboard.sql`.

## 2. Configure the backend

```bash
cd backend
cp .env.example .env    # then edit ORACLE_* / JWT_SECRET
pip install -r requirements.txt
python -m seed.provision_dashboard   # if not done in step 1
```

## 3. Run (development)

```bash
# terminal 1 — backend :8000
cd backend
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend :5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in with `admin` / `user` (use the passwords
you chose during provisioning).

> **Note:** if port 8000 is already in use by another process on this machine,
> the backend will fail to bind. Either stop that process or change the backend
> port with `--port <n>` and update the `/api` proxy in `frontend/vite.config.mjs`.

## 4. Run (container)

```bash
docker compose up --build
```

The single container serves the built frontend and the API on `:8000`. It
expects Oracle on the host via `host.docker.internal` (override with
`ORACLE_DSN`).

## Features

- **CRUD (admin):** employees, orders (header + line items in one transaction),
  customers, products. Everything else is read-only reference/lookup data.
- **Seeding:** "Generate" fills a create/edit form with valid random values
  (fully editable before save); "Bulk add" inserts N random rows.
- **Trends:** 8 server-side charts (revenue over time, orders by status, top
  products, revenue by store, top customers, headcount by department, salary
  stats, hires over time) with a global date-range filter.
- **Export:** CSV (UTF-8 BOM) and XLSX of the current filtered view — admin and
  viewer.
- **Roles:** `admin` = everything; `viewer` = read + export only (`403` on
  mutations, mutation controls hidden).

## Tests

```bash
cd backend
python -m pytest -q
```

The suite exercises auth, CRUD round-trips, analytics, and export against the
live Oracle instance (read-oriented; mutation tests clean up after themselves).

## API overview

`/api/health` · `/api/auth/login` · `/api/users` (admin)
`/api/customers` · `/api/products` · `/api/employees` · `/api/orders` (CRUD +
`/generate`, `/bulk`)
`/api/lookup/*` (dropdowns) · `/api/analytics/*` (8 trends) · `/api/export/{entity}`
