import os
import shutil
import time
import zipfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

import config
from engine import run_mep_pipeline
from sql import update_task_status, update_review_decision, batch_upsert_tasks, delete_tasks, check_keyid_exists

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

# 2. KHỞI TẠO THƯ MỤC LƯU TRỮ
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "sessions"
FINAL_REPORT_DIR = BASE_DIR / "final_reports"

STORAGE_DIR.mkdir(exist_ok=True)
FINAL_REPORT_DIR.mkdir(exist_ok=True)


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

# 3. TIẾN TRÌNH XỬ LÝ CHẠY NGẦM (BACKGROUND TASK)


def run_ai_task_background(keyid: str, session_dir: Path, excel_path: str):
    """
    Hàm này chạy hoàn toàn độc lập dưới nền (Background).
    Không làm đơ hay timeout giao diện người dùng trên OneAI.
    """
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
                print(f"⚠️ [Progress Warning] Không thể cập nhật tiến độ: {prog_err}")

        update_task_status(keyid=keyid, status="RUNNING",
                           reason="AI đang bóc tách bản vẽ & đối soát...", progress=5)

        pdf_drawings = session_dir / "drawings"
        pdf_gatepass = session_dir / "gatepass"
        csv_drawings = session_dir / "csv_drawings"
        csv_gatepass = session_dir / "csv_gatepass"
        evidence_dir = session_dir / "evidence_images"

        final_excel_path = run_mep_pipeline(
            pdf_drawing_dir=str(pdf_drawings),
            pdf_gatepass_dir=str(pdf_gatepass),
            vendor_excel_path=excel_path,
            master_data_path=excel_path,
            output_dir=str(FINAL_REPORT_DIR),
            csv_drawing_dir=str(csv_drawings),
            csv_gatepass_dir=str(csv_gatepass),
            skip_existing=False,
            status_callback=on_pipeline_progress
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
            detail_data = parse_excel_report_to_detail(Path(final_excel_path), keyid, session_dir)
            if detail_data:
                json_path = FINAL_REPORT_DIR / f"{safe_id(keyid)}_detail.json"
                with open(json_path, "w", encoding="utf-8") as jf:
                    json.dump(detail_data, jf, ensure_ascii=False, indent=2)
                print(f"💾 [Detail Cache] Đã lưu chi tiết đối soát: {json_path.name}")
        except Exception as det_err:
            print(f"⚠️ [Detail Cache Warning] {det_err}")

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
        session_dir = STORAGE_DIR / f"session_{safe_keyid}_{int(time.time())}"
        session_dir.mkdir(parents=True, exist_ok=True)

        excel_path = session_dir / file.filename
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Kiểm tra lại dung lượng sau khi ghi đĩa
        saved_file_size = excel_path.stat().st_size
        if saved_file_size > max_bytes:
            excel_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=413,
                detail=f"Dung lượng file ({saved_file_size / (1024*1024):.1f}MB) vượt quá giới hạn ({config.MAX_UPLOAD_SIZE_MB}MB)!")

        update_task_status(keyid=KEYID, status="WAITING",
                           reason="Đã nhận file, đang xếp hàng chạy...", progress=0)
        background_tasks.add_task(
            run_ai_task_background, KEYID, session_dir, str(excel_path))

        return {"status": "accepted", "message": "Nạp file thành công, AI đang khởi chạy."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await file.close()


@app.get("/mep_payment/files/{filename}")
async def download_report_file(filename: str):
    """Phục vụ tải file Báo cáo 2 Sheet về máy (Hỗ trợ cả .zip và .xlsx)."""
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
    Hỗ trợ đọc từ cache JSON, quét file Excel cũ hoặc tạo fallback an toàn.
    """
    try:
        from detail_builder import build_or_load_task_detail
        fallback_info = {
            "status": status,
            "error_count": int(error_count or 0),
            "reason": reason or ""
        }
        detail = build_or_load_task_detail(keyid, FINAL_REPORT_DIR, STORAGE_DIR, fallback_info)
        return detail
    except Exception as e:
        print(f"❌ [FastAPI Error] get_task_detail: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi đọc chi tiết đối soát: {str(e)}")


@app.get("/mep_payment/image/{keyid}/{filename}")
async def get_task_image(keyid: str, filename: str):
    """Phục vụ ảnh bản vẽ / ảnh bằng chứng đối soát để hiển thị trong Lightbox / Preview."""
    try:
        from detail_builder import safe_id
        safe_key = safe_id(keyid)

        # Quét trong các thư mục session của keyid
        for s_dir in STORAGE_DIR.glob(f"*session_{safe_key}*"):
            for sub in ["", "drawings", "evidence_images", "pages"]:
                target = (s_dir / sub / filename) if sub else (s_dir / filename)
                if target.exists() and target.is_file():
                    ext = target.suffix.lower()
                    media_type = "image/png" if ext == ".png" else "image/jpeg"
                    return FileResponse(str(target), media_type=media_type)

        raise HTTPException(status_code=404, detail="Không tìm thấy file ảnh bản vẽ.")
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

        # 1. Tìm phiên làm việc (session) gần nhất của KEYID
        sess_candidates = sorted(STORAGE_DIR.glob(f"*session_{safe_key}*"), key=os.path.getmtime, reverse=True)
        if not sess_candidates:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy phiên làm việc cũ cho [{keyid}]. Vui lòng bấm Upload lại file Excel!"
            )

        session_dir = sess_candidates[0]
        excels = list(session_dir.glob("*.xlsx")) + list(session_dir.glob("*.xlsm"))
        if not excels:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy file Excel trong thư mục session của [{keyid}]. Vui lòng upload lại file!"
            )

        excel_path = excels[0]
        print(f"🔄 [RERUN] Bắt đầu kích hoạt chạy lại AI cho KEYID={keyid} với file {excel_path.name}")

        update_task_status(
            keyid=keyid,
            status="RUNNING",
            reason="Đang chạy lại AI đối soát...",
            progress=5
        )
        background_tasks.add_task(run_ai_task_background, keyid, session_dir, str(excel_path))

        return {"status": "ok", "message": f"Đã bắt đầu chạy lại tác vụ AI cho [{keyid}]."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [FastAPI Error] rerun_task: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi kích hoạt chạy lại AI: {str(e)}")


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


