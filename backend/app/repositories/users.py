from ..db import dash_pool
from ..errors import ClientError
from ..schemas.auth import UserCreate, UserUpdate
from ..security import hash_password

_COLS = "app_user_id, username, password_hash, role, created_at"


def _row(r) -> dict | None:
    if r is None:
        return None
    return {
        "app_user_id": r[0],
        "username": r[1],
        "password_hash": r[2],
        "role": r[3],
        "created_at": r[4].isoformat() if r[4] else None,
    }


def _public(r) -> dict | None:
    u = _row(r)
    if u is None:
        return None
    u.pop("password_hash", None)
    return u


def find_by_username(username: str) -> dict | None:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {_COLS} FROM app_users WHERE username = :1", (username,))
        return _row(cur.fetchone())


def get_user(user_id: int) -> dict | None:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {_COLS} FROM app_users WHERE app_user_id = :1", (user_id,))
        return _public(cur.fetchone())


def list_users() -> list[dict]:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {_COLS} FROM app_users ORDER BY username")
        return [_public(r) for r in cur.fetchall()]


def create_user(data: UserCreate) -> dict:
    with dash_pool().acquire() as conn:
        cur = conn.cursor()
        uid = cur.var(int)
        try:
            cur.execute(
                "INSERT INTO app_users (username, password_hash, role) "
                "VALUES (:1, :2, :3) RETURNING app_user_id INTO :4",
                (data.username, hash_password(data.password), data.role, uid),
            )
            conn.commit()
            return get_user(uid.getvalue())
        except Exception as exc:
            conn.rollback()
            if "ORA-00001" in str(exc):
                raise ClientError(409, "DUP_USER", "Username already exists")
            raise ClientError(400, "DB_ERROR", str(exc))


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
