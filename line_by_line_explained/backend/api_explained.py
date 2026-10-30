# ==============================================================================
# FASTAPI WORKER SERVICE - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/api.py
# ==============================================================================

# Dòng 1-13: Nhúng các thư viện web và xử lý dữ liệu
import os                       # Thao tác đường dẫn hệ thống
import shutil                   # Sao chép và lưu luồng dữ liệu file upload
import time                     # Đóng dấu timestamp tạo thư mục session
from pathlib import Path        # Thao tác hướng đối tượng với đường dẫn file
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel  # Định nghĩa Schema dữ liệu cho API Review
import pandas as pd             # Đọc sheet kết quả để đếm số lượng lỗi

# Nhúng các module nội bộ
import config
from engine import run_mep_pipeline
from sql import update_task_status, update_review_decision

# Dòng 21: Khởi tạo ứng dụng FastAPI với tiêu đề và phiên bản
app = FastAPI(title="MEP Payment AI Worker Service", version="2.0")

# ==============================================================================
# 1. CẤU HÌNH BẢO MẬT & KẾT NỐI (CORS)
# ==============================================================================
# Dòng 27-33: Bật Cross-Origin Resource Sharing (CORS) để cho phép trình duyệt của
# nền tảng OneAI (chạy ở domain/port khác) có thể gửi request upload và download file tới cổng 8386.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Cho phép mọi domain/IP trong mạng nội bộ
    allow_credentials=True,    # Cho phép gửi cookie/token xác thực
    allow_methods=["*"],        # Cho phép mọi phương thức HTTP: GET, POST...
    allow_headers=["*"],        # Cho phép mọi header HTTP
)

# ==============================================================================
# 2. KHỞI TẠO CÁC THƯ MỤC LƯU TRỮ VẬT LÝ
# ==============================================================================
# Dòng 39-43:
# - STORAGE_DIR: Nơi tạo các thư mục session tạm theo từng lượt upload (sessions/session_KEYID_timestamp/).
# - FINAL_REPORT_DIR: Nơi lưu trữ vĩnh viễn các file Excel Báo cáo 2 Sheet sau khi AI hoàn tất.
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "sessions"
FINAL_REPORT_DIR = BASE_DIR / "final_reports"

STORAGE_DIR.mkdir(exist_ok=True)
FINAL_REPORT_DIR.mkdir(exist_ok=True)

# Dòng 48-52: Định nghĩa Schema cho API Review (Duyệt/Từ chối)
class ReviewRequest(BaseModel):
    keyid: str                 # Mã số Work Order
    decision: str              # Quyết định: 'APPROVED' hoặc 'REJECTED'
    note: str = ""             # Ghi chú của kỹ sư nghiệm thu
    reviewer: str = "PIC"      # Tên người thực hiện duyệt

# ==============================================================================
# 3. TIẾN TRÌNH XỬ LÝ CHẠY NGẦM DƯỚI NỀN (BACKGROUND TASK)
# ==============================================================================
def run_ai_task_background(keyid: str, session_dir: Path, excel_path: str):
    """
    HÀM XỬ LÝ NẶNG CHẠY NGẦM:
    - Khi người dùng bấm Upload trên OneAI, server trả về 'accepted' ngay lập tức (<0.5 giây).
    - Toàn bộ thời gian xử lý AI (~33 giây) được đẩy vào hàm này chạy trong một Thread riêng biệt.
    - Nhờ đó, giao diện web của người dùng KHÔNG BAO GIỜ BỊ ĐƠ (Freeze) hay bị Timeout!
    """
    try:
        print(f"\n🚀 [TASK {keyid}] Bắt đầu thực thi Pipeline MEP AI...")
        # Cập nhật trạng thái Oracle DB sang 'RUNNING'
        update_task_status(keyid=keyid, status="RUNNING", reason="AI đang bóc tách bản vẽ & đối soát...")

        # Định nghĩa các thư mục tạm cô lập riêng cho Work Order này
        pdf_drawings = session_dir / "drawings"
        pdf_gatepass = session_dir / "gatepass"
        csv_drawings = session_dir / "csv_drawings"
        csv_gatepass = session_dir / "csv_gatepass"

        # GỌI HÀM ENGINE LÕI 4 BƯỚC ĐÃ ĐƯỢC KIỂM CHỨNG
        final_excel_path = run_mep_pipeline(
            pdf_drawing_dir=str(pdf_drawings),
            pdf_gatepass_dir=str(pdf_gatepass),
            vendor_excel_path=excel_path,
            master_data_path=excel_path, # Dùng chung file Excel
            output_dir=str(FINAL_REPORT_DIR),
            csv_drawing_dir=str(csv_drawings),
            csv_gatepass_dir=str(csv_gatepass),
            skip_existing=False
        )

        # ĐẾM SỐ LỖI THỰC TẾ TRONG SHEET 1 ĐỂ BÁO LÊN WEB
        # Mở file báo cáo, kiểm tra cột 'Note'. Đếm số dòng xuất hiện chữ 'Lệch' hoặc 'Mã mồ côi'.
        error_count = 0
        try:
            df_check = pd.read_excel(final_excel_path, sheet_name="1. Đối Soát Bản Vẽ")
            if 'Note' in df_check.columns:
                error_count = int(df_check['Note'].astype(str).str.contains('Lệch|Mã mồ côi', na=False).sum())
        except Exception as e:
            print(f"⚠️ Cảnh báo đọc lỗi: {e}")

        # TẠO ĐƯỜNG DẪN DOWNLOAD CHO CLIENT
        file_name = os.path.basename(final_excel_path)
        download_link = f"/mep_payment/files/{file_name}"

        # CẬP NHẬT TRẠNG THÁI HOÀN TẤT VÀO ORACLE DB
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

# ==============================================================================
# 4. CÁC ENDPOINT API RESTFUL
# ==============================================================================

@app.get("/mep_payment/health")
async def health_check():
    """Endpoint kiểm tra tình trạng sống/chết (Healthcheck) của Worker."""
    return {"status": "ok", "service": "MEP Payment AI Worker", "timestamp": time.time()}

@app.post("/mep_payment/upload")
async def upload_excel_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    KEYID: str = Form(...)
):
    """
    ENDPOINT TIẾP NHẬN FILE TỪ ONEAI:
    1. Kiểm tra đuôi file (.xlsx hoặc .xlsm).
    2. Tạo thư mục session tạm cô lập.
    3. Ghi file lên đĩa.
    4. Cập nhật DB trạng thái 'WAITING'.
    5. Đẩy hàm run_ai_task_background vào hàng đợi BackgroundTasks.
    6. Trả ngay phản hồi status="accepted" cho giao diện.
    """
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
    """
    ENDPOINT TẢI BÁO CÁO:
    Trả về FileResponse với media_type chuẩn của file Excel (.xlsx)
    kèm header Content-Disposition ép trình duyệt tải về thay vì mở xem trước.
    """
    file_path = FINAL_REPORT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File báo cáo không tồn tại.")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/mep_payment/review")
async def submit_review(req: ReviewRequest):
    """
    ENDPOINT DUYỆT BÁO CÁO:
    Tiếp nhận quyết định phê duyệt ('APPROVED' hoặc 'REJECTED') từ Kỹ sư và cập nhật vào DB.
    """
    update_review_decision(req.keyid, req.decision, req.note, req.reviewer)
    return {"status": "ok", "message": f"Đã lưu quyết định: {req.decision}"}

# ==============================================================================
# 5. KHỞI CHẠY TRỰC TIẾP TỪ DÒNG LỆNH
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Khởi động MEP Payment AI Worker tại cổng 8386...")
    # host="0.0.0.0" cho phép các máy tính khác trong mạng nội bộ công ty kết nối vào
    uvicorn.run("api:app", host="0.0.0.0", port=8386, reload=False)

