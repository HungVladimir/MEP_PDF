
"""
Invoice AI - backend
Người dùng upload hoá đơn ChatGPT / Claude / Gemini -> model vision (vLLM, OpenAI-compatible)
đọc email, số tiền, ngày... -> admin xem tổng hợp và xác nhận.

Lưu ý:
  - CRUD dữ liệu     -> Oracle qua `dataman.sql_execute`, action nằm trong
                        `database/query/menu_operation/ai_bill/invoiceCheck.py`
                        (prefix `menu_operation.ai_bill.invoiceCheck:`).
  - Ảnh / PDF upload -> **MinIO** (pattern y hệt `router/minio/visionGuard.py`)
                        bucket = `settings.minio_bucketname` (enV: `oneai`)
                        Object key : `aibill/<month>/<inv_id><ext>`
                        Cột FILE_PATH của AI_INVOICE_CHECK lưu **object_key MinIO**.
  - Bảng `LOCAL_AI.AI_INVOICE_CHECK` đã có sẵn; app KHÔNG tạo / không DROP.
"""
import base64
import csv
import io
import json
import os
import re
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse, Response
from openai import OpenAI
from pydantic import BaseModel
from minio.error import S3Error
from starlette.concurrency import run_in_threadpool
import httpx

from logs import logger
from database import dataman
from minio_object import minio_object
from router.auth import validate_token

load_dotenv()

# ---------------------------------------------------------------- cấu hình
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")
ALLOWED_DOMAINS = [d.strip().lower() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()]
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", 10))

# --- MinIO (chỗ chứa HOÁ ĐƠN ẢNH/PDF) ---
MINIO_PREFIX = "aibill"       # object key = aibill/<month>/<inv_id><ext>


def get_client() -> OpenAI:
    """Tạo OpenAI client khi thực sự gọi model, để backend vẫn khởi động được
    khi chưa cấu hình LLM (LLM_BASE_URL / LLM_API_KEY / LLM_MODEL)."""
    if not (LLM_BASE_URL and LLM_API_KEY and LLM_MODEL):
        raise RuntimeError("Chưa cấu hình LLM_BASE_URL / LLM_API_KEY / LLM_MODEL trong .env")
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY,
                  http_client=httpx.Client(trust_env=False, timeout=None))


aiBill_router = APIRouter(prefix="/ai_bill", tags=["ai bill"], dependencies=[Depends(validate_token)])

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "application/pdf"}
EDITABLE = ["provider", "invoice_number", "invoice_date", "billing_email", "amount", "plan"]

# action_id prefix. Mọi CRUD đi qua dataman.sql_execute theo pattern humanoid/mcr.
_A = "menu_operation.ai_bill.invoiceCheck:"


def _who(user):
    # Knox ID (sub) tu id_token; None neu goi bang API key
    sub = user.get("sub") if isinstance(user, dict) else None
    return str(sub).strip() if sub else None

# ---------------------------------------------------------------- DB helper
def _read_lob(v):
    """cx_Oracle CLOB trả về object có .read(); chuẩn về str để JSON-able."""
    if v is not None and hasattr(v, "read") and not isinstance(v, (str, bytes, bytearray)):
        try:
            return v.read()
        except Exception:
            return v
    return v


def _db(act_id: str, params=None, one: bool = False):
    """Gọi dataman.sql_execute, chuẩn hoá key lower_snake + handle error.
    `dataman.sql_execute` trả list[dict] khi OK, trả str khi lỗi (xem base.py)."""
    res = dataman.sql_execute(act_id=_A + act_id, params=params or {})
    if isinstance(res, str):                       # DataMan trả str khi exception
        logger.error(f"[ai_bill] {act_id} -> {res}")
        raise HTTPException(500, f"Lỗi DB ({act_id}): {res}")
    rows = [{(k or "").lower(): _read_lob(v) for k, v in (r or {}).items()} for r in (res or [])]
    if one:
        return rows[0] if rows else None
    return rows


def out(row: dict) -> dict:
    """Bỏ các cột nội bộ, parse warnings."""
    if not row:
        return row
    r = {k: v for k, v in row.items() if k not in ("file_path", "delete_token", "ai_raw", "currency")}
    r["warnings"] = json.loads(r.get("warnings") or "[]")
    return r


# ---------------------------------------------------------------- Oracle bridge
#   Mọi CRUD dữ liệu -> dataman.sql_execute() vào module query:
#     "menu_operation.ai_bill.invoiceCheck:<query_name>"
#   Bảng      : LOCAL_AI.AI_INVOICE_CHECK (phải có sẵn; app KHÔNG tạo/DROP)
#   DNS       : theo settings.env["dns"]  (dev=MBLDB / prod=MBAYMS, user LOCAL_AI)


# ---------------------------------------------------------------- MinIO bridge
#   Ảnh/PDF upload trực tiếp lên MinIO theo pattern visionGuard.py:
#     - put_object / remove_object / open_object+stream_object / download_bytes
#     - mọi thao tác IO chạy trong threadpool (starlette.concurrency)
#   Object key : `aibill/<month>/<inv_id><ext>`  (luôn dùng "/" Posix style)
#   Cột FILE_PATH của AI_INVOICE_CHECK chứa đúng object-key này.
def _obj_key(month: str, inv_id: str, ext: str) -> str:
    """aibill/<month>/<inv_id><ext> (vd: aibill/2026-10/abc123.png)."""
    return f"{MINIO_PREFIX}/{month}/{inv_id}{ext}"


def _minio_put(*, object_key: str, content: bytes, content_type: str):
    """Uploadbytes-> MinIO. Wrapper quanh `minio_object.client.put_object`
    (giữ đúng pattern ở `router/minio/visionGuard.py::upload_to_minio`)."""
    try:
        return minio_object.client.put_object(
            bucket_name=minio_object.bucket_name,
            object_name=object_key,
            data=io.BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )
    except S3Error as exc:
        raise RuntimeError(f"Không thể upload ảnh lên MinIO: {exc.message}") from exc


def _minio_delete(object_key: str) -> None:
    """Xoá object MinIO. Nuốt im lặng nếu object_key rỗng."""
    if not object_key:
        return
    try:
        minio_object.client.remove_object(
            bucket_name=minio_object.bucket_name,
            object_name=object_key,
        )
    except S3Error as exc:
        raise RuntimeError(f"Không thể xoá object MinIO: {exc.message}") from exc


def _minio_bytes(object_key: str) -> bytes:
    """Đọc toàn bộ object về bytes (dùng khi AI cần đọc nội dung ảnh/PDF)."""
    if not object_key:
        raise RuntimeError("Thiếu object_key MinIO")
    return minio_object.download_bytes(object_key)


# ---------------------------------------------------------------- AI
SYSTEM_PROMPT = """Bạn là trợ lý đọc hoá đơn/biên lai thanh toán dịch vụ AI (ChatGPT/OpenAI, Claude/Anthropic, Gemini/Google, Other).
Hãy đọc ảnh và trả về DUY NHẤT một JSON object (không markdown, không giải thích) với các khoá:
- "is_invoice": true nếu đây là hoá đơn/biên lai thanh toán, ngược lại false
- "provider": một trong "ChatGPT", "Claude", "Gemini", "Other"
- "invoice_number": ID đơn hàng/số hoá đơn/receipt number, hoặc null
- "invoice_date": ngày thanh toán/ngày xuất hoá đơn dạng "YYYY-MM-DD", hoặc null
- "billing_email": email của tài khoản/người được tính tiền ghi trên hoá đơn (KHÔNG lấy email của nhà cung cấp như support@, billing@openai.com...), hoặc null
- "amount": TỔNG số tiền đã thanh toán (Amount paid / Total, tổng cộng, tổng cộng đã gồm thuế), dạng số, không ký hiệu tiền tệ, không làm tròn, hoặc null
- "plan": tên gói, ví dụ "ChatGPT Plus", "Claude Pro", "Google AI Pro", hoặc null
- "notes": ghi chú ngắn nếu có điều bất thường, hoặc null
Quy tắc:
- Chỉ sử dụng thông tin thực sự đọc được từ ảnh.
- Không suy đoán hoặc tự tạo dữ liệu. Chỗ nào không đọc rõ thì để null
- Không nhầm ID đơn hàng với ID giao dịch.
- Không nhầm ngày tạo đơn với ngày thanh toán.
- Không nhầm giá gốc với số tiền thực tế đã thanh toán."""


def shrink_image(data: bytes) -> tuple[str, bytes]:
    """Xoay đúng chiều + thu nhỏ ảnh để model đọc nhanh, ít token."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    im.thumbnail((1800, 1800))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return "image/jpeg", buf.getvalue()


def load_for_ai(content: bytes, mime: str) -> tuple[list[tuple[str, bytes]], str]:
    """Trả về (danh sách ảnh, text trích từ PDF). `content` = bytes đã download từ MinIO."""
    if mime == "application/pdf":
        import fitz  # pymupdf
        images, text = [], ""
        with fitz.open(stream=content, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                if i >= 2:  # hoá đơn thường 1-2 trang
                    break
                text += page.get_text()
                images.append(("image/png", page.get_pixmap(dpi=150).tobytes("png")))
        return images, text.strip()
    return [shrink_image(content)], ""


def parse_json(raw: str) -> dict:
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)  # model có chế độ thinking
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Model không trả về JSON")
    return json.loads(raw[start:end + 1])


def to_number(v) -> Optional[float]:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.,-]", "", str(v))
    if "," in s and "." not in s and len(s.split(",")[-1]) == 2:
        s = s.replace(",", ".")  # 20,00 -> 20.00
    else:
        if s.count(".") > 1:
            s = s.replace(".", "")  # 1.000.000 -> 1000000 (dấu phân cách hàng nghìn kiểu VND)
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def norm_provider(p: Optional[str], plan: Optional[str]) -> str:
    s = f"{p or ''} {plan or ''}".lower()
    if any(k in s for k in ("chatgpt", "openai")):
        return "ChatGPT"
    if any(k in s for k in ("claude", "anthropic")):
        return "Claude"
    if any(k in s for k in ("gemini", "google")):
        return "Gemini"
    return "Other"


def run_ai(object_key: str, mime: str) -> tuple[str, dict]:
    """Tải ảnh/PDF từ MinIO theo object_key -> gửi model vision."""
    images, pdf_text = load_for_ai(_minio_bytes(object_key), mime)
    text = "Đọc hoá đơn này và trả về JSON."
    if pdf_text:
        text += "\n\nText trích từ PDF (dùng để đối chiếu):\n" + pdf_text[:4000]
    content = [{"type": "text", "text": text}]
    for m, data in images:
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{m};base64,{base64.b64encode(data).decode()}"}})
    resp = get_client().chat.completions.create(
        model=LLM_MODEL, temperature=0, max_tokens=1500,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}],
    )
    raw = resp.choices[0].message.content or ""
    data = parse_json(raw)
    data["amount"] = to_number(data.get("amount"))
    data["provider"] = norm_provider(data.get("provider"), data.get("plan"))
    if data.get("billing_email"):
        data["billing_email"] = str(data["billing_email"]).strip().lower()
    return raw, data


# ---------------------------------------------------------------- kiểm tra
def validate(row: dict, extra: Optional[list] = None) -> tuple[int, list]:
    """Tính email_match + danh sách cảnh báo từ dữ liệu hiện tại của hoá đơn."""
    w = list(extra or [])
    be = (row.get("billing_email") or "").strip().lower()
    se = (row.get("submitter_email") or "").strip().lower()
    match = int(bool(be) and be == se)
    if not be:
        w.append("Không đọc được email trên hoá đơn")
    elif not match:
        w.append(f"Email trên hoá đơn ({be}) khác email người gửi ({se})")
    if be and ALLOWED_DOMAINS and be.split("@")[-1] not in ALLOWED_DOMAINS:
        w.append(f"Email {be} không thuộc domain cho phép")
    if row.get("amount") is None:
        w.append("Không đọc được số tiền")
    d, m = row.get("invoice_date"), row.get("month")
    if d and m and not str(d).startswith(m):
        w.append(f"Ngày hoá đơn {d} không thuộc tháng {m}")
    if row.get("provider") == "Other":
        w.append("Không phải hoá đơn ChatGPT / Claude / Gemini")
    if row.get("invoice_number"):
        dup = _db("countDupInvoiceNumber",
                  dict(INVOICE_NUMBER=row["invoice_number"], PROVIDER=row.get("provider"), ID=row["id"]),
                  one=True)
        if dup:
            w.append(f"Trùng số hoá đơn với hoá đơn của {dup['submitter_name']}")
    return match, w


def analyze_and_save(row: dict):
    extra = []
    try:
        raw, data = run_ai(row["file_path"], row["mime"])
        if data.get("is_invoice") is False:
            extra.append("AI cho rằng ảnh này không phải hoá đơn")
        if data.get("notes"):
            extra.append(f"AI ghi chú: {data['notes']}")
        for k in EDITABLE:
            row[k] = data.get(k)
    except Exception as e:  # lỗi AI vẫn lưu để admin nhập tay
        raw = f"ERROR: {e}"
        extra.append(f"AI lỗi, cần admin nhập tay: {e}")
        for k in EDITABLE:
            row.setdefault(k, None)
    match, warnings = validate(row, extra)
    _db("updateAnalysis", {
        "PROVIDER":       row.get("provider"),
        "INVOICE_NUMBER": row.get("invoice_number"),
        "INVOICE_DATE":   row.get("invoice_date"),
        "BILLING_EMAIL":  row.get("billing_email"),
        "AMOUNT":         row.get("amount"),
        "PLAN":           row.get("plan"),
        "EMAIL_MATCH":    match,
        "WARNINGS":       json.dumps(warnings, ensure_ascii=False),
        "AI_RAW":         raw,
        "ID":             row["id"],
    })


# ---------------------------------------------------------------- API người dùng
@aiBill_router.post("/invoices")
async def upload_invoice(name: str = Form(...), email: str = Form(...), userid: str = Form(...), month: str = Form(...),
                         file: UploadFile = File(...), user=Depends(validate_token)):
    email = email.strip().lower()
    userid = userid.strip()
    actor = _who(user)
    if actor:
        if userid and userid != actor:
            raise HTTPException(403, "USERID khong khop tai khoan dang nhap")
        userid = actor
    elif not userid:
        raise HTTPException(400, "Thieu USERID khi goi qua API key")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Email không hợp lệ")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(400, "Tháng phải dạng YYYY-MM")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, "Chỉ nhận ảnh PNG/JPG/WEBP hoặc PDF")
    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(400, f"File quá {MAX_FILE_MB}MB")

    inv_id = uuid.uuid4().hex
    ext = Path(file.filename or "").suffix.lower() or ".bin"
    object_key = _obj_key(month, inv_id, ext)     # aibill/<month>/<inv_id><ext>

    # 1) Upload ảnh/PDF thẳng lên MinIO (pattern visionGuard.py) trong threadpool
    try:
        await run_in_threadpool(
            _minio_put,
            object_key=object_key,
            content=content,
            content_type=file.content_type,
        )
    except Exception as e:
        logger.exception("Upload MinIO thất bại key=%s", object_key)
        raise HTTPException(502, f"Upload MinIO thất bại: {e}")

    # 2) Ghi metadata vào Oracle, cột FILE_PATH lưu object_key MinIO (KHÔNG phải local path)
    row = dict(id=inv_id, created_at=datetime.now().isoformat(timespec="seconds"), month=month,
               submitter_name=name.strip(), submitter_email=email, file_name=file.filename,
               file_path=object_key, mime=file.content_type, delete_token=secrets.token_urlsafe(16),
               userid=userid)
    try:
        _db("insertInvoice", {k.upper(): v for k, v in row.items()})
    except Exception:
        # compensating transaction: DB lỗi -> dọn MinIO giống visionGuard.py::_upload_with_compensation
        try:
            await run_in_threadpool(_minio_delete, object_key)
            logger.warning("Rollback MinIO sau khi DB insert fail: %s", object_key)
        except Exception:
            logger.exception("Rollback MinIO cũng lỗi (object mồ côi): %s", object_key)
        raise

    analyze_and_save(row)
    result = out(_db("getInvoiceById", dict(ID=inv_id), one=True))
    result["delete_token"] = row["delete_token"]  # chỉ trả 1 lần cho người upload
    return result


@aiBill_router.get("/invoices/mine")
def my_invoices(month: str, user=Depends(validate_token)):
    userid = _who(user)
    if not userid:
        raise HTTPException(401, "Khong xac dinh duoc USERID tu token")
    rows = _db("getMine", dict(USERID=userid, MONTH=month))
    return [out(r) for r in rows]


@aiBill_router.delete("/invoices/{inv_id}")
async def delete_invoice(inv_id: str, token: str):
    row = _db("getInvoiceById", dict(ID=inv_id), one=True)
    if not row or not secrets.compare_digest(row["delete_token"], token):
        raise HTTPException(404, "Không tìm thấy")
    if row["status"] == "confirmed":
        raise HTTPException(400, "Hoá đơn đã được xác nhận, không xoá được")
    _db("deleteInvoice", dict(ID=inv_id))                     # DB trước
    try:                                                       # MinIO sau
        await run_in_threadpool(_minio_delete, row["file_path"])
    except Exception:
        logger.warning("DB đã xoá nhưng MinIO chưa: %s", row.get("file_path"))
    return {"ok": True}


@aiBill_router.get("/files/{inv_id}")
async def get_file(inv_id: str, token: Optional[str] = None, user=Depends(validate_token)):
    row = _db("getInvoiceById", dict(ID=inv_id), one=True)
    if not row:
        raise HTTPException(404)
    authorized = bool(token) and secrets.compare_digest(row["delete_token"], token)
    owner = _who(user) is not None and _who(user) == row.get("userid")
    if not (authorized or owner):
        raise HTTPException(403, "Ban khong co quyen xem hoa don nay")
    try:
        minio_resp = await run_in_threadpool(minio_object.open_object, row["file_path"])
    except Exception as e:
        logger.exception("Đọc MinIO lỗi key=%s", row.get("file_path"))
        raise HTTPException(502, f"Không đọc được file từ MinIO: {e}")
    return StreamingResponse(
        minio_object.stream_object(minio_resp),
        media_type=row["mime"],
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------------------------------------------------------------- API admin
@aiBill_router.get("/admin/invoices")
def admin_list(month: str, status: Optional[str] = None):
    params = dict(MONTH=month)
    if status:
        params["STATUS"] = status
    rows = _db("getList", params)
    return [out(r) for r in rows]


@aiBill_router.get("/admin/summary")
def admin_summary(month: str):
    rows = _db("getRowsByMonth", dict(MONTH=month))
    counts = {"total": len(rows), "pending": 0, "confirmed": 0, "rejected": 0, "warning": 0}
    totals, people, providers = {"all": 0, "confirmed": 0}, {}, {}
    for r in rows:
        counts[r["status"]] += 1
        if r["status"] == "rejected":
            continue
        if r["status"] == "pending" and json.loads(r["warnings"] or "[]"):
            counts["warning"] += 1
        amt = r["amount"] or 0
        totals["all"] += amt
        if r["status"] == "confirmed":
            totals["confirmed"] += amt
        p = people.setdefault(r["submitter_email"], {"name": r["submitter_name"], "email": r["submitter_email"],
                                                     "count": 0, "confirmed": 0, "total": 0, "providers": []})
        p["count"] += 1
        p["confirmed"] += r["status"] == "confirmed"
        p["total"] += amt
        if r["provider"] and r["provider"] not in p["providers"]:
            p["providers"].append(r["provider"])
        pv = providers.setdefault(r["provider"] or "?", {"count": 0, "total": 0})
        pv["count"] += 1
        pv["total"] += amt
    return {"counts": counts, "totals": totals, "people": sorted(people.values(), key=lambda x: x["name"]),
            "providers": providers}


class PatchBody(BaseModel):
    provider: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    billing_email: Optional[str] = None
    amount: Optional[float] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    admin_note: Optional[str] = None


@aiBill_router.patch("/admin/invoices/{inv_id}")
def admin_patch(inv_id: str, body: PatchBody):
    row = _db("getInvoiceById", dict(ID=inv_id), one=True)
    if not row:
        raise HTTPException(404)
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in ("pending", "confirmed", "rejected"):
        raise HTTPException(400, "Trạng thái không hợp lệ")
    if changes.get("billing_email"):
        changes["billing_email"] = changes["billing_email"].strip().lower()
    row.update(changes)
    if any(k in changes for k in EDITABLE):  # admin sửa dữ liệu -> tính lại cảnh báo
        row["email_match"], w = validate(row)
        row["warnings"] = json.dumps(w, ensure_ascii=False)
    if "status" in changes:
        row["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
    _db("updateAdminEdit", {
        "PROVIDER":       row.get("provider"),
        "INVOICE_NUMBER": row.get("invoice_number"),
        "INVOICE_DATE":   row.get("invoice_date"),
        "BILLING_EMAIL":  row.get("billing_email"),
        "AMOUNT":         row.get("amount"),
        "PLAN":           row.get("plan"),
        "STATUS":         row.get("status"),
        "ADMIN_NOTE":     row.get("admin_note"),
        "EMAIL_MATCH":    row.get("email_match"),
        "WARNINGS":       row.get("warnings"),
        "REVIEWED_AT":    row.get("reviewed_at"),
        "ID":             inv_id,
    })
    return out(_db("getInvoiceById", dict(ID=inv_id), one=True))


@aiBill_router.post("/admin/invoices/{inv_id}/reanalyze")
def admin_reanalyze(inv_id: str):
    row = _db("getInvoiceById", dict(ID=inv_id), one=True)
    if not row:
        raise HTTPException(404)
    analyze_and_save(row)
    return out(_db("getInvoiceById", dict(ID=inv_id), one=True))


@aiBill_router.delete("/admin/invoices/{inv_id}")
async def admin_delete(inv_id: str):
    """Admin được xoá hoá đơn ở mọi trạng thái (kể cả confirmed / rejected)."""
    row = _db("getInvoiceById", dict(ID=inv_id), one=True)
    if not row:
        raise HTTPException(404)
    _db("deleteInvoice", dict(ID=inv_id))                    # DB trước
    try:                                                      # MinIO sau
        await run_in_threadpool(_minio_delete, row["file_path"])
    except Exception:
        logger.warning("DB đã xoá nhưng MinIO chưa: %s", row.get("file_path"))
    return {"ok": True}


@aiBill_router.post("/admin/confirm-valid")
def admin_confirm_valid(month: str):
    """Xác nhận hàng loạt các hoá đơn chờ duyệt không có cảnh báo nào."""
    now = datetime.now().isoformat(timespec="seconds")
    ids = [r["id"] for r in _db("listPendingByMonth", dict(MONTH=month))
           if not json.loads(r["warnings"] or "[]")]
    for i in ids:
        _db("confirmOneInvoice", dict(REVIEWED_AT=now, ID=i))
    return {"confirmed": len(ids)}


@aiBill_router.get("/admin/export")
def admin_export(month: str):
    rows = _db("getRowsByMonth", dict(MONTH=month))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Người gửi", "Email người gửi", "Dịch vụ", "Gói", "Số hoá đơn", "Ngày hoá đơn",
                "Email trên hoá đơn", "Khớp email", "Số tiền", "Trạng thái", "Cảnh báo", "Ghi chú admin"])
    status_vn = {"pending": "Chờ duyệt", "confirmed": "Đã xác nhận", "rejected": "Từ chối"}
    for r in rows:
        w.writerow([r["submitter_name"], r["submitter_email"], r["provider"], r["plan"], r["invoice_number"],
                    r["invoice_date"], r["billing_email"], "Có" if r["email_match"] else "Không", r["amount"],
                    status_vn.get(r["status"], r["status"]),
                    "; ".join(json.loads(r["warnings"] or "[]")), r["admin_note"]])
    return Response(("\ufeff" + buf.getvalue()).encode("utf-8"), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="hoa-don-{month}.csv"'})
