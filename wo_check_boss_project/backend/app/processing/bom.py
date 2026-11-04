"""Đọc sheet danh sách vật tư: hàng = vật tư, mỗi cột = 1 số bản vẽ."""
import re

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

RE_CODE = re.compile(r"m[ãa]\s*(v[ậa]t\s*t[ưu]|vt|h[àa]ng|nvl|linh\s*ki[ệe]n)|material|part\s*(no|number|#)|item\s*(code|no)|^code$|^p/?n$|品番|物料", re.I)
RE_SKIP = re.compile(r"^(stt|no\.?|t[êe]n|name|m[ôo]\s*t[ảa]|desc|description|spec|quy\s*c[áa]ch|đvt|dvt|unit|uom|ghi\s*ch[úu]|note|remark|t[ổo]ng|total|sum|maker|nh[àa]\s*cung|vendor|lo[ạa]i|type)", re.I)


def col_idx(letter: str) -> int:
    letter = (letter or "").strip().upper()
    return column_index_from_string(letter) - 1 if letter else -1


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def parse_bom(path: str, st: dict):
    wb = load_workbook(path, read_only=True, data_only=True)
    names = wb.sheetnames
    if st.get("sheet"):
        f = [n for n in names if st["sheet"].lower() in n.lower()]
        names = f or names
    best = None
    for name in names:
        rows = [list(r) for r in wb[name].iter_rows(values_only=True)]
        if not rows:
            continue
        hdr = st["hdr"] - 1 if st.get("hdr") else -1
        code_col = col_idx(st.get("code_col"))
        if hdr < 0 or code_col < 0:
            for r in range(min(40, len(rows))):
                c = next((i for i, v in enumerate(rows[r]) if RE_CODE.search(_s(v))), -1)
                if c >= 0:
                    hdr = r if hdr < 0 else hdr
                    code_col = c if code_col < 0 else code_col
                    break
        if hdr < 0 or code_col < 0 or hdr >= len(rows):
            continue
        header = rows[hdr]
        first = col_idx(st.get("first_col"))
        dcols = []
        for c, v in enumerate(header):
            h = _s(v)
            if c == code_col or not h:
                continue
            if first >= 0:
                if c >= first:
                    dcols.append(c)
            elif c > code_col and not RE_SKIP.search(h) and not RE_CODE.search(h):
                dcols.append(c)
        items = []
        for r in range(hdr + 1, len(rows)):
            row = rows[r]
            code = _s(row[code_col]) if code_col < len(row) else ""
            if not code:
                continue
            items.append({"code": code, "row": r + 1, "cells": {c: (row[c] if c < len(row) else None) for c in dcols}})
        score = len(items) * len(dcols)
        if best is None or score > best["score"]:
            best = {"sheet": name, "hdr": hdr + 1, "code_col": code_col,
                    "dcols": [{"c": c, "col": get_column_letter(c + 1), "dwg": _s(header[c])} for c in dcols],
                    "items": items, "score": score}
    wb.close()
    return best