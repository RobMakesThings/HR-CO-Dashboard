"""Offset-pagination helpers over parameterized Oracle SQL."""


def clamp(page: int, page_size: int) -> tuple[int, int]:
    return max(1, page), min(200, max(1, page_size))


def run_page(
    cursor,
    cols_sql: str,
    from_sql: str,
    where_sql: str,
    order_sql: str,
    params: tuple,
    page: int,
    page_size: int,
) -> dict:
    page, page_size = clamp(page, page_size)
    cursor.execute(f"SELECT COUNT(*) FROM {from_sql} {where_sql}", params)
    total = cursor.fetchone()[0]
    offset = (page - 1) * page_size
    cursor.execute(
        f"{cols_sql} FROM {from_sql} {where_sql} {order_sql} "
        f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY",
        params,
    )
    cols = [c[0].lower() for c in cursor.description]
    rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
    return {"items": rows, "total": total, "page": page, "pageSize": page_size}
