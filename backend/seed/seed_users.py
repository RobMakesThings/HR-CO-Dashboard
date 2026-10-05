"""Create/update the starter admin + viewer accounts.

Usage:
    python -m seed.seed_users                       # interactive prompts
    DASH_ADMIN_PASSWORD=x DASH_USER_PASSWORD=y python -m seed.seed_users
    python -m seed.seed_users <admin_pw> <viewer_pw>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import dash_pool
from app.security import hash_password


def upsert_user(conn, username: str, password: str, role: str):
    cur = conn.cursor()
    cur.execute("SELECT app_user_id FROM app_users WHERE username = :1", (username,))
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
    if len(sys.argv) >= 3:
        admin_pw, viewer_pw = sys.argv[1], sys.argv[2]
    else:
        admin_pw = os.environ.get("DASH_ADMIN_PASSWORD")
        viewer_pw = os.environ.get("DASH_USER_PASSWORD")
        if not admin_pw or not viewer_pw:
            admin_pw = input("Admin password: ").strip()
            viewer_pw = input("Viewer ('user') password: ").strip()

    with dash_pool().acquire() as conn:
        upsert_user(conn, "admin", admin_pw, "admin")
        upsert_user(conn, "user", viewer_pw, "viewer")
    print("Seeded: admin (admin), user (viewer)")


if __name__ == "__main__":
    main()
