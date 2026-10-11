from __future__ import annotations

import oracledb
from .config import settings

_pools: dict[str, oracledb.Pool] = {}


def _pool(user: str, password: str) -> oracledb.Pool:
    if user not in _pools:
        _pools[user] = oracledb.create_pool(
            user=user, password=password, dsn=settings.oracle_dsn,
            min=1, max=10,
        )
    return _pools[user]


def co_pool() -> oracledb.Pool:
    return _pool(settings.oracle_co_user, settings.oracle_co_password)


def hr_pool() -> oracledb.Pool:
    return _pool(settings.oracle_hr_user, settings.oracle_hr_password)


def dash_pool() -> oracledb.Pool:
    return _pool(settings.oracle_dash_user, settings.oracle_dash_password)
