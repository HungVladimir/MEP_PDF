"""So sánh bảng vật tư AI đọc từ PDF với sheet danh sách vật tư trong Excel."""
import re

_DASH = str.maketrans({"‐": "-", "‑": "-", "–": "-", "—": "-"})


def norm_code(s):
    return re.sub(r"\s+", "", str(s if s is not None else "")).upper().translate(_DASH)


def loose_code(s):
    return re.sub(r"[^A-Z0-9?]", "", norm_code(s))


def norm_dwg(s):
    return re.sub(r"\s+", "", str(s if s is not None else "")).upper()


def loose_dwg(s):
    return re.sub(r"(^|[A-Z])0+(\d)", r"\1\2", re.sub(r"[^A-Z0-9]", "", norm_dwg(s)))


def num(v):
    if v is None or v == "" or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", "."))
    try:
        return float(s)
    except ValueError:
        return None


def empty(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def fmt(v):
    """Số nguyên hiển thị không có .0"""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def compare(pdf_drawings, bom, st):
    errors, groups = [], []

    # gộp bản vẽ trùng số (bảng kéo dài nhiều trang), cộng dồn mã trùng
    dmap = {}
    for d in pdf_drawings:
        k = loose_dwg(d.get("drawing_no")) or "(không rõ số)"
        g = dmap.setdefault(k, {"drawing_no": str(d.get("drawing_no") or "").strip() or "(không rõ số)", "pages": set(), "items": {}})
        g["pages"].add(d.get("page"))
        for it in d.get("items") or []:
            c = norm_code(it.get("code"))
            if not c:
                continue
            if c in g["items"]:
                g["items"][c]["qty"] = (g["items"][c]["qty"] or 0) + (num(it.get("qty")) or 0)
            else:
                g["items"][c] = {"code": str(it.get("code")).strip(), "name": it.get("name") or "", "qty": num(it.get("qty")), "page": d.get("page")}

    by_code = {norm_code(i["code"]): i for i in bom["items"]}
    by_loose = {loose_code(i["code"]): i for i in bom["items"]}
    col_by = {norm_dwg(d["dwg"]): d for d in bom["dcols"]}
    col_loose = {loose_dwg(d["dwg"]): d for d in bom["dcols"]}
    used = set()

    def err(t, dwg, code="", pdf="", xl="", page="", msg=""):
        errors.append({"type": t, "dwg": dwg, "code": code, "pdf": fmt(pdf), "xl": fmt(xl), "page": page, "msg": msg})

    for g in dmap.values():
        pages = ",".join(str(p) for p in sorted(x for x in g["pages"] if x is not None))
        col = col_by.get(norm_dwg(g["drawing_no"])) or col_loose.get(loose_dwg(g["drawing_no"]))
        if not col:
            err("Không có cột bản vẽ", g["drawing_no"], page=pages, msg="Excel không có cột cho số bản vẽ này")
            groups.append({"drawing_no": g["drawing_no"], "pages": pages, "col": None,
                           "rows": [{**it, "qty": fmt(it["qty"]), "xl": "", "ok": False, "why": "Không có cột", "cell": ""} for it in g["items"].values()]})
            continue
        used.add(col["c"])
        seen, rows = set(), []
        for it in g["items"].values():
            r = by_code.get(norm_code(it["code"])) or by_loose.get(loose_code(it["code"]))
            ok, why, xl = True, "", ""
            if "?" in it["code"]:
                ok, why = False, "AI đọc không rõ mã"
                err("Mã đọc không rõ", g["drawing_no"], it["code"], it["qty"], page=it["page"], msg="Cần người kiểm tra trực tiếp trên ảnh")
            elif not r:
                ok, why = False, "Không có trong Excel"
                err("Thiếu vật tư trong Excel", g["drawing_no"], it["code"], it["qty"], page=it["page"], msg="Mã có trong PDF nhưng không có dòng nào trong sheet")
            else:
                seen.add(r["row"])
                xl = r["cells"].get(col["c"])
                if empty(xl):
                    ok, why, xl = False, "Ô Excel trống", ""
                    err("Ô Excel trống", g["drawing_no"], it["code"], it["qty"], page=it["page"], msg=f"Ô {col['col']}{r['row']} để trống")
                elif st.get("compare_qty") and it["qty"] is not None and num(xl) is not None and abs(num(xl) - it["qty"]) > 1e-6:
                    ok, why = False, "Sai số lượng"
                    err("Sai số lượng", g["drawing_no"], it["code"], it["qty"], xl, it["page"], f"PDF {fmt(it['qty'])} ≠ Excel {fmt(xl)} (ô {col['col']}{r['row']})")
            rows.append({**it, "qty": fmt(it["qty"]), "xl": fmt(xl) if xl is not None else "", "ok": ok, "why": why,
                         "cell": f"{col['col']}{r['row']}" if r else ""})
        for r in bom["items"]:
            v = r["cells"].get(col["c"])
            if not empty(v) and r["row"] not in seen and num(v) != 0:
                err("Excel thừa vật tư", g["drawing_no"], r["code"], "", v, pages, f"Ô {col['col']}{r['row']} có giá trị nhưng PDF không có mã này")
                rows.append({"code": r["code"], "name": "", "qty": None, "xl": fmt(v), "ok": False, "why": "Excel thừa", "cell": f"{col['col']}{r['row']}", "page": ""})
        groups.append({"drawing_no": g["drawing_no"], "pages": pages, "col": col["col"], "rows": rows})

    if st.get("missing_col_is_error"):
        for d in bom["dcols"]:
            if d["c"] in used:
                continue
            if any(not empty(r["cells"].get(d["c"])) for r in bom["items"]):
                err("Bản vẽ không có trong PDF", d["dwg"], msg=f"Cột {d['col']} (bản vẽ {d['dwg']}) có dữ liệu nhưng AI không thấy bản vẽ này trong PDF")

    return {"errors": errors, "groups": groups, "pdf_drawings": len(dmap),
            "pdf_items": sum(len(g["items"]) for g in dmap.values())}