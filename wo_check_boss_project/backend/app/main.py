"""API kiểm tra vật tư workorder.

Chạy: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import io
import os
import re
import shutil
import time
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from .auth import User, get_current_user
from .config import BASE_DIR, MAX_UPLOAD_MB
from .processing import pipeline
from .processing.ai import call_ai

app = FastAPI(title="Kiểm tra vật tư Workorder", docs_url="/api/docs", openapi_url="/api/openapi.json")
db.init()

STATUS_TEXT = {"new": "Chưa xử lý", "running": "Đang xử lý", "ok": "Khớp", "error": "Có lỗi", "failed": "Thất bại"}


def must_review(u: User):
    if not u.can_review:
        raise HTTPException(403, "Tài khoản của bạn không có quyền duyệt")


def get_or_404(wo_id):
    w = db.get_wo(wo_id)
    if not w:
        raise HTTPException(404, "Không tìm thấy workorder")
    return w


async def save_upload(up: UploadFile, path: str, exts: tuple):
    if not up.filename.lower().endswith(exts):
        raise HTTPException(400, f"File {up.filename} không đúng định dạng ({', '.join(exts)})")
    size, limit = 0, MAX_UPLOAD_MB * 1024 * 1024
    with open(path, "wb") as f:
        while chunk := await up.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                f.close()
                os.remove(path)
                raise HTTPException(413, f"File vượt quá {MAX_UPLOAD_MB} MB")
            f.write(chunk)


# ------------------------------------------------------------------ user
@app.get("/api/me")
def me(u: User = Depends(get_current_user)):
    return u.to_dict()


# ------------------------------------------------------------------ workorder
@app.get("/api/workorders")
def list_workorders(status: str = "", q: str = "", u: User = Depends(get_current_user)):
    return {"items": db.list_wos(status, q.strip()), "stats": db.stats()}


@app.post("/api/workorders")
async def create_workorder(wo: str = Form(...), description: str = Form(""), file: UploadFile = File(...),
                           pdf: Optional[UploadFile] = File(None), u: User = Depends(get_current_user)):
    wo = wo.strip()
    if not wo:
        raise HTTPException(400, "Thiếu mã workorder")
    wo_id = uuid.uuid4().hex[:12]
    d = pipeline.wo_dir(wo_id)
    os.makedirs(d)
    try:
        await save_upload(file, pipeline.source_path(wo_id), (".xlsx", ".xlsm"))
        pdf_name = None
        if pdf is not None and pdf.filename:
            ext = os.path.splitext(pdf.filename)[1].lower()
            await save_upload(pdf, os.path.join(d, "extra" + ext), (".pdf", ".png", ".jpg", ".jpeg"))
            pdf_name = pdf.filename
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise
    db.insert_wo(id=wo_id, wo=wo, description=description.strip(), created_by=u.username, created_by_name=u.name,
                 file_name=file.filename, pdf_name=pdf_name, status="new")
    pipeline.submit(wo_id)
    return db.get_wo(wo_id)


@app.get("/api/workorders/{wo_id}")
def get_workorder(wo_id: str, u: User = Depends(get_current_user)):
    return get_or_404(wo_id)


@app.post("/api/workorders/{wo_id}/rerun")
def rerun(wo_id: str, u: User = Depends(get_current_user)):
    w = get_or_404(wo_id)
    if w["status"] == "running":
        raise HTTPException(409, "Workorder đang được xử lý")
    pipeline.submit(wo_id)
    return db.get_wo(wo_id)


@app.post("/api/workorders/{wo_id}/file")
async def replace_file(wo_id: str, file: UploadFile = File(...), u: User = Depends(get_current_user)):
    w = get_or_404(wo_id)
    if w["status"] == "running":
        raise HTTPException(409, "Workorder đang được xử lý")
    await save_upload(file, pipeline.source_path(wo_id), (".xlsx", ".xlsm"))
    ex = pipeline.extra_path(wo_id)
    if ex:
        os.remove(ex)
    db.update_wo(wo_id, file_name=file.filename, pdf_name=None)
    pipeline.submit(wo_id)
    return db.get_wo(wo_id)


class ReviewIn(BaseModel):
    decision: str
    note: str = ""


@app.post("/api/workorders/{wo_id}/review")
def review(wo_id: str, body: ReviewIn, u: User = Depends(get_current_user)):
    must_review(u)
    w = get_or_404(wo_id)
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision phải là approved hoặc rejected")
    if w["status"] not in ("ok", "error"):
        raise HTTPException(409, "Chỉ duyệt được workorder đã có kết quả")
    db.update_wo(wo_id, review_decision=body.decision, review_by=u.username, review_by_name=u.name,
                 review_note=body.note.strip(), review_at=time.time())
    return db.get_wo(wo_id)


@app.delete("/api/workorders/{wo_id}")
def delete(wo_id: str, u: User = Depends(get_current_user)):
    w = get_or_404(wo_id)
    if w["created_by"] != u.username and not u.can_review:
        raise HTTPException(403, "Chỉ người tạo hoặc người duyệt được xoá")
    if w["status"] == "running":
        raise HTTPException(409, "Workorder đang được xử lý")
    db.delete_wo(wo_id)
    shutil.rmtree(pipeline.wo_dir(wo_id), ignore_errors=True)
    return {"ok": True}


@app.get("/api/workorders/{wo_id}/pages/{n}.jpg")
def page_image(wo_id: str, n: int, u: User = Depends(get_current_user)):
    p = pipeline.page_path(wo_id, n)
    if not os.path.exists(p):
        raise HTTPException(404, "Không có ảnh trang")
    return FileResponse(p, media_type="image/jpeg")


@app.get("/api/workorders/{wo_id}/source")
def download_source(wo_id: str, u: User = Depends(get_current_user)):
    w = get_or_404(wo_id)
    return FileResponse(pipeline.source_path(wo_id), filename=w["file_name"] or "workorder.xlsx")


# ------------------------------------------------------------------ xuất báo cáo
@app.get("/api/export")
def export(status: str = "", q: str = "", u: User = Depends(get_current_user)):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    fd = lambda t: time.strftime("%d/%m/%Y %H:%M", time.localtime(t)) if t else ""
    wb = Workbook()
    s1 = wb.active
    s1.title = "Tổng hợp"
    s1.append(["Workorder", "Mô tả", "File", "Người tạo", "TK người tạo", "Ngày tạo", "Kết quả AI", "Số lỗi",
               "Duyệt", "Người duyệt", "TK người duyệt", "Thời gian duyệt", "Ghi chú"])
    s2 = wb.create_sheet("Chi tiết lỗi")
    s2.append(["Workorder", "#", "Loại lỗi", "Bản vẽ", "Mã vật tư", "SL PDF", "SL Excel", "Trang", "Chi tiết"])
    for w in db.list_wos(status, q, limit=100000):
        rv = w["review"] or {}
        s1.append([w["wo"], w["description"], w["file_name"], w["created_by_name"], w["created_by"], fd(w["created_at"]),
                   STATUS_TEXT.get(w["status"], w["status"]), w["error_count"],
                   {"approved": "Đã duyệt", "rejected": "Từ chối"}.get(rv.get("decision"), ""),
                   rv.get("by_name") or "", rv.get("by") or "", fd(rv.get("at")), rv.get("note") or w["fail_reason"] or ""])
        if w["error_count"]:
            full = db.get_wo(w["id"])
            for i, e in enumerate((full["result"] or {}).get("errors", []), 1):
                s2.append([w["wo"], i, e["type"], e["dwg"], e["code"], e["pdf"], e["xl"], str(e["page"]), e["msg"]])
    for s in (s1, s2):
        for c in s[1]:
            c.font = Font(bold=True)
        for col in s.columns:
            s.column_dimensions[col[0].column_letter].width = min(45, max(10, *(len(str(c.value or "")) + 2 for c in col)))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = f"ket-qua-kiem-tra-WO_{time.strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


# ------------------------------------------------------------------ cài đặt
def public_settings(s):
    s = dict(s)
    s["api_key_set"] = bool(s.pop("api_key", ""))
    return s


@app.get("/api/settings")
def get_settings(u: User = Depends(get_current_user)):
    return public_settings(db.get_settings())


@app.put("/api/settings")
def put_settings(body: dict, u: User = Depends(get_current_user)):
    must_review(u)
    cur = db.get_settings()
    for k, v in body.items():
        if k not in cur:
            continue
        if k == "api_key" and v is None:  # None = giữ nguyên key cũ
            continue
        if isinstance(cur[k], bool):
            v = bool(v)
        elif isinstance(cur[k], int):
            v = int(v or 0)
        elif isinstance(v, str):
            v = v.strip()
        cur[k] = v
    for k in ("code_col", "first_col"):
        if cur[k] and not re.fullmatch(r"[A-Za-z]{1,3}", cur[k]):
            raise HTTPException(400, f"{k} phải là chữ cột Excel, ví dụ B")
    db.save_settings(cur)
    return public_settings(cur)


@app.post("/api/settings/test-ai")
def test_ai(u: User = Depends(get_current_user)):
    st = db.get_settings()
    try:
        t = call_ai({**st, "timeout": 60}, [{"type": "text", "text": "Trả lời đúng 1 từ: OK"}], 16)
        return {"ok": True, "reply": t[:100]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------------ giao diện (bản build Vue)
DIST = os.getenv("WO_FRONTEND_DIST", os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist"))
if os.path.isdir(DIST):
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")