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
    except Exception as exc:
        return {"status": "degraded", "database": None, "error": str(exc)}
