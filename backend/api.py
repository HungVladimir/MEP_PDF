import os
import sys
import shutil
import time
import zipfile
from urllib.parse import quote
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import pandas as pd

from typing import Optional
import config
from engine import run_mep_pipeline
from sql import (
    update_task_status, update_review_decision, batch_upsert_tasks,
    delete_tasks, check_keyid_exists, get_task_payment_month, cache_task_month,
    get_task_status, get_task_result_link, get_report_owner
)
from minio_storage import minio_storage, MINIO_PREFIX
from detail_builder import safe_id, load_task_detail_cache
from task_files import (
    file_in_directory, new_session_name, report_download_link, report_filename,
    report_variants, task_sessions, valid_filename,
)

app = FastAPI(title="MEP Payment AI Worker Service", version="2.0")

# 1. CẤU HÌNH CORS CHO PHÉP GIAO TIẾP VỚI ONEAI VUE.JS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# 2. KHỞI TẠO THƯ MỤC LƯU TRỮ (TỰ THÍCH ỨNG LOCAL HOẶC SERVER)
BASE_DIR = Path(__file__).resolve().parent

# Đường dẫn thư mục máy Local
COMPANY_PRIVATE_ROOT = Path(r"D:\Private_Documents\Doc\AI-Infra")

if COMPANY_PRIVATE_ROOT.exists():
    # 🏢 [MÔI TRƯỜNG LOCAL]:
    PRIVATE_EXCEL_DIR = COMPANY_PRIVATE_ROOT / "sessions"
    FINAL_REPORT_DIR = COMPANY_PRIVATE_ROOT / "FinalReport"
    PROJECT_STORAGE_DIR = BASE_DIR / "sessions"
    print("🏢 [Môi trường] Đang chạy trên Máy Local")
else:
    # 🌐 [MÔI TRƯỜNG SERVER / LINUX]:
    PRIVATE_EXCEL_DIR = BASE_DIR / "sessions"
    FINAL_REPORT_DIR = BASE_DIR / "final_reports"
    PROJECT_STORAGE_DIR = BASE_DIR / "sessions"
    print("🌐 [Môi trường] Đang chạy trên Server")

PRIVATE_EXCEL_DIR.mkdir(parents=True, exist_ok=True)
FINAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ReviewRequest(BaseModel):
    keyid: str
    decision: str  # APPROVED hoặc REJECTED
    note: str = ""
    reviewer: str = "Engineer"
    user_id: Optional[str] = None
    roles: Optional[list] = None


class SaveRowsRequest(BaseModel):
    rows: list
    user_id: Optional[str] = None
    reviewer: Optional[str] = None
    roles: Optional[list] = None


class DeleteRowsRequest(BaseModel):
    keyids: list
    reviewer: str = "PIC"
    user_id: Optional[str] = None
    roles: Optional[list] = None


def check_user_permission(user_id: Optional[str] = None, roles: Optional[list] = None) -> dict:
    """
    Kiểm tra quyền hạn của người dùng (Admin/Editor vs Viewer/ReadOnly).
    - MEP_ENABLE_AUTH = False (mặc định môi trường dev/local): Mở toàn quyền cho tất cả.
    - MEP_ENABLE_AUTH = True:
        + Admin/Editor: nếu user_id nằm trong MEP_ADMIN_USERS hoặc roles chứa MEP_ADMIN_ROLES.
        + Viewer: các user còn lại (chỉ xem, không được sửa/xóa/upload).
    """
    if not getattr(config, "MEP_ENABLE_AUTH", False):
        return {
            "is_admin": True,
            "can_edit": True,
            "can_delete": True,
            "can_upload": True,
            "auth_enabled": False,
            "role": "ADMIN",
            "message": "Chế độ mở quyền (Auth Disabled)"
        }

    admin_users = [u.strip().lower() for u in getattr(config, "MEP_ADMIN_USERS", "").split(",") if u.strip()]
    admin_roles = [r.strip().upper() for r in getattr(config, "MEP_ADMIN_ROLES", "").split(",") if r.strip()]

    uid_clean = str(user_id or "").strip().lower()
    user_roles = [str(r).strip().upper() for r in (roles or []) if str(r).strip()]

    is_user_admin = (uid_clean in admin_users) if uid_clean else False
    is_role_admin = any(r in admin_roles for r in user_roles) if user_roles else False

    has_full_rights = is_user_admin or is_role_admin

    return {
        "is_admin": has_full_rights,
        "can_edit": has_full_rights,
        "can_delete": has_full_rights,
        "can_upload": has_full_rights,
        "auth_enabled": True,
        "role": "ADMIN" if has_full_rights else "VIEWER",
        "message": "Có quyền Quản trị viên (Admin)" if has_full_rights else "Chế độ Chỉ xem (Viewer)"
    }


@app.get("/mep_payment/permissions")
async def get_permissions_endpoint(user_id: Optional[str] = None, roles: Optional[str] = None):
    """
    API kiểm tra và đồng bộ quyền hạn người dùng với Frontend OneAI.
    Trả về cờ is_admin, can_edit, can_delete, can_upload.
    """
    role_list = [r.strip() for r in roles.split(",")] if roles else []
    perm = check_user_permission(user_id=user_id, roles=role_list)
    return {"status": "ok", "data": perm}

# 3. TIẾN TRÌNH XỬ LÝ CHẠY NGẦM (BACKGROUND TASK) VÀ LỚP BẮT FULL LOG


class StreamLogTee:
    """Lớp chuyển hướng và đồng bộ log stdout ra cả console và mảng log / file pipeline.log."""

    def __init__(self, original_stdout, log_file_path: Path = None):
        self.original_stdout = original_stdout
        self.log_file_path = log_file_path
        self.log_lines = []
        self._buffer = ""

    def write(self, text):
        if self.original_stdout:
            self.original_stdout.write(text)
            self.original_stdout.flush()
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            stripped = line.strip()
            if stripped:
                timestamp = time.strftime("[%H:%M:%S] ")
                formatted = f"{timestamp}{stripped}"
                self.log_lines.append(formatted)
                if self.log_file_path:
                    try:
                        with open(self.log_file_path, "a", encoding="utf-8") as lf:
                            lf.write(formatted + "\n")
                    except Exception:
                        pass

    def flush(self):
        if self.original_stdout:
            self.original_stdout.flush()
        if self._buffer.strip():
            timestamp = time.strftime("[%H:%M:%S] ")
            formatted = f"{timestamp}{self._buffer.strip()}"
            self.log_lines.append(formatted)
            if self.log_file_path:
                try:
                    with open(self.log_file_path, "a", encoding="utf-8") as lf:
                        lf.write(formatted + "\n")
                except Exception:
                    pass
            self._buffer = ""


def run_ai_task_background(keyid: str, session_dir: Path, excel_path: str, payment_month: str = None):
    """
    Hàm này chạy hoàn toàn độc lập dưới nền (Background).
    Không làm đơ hay timeout giao diện người dùng trên OneAI.
    """
    if not payment_month:
        payment_month = get_task_payment_month(keyid) or time.strftime("%Y-%m")

    pipeline_log_path = session_dir / "pipeline.log"
    tee = StreamLogTee(sys.stdout, pipeline_log_path)
    old_stdout = sys.stdout
    sys.stdout = tee

    try:
        print(f"\n🚀 [TASK {keyid}] Bắt đầu thực thi Pipeline MEP AI...")

        # Định nghĩa callback tiến độ để ghi trực tiếp % vào Oracle DB
        def on_pipeline_progress(msg: str, progress: float):
            try:
                pct = int(round(progress * 100))
                update_task_status(
                    keyid=keyid,
                    status="RUNNING",
                    reason=msg[:400],
                    progress=pct
                )
            except Exception as prog_err:
                print(
                    f"⚠️ [Progress Warning] Không thể cập nhật tiến độ: {prog_err}")

        update_task_status(keyid=keyid, status="RUNNING",
                           reason="AI đang bóc tách bản vẽ & đối soát...", progress=5)

        pdf_drawings = session_dir / "drawings"
        pdf_gatepass = session_dir / "gatepass"
        csv_drawings = session_dir / "csv_drawings"
        csv_gatepass = session_dir / "csv_gatepass"
        evidence_dir = session_dir / "evidence_images"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        report_dir = FINAL_REPORT_DIR / session_dir.name
        report_dir.mkdir(exist_ok=False)
        final_excel_path = run_mep_pipeline(
            pdf_drawing_dir=str(pdf_drawings),
            pdf_gatepass_dir=str(pdf_gatepass),
            vendor_excel_path=excel_path,
            master_data_path=excel_path,
            output_dir=str(report_dir),
            csv_drawing_dir=str(csv_drawings),
            csv_gatepass_dir=str(csv_gatepass),
            skip_existing=False,
            status_callback=on_pipeline_progress,
            evidence_dir=str(evidence_dir)
        )

        # ĐÓNG GÓI .ZIP ĐỂ LƯU TRỮ VÀ TẢI VỀ BÁO CÁO
        excel_report = Path(final_excel_path)
        run_id = session_dir.name.rsplit("_", 1)[-1]
        file_name = f"{run_id}_{excel_report.name}"
        excel_report = excel_report.rename(report_dir / file_name)
        final_excel_path = str(excel_report)
        zip_name = excel_report.with_suffix(".zip").name
        zip_path = report_dir / zip_name
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(final_excel_path, arcname=file_name)
            download_link = report_download_link(keyid, zip_name)
            print(f"📦 [ZIP Archive] Đã nén báo cáo thành công: {zip_name}")
        except Exception as z_err:
            print(f"⚠️ [ZIP Warning] Lỗi nén zip, dùng link excel: {z_err}")
            download_link = report_download_link(keyid, file_name)

        # TRÍCH XUẤT VÀ LƯU CHI TIẾT ĐỐI SOÁT (JSON CACHE CHO MODAL DIALOG)
        error_count = 0
        detail_data = None
        try:
            from detail_builder import parse_excel_report_to_detail
            import json

            tee.flush()
            detail_data = parse_excel_report_to_detail(
                Path(final_excel_path), keyid, session_dir, logs=list(tee.log_lines))

            # ĐỒNG BỘ CHUẨN XÁC: Lấy tổng số lỗi thực tế bóc tách theo từng bản vẽ thay vì đếm số dòng thô
            if detail_data and "error_count" in detail_data and detail_data["error_count"] is not None:
                error_count = int(detail_data["error_count"])
            else:
                try:
                    df_check = pd.read_excel(final_excel_path, sheet_name="1. Đối Soát Bản Vẽ")
                    if 'Note' in df_check.columns:
                        error_count = int(df_check['Note'].astype(str).str.contains('Lệch|Mã mồ côi|Chỉ có ở bản vẽ', na=False).sum())
                except Exception as e:
                    print(f"⚠️ Cảnh báo đọc lỗi fallback: {e}")

            conclusion_logs = [
                f"[KẾT LUẬN] Đã đối soát xong: Phát hiện {error_count} sai lệch chi tiết.",
                f"[BÁO CÁO] File Excel kết quả: {os.path.basename(final_excel_path)}",
                f"[LƯU TRỮ] File nén phục vụ tải về: {zip_name}"
            ]
            full_logs = list(tee.log_lines) + conclusion_logs
            if detail_data:
                detail_data["logs"] = full_logs
                with (report_dir / "detail.json").open("w", encoding="utf-8") as jf:
                    json.dump(detail_data, jf, ensure_ascii=False, indent=2)
                print(f"💾 [Detail Cache] Đã lưu chi tiết đối soát (Tổng lỗi: {error_count})")
        except Exception as det_err:
            print(f"⚠️ [Detail Cache Warning] {det_err}")

        # ĐỒNG BỘ TOÀN BỘ KẾT QUẢ LÊN MINIO STORAGE THEO THÁNG (mep_payment/<month>/<keyid>/...)
        if minio_storage.is_available():
            try:
                # 1. Upload ZIP & Excel Báo cáo vào đúng folder tháng của task (Không upload bản copy mồ côi nữa)
                if zip_path.exists():
                    zip_obj_key = minio_storage.get_obj_key(
                        keyid, "reports", zip_name, month=payment_month)
                    minio_storage.upload_file(zip_path, zip_obj_key, "application/zip")
                if Path(final_excel_path).exists():
                    excel_obj_key = minio_storage.get_obj_key(
                        keyid, "reports", file_name, month=payment_month)
                    minio_storage.upload_file(
                        final_excel_path, excel_obj_key, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                # 2. Upload Toàn bộ ảnh bằng chứng / thumbnail đối soát theo tháng
                search_imgs = list(evidence_dir.glob(
                    "*.*")) + list(session_dir.glob("*.png")) + list(session_dir.glob("*.jpg"))
                uploaded_count = 0
                for img_p in search_imgs:
                    if img_p.is_file() and img_p.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                        img_obj_key = minio_storage.get_obj_key(
                            keyid, "images", img_p.name, month=payment_month)
                        if minio_storage.upload_file(img_p, img_obj_key):
                            uploaded_count += 1

                # 3. Upload cache chi tiết JSON lên MinIO theo tháng
                if detail_data:
                    json_bytes = json.dumps(
                        detail_data, ensure_ascii=False, indent=2).encode('utf-8')
                    detail_obj_key = minio_storage.get_obj_key(
                        keyid, "cache", "detail.json", month=payment_month)
                    minio_storage.upload_bytes(json_bytes, detail_obj_key, "application/json")

                print(
                    f"☁️ [MinIO Storage] Đã đồng bộ lên MinIO ({payment_month}/{keyid}): Báo cáo={zip_name}, Ảnh={uploaded_count} files")
            except Exception as minio_sync_err:
                print(
                    f"⚠️ [MinIO Sync Warning] Lỗi đồng bộ MinIO: {minio_sync_err}")

        update_task_status(
            keyid=keyid,
            status="COMPLETED",
            error_count=error_count,
            result_link=download_link,
            reason=f"Hoàn thành đối soát 2 vòng (Phát hiện {error_count} sai lệch)",
            progress=100
        )
        print(f"🎉 [TASK {keyid}] THÀNH CÔNG -> Lưu tại {final_excel_path}")

    except Exception as e:
        error_msg = f"Lỗi pipeline: {str(e)}"
        print(f"❌ [TASK {keyid}] THẤT BẠI: {error_msg}")
        update_task_status(
            keyid=keyid,
            status="CANCEL",
            error_count=0,
            result_link=None,
            reason=error_msg[:900],
            progress=0
        )
    finally:
        tee.flush()
        sys.stdout = old_stdout

# 4. CÁC ENDPOINT API GIAO TIẾP VỚI WEB


@app.get("/healthz")
@app.get("/mep_payment/health")
async def health_check():
    """Kiểm tra tình trạng hoạt động của Worker Service (Hỗ trợ K8s Liveness/Readiness Probe)."""
    return {"status": "ok", "service": "MEP Payment AI Worker", "timestamp": time.time()}


@app.post("/mep_payment/upload")
async def upload_excel_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    KEYID: str = Form(...),
    payment_month: Optional[str] = Form(None),
    uploader_name: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """Tiếp nhận file Excel từ OneAI Portal và kích hoạt Background Task."""
    try:
        # Kiểm tra quyền hạn upload & chạy AI
        uid = user_id or uploader_name
        perm = check_user_permission(user_id=uid)
        if not perm["can_upload"]:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền tải lên file và chạy AI bóc tách MEP. Vui lòng liên hệ Quản trị viên."
            )

        # Chống xung đột đồng thời (Concurrency check): Nếu task đang RUNNING thì chặn upload đè
        current_status = get_task_status(KEYID)
        if current_status == "RUNNING":
            raise HTTPException(
                status_code=409,
                detail=f"Hồ sơ [{KEYID}] đang được chạy đối soát bởi hệ thống! Vui lòng đợi hoàn tất."
            )

        if not valid_filename(file.filename):
            raise HTTPException(status_code=400, detail="Tên file tải lên không hợp lệ.")
        if Path(file.filename).suffix.lower() not in (".xlsx", ".xlsm"):
            raise HTTPException(
                status_code=400, detail="Chỉ chấp nhận file Excel (.xlsx / .xlsm)")

        # Kiểm tra dung lượng file theo config
        max_bytes = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size and file.size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Dung lượng file ({file.size / (1024*1024):.1f}MB) vượt quá giới hạn ({config.MAX_UPLOAD_SIZE_MB}MB)!")

        KEYID = KEYID.strip()
        if not KEYID:
            raise HTTPException(status_code=400, detail="Thiếu mã hồ sơ.")
        session_name = new_session_name(KEYID)

        # Xác định tháng thanh toán để tổ chức thư mục MinIO
        actual_month = (payment_month or "").strip() or get_task_payment_month(KEYID) or time.strftime("%Y-%m")

        # 1. Thư mục lưu file Excel upload
        private_session_dir = PRIVATE_EXCEL_DIR / session_name
        private_session_dir.mkdir(parents=True, exist_ok=False)
        excel_path = private_session_dir / file.filename

        with excel_path.open("xb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Kiểm tra lại dung lượng sau khi ghi đĩa
        saved_file_size = excel_path.stat().st_size
        if saved_file_size > max_bytes:
            excel_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=413,
                detail=f"Dung lượng file ({saved_file_size / (1024*1024):.1f}MB) vượt quá giới hạn ({config.MAX_UPLOAD_SIZE_MB}MB)!")

        # 2. Thư mục Project để lưu toàn bộ ảnh evidence, PDF, CSV, pipeline.log
        project_session_dir = PROJECT_STORAGE_DIR / session_name
        project_session_dir.mkdir(parents=True, exist_ok=True)

        # 3. Nếu MinIO đang hoạt động, sao lưu thêm 1 bản Excel input lên MinIO theo tháng
        if minio_storage.is_available():
            try:
                minio_storage.upload_file(
                    excel_path, minio_storage.get_obj_key(KEYID, "inputs", file.filename, month=actual_month))
            except Exception:
                pass

        update_task_status(
            keyid=KEYID,
            status="RUNNING",
            reason="Đã nhận file, AI đang bóc tách ngầm...",
            progress=5,
            pic=uploader_name
        )
        background_tasks.add_task(
            run_ai_task_background, KEYID, project_session_dir, str(excel_path), actual_month)

        return {"status": "accepted", "message": "Nạp file thành công, AI đang khởi chạy."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await file.close()


@app.get("/mep_payment/files/{keyid}/{filename}")
async def download_task_report_file(keyid: str, filename: str):
    if not valid_filename(filename) or Path(filename).suffix.lower() not in (".zip", ".xlsx"):
        raise HTTPException(status_code=404, detail="File báo cáo không tồn tại.")

    variants = report_variants(filename)
    report_dirs = task_sessions(FINAL_REPORT_DIR, keyid, include_legacy=False)
    for candidate in variants:
        for directory in report_dirs:
            path = directory / candidate
            if file_in_directory(directory, path):
                return FileResponse(path, filename=path.name)

    if minio_storage.is_available():
        month = get_task_payment_month(keyid)
        for candidate in variants:
            object_key = minio_storage.find_task_object(keyid, "reports", candidate, month=month)
            if object_key:
                response = minio_storage.open_object(object_key)
                if response:
                    return stream_report(response, candidate)

    if get_report_owner(filename) == keyid.strip():
        for candidate in variants:
            path = FINAL_REPORT_DIR / candidate
            if file_in_directory(FINAL_REPORT_DIR, path):
                return FileResponse(path, filename=path.name)
            if minio_storage.is_available():
                response = minio_storage.open_object(f"{MINIO_PREFIX}/reports/{candidate}")
                if response:
                    return stream_report(response, candidate)

    raise HTTPException(status_code=404, detail="File báo cáo không tồn tại.")


def stream_report(response, filename: str):
    media_type = (
        "application/zip" if Path(filename).suffix.lower() == ".zip"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return StreamingResponse(
        minio_storage.stream_object(response),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )


@app.get("/mep_payment/files/{filename}")
async def download_report_file(filename: str, keyid: Optional[str] = None):
    if valid_filename(filename) and Path(filename).suffix.lower() in (".zip", ".xlsx"):
        owner = keyid or get_report_owner(filename)
        if owner:
            return await download_task_report_file(owner, filename)
    raise HTTPException(status_code=404, detail="File báo cáo không tồn tại.")


@app.post("/mep_payment/save_rows")
async def save_rows(req: SaveRowsRequest):
    """Tiếp nhận danh sách các dòng mới thêm hoặc chỉnh sửa từ Web để lưu vào Oracle DB."""
    if not req.rows:
        raise HTTPException(status_code=400, detail="Danh sách dòng rỗng.")

    # 0. Kiểm tra quyền hạn chỉnh sửa / lưu
    uid = req.user_id or req.reviewer
    perm = check_user_permission(user_id=uid, roles=req.roles)
    if not perm["can_edit"]:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền chỉnh sửa hoặc lưu dữ liệu MEP. Vui lòng liên hệ Quản trị viên."
        )

    # Kiểm tra nếu là dòng mới thêm (isNew) mà KEYID đã tồn tại trong DB -> Báo lỗi trùng
    for r in req.rows:
        if r.get("isNew"):
            keyid = str(r.get("KEYID", "")).strip()
            if keyid and check_keyid_exists(keyid):
                raise HTTPException(
                    status_code=400,
                    detail=f"Số công việc (KEYID) '{keyid}' đã tồn tại trong Database! Không thể thêm trùng."
                )
        elif r.get("OLD_KEYID"):
            old_k = str(r.get("OLD_KEYID")).strip()
            new_k = str(r.get("KEYID", "")).strip()
            if old_k and new_k and old_k != new_k and check_keyid_exists(new_k):
                raise HTTPException(
                    status_code=400,
                    detail=f"Số công việc mới '{new_k}' đã tồn tại trong Database! Không thể đổi sang mã này."
                )

    try:
        print(
            f"📥 [FastAPI Worker] Nhận yêu cầu /save_rows ({len(req.rows)} dòng): {req.rows}")

        # TỰ ĐỘNG DỜI FOLDER TRÊN MINIO NẾU USER SỬA THÁNG THANH TOÁN (PAYMENT_MONTH)
        if minio_storage.is_available():
            for r in req.rows:
                if not r.get("isNew"):
                    kid = str(r.get("KEYID", "")).strip()
                    new_m = str(r.get("PAYMENT_MONTH", "")).strip()
                    if kid and new_m:
                        old_m = get_task_payment_month(kid)
                        if old_m and old_m != new_m:
                            try:
                                moved = minio_storage.move_task_month(kid, old_m, new_m)
                                if moved > 0:
                                    print(f"📦 [save_rows] Đã dời {moved} files trên MinIO cho {kid} từ {old_m} sang {new_m}")
                            except Exception as m_err:
                                print(f"⚠️ [save_rows] Không thể dời MinIO folder: {m_err}")
                            cache_task_month(kid, new_m)

        count = batch_upsert_tasks(req.rows)
        return {"status": "ok", "message": f"Đã lưu thành công {count} bản ghi vào Database."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [FastAPI Worker Error] save_rows: {e}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lưu vào Database: {str(e)}")


@app.post("/mep_payment/delete_rows")
async def delete_rows_endpoint(req: DeleteRowsRequest):
    """
    Tiếp nhận danh sách KEYID cần xóa:
    1. Dọn dẹp sạch sẽ 100% MinIO Storage (mep_payment/<month>/<keyid>/, mep_payment/<keyid>/, reports).
    2. Dọn dẹp sạch sẽ toàn bộ file báo cáo Excel/ZIP và session trên đĩa cứng cục bộ.
    3. Xóa bản ghi trong Database Oracle (Cascade Cleanup toàn diện).
    """
    if not req.keyids:
        raise HTTPException(
            status_code=400, detail="Vui lòng chọn ít nhất 1 dòng để xóa.")

    # 0. Kiểm tra quyền hạn xóa dòng
    uid = req.user_id or req.reviewer
    perm = check_user_permission(user_id=uid, roles=req.roles)
    if not perm["can_delete"]:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xóa dữ liệu MEP. Vui lòng liên hệ Quản trị viên."
        )

    try:
        # 1. Thu thập tháng của từng task trước khi xóa khỏi DB
        task_months = {}
        linked_reports = {}
        for kid in req.keyids:
            task_months[kid] = get_task_payment_month(kid)
            linked_reports[kid] = verified_report_name(kid)

        # 2. Xóa bản ghi trong Database Oracle
        count = delete_tasks(req.keyids)

        # 3. Dọn dẹp triệt để trên MinIO Storage
        if minio_storage.is_available():
            for kid in req.keyids:
                try:
                    m = task_months.get(kid)
                    deleted_minio_count = minio_storage.remove_task_objects(kid, month=m)
                    if deleted_minio_count > 0:
                        print(
                            f"🗑️ [MinIO Cleanup] Đã xóa {deleted_minio_count} objects trên MinIO cho KEYID={kid} (Tháng {m or 'ALL'})")
                except Exception as m_del_err:
                    print(f"⚠️ [MinIO Cleanup Warning] {m_del_err}")

        for kid in req.keyids:
            for root in {PROJECT_STORAGE_DIR, PRIVATE_EXCEL_DIR, FINAL_REPORT_DIR}:
                for directory in task_sessions(root, kid, include_legacy=root != FINAL_REPORT_DIR):
                    try:
                        shutil.rmtree(directory)
                    except OSError as error:
                        print(f"⚠️ Không thể dọn thư mục của {kid}: {error}")

            legacy_report = linked_reports[kid]
            paths = [FINAL_REPORT_DIR / name for name in report_variants(legacy_report)] if legacy_report else []
            legacy_cache = FINAL_REPORT_DIR / f"{safe_id(kid)}_detail.json"
            if load_task_detail_cache(legacy_cache, FINAL_REPORT_DIR, kid) is not None:
                paths.append(legacy_cache)
            for path in paths:
                try:
                    if file_in_directory(FINAL_REPORT_DIR, path):
                        path.unlink(missing_ok=True)
                except OSError as error:
                    print(f"⚠️ Không thể dọn file của {kid}: {error}")

        return {"status": "ok", "message": f"Đã xóa {count} bản ghi và dọn các file xác định được."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi xóa trong Database: {str(e)}")


@app.post("/mep_payment/review")
async def submit_review(req: ReviewRequest):
    """Tiếp nhận quyết định phê duyệt (Approve / Reject) từ Kỹ sư."""
    uid = req.user_id or req.reviewer
    perm = check_user_permission(user_id=uid, roles=req.roles)
    if not perm["can_edit"]:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền phê duyệt hồ sơ MEP. Vui lòng liên hệ Quản trị viên."
        )

    try:
        update_review_decision(req.keyid, req.decision, req.note, req.reviewer)
        return {"status": "ok", "message": f"Đã lưu quyết định: {req.decision}"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lưu phê duyệt: {str(e)}")


# 5. CÁC ENDPOINT: CHI TIẾT ĐỐI SOÁT, SOI ẢNH BẢN VẼ & CHẠY LẠI AI

def verified_report_name(keyid: str) -> Optional[str]:
    name = report_filename(get_task_result_link(keyid))
    if name and get_report_owner(name) == keyid.strip():
        return name
    if name:
        print(f"⚠️ Bỏ qua báo cáo chưa xác định được chủ sở hữu của {keyid}.")
    return None


@app.get("/mep_payment/detail/{keyid}")
async def get_task_detail(
    keyid: str,
    status: str = "COMPLETED",
    error_count: int = 0,
    reason: str = "",
    month: Optional[str] = None
):
    """
    Trả về chi tiết kết quả đối soát của task (danh sách lỗi, nhóm theo bản vẽ, ảnh bằng chứng, log).
    Tối ưu hóa siêu tốc: Đọc trực tiếp cache local/MinIO trong < 20ms, tuyệt đối không gọi Oracle DB.
    """
    try:
        import json
        from detail_builder import build_or_load_task_detail

        # 1. Nếu frontend truyền month, lưu ngay vào RAM cache để phục vụ các request ảnh tiếp theo
        if month:
            cache_task_month(keyid, month)

        # Tự động đồng bộ số lỗi vào Oracle DB nếu có sự lệch số giữa DB và chi tiết bóc tách
        def _check_and_sync_db(detail_obj):
            if detail_obj and "error_count" in detail_obj:
                try:
                    true_cnt = int(detail_obj["error_count"])
                    if error_count is not None and int(error_count or 0) != true_cnt:
                        from sql import update_task_status
                        update_task_status(keyid=keyid, status=status or "COMPLETED", error_count=true_cnt)
                        print(f"🔄 [Auto-sync Error Count] Đã tự động đồng bộ ERROR_COUNT {error_count} -> {true_cnt} cho {keyid}")
                except Exception as sync_e:
                    print(f"⚠️ [Auto-sync Warning] {sync_e}")

        report_dirs = task_sessions(FINAL_REPORT_DIR, keyid, include_legacy=False)
        local_caches = [(directory, directory / "detail.json") for directory in report_dirs]
        local_caches.append((FINAL_REPORT_DIR, FINAL_REPORT_DIR / f"{safe_id(keyid)}_detail.json"))
        for directory, path in local_caches:
            cached_data = load_task_detail_cache(path, directory, keyid)
            if cached_data is not None:
                _check_and_sync_db(cached_data)
                return cached_data

        # 3. Đọc từ MinIO cache JSON (lấy month từ query param hoặc RAM cache, không kết nối DB)
        if minio_storage.is_available():
            m = month or get_task_payment_month(keyid)
            detail_key = minio_storage.find_task_object(keyid, "cache", "detail.json", month=m)
            if detail_key:
                data_bytes = minio_storage.download_bytes(detail_key)
                if data_bytes:
                    try:
                        cached_data = json.loads(data_bytes.decode('utf-8'))
                        _check_and_sync_db(cached_data)
                        return cached_data
                    except Exception as e:
                        print(f"⚠️ [MinIO Cache] Lỗi đọc JSON cache cho KEYID={keyid}: {e}")

        # 4. Quét từ đĩa cục bộ / parse từ file Excel (Fallback)
        fallback_info = {
            "status": status,
            "error_count": int(error_count or 0),
            "reason": reason or ""
        }
        detail = build_or_load_task_detail(
            keyid, FINAL_REPORT_DIR, PROJECT_STORAGE_DIR, fallback_info,
            legacy_report=verified_report_name(keyid) if not report_dirs and status == "COMPLETED" else None,
        )

        _check_and_sync_db(detail)
        return detail
    except Exception as e:
        print(f"❌ [FastAPI Error] get_task_detail: {e}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi đọc chi tiết đối soát: {str(e)}")


@app.get("/mep_payment/image/{keyid}/{filename}")
async def get_task_image(keyid: str, filename: str, month: Optional[str] = None):
    """Phục vụ ảnh bản vẽ / ảnh bằng chứng đối soát siêu tốc (Ưu tiên SSD Local < 1ms, MinIO O(1))."""
    try:
        if not valid_filename(filename):
            raise HTTPException(status_code=404, detail="Không tìm thấy file ảnh bản vẽ.")
        ext = Path(filename).suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"

        for root in dict.fromkeys((PROJECT_STORAGE_DIR, PRIVATE_EXCEL_DIR)):
            for directory in task_sessions(root, keyid):
                for sub in ("", "evidence_images", "drawings", "pages"):
                    target = directory / sub / filename
                    if file_in_directory(directory, target):
                        return FileResponse(target, media_type=media_type)

        # 2. Nếu local không có, tải từ MinIO Storage (lấy month từ RAM cache, tuyệt đối không kết nối Oracle DB)
        if minio_storage.is_available():
            m = month or get_task_payment_month(keyid)
            img_key = minio_storage.find_task_object(keyid, "images", filename, month=m)
            if img_key:
                minio_resp = minio_storage.open_object(img_key)
                if minio_resp:
                    return StreamingResponse(
                        minio_storage.stream_object(minio_resp),
                        media_type=media_type,
                        headers={
                            "Cache-Control": "public, max-age=86400",
                            "Content-Disposition": f"inline; filename={filename}"
                        }
                    )

        raise HTTPException(
            status_code=404, detail="Không tìm thấy file ảnh bản vẽ.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải ảnh: {str(e)}")


@app.post("/mep_payment/rerun/{keyid}")
async def rerun_task_endpoint(
    keyid: str,
    background_tasks: BackgroundTasks,
    uploader_name: Optional[str] = None,
    user_id: Optional[str] = None,
    roles: Optional[str] = None
):
    """
    Chạy lại tác vụ AI đối soát (Rerun) cho hồ sơ đã có file Excel trong session cũ.
    Giúp xử lý lại ngay lập tức khi mạng lag hoặc AI bị timeout mà không cần upload lại.
    """
    uid = user_id or uploader_name
    role_list = [r.strip() for r in roles.split(",")] if roles else []
    perm = check_user_permission(user_id=uid, roles=role_list)
    if not perm["can_upload"]:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền kích hoạt chạy lại AI đối soát. Vui lòng liên hệ Quản trị viên."
        )

    try:
        current_status = get_task_status(keyid)
        if current_status == "RUNNING":
            raise HTTPException(
                status_code=409,
                detail=f"Hồ sơ [{keyid}] đang chạy đối soát! Vui lòng không kích hoạt chạy lại."
            )

        roots = dict.fromkeys((PRIVATE_EXCEL_DIR, PROJECT_STORAGE_DIR))
        sessions = sorted(
            (directory for root in roots for directory in task_sessions(root, keyid)),
            key=lambda directory: directory.stat().st_mtime,
            reverse=True,
        )
        excel_path = next((
            path for directory in sessions for path in sorted(directory.iterdir())
            if path.suffix.lower() in (".xlsx", ".xlsm") and file_in_directory(directory, path)
        ), None)

        if not excel_path:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy file Excel trong thư mục session của [{keyid}]. Vui lòng upload lại file!"
            )

        print(
            f"🔄 [RERUN] Bắt đầu kích hoạt chạy lại AI cho KEYID={keyid} với file {excel_path.name}")

        # Tạo project_session_dir mới để lưu ảnh và log mới
        project_session_dir = PROJECT_STORAGE_DIR / new_session_name(keyid)
        project_session_dir.mkdir(parents=True, exist_ok=False)

        update_task_status(
            keyid=keyid,
            status="RUNNING",
            reason="Đang chạy lại AI đối soát...",
            progress=5,
            pic=uploader_name
        )
        task_month = get_task_payment_month(keyid) or time.strftime("%Y-%m")
        background_tasks.add_task(
            run_ai_task_background, keyid, project_session_dir, str(excel_path), task_month)

        return {"status": "ok", "message": f"Đã bắt đầu chạy lại tác vụ AI cho [{keyid}]."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [FastAPI Error] rerun_task: {e}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi kích hoạt chạy lại AI: {str(e)}")


@app.get("/mep_payment/kpi_summary")
async def kpi_summary_endpoint(payment_month: str = "ALL", keyword: str = "ALL"):
    """API trả về 5 chỉ số KPI toàn cục cố định (Tổng, Khớp 100%, Sai lệch, Đang chạy, Chờ duyệt)."""
    try:
        from sql import get_kpi_summary
        data = get_kpi_summary(payment_month, keyword)
        return {"status": "ok", "data": data}
    except Exception as e:
        print(f"❌ [FastAPI Error] kpi_summary: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": {"total": 0, "ok": 0, "err": 0, "running": 0, "waiting": 0}
        }
