# ==========================================
# FASTAPI WORKER SERVICE (MEP AI BACKEND)
# ==========================================
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
from sql import update_task_status, update_review_decision, batch_upsert_tasks, delete_tasks

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
        update_task_status(keyid=keyid, status="RUNNING", reason="AI đang bóc tách bản vẽ & đối soát...")

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
            skip_existing=False
        )

        # ĐẾM SỐ LỖI THỰC TẾ TRONG SHEET 1 ĐỂ BÁO LÊN GIAO DIỆN
        error_count = 0
        try:
            df_check = pd.read_excel(final_excel_path, sheet_name="1. Đối Soát Bản Vẽ")
            if 'Note' in df_check.columns:
                error_count = int(df_check['Note'].astype(str).str.contains('Lệch|Mã mồ côi', na=False).sum())
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

        update_task_status(
            keyid=keyid,
            status="COMPLETED",
            error_count=error_count,
            result_link=download_link,
            reason=f"Hoàn thành đối soát 2 vòng (Phát hiện {error_count} sai lệch)"
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
            reason=error_msg[:900]
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
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file Excel (.xlsx / .xlsm)")

        safe_keyid = KEYID.replace('/', '_').replace('\\', '_')
        session_dir = STORAGE_DIR / f"session_{safe_keyid}_{int(time.time())}"
        session_dir.mkdir(parents=True, exist_ok=True)

        excel_path = session_dir / file.filename
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        update_task_status(keyid=KEYID, status="WAITING", reason="Đã nhận file, đang xếp hàng chạy...")
        background_tasks.add_task(run_ai_task_background, KEYID, session_dir, str(excel_path))

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
        raise HTTPException(status_code=404, detail="File báo cáo không tồn tại.")

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
    count = batch_upsert_tasks(req.rows)
    return {"status": "ok", "message": f"Đã lưu thành công {count} bản ghi vào Database."}

@app.post("/mep_payment/delete_rows")
async def delete_rows_endpoint(req: DeleteRowsRequest):
    """Tiếp nhận danh sách KEYID cần xóa khỏi Database."""
    if not req.keyids:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 dòng để xóa.")
    count = delete_tasks(req.keyids)
    return {"status": "ok", "message": f"Đã xóa thành công {count} bản ghi."}

@app.post("/mep_payment/review")
async def submit_review(req: ReviewRequest):
    """Tiếp nhận quyết định phê duyệt (Approve / Reject) từ Kỹ sư."""
    update_review_decision(req.keyid, req.decision, req.note, req.reviewer)
    return {"status": "ok", "message": f"Đã lưu quyết định: {req.decision}"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Khởi động MEP Payment AI Worker tại cổng 8386...")
    uvicorn.run("api:app", host="0.0.0.0", port=8386, reload=False)

