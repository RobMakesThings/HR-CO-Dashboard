import csv
import io

from openpyxl import Workbook


def _clean(rows: list[dict]) -> list[dict]:
    return [{k: ("" if v is None else v) for k, v in r.items()} for r in rows]


def to_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b"\xef\xbb\xbf"
    rows = _clean(rows)
    keys = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def to_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    if rows:
        keys = list(rows[0].keys())
        ws.append(keys)
        for r in _clean(rows):
            ws.append([r.get(k) for k in keys])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
