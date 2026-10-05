# Dashboard Auth Schema — Provisioning & Seeding

## Step 1 — Create the schema (once, as SYSTEM)

Run `provision_dashboard.sql` as a privileged user (e.g. SYSTEM). It creates the
`dashboard` user, grants privileges, then creates the `app_users` table and its
index in that schema.

## Step 2 — Seed the starter accounts

```bash
cd backend
# non-interactive (recommended for automation / CI)
DASH_ADMIN_PASSWORD='...' DASH_USER_PASSWORD='...' python -m seed.seed_users

# or interactive (prompts for both passwords)
python -m seed.seed_users
```

This creates/updates two starter accounts:
- `admin` — role `admin` (full CRUD)
- `user` — role `viewer` (read + export)

Passwords are bcrypt-hashed; the same command is safe to re-run to rotate the
starter passwords.
