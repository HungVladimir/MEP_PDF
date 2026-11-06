
import os
import sys
import shutil
import time
import zipfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import pandas as pd

import config
from engine import run_mep_pipeline
from sql import update_task_status, update_review_decision, batch_upsert_tasks, delete_tasks, check_keyid_exists
from minio_storage import minio_storage, MINIO_PREFIX
from detail_builder import safe_id

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

# 2. KHỞI TẠO THƯ MỤC LƯU TRỮ (TỰ THÍCH ỨNG LOCAL DLP HOẶC SERVER)
BASE_DIR = Path(__file__).resolve().parent

# Đường dẫn thư mục bảo mật máy Local công ty (DLP)
COMPANY_PRIVATE_ROOT = Path(r"D:\Private_Documents\Doc\AI-Infra")

if COMPANY_PRIVATE_ROOT.exists():
    # 🏢 [MÔI TRƯỜNG LOCAL CÔNG TY - CÓ DLP CHẶN ẢNH]:
    # - File Excel upload: lưu vào Private để tuân thủ DLP
    # - File Excel kết quả & zip: lưu vào FinalReport trong Private
    # - Toàn bộ Ảnh trích xuất, PDF, CSV, Log: lưu trong Project để không bị DLP chặn
    PRIVATE_EXCEL_DIR = COMPANY_PRIVATE_ROOT / "sessions"
    FINAL_REPORT_DIR  = COMPANY_PRIVATE_ROOT / "FinalReport"
    PROJECT_STORAGE_DIR = BASE_DIR / "sessions"
    print("🏢 [Môi trường] Đang chạy trên Máy Local Công Ty (Bật chế độ DLP 2 vùng lưu trữ)")
else:
    # 🌐 [MÔI TRƯỜNG SERVER / LINUX / MÁY KHÔNG CÓ DLP]:
    # Tự động gộp tất cả về 1 vùng duy nhất ngay trong Project
    PRIVATE_EXCEL_DIR = BASE_DIR / "sessions"
    FINAL_REPORT_DIR  = BASE_DIR / "final_reports"
    PROJECT_STORAGE_DIR = BASE_DIR / "sessions"
    print("🌐 [Môi trường] Đang chạy trên Server (Bật chế độ Thống Nhất 1 vùng lưu trữ)")

PRIVATE_EXCEL_DIR.mkdir(parents=True, exist_ok=True)
FINAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ReviewRequest(BaseModel):
    keyid: str
    decision: str  # APPROVED hoặc REJECTED
    note: str = ""
    reviewer: str = "Engineer"


class SaveRowsRequest(BaseModel):
    rows: list


class DeleteRowsRequest(BaseModel):
    keyids: list
    reviewer: str = "PIC"

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


def run_ai_task_background(keyid: str, session_dir: Path, excel_path: str):
    """
    Hàm này chạy hoàn toàn độc lập dưới nền (Background).
    Không làm đơ hay timeout giao diện người dùng trên OneAI.
    """
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

        final_excel_path = run_mep_pipeline(
            pdf_drawing_dir=str(pdf_drawings),
            pdf_gatepass_dir=str(pdf_gatepass),
            vendor_excel_path=excel_path,
            master_data_path=excel_path,
            output_dir=str(FINAL_REPORT_DIR),
            csv_drawing_dir=str(csv_drawings),
            csv_gatepass_dir=str(csv_gatepass),
            skip_existing=False,
            status_callback=on_pipeline_progress,
            evidence_dir=str(evidence_dir)
        )

        # ĐẾM SỐ LỖI THỰC TẾ TRONG SHEET 1 ĐỂ BÁO LÊN GIAO DIỆN
        error_count = 0
        try:
            df_check = pd.read_excel(
                final_excel_path, sheet_name="1. Đối Soát Bản Vẽ")
            if 'Note' in df_check.columns:
                error_count = int(df_check['Note'].astype(
                    str).str.contains('Lệch|Mã mồ côi', na=False).sum())
        except Exception as e:
            print(f"⚠️ Cảnh báo đọc lỗi: {e}")

        file_name = os.path.basename(final_excel_path)

        # ĐÓNG GÓI .ZIP ĐỂ LÁCH BẢO MẬT HỆ THỐNG / DLP (THEO REFER_SAVE.PY)
        zip_name = f"{Path(file_name).stem}.zip"
        zip_path = FINAL_REPORT_DIR / zip_name
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(final_excel_path, arcname=file_name)
            download_link = f"/mep_payment/files/{zip_name}"
            print(f"📦 [ZIP Archive] Đã nén báo cáo thành công: {zip_name}")
        except Exception as z_err:
            print(f"⚠️ [ZIP Warning] Lỗi nén zip, dùng link excel: {z_err}")
            download_link = f"/mep_payment/files/{file_name}"

        # TRÍCH XUẤT VÀ LƯU CHI TIẾT ĐỐI SOÁT (JSON CACHE CHO MODAL DIALOG)
        try:
            from detail_builder import parse_excel_report_to_detail, safe_id
            import json

            tee.flush()
            conclusion_logs = [
                f"[KẾT LUẬN] Đã đối soát xong: Phát hiện {error_count} sai lệch.",
                f"[BÁO CÁO] File Excel kết quả: {os.path.basename(final_excel_path)}",
                f"[LƯU TRỮ] File nén phục vụ tải về: {zip_name}"
            ]
            full_logs = list(tee.log_lines) + conclusion_logs

            detail_data = parse_excel_report_to_detail(
                Path(final_excel_path), keyid, session_dir, logs=full_logs)
            if detail_data:
                json_name = f"{safe_id(keyid)}_detail.json"
                try:
                    with open(FINAL_REPORT_DIR / json_name, "w", encoding="utf-8") as jf:
                        json.dump(detail_data, jf, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                try:
                    with open(session_dir / json_name, "w", encoding="utf-8") as jf:
                        json.dump(detail_data, jf, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                print(
                    f"💾 [Detail Cache] Đã lưu chi tiết đối soát: {json_name}")
        except Exception as det_err:
            print(f"⚠️ [Detail Cache Warning] {det_err}")

        # ĐỒNG BỘ TOÀN BỘ KẾT QUẢ LÊN MINIO STORAGE (NẾU MINIO ĐANG KẾT NỐI)
        if minio_storage.is_available():
            try:
                # 1. Upload ZIP & Excel Báo cáo
                if zip_path.exists():
                    minio_storage.upload_file(zip_path, minio_storage.get_obj_key(keyid, "reports", zip_name), "application/zip")
                    minio_storage.upload_file(zip_path, f"{MINIO_PREFIX}/reports/{zip_name}", "application/zip")
                if Path(final_excel_path).exists():
                    minio_storage.upload_file(final_excel_path, minio_storage.get_obj_key(keyid, "reports", file_name), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    minio_storage.upload_file(final_excel_path, f"{MINIO_PREFIX}/reports/{file_name}", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                # 2. Upload Toàn bộ ảnh bằng chứng / thumbnail đối soát
                search_imgs = list(evidence_dir.glob("*.*")) + list(session_dir.glob("*.png")) + list(session_dir.glob("*.jpg"))
                uploaded_count = 0
                for img_p in search_imgs:
                    if img_p.is_file() and img_p.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                        if minio_storage.upload_file(img_p, minio_storage.get_obj_key(keyid, "images", img_p.name)):
                            uploaded_count += 1

                # 3. Upload cache chi tiết JSON lên MinIO
                if detail_data:
                    json_bytes = json.dumps(detail_data, ensure_ascii=False, indent=2).encode('utf-8')
                    minio_storage.upload_bytes(json_bytes, minio_storage.get_obj_key(keyid, "cache", "detail.json"), "application/json")

                print(f"☁️ [MinIO Storage] Đã đồng bộ lên MinIO: Báo cáo={zip_name}, Ảnh={uploaded_count} files (KEYID={keyid})")
            except Exception as minio_sync_err:
                print(f"⚠️ [MinIO Sync Warning] Lỗi đồng bộ MinIO: {minio_sync_err}")

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


@app.get("/mep_payment/health")
async def health_check():
    """Kiểm tra tình trạng hoạt động của Worker Service."""
    return {"status": "ok", "service": "MEP Payment AI Worker", "timestamp": time.time()}


@app.post("/mep_payment/upload")
async def upload_excel_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    KEYID: str = Form(...)
):
    """Tiếp nhận file Excel từ OneAI Portal và kích hoạt Background Task."""
    try:
        if not file.filename.endswith(('.xlsx', '.xlsm')):
            raise HTTPException(
                status_code=400, detail="Chỉ chấp nhận file Excel (.xlsx / .xlsm)")

        # Kiểm tra dung lượng file theo config
        max_bytes = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size and file.size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Dung lượng file ({file.size / (1024*1024):.1f}MB) vượt quá giới hạn ({config.MAX_UPLOAD_SIZE_MB}MB)!")

        safe_keyid = KEYID.replace('/', '_').replace('\\', '_')
        session_name = f"session_{safe_keyid}_{int(time.time())}"

        # 1. Thư mục Private để lưu file Excel upload (tuân thủ DLP máy công ty)
        private_session_dir = PRIVATE_EXCEL_DIR / session_name
        private_session_dir.mkdir(parents=True, exist_ok=True)
        excel_path = private_session_dir / file.filename

        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Kiểm tra lại dung lượng sau khi ghi đĩa
        saved_file_size = excel_path.stat().st_size
        if saved_file_size > max_bytes:
            excel_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=413,
                detail=f"Dung lượng file ({saved_file_size / (1024*1024):.1f}MB) vượt quá giới hạn ({config.MAX_UPLOAD_SIZE_MB}MB)!")

        # 2. Thư mục Project để lưu toàn bộ ảnh evidence, PDF, CSV, pipeline.log (không bị DLP chặn)
        project_session_dir = PROJECT_STORAGE_DIR / session_name
        project_session_dir.mkdir(parents=True, exist_ok=True)

        # 3. Nếu MinIO đang hoạt động, sao lưu thêm 1 bản Excel input lên MinIO
        if minio_storage.is_available():
            try:
                minio_storage.upload_file(excel_path, minio_storage.get_obj_key(KEYID, "inputs", file.filename))
            except Exception:
                pass

        update_task_status(keyid=KEYID, status="RUNNING",
                           reason="Đã nhận file, AI đang bóc tách ngầm...", progress=5)
        background_tasks.add_task(
            run_ai_task_background, KEYID, project_session_dir, str(excel_path))

        return {"status": "accepted", "message": "Nạp file thành công, AI đang khởi chạy."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await file.close()


@app.get("/mep_payment/files/{filename}")
async def download_report_file(filename: str):
    """Phục vụ tải file Báo cáo 2 Sheet về máy (Hỗ trợ cả .zip và .xlsx từ MinIO hoặc Local Disk)."""
    # 1. Kiểm tra ưu tiên trong MinIO Storage
    if minio_storage.is_available():
        minio_candidates = [
            f"{MINIO_PREFIX}/reports/{filename}",
            f"{MINIO_PREFIX}/reports/{filename.replace('.zip', '.xlsx')}" if filename.endswith('.zip') else f"{MINIO_PREFIX}/reports/{filename.replace('.xlsx', '.zip')}"
        ]
        for m_key in minio_candidates:
            if minio_storage.object_exists(m_key):
                minio_resp = minio_storage.open_object(m_key)
                if minio_resp:
                    actual_fname = Path(m_key).name
                    is_zip = actual_fname.lower().endswith(".zip")
                    media_type = "application/zip" if is_zip else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    return StreamingResponse(
                        minio_storage.stream_object(minio_resp),
                        media_type=media_type,
                        headers={
                            "Content-Disposition": f"attachment; filename={actual_fname}",
                            "Access-Control-Expose-Headers": "Content-Disposition"
                        }
                    )

    # 2. Fallback sang Local Disk nếu MinIO không có hoặc offline
    file_path = FINAL_REPORT_DIR / filename

    # Cơ chế fallback tự tìm file tương ứng nếu khác đuôi
    if not file_path.exists():
        if filename.endswith(".zip"):
            alt_path = FINAL_REPORT_DIR / filename.replace(".zip", ".xlsx")
            if alt_path.exists():
                file_path = alt_path
                filename = alt_path.name
        elif filename.endswith(".xlsx"):
            alt_path = FINAL_REPORT_DIR / filename.replace(".xlsx", ".zip")
            if alt_path.exists():
                file_path = alt_path
                filename = alt_path.name

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="File báo cáo không tồn tại.")

    is_zip = filename.lower().endswith(".zip")
    media_type = "application/zip" if is_zip else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.post("/mep_payment/save_rows")
async def save_rows(req: SaveRowsRequest):
    """Tiếp nhận danh sách các dòng mới thêm hoặc chỉnh sửa từ Web để lưu vào Oracle DB."""
    if not req.rows:
        raise HTTPException(status_code=400, detail="Danh sách dòng rỗng.")

    # Kiểm tra nếu là dòng mới thêm (isNew) mà KEYID đã tồn tại trong DB -> Báo lỗi trùng
    for r in req.rows:
        if r.get("isNew"):
            keyid = str(r.get("KEYID", "")).strip()
            if keyid and check_keyid_exists(keyid):
                raise HTTPException(
                    status_code=400,
                    detail=f"Số công việc (KEYID) '{keyid}' đã tồn tại trong Database! Không thể thêm trùng."
                )

    try:
        print(
            f"📥 [FastAPI Worker] Nhận yêu cầu /save_rows ({len(req.rows)} dòng): {req.rows}")
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
    """Tiếp nhận danh sách KEYID cần xóa khỏi Database."""
    if not req.keyids:
        raise HTTPException(
            status_code=400, detail="Vui lòng chọn ít nhất 1 dòng để xóa.")
    try:
        count = delete_tasks(req.keyids)
        # Dọn dẹp dữ liệu MinIO tương ứng với từng KEYID bị xóa (Compensating Cleanup theo chuẩn visionGuard)
        if minio_storage.is_available():
            for kid in req.keyids:
                try:
                    safe_k = safe_id(kid)
                    deleted_minio_count = minio_storage.remove_prefix(f"{MINIO_PREFIX}/{safe_k}/")
                    if deleted_minio_count > 0:
                        print(f"🗑️ [MinIO Cleanup] Đã xóa {deleted_minio_count} objects trên MinIO cho KEYID={kid}")
                except Exception as m_del_err:
                    print(f"⚠️ [MinIO Cleanup Warning] {m_del_err}")
        return {"status": "ok", "message": f"Đã xóa thành công {count} bản ghi khỏi Database."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi xóa trong Database: {str(e)}")


@app.post("/mep_payment/review")
async def submit_review(req: ReviewRequest):
    """Tiếp nhận quyết định phê duyệt (Approve / Reject) từ Kỹ sư."""
    try:
        update_review_decision(req.keyid, req.decision, req.note, req.reviewer)
        return {"status": "ok", "message": f"Đã lưu quyết định: {req.decision}"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lưu phê duyệt: {str(e)}")


# 5. CÁC ENDPOINT MỚI: CHI TIẾT ĐỐI SOÁT, SOI ẢNH BẢN VẼ & CHẠY LẠI AI (THEO CHUẨN THIẾT KẾ CỦA SẾP)

@app.get("/mep_payment/detail/{keyid}")
async def get_task_detail(keyid: str, status: str = "COMPLETED", error_count: int = 0, reason: str = ""):
    """
    Trả về chi tiết kết quả đối soát của task (danh sách lỗi, nhóm theo bản vẽ, ảnh bằng chứng, log).
    Hỗ trợ đọc từ MinIO cache JSON, quét file Excel cũ hoặc tạo fallback an toàn.
    """
    try:
        import json
        from detail_builder import build_or_load_task_detail

        # 1. Thử đọc nhanh từ MinIO cache JSON nếu có
        if minio_storage.is_available():
            detail_key = minio_storage.get_obj_key(keyid, "cache", "detail.json")
            data_bytes = minio_storage.download_bytes(detail_key)
            if data_bytes:
                try:
                    return json.loads(data_bytes.decode('utf-8'))
                except Exception:
                    pass

        # 2. Quét từ đĩa cục bộ / parse từ file Excel
        fallback_info = {
            "status": status,
            "error_count": int(error_count or 0),
            "reason": reason or ""
        }
        detail = build_or_load_task_detail(
            keyid, FINAL_REPORT_DIR, PROJECT_STORAGE_DIR, fallback_info)
        return detail
    except Exception as e:
        print(f"❌ [FastAPI Error] get_task_detail: {e}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi đọc chi tiết đối soát: {str(e)}")


@app.get("/mep_payment/image/{keyid}/{filename}")
async def get_task_image(keyid: str, filename: str):
    """Phục vụ ảnh bản vẽ / ảnh bằng chứng đối soát để hiển thị trong Lightbox / Preview (MinIO Stream hoặc Local)."""
    try:
        from detail_builder import safe_id
        safe_key = safe_id(keyid)
        ext = Path(filename).suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"

        # 1. Kiểm tra ưu tiên trong MinIO Storage
        if minio_storage.is_available():
            img_key = minio_storage.get_obj_key(keyid, "images", filename)
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

        # 2. Quét ưu tiên trong PROJECT_STORAGE_DIR (nơi lưu evidence_images không bị DLP chặn)
        search_roots = [PROJECT_STORAGE_DIR, PRIVATE_EXCEL_DIR]
        for root in search_roots:
            if root.exists():
                for s_dir in root.glob(f"*session_{safe_key}*"):
                    for sub in ["", "evidence_images", "drawings", "pages"]:
                        target = (s_dir / sub / filename) if sub else (s_dir / filename)
                        if target.exists() and target.is_file():
                            return FileResponse(str(target), media_type=media_type)

        raise HTTPException(
            status_code=404, detail="Không tìm thấy file ảnh bản vẽ.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải ảnh: {str(e)}")


@app.post("/mep_payment/rerun/{keyid}")
async def rerun_task_endpoint(keyid: str, background_tasks: BackgroundTasks):
    """
    Chạy lại tác vụ AI đối soát (Rerun) cho hồ sơ đã có file Excel trong session cũ.
    Giúp xử lý lại ngay lập tức khi mạng lag hoặc AI bị timeout mà không cần upload lại.
    """
    try:
        from detail_builder import safe_id
        safe_key = safe_id(keyid)

        # 1. Tìm file Excel trong các phiên làm việc cũ (tìm cả trong PRIVATE_EXCEL_DIR và PROJECT_STORAGE_DIR)
        search_roots = [PRIVATE_EXCEL_DIR, PROJECT_STORAGE_DIR]
        sess_candidates = []
        for root in search_roots:
            if root.exists():
                sess_candidates.extend(root.glob(f"*session_{safe_key}*"))
        sess_candidates = sorted(sess_candidates, key=os.path.getmtime, reverse=True)

        excel_path = None
        for s_dir in sess_candidates:
            excels = list(s_dir.glob("*.xlsx")) + list(s_dir.glob("*.xlsm"))
            if excels:
                excel_path = excels[0]
                break

        if not excel_path:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy file Excel trong thư mục session của [{keyid}]. Vui lòng upload lại file!"
            )

        print(
            f"🔄 [RERUN] Bắt đầu kích hoạt chạy lại AI cho KEYID={keyid} với file {excel_path.name}")

        # Tạo project_session_dir mới để lưu ảnh và log mới
        new_session_name = f"session_{safe_key}_{int(time.time())}"
        project_session_dir = PROJECT_STORAGE_DIR / new_session_name
        project_session_dir.mkdir(parents=True, exist_ok=True)

        update_task_status(
            keyid=keyid,
            status="RUNNING",
            reason="Đang chạy lại AI đối soát...",
            progress=5
        )
        background_tasks.add_task(
            run_ai_task_background, keyid, project_session_dir, str(excel_path))

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
