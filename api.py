
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import HTTPException
from pathlib import Path
from sql import update_status, update_status_spec
from spec_tool import StatusResponse, process_ng_lots_data, process_data

import shutil
import pandas as pd
import os
import time

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR = Path(__file__).parent / "final_result"
OUTPUT_DIR_SPEC = Path(__file__).parent / "output_analysis_spec"
# OUTPUT_DIR_SPEC = Path("D:/Private_Documents/output_analysis_spec")
OUTPUT_DIR_SPEC.mkdir(exist_ok=True)

app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các nguồn truy cập (*).
    # Để bảo mật hơn, bạn có thể liệt kê cụ thể các domain/IP, ví dụ: ["http://localhost:8800", "http://192.168.1.x:8800"]
    allow_credentials=True,  # Cho phép gửi cookie/authorization headers
    allow_methods=[
        "*"
    ],  # Cho phép tất cả các phương thức HTTP (GET, POST, PUT, DELETE...)
    allow_headers=["*"],  # Cho phép tất cả các headers
)


@app.post("/param_tool_analysis/uploadfile")
async def upload_file(
    file: UploadFile = File(...),
    KEYID: str = Form(...),
    EQPID: str = Form(...),
    PRODUCTID: str = Form(...),
):

    try:

        # Lấy phần mở rộng của file
        ext = Path(file.filename).suffix.lower()

        # Đặt tên file theo KEYID
        save_path = UPLOAD_DIR / f"{KEYID}{ext}"

        # Nếu đã tồn tại thì ghi đè (hoặc có thể kiểm tra để báo lỗi)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Cập nhật trạng thái
        update_status(keyid=KEYID, status="WAITING")

        return {"status": "accepted", "message": "Upload thành công"}

    except ValueError as e:

        return {"status": "error", "message": str(e)}

    except Exception as e:

        return {"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}

    finally:
        await file.close()


@app.post("/param_tool_analysis/search_result")
async def search_result(KEYID: str = Form(...)):
    try:
        png_file = next(RESULT_DIR.glob(f"*{KEYID}*.png"), None)
        files = list(RESULT_DIR.glob(f"*{KEYID}*.png"))

        print(KEYID, png_file, files)

        if png_file is None:
            raise HTTPException(
                status_code=404, detail="Không tìm thấy file PNG")

        return FileResponse(
            path=png_file, media_type="image/png", filename=png_file.name
        )

    except HTTPException:
        raise

    except Exception as e:
        import traceback

        traceback.print_exc()  # In đầy đủ lỗi ra console
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/param_tool_analysis/files/{filename}")
async def get_spec_result_file(filename: str):
    file_path = OUTPUT_DIR_SPEC / filename

    # Kiểm tra file có tồn tại không để tránh lỗi 500
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="File không tồn tại trên server")
    print(f"file_path_SAVE= {file_path}")
    return FileResponse(
        path=file_path,
        media_type="application/zip",
        filename=filename,
        # Bắt buộc trình duyệt tải về thay vì xem trước
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/param_tool_analysis/uploadfile_spec", response_model=StatusResponse)
async def upload_file_spec(
    spec_file: UploadFile = File(...,
                                 description="File CSV chính (lami_spec2.csv)"),
    KEYID: str = Form(...)  # Thay thế ng_file bằng keyid
):
    safe_keyid = KEYID.replace("/", "_").replace("\\", "_")
    temp_spec_path = UPLOAD_DIR / f"temp_spec_{safe_keyid}.csv"
    try:
        # 1. Validate file extensions
        if not spec_file.filename.endswith('.csv'):
            try:
                update_status_spec(keyid=KEYID, status="ERROR", result_link="",
                                   reason="Sai định dạng file, chỉ chấp nhận .csv")
            except Exception as db_err:
                print(f"Cảnh báo không thể log lỗi DB: {db_err}")

            raise HTTPException(
                status_code=400, detail="Chỉ chấp nhận file .csv cho Spec")

        # 2. Save uploaded spec file to temporary location
        with open(temp_spec_path, "wb") as buffer:
            shutil.copyfileobj(spec_file.file, buffer)

        update_status_spec(keyid=KEYID, status="RUNNING",
                           result_link="", reason="-")

        # 3. Load DataFrames
        # --- LOAD SPEC FROM FILE ---
        df = None
        encodings_to_try = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1']

        for enc in encodings_to_try:
            try:
                df = pd.read_csv(temp_spec_path, parse_dates=[
                                 "act_time"], encoding=enc)
                print(f"Thành công khi đọc file với encoding: {enc}")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e_parse:
                # Nếu lỗi không phải do encoding (ví dụ: thiếu cột), ném lỗi ngay
                raise HTTPException(
                    status_code=400, detail=f"Lỗi đọc file CSV: {str(e_parse)}")

        if df is None or df.empty:
            raise HTTPException(
                status_code=400, detail="File CSV rỗng hoặc không thể phân tích cú pháp.")

        # --- LOAD NG FROM DATABASE (THAY THẾ CHO UPLOAD FILE) ---
        print(f"Đang load dữ liệu NG từ Database Oracle với KeyID: {KEYID}...")
        ng_df = process_ng_lots_data(keyid=KEYID)
        if ng_df is None:
            raise HTTPException(
                status_code=500,
                detail=" Không thể kết nối hoặc lấy dữ liệu từ Database. Vui lòng kiểm tra log ORA-00942."
            )

        # Kiểm tra xem có lấy được dữ liệu không
        if ng_df.empty:
            raise ValueError(
                f"Không tìm thấy dữ liệu NG nào cho KeyID: {KEYID}")

        # 4. Run Processing Logic
        print("Đang chạy mô hình LightGBM và Optuna...")
        timestamp = int(time.time())
        # Loại bỏ ký tự đặc biệt
        safe_keyid = KEYID.replace("/", "_").replace("\\", "_")
        output_filename = f"spec_result_{safe_keyid}_{timestamp}.xlsx"
        output_path = OUTPUT_DIR_SPEC / output_filename
        result_path, msg = process_data(df, ng_df, output_path=output_path)
        file_url = f"/param_tool_analysis/files/{os.path.basename(result_path)}"

        try:
            # Gọi hàm update sql của bạn tại đây
            update_status_spec(keyid=KEYID, status="COMPLETED",
                               result_link=file_url, reason=msg)
            print(
                f"Đã cập nhật trạng thái COMPLETED cho KeyID: {KEYID}, path={file_url}")
        except Exception as db_update_err:
            # Lưu ý: Dù update DB thất bại, ta vẫn có thể trả về kết quả file nếu file đã tạo xong
            # Nhưng tốt nhất là log lại lỗi này để debug
            print(
                f"Cảnh báo: Không thể cập nhật trạng thái vào DB: {str(db_update_err)}")
        # 5. Return Success Response
        # Đường dẫn URL tương đối với mount point "/files"
        return StatusResponse(
            status="complete",
            message=msg,
            result_link=file_url
        )

    except Exception as e:
        try:
            update_status_spec(keyid=KEYID, status="CANCEL",
                               result_link="", reason=f"Lỗi: {str(e)}")
        except Exception as db_err:
            print(
                f"CẢNH BÁO NGHIÊM TRỌNG: Không thể cập nhật trạng thái FAIL vào DB: {db_err}")

        return StatusResponse(
            status="error",
            message=f"Lỗi: {str(e)}",
            result_link=None
        )
    finally:
        if temp_spec_path.exists():
            temp_spec_path.unlink()
