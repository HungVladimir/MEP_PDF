# BẢN KẾ HOẠCH THI CÔNG HOÀN THIỆN HỆ THỐNG MEP AI (FINAL VERSION)
## TÍCH HỢP TOÀN DIỆN: CORE PIPELINE + Ý TƯỞNG CỦA SẾP + NỀN TẢNG ONEAI

> **Tài liệu chốt hạ (Master Blueprint):** Hướng dẫn chi tiết từng file cần tạo mới, từng file cần sửa đổi, nội dung code hoàn chỉnh và cách kết nối tất cả các thành phần thành một hệ thống duy nhất, vận hành trơn tru.

---

## TỔNG THỂ BẢNG PHÂN BỔ CÁC FILE TRONG DỰ ÁN

| Vị trí triển khai | Tên file | Trạng thái | Nhiệm vụ chính |
| :--- | :--- | :---: | :--- |
| **Oracle Database** | `LOCAL_AI.MEP_PAYMENT_ANALYSIS` | **Tạo mới (SQL)** | Bảng lưu trữ trung tâm các Work Order (WO) |
| **Payment_PDF (Worker)** | `engine.py` | **Nâng cấp** | Nhúng thuật toán OLE CFB của sếp để bóc PDF chống hỏng sector |
| **Payment_PDF (Worker)** | `pdf_extractor.py` | **Nâng cấp** | Chỉ lưu 1-2 ảnh bằng chứng JPG/trang, RAM chunking |
| **Payment_PDF (Worker)** | `sql.py` | **Tạo mới** | Kết nối Oracle DB bằng `oracledb` cập nhật tiến độ |
| **Payment_PDF (Worker)** | `api.py` (thay `main.py`) | **Tạo mới** | FastAPI Worker chạy ngầm, endpoint upload, download, review |
| **OneAI Portal (Core)** | `mep_payment_analysis.py` | **Tạo mới** | Định nghĩa câu SQL `QuerySettings` cho OneAI Gateway `/crud/ui` |
| **OneAI Portal (Web)** | `src/js/mepPayment.js` | **Tạo mới** | JS gọi gateway `/crud/ui` lấy danh sách bảng |
| **OneAI Portal (Web)** | `src/views/MepOperation.vue` | **Tạo mới** | Giao diện Dark Theme chuẩn 10 cột, nút upload, review |

---

# BƯỚC 1: THIẾT LẬP DATABASE TRÊN ORACLE (DBEAVER)

Mở **DBeaver**, kết nối tới Oracle DB của công ty, mở **SQL Editor (F3)** và chạy script sau để tạo bảng với đầy đủ các trường nghiệp vụ MEP lẫn các trường **Duyệt/Từ chối (Review)** từ ý tưởng của sếp:

```sql
-- 1. TẠO BẢNG CHÍNH THỨC LOCAL_AI.MEP_PAYMENT_ANALYSIS
CREATE TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS (
    KEYID           VARCHAR2(100) NOT NULL,          -- Số công việc (Số WO / Task ID) - Khóa chính
    TASK_NAME       VARCHAR2(300),                   -- Tên công việc / hạng mục
    PAYMENT_MONTH   VARCHAR2(20),                    -- Tháng thanh toán (VD: 2026-10)
    PIC             VARCHAR2(100),                   -- Người phụ trách
    PART_NAME       VARCHAR2(100),                   -- Part (MEP, Cơ điện, Xây dựng...)
    GROUP_NAME      VARCHAR2(100),                   -- Group (Infra Group, EHS...)
    STATUS          VARCHAR2(30) DEFAULT 'WAITING',  -- Trạng thái: WAITING, RUNNING, COMPLETED, CANCEL
    ERROR_COUNT     NUMBER DEFAULT 0,                -- Tổng số lỗi phát sinh (0: Khớp 100%, >0: Lệch)
    RESULT_LINK     VARCHAR2(500),                   -- Đường dẫn file Excel báo cáo 2 sheet tải về
    REASON          VARCHAR2(1000),                  -- Ghi chú chi tiết kết quả hoặc lỗi sập luồng
    REVIEW_DECISION VARCHAR2(30),                    -- Quyết định duyệt: APPROVED, REJECTED, NULL
    REVIEW_NOTE     VARCHAR2(500),                   -- Ghi chú của người duyệt
    REVIEW_BY       VARCHAR2(100),                   -- Tên người duyệt
    UPLOAD_TIME     DATE,                            -- Ngày giờ upload file
    RESULT_TIME     DATE,                            -- Ngày giờ AI đối soát xong
    CONSTRAINT PK_MEP_PAYMENT PRIMARY KEY (KEYID)
);

-- 2. TẠO CHỈ MỤC ĐỂ GIAO DIỆN LỌC NHANH
CREATE INDEX LOCAL_AI.IDX_MEP_STATUS ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (STATUS);
CREATE INDEX LOCAL_AI.IDX_MEP_MONTH  ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PAYMENT_MONTH);

-- 3. CHÈN DỮ LIỆU MẪU ĐỂ TEST HIỂN THỊ TRÊN GIAO DIỆN
INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
(KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME)
VALUES 
('WOR2512230006V', 'Thi công hệ thống điện chiếu sáng xưởng A', '2026-10', 'Nguyen Van A', 'MEP Part', 'Infra Group', 'WAITING', 0, NULL, 'Chờ upload file kiểm tra', SYSDATE);

INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
(KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME, REVIEW_DECISION)
VALUES 
('WOR2510150002M', 'Lắp đặt đường ống Chiller Phase 2', '2026-10', 'Tran Van B', 'HVAC Part', 'Infra Group', 'COMPLETED', 2, '/mep_payment/files/Sample_Report.xlsx', 'Lệch 2 mã vật tư ở Bản vẽ 1', SYSDATE, 'REJECTED');

INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
(KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME, REVIEW_DECISION)
VALUES 
('WOR2509010045E', 'Bảo trì hệ thống PCCC khu văn phòng', '2026-09', 'Le Thi C', 'Fire Safety', 'EHS Group', 'COMPLETED', 0, '/mep_payment/files/Sample_Report_2.xlsx', 'Khớp 100% không sai lệch', SYSDATE, 'APPROVED');

COMMIT;
```

---

# BƯỚC 2: NÂNG CẤP LÕI AI TRONG PROJECT `Payment_PDF`

### 1. Nâng cấp `engine.py`: Nhúng hàm giải mã OLE Binary xịn từ code của sếp
Thay vì chỉ giải nén zip đơn thuần, ta bổ sung thuật toán đọc OLE Compound File (`struct`) của sếp vào hàm `extract_pdfs_from_excel`. Điều này giúp hệ thống không bao giờ bị đứt file PDF dù Excel phân mảnh sector.

Trong file `d:\Project\Payment_PDF\engine.py`, cập nhật phần trích xuất PDF:

```python
import struct
import zipfile
import re
import os
import xml.etree.ElementTree as ET
import config
import utils as ut

PDF_HEAD, PDF_EOF = b"%PDF-", b"%%EOF"
CFB_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
ENDS = 0xFFFFFFFA

def find_pdf_bytes(b: bytes):
    """Tìm chuỗi nhị phân PDF chuẩn trong stream dữ liệu."""
    s = b.find(PDF_HEAD)
    if s < 0: return None
    e = b.rfind(PDF_EOF)
    return b[s:e + 5] if e > s else b[s:]

def cfb_streams(data: bytes):
    """Giải mã cấu trúc OLE Compound Binary theo từng sector (Code của sếp)."""
    if data[:8] != CFB_SIG: return []
    try:
        ssz = 1 << struct.unpack_from("<H", data, 30)[0]
        mssz = 1 << struct.unpack_from("<H", data, 32)[0]
        (n_fat, dir_start, _, mini_cutoff, minifat_start, n_minifat, difat_start, n_difat) = struct.unpack_from("<8I", data, 44)
        sec = lambda i: data[(i + 1) * ssz:(i + 2) * ssz]
        per = ssz // 4
        difat = list(struct.unpack_from("<109I", data, 76))
        d, k = difat_start, 0
        while d < ENDS and k < n_difat:
            ent = struct.unpack(f"<{per}I", sec(d))
            difat += ent[:-1]
            d, k = ent[-1], k + 1
        fat = []
        for f in difat[:max(n_fat, 0) or len(difat)]:
            if f < ENDS: fat += struct.unpack(f"<{per}I", sec(f))

        def chain(start, table):
            seen = set()
            while start < ENDS and start < len(table) and start not in seen:
                seen.add(start); yield start; start = table[start]

        read = lambda start, size=None: b"".join(sec(i) for i in chain(start, fat))[:size]
        dirs = read(dir_start)
        entries = []
        for off in range(0, len(dirs) - 127, 128):
            e = dirs[off:off + 128]
            nlen = struct.unpack_from("<H", e, 64)[0]
            name = e[:max(nlen - 2, 0)].decode("utf-16-le", "ignore")
            typ = e[66]
            start, size = struct.unpack_from("<II", e, 116)
            entries.append((name, typ, start, size))
        if not entries: return []
        root = entries[0]
        mini_stream = read(root[2], root[3]) if root[2] < ENDS else b""
        minifat = []
        if n_minifat and minifat_start < ENDS:
            raw = read(minifat_start)
            minifat = list(struct.unpack(f"<{len(raw) // 4}I", raw[:len(raw) // 4 * 4]))

        out = []
        for name, typ, start, size in entries[1:]:
            if typ != 2 or size == 0: continue
            if size < mini_cutoff:
                b = b"".join(mini_stream[i * mssz:(i + 1) * mssz] for i in chain(start, minifat))[:size]
            else:
                b = read(start, size)
            out.append((name, b))
        return out
    except Exception:
        return []

def extract_pdfs_from_excel(excel_path, out_drawings_dir, out_gatepass_dir):
    """
    Rạch bụng Excel, kết hợp lọc theo Sheet quan hệ XML và giải mã OLE nhị phân.
    """
    if not os.path.exists(excel_path): return
    os.makedirs(out_drawings_dir, exist_ok=True)
    os.makedirs(out_gatepass_dir, exist_ok=True)

    ns = {
        'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'
    }

    try:
        with zipfile.ZipFile(excel_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            if 'xl/workbook.xml' not in file_list: return

            wb_root = ET.fromstring(zip_ref.read('xl/workbook.xml'))
            sheet_map = {}
            for sheet in wb_root.findall('.//main:sheet', ns):
                name = sheet.attrib.get('name', '').lower()
                r_id = sheet.attrib.get(f"{{{ns['r']}}}id")
                if r_id: sheet_map[r_id] = name

            rels_root = ET.fromstring(zip_ref.read('xl/_rels/workbook.xml.rels'))
            sheet_file_map = {}
            for rel in rels_root.findall('.//rels:Relationship', ns):
                r_id = rel.attrib.get('Id')
                target = rel.attrib.get('Target')
                if r_id in sheet_map and target:
                    sheet_filename = target.split('/')[-1]
                    sheet_file_map[sheet_filename] = sheet_map[r_id]

            extracted_count = 0
            for rel_file in file_list:
                if rel_file.startswith('xl/worksheets/_rels/') and rel_file.endswith('.rels'):
                    sheet_filename = rel_file.split('/')[-1].replace('.rels', '')
                    sheet_name = sheet_file_map.get(sheet_filename, "")
                    sheet_lower = sheet_name.lower()

                    target_dir = None
                    prefix = ""
                    if any(kw in sheet_lower for kw in config.SHEET_KEYWORDS_DRAWING):
                        target_dir = out_drawings_dir; prefix = "Ban_Ve"
                    elif any(kw in sheet_lower for kw in config.SHEET_KEYWORDS_GATEPASS):
                        target_dir = out_gatepass_dir; prefix = "BBGN"

                    if not target_dir: continue

                    s_rels_root = ET.fromstring(zip_ref.read(rel_file))
                    idx = 1
                    for rel in s_rels_root.findall('.//rels:Relationship', ns):
                        target_path = rel.attrib.get('Target', '')
                        if 'embeddings/' in target_path:
                            embed_filename = target_path.split('/')[-1]
                            zip_embed_path = f"xl/embeddings/{embed_filename}"

                            if zip_embed_path in file_list:
                                data = zip_ref.read(zip_embed_path)
                                pdf_data = None
                                
                                # Ưu tiên 1: Đọc bằng giải mã sector OLE của sếp
                                for _, b in cfb_streams(data):
                                    p = find_pdf_bytes(b)
                                    if p and (pdf_data is None or len(p) > len(pdf_data)):
                                        pdf_data = p
                                
                                # Ưu tiên 2: Fallback tìm trực tiếp
                                if pdf_data is None:
                                    pdf_data = find_pdf_bytes(data)

                                if pdf_data:
                                    clean_sheet_name = ut.clean_vietnamese_filename(sheet_name)
                                    out_pdf_name = f"{prefix}_{clean_sheet_name}_File_{idx}.pdf"
                                    out_pdf_path = os.path.join(target_dir, out_pdf_name)
                                    with open(out_pdf_path, 'wb') as f_out:
                                        f_out.write(pdf_data)
                                    print(f"   [+] Đã móc được PDF chuẩn từ Sheet '{sheet_name}' -> {out_pdf_name}")
                                    extracted_count += 1
                                    idx += 1

            print(f"🎉 Tổng kết trích xuất: {extracted_count} file PDF sẵn sàng xử lý.")
    except Exception as e:
        print(f"⚠️ Lỗi khi trích xuất PDF từ Excel: {e}")
```

---

### 2. Tinh chỉnh `pdf_extractor.py`: Chỉ lưu 1-2 ảnh bằng chứng JPG / trang (Tiết kiệm 99% đĩa)
Trong `pdf_extractor.py`:
- **KHÔNG GHI ĐĨA** các khúc cắt nhỏ (`chunk_1.png`...). Chuyển trực tiếp numpy array trên RAM sang Base64 gửi AI.
- **CHỈ GHI ĐÚNG 2 ẢNH JPEG (85% Quality)**:
  1. `BV_page{N}_TableCrop.jpg` (ảnh bảng sau khi Magic Crop)
  2. `BV_page{N}_DrawingNo_ROI.jpg` (ảnh góc số bản vẽ)
  3. Với Gate Pass: `GATEPASS_page{N}_TableCrop.jpg`.

Code tinh chỉnh trong hàm `process_single_pdf`:
```python
# Trong pdf_extractor.py -> process_single_pdf():
# Thay đổi đuôi file và chất lượng lưu ảnh bằng chứng:
jpeg_opts = [int(cv2.IMWRITE_JPEG_QUALITY), 85]

# 1. Lưu ảnh ROI số bản vẽ (chỉ 1 ảnh nhỏ 30KB)
if case_type != "gate_pass":
    roi_img = capture_roi_image(page)
    roi_save_path = os.path.join(config.DIR_IMG_EXTRACTED, f"{base_name}_p{page_num+1}_ROI.jpg")
    cv2.imwrite(roi_save_path, roi_img, jpeg_opts)
    # ...

# 2. Lưu ảnh bảng khối lượng gốc (chỉ 1 ảnh khoảng 150KB)
for tbl_idx, table_img in enumerate(table_imgs):
    table_save_path = os.path.join(config.DIR_IMG_EXTRACTED, f"{base_name}_p{page_num+1}_tbl{tbl_idx+1}_{case_type}.jpg")
    cv2.imwrite(table_save_path, table_img, jpeg_opts)

    # CẮT KHÚC CHỈ ĐỂ GỬI AI - TUYỆT ĐỐI KHÔNG GHI RA Ổ CỨNG (BỎ cv2.imwrite chunk)
    if h > config.MAX_CHUNK_HEIGHT:
        # cut_points...
        for i in range(len(cut_points) - 1):
            img_chunk = table_img[cut_points[i]:cut_points[i+1], :]
            if np.std(img_chunk) < 5: continue
            # ĐƯA TRỰC TIẾP VÀO TASK GỌI AI TRÊN RAM
            tasks.append({"type": "table", "case_type": case_type, "img": img_chunk, "label": f"Bảng {tbl_idx+1} - Khúc {i+1}"})
```

---

### 3. Tạo file `sql.py`: Kết nối Oracle DB (Thư viện `oracledb`)
Tạo file mới tại: `d:\Project\Payment_PDF\sql.py`:

```python
# File: d:\Project\Payment_PDF\sql.py
import oracledb
import os

DB_USER     = os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mat_khau_db")
DB_HOST     = os.getenv("DB_HOST", "107.126.xx.xx")
DB_PORT     = int(os.getenv("DB_PORT", 1521))
DB_SERVICE  = os.getenv("DB_SERVICE", "MBAYMS")

def get_connection():
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            service_name=DB_SERVICE
        )
        return conn
    except Exception as e:
        print(f"❌ [Oracle DB Error] Không thể kết nối DB: {e}")
        return None

def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """Cập nhật tiến trình AI vào Oracle DB."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        sql = """
            UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
            SET STATUS       = :status,
                ERROR_COUNT  = :error_count,
                RESULT_LINK  = :result_link,
                REASON       = :reason,
                RESULT_TIME  = CASE WHEN :status IN ('COMPLETED', 'CANCEL') THEN SYSDATE ELSE RESULT_TIME END,
                UPLOAD_TIME  = CASE WHEN :status = 'WAITING' THEN SYSDATE ELSE UPLOAD_TIME END
            WHERE KEYID = :keyid
        """
        cursor.execute(sql, {
            "status": status,
            "error_count": error_count,
            "result_link": result_link,
            "reason": reason,
            "keyid": keyid
        })
        conn.commit()
        print(f"📊 [Oracle DB] Đã cập nhật KEYID={keyid} -> STATUS={status}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_task_status: {e}")
    finally:
        cursor.close()
        conn.close()

def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    """Cập nhật quyết định phê duyệt (Approve / Reject) của kỹ sư."""
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        sql = """
            UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
            SET REVIEW_DECISION = :decision,
                REVIEW_NOTE     = :note,
                REVIEW_BY       = :reviewer
            WHERE KEYID = :keyid
        """
        cursor.execute(sql, {
            "decision": decision,
            "note": note,
            "reviewer": reviewer,
            "keyid": keyid
        })
        conn.commit()
        print(f"✅ [Oracle DB] Review xong KEYID={keyid} -> {decision}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_review_decision: {e}")
    finally:
        cursor.close()
        conn.close()
```

---

### 4. Tạo file `api.py`: FastAPI Worker chạy ngầm (Thay thế `main.py` cũ)
Tạo file mới tại: `d:\Project\Payment_PDF\api.py`:

```python
# File: d:\Project\Payment_PDF\api.py
import os
import shutil
import time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

import config
from engine import run_mep_pipeline
from sql import update_task_status, update_review_decision

app = FastAPI(title="MEP Payment AI Worker Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = Path(__file__).resolve().parent / "sessions"
FINAL_REPORT_DIR = Path(__file__).resolve().parent / "final_reports"
STORAGE_DIR.mkdir(exist_ok=True)
FINAL_REPORT_DIR.mkdir(exist_ok=True)

class ReviewRequest(BaseModel):
    keyid: str
    decision: str  # APPROVED hoặc REJECTED
    note: str = ""
    reviewer: str = "PIC"

def run_ai_task_background(keyid: str, session_dir: Path, excel_path: str):
    try:
        print(f"\n🚀 [TASK {keyid}] Bắt đầu chạy ngầm Pipeline MEP AI...")
        update_task_status(keyid=keyid, status="RUNNING", reason="AI đang bóc tách bản vẽ & đối soát...")

        pdf_drawings = session_dir / "drawings"
        pdf_gatepass = session_dir / "gatepass"
        csv_drawings = session_dir / "csv_drawings"
        csv_gatepass = session_dir / "csv_gatepass"

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

        # ĐẾM SỐ LỖI THỰC TẾ TRONG SHEET 1 ĐỂ BÁO LÊN WEB
        error_count = 0
        try:
            df_check = pd.read_excel(final_excel_path, sheet_name="1. Đối Soát Bản Vẽ")
            if 'Note' in df_check.columns:
                error_count = int(df_check['Note'].astype(str).str.contains('Lệch|Mã mồ côi', na=False).sum())
        except Exception as e:
            print(f"⚠️ Lỗi đếm số dòng lệch: {e}")

        file_name = os.path.basename(final_excel_path)
        download_link = f"/mep_payment/files/{file_name}"

        update_task_status(
            keyid=keyid,
            status="COMPLETED",
            error_count=error_count,
            result_link=download_link,
            reason=f"Hoàn thành đối soát (Phát hiện {error_count} sai lệch)"
        )
        print(f"🎉 [TASK {keyid}] THÀNH CÔNG -> Link: {download_link}")

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

@app.post("/mep_payment/upload")
async def upload_excel_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    KEYID: str = Form(...)
):
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
    update_review_decision(req.keyid, req.decision, req.note, req.reviewer)
    return {"status": "ok", "message": f"Đã lưu quyết định: {req.decision}"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Khởi động MEP Payment AI Worker tại cổng 8386...")
    uvicorn.run("api:app", host="0.0.0.0", port=8386, reload=False)
```

---

# BƯỚC 3: THIẾT LẬP PHÍA NỀN TẢNG ONEAI PORTAL

### 1. Tạo file backend truy vấn DB: `mep_payment_analysis.py`
Tạo file này trong thư mục backend của OneAI (cùng vị trí với `cdm_analysis.py`):

```python
# File: mep_payment_analysis.py (Backend OneAI Portal)
from database.query_utils import QuerySettings

searchTotalRow = QuerySettings(
    query="""
        SELECT COUNT(*) AS TOTAL
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    """,
    dns="MBAYMS",
    note="Đếm tổng số dòng quản lý thanh toán MEP"
)

getdata_page = QuerySettings(
    query="""
    SELECT 
        RN AS STT,
        KEYID,
        TASK_NAME,
        PAYMENT_MONTH,
        PIC,
        PART_NAME,
        GROUP_NAME,
        STATUS,
        ERROR_COUNT,
        RESULT_LINK,
        REASON,
        REVIEW_DECISION,
        REVIEW_NOTE,
        REVIEW_BY,
        TO_CHAR(UPLOAD_TIME, 'YYYY-MM-DD HH24:MI') AS UPLOAD_TIME,
        TO_CHAR(RESULT_TIME, 'YYYY-MM-DD HH24:MI') AS RESULT_TIME
    FROM (
        SELECT A.*,
               ROW_NUMBER() OVER(ORDER BY UPLOAD_TIME DESC NULLS LAST, KEYID DESC) RN
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS A
        WHERE 1 = 1
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    )
    WHERE RN BETWEEN :start_row AND :end_row
    ORDER BY RN
    """,
    dns="MBAYMS",
    note="Lấy danh sách phân trang bảng MEP"
)
```

---

### 2. Tạo file Javascript gọi Gateway: `src/js/mepPayment.js`
Tạo file trong thư mục `src/js/` của Frontend OneAI:

```javascript
// File: src/js/mepPayment.js
import { api } from '@/aiPlugins/aiApiConfig'

// Đổi tiền tố menu theo đúng thư mục khai báo trên OneAI của bạn
const BASE_REQ_ID = "menu_operation.mep_payment.mep_payment_analysis"

export async function get_total_row(status = "ALL", paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:searchTotalRow`
  const param = {
    STATUS: status || "ALL",
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const res = await api.get("/crud/ui", { params: { [reqId]: param }, loading: false })
  return res.data[reqId].VAL
}

export async function get_data_page(page = 1, pageSize = 50, status = "ALL", paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:getdata_page`
  const param = {
    start_row: (page - 1) * pageSize + 1,
    end_row: page * pageSize,
    STATUS: status || "ALL",
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const res = await api.get("/crud/ui", { params: { [reqId]: param }, loading: false })
  return res.data[reqId].VAL
}
```

---

### 3. Tạo Giao diện Vue 3 hoàn chỉnh: `src/views/MepOperation.vue`
File Vue này chứa đầy đủ:
- **Dark Theme** chuẩn mực của OneAI như ảnh `1.jpg`.
- **Thanh Toolbar lọc**: Trạng thái, Tháng thanh toán, Tìm kiếm số WO/Tên task, Đồng hồ Reload đếm ngược 10s.
- **Bảng 10 cột nghiệp vụ đúng yêu cầu**:
  1. STT
  2. Số công việc (WO)
  3. Tên công việc
  4. Tháng thanh toán
  5. Người phụ trách (PIC)
  6. Part
  7. Group
  8. Nút Upload File trên từng dòng
  9. Kết quả kiểm tra (Tag Xanh khớp 100% / Tag Đỏ số lỗi)
  10. Nút tải Báo cáo 2 Sheet + Nút Duyệt / Từ chối (Review Workflow).

```vue
<!-- File: src/views/MepOperation.vue -->
<template>
  <div class="mep-container">
    <!-- TOOLBAR LỌC DỮ LIỆU -->
    <div class="toolbar">
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable style="width: 170px">
        <el-option v-for="item in statusList" :key="item" :label="item" :value="item" />
      </el-select>

      <el-date-picker
        v-model="selectedMonth"
        type="month"
        placeholder="Chọn Tháng Thanh Toán"
        value-format="YYYY-MM"
        style="width: 190px"
      />

      <el-input
        v-model="searchKeyword"
        placeholder="Nhập số WO hoặc tên công việc..."
        clearable
        style="width: 270px"
        @keyup.enter="handleReload"
      />

      <el-button type="primary" @click="handleReload">
        Reload ({{ countdown }}s)
      </el-button>
    </div>

    <!-- BẢNG DỮ LIỆU 10 CỘT -->
    <div class="table-container">
      <el-table
        :data="tableData"
        border
        height="720"
        size="small"
        style="width: 100%"
        show-overflow-tooltip
      >
        <el-table-column prop="STT" label="STT" width="55" align="center" />

        <el-table-column prop="KEYID" label="Số Công Việc (WO)" width="150" sortable align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain" class="font-bold">{{ row.KEYID }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="TASK_NAME" label="Tên Công Việc" min-width="200" show-overflow-tooltip />
        <el-table-column prop="PAYMENT_MONTH" label="Tháng TT" width="95" align="center" sortable />
        <el-table-column prop="PIC" label="Người Phụ Trách" width="125" align="center" />
        <el-table-column prop="PART_NAME" label="Part" width="95" align="center" />
        <el-table-column prop="GROUP_NAME" label="Group" width="105" align="center" />

        <!-- CỘT TRẠNG THÁI HỆ THỐNG -->
        <el-table-column prop="STATUS" label="Trạng Thái" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.STATUS === 'COMPLETED'" type="success" effect="dark">Hoàn Tất</el-tag>
            <el-tag v-else-if="row.STATUS === 'RUNNING'" type="warning" effect="dark">Đang Xử Lý</el-tag>
            <el-tag v-else-if="row.STATUS === 'WAITING'" type="info">Chờ Duyệt</el-tag>
            <el-tag v-else type="danger">{{ row.STATUS }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT 8: UPLOAD FILE EXCEL -->
        <el-table-column label="Tài Liệu Đính Kèm" width="125" align="center">
          <template #default="{ row }">
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              accept=".xlsx,.xlsm"
              :on-change="(file) => handleUploadExcel(file, row)"
              :disabled="row.STATUS === 'RUNNING'"
            >
              <el-button
                type="primary"
                size="small"
                :loading="row.STATUS === 'RUNNING'"
                :disabled="row.STATUS === 'RUNNING'"
              >
                {{ row.STATUS === 'RUNNING' ? 'Đang chạy...' : '+ Upload File' }}
              </el-button>
            </el-upload>
          </template>
        </el-table-column>

        <!-- CỘT 9: KẾT QUẢ KIỂM TRA -->
        <el-table-column label="Kết Quả Kiểm Tra" width="150" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <el-tag v-if="row.ERROR_COUNT === 0" type="success" effect="light">
                ✅ Khớp 100% (0 lỗi)
              </el-tag>
              <el-tag v-else type="danger" effect="dark">
                ❌ Lệch {{ row.ERROR_COUNT }} lỗi
              </el-tag>
            </div>
            <span v-else-if="row.STATUS === 'RUNNING'" style="color: #E6A23C;">
              <i class="el-icon-loading"></i> Đang đối soát AI...
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>

        <!-- CỘT 10: CHI TIẾT BÁO CÁO & DUYỆT (REVIEW) -->
        <el-table-column label="Chi Tiết Báo Cáo" min-width="210" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <!-- Nút tải file Excel -->
              <a v-if="row.RESULT_LINK" :href="getDownloadUrl(row.RESULT_LINK)" target="_blank" download class="download-link">
                📥 Tải Báo Cáo 2 Sheet
              </a>
              <!-- Trạng thái Review hoặc Nút bấm Review -->
              <div style="margin-top: 4px;">
                <el-tag v-if="row.REVIEW_DECISION === 'APPROVED'" type="success" size="small">Đã Duyệt</el-tag>
                <el-tag v-else-if="row.REVIEW_DECISION === 'REJECTED'" type="danger" size="small">Từ Chối</el-tag>
                <div v-else style="display: inline-flex; gap: 4px;">
                  <el-button type="success" size="mini" @click="handleReview(row, 'APPROVED')">Duyệt</el-button>
                  <el-button type="danger" size="mini" @click="handleReview(row, 'REJECTED')">Hủy</el-button>
                </div>
              </div>
            </div>
            <span v-else-if="row.REASON" class="text-reason">{{ row.REASON }}</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- PHÂN TRANG -->
      <div class="pagination-bar">
        <el-button @click="goFirst" :disabled="page === 1">First</el-button>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
        <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
        <el-button @click="goLast" :disabled="page === totalPages">Last</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { get_total_row, get_data_page } from '../js/mepPayment'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// Cấu hình URL tới Worker FastAPI của bạn
const FASTAPI_BASE_URL = "http://127.0.0.1:8386"

const selectedStatus = ref('')
const selectedMonth = ref('')
const searchKeyword = ref('')
const tableData = ref([])

const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const countdown = ref(10)

const statusList = ref(['ALL', 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL'])

let timer = null
let countdownTimer = null

const loadData = async () => {
  try {
    tableData.value = await get_data_page(
      page.value, pageSize.value,
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
  } catch (err) {
    console.error("Lỗi tải dữ liệu:", err)
  }
}

const loadTotal = async () => {
  try {
    const res = await get_total_row(
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
    total.value = res?.[0]?.TOTAL ?? 0
  } catch (err) {
    console.error("Lỗi lấy tổng số dòng:", err)
  }
}

const handleReload = async () => {
  await loadData()
  await loadTotal()
  countdown.value = 10
}

onMounted(() => {
  handleReload()
  timer = setInterval(() => {
    loadData()
    loadTotal()
    countdown.value = 10
  }, 10 * 1000)

  countdownTimer = setInterval(() => {
    if (countdown.value > 0) countdown.value--
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(countdownTimer)
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const handlePageChange = (p) => { page.value = p; loadData(); }
const handleSizeChange = (s) => { pageSize.value = s; page.value = 1; loadData(); }
const goFirst = () => { if (page.value > 1) { page.value = 1; loadData(); } }
const goLast = () => { if (page.value < totalPages.value) { page.value = totalPages.value; loadData(); } }

watch([selectedStatus, selectedMonth], () => {
  page.value = 1
  handleReload()
})

const handleUploadExcel = async (file, row) => {
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xlsm')) {
    ElMessage.error("Chỉ chấp nhận file Excel (.xlsx / .xlsm)")
    return
  }

  const formData = new FormData()
  formData.append("file", file.raw)
  formData.append("KEYID", row.KEYID)

  row.STATUS = 'RUNNING'
  row.REASON = 'Đang đẩy file lên AI Server...'

  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData)
    if (res.data.status === "accepted") {
      ElMessage.success(`Đã nạp file cho WO [${row.KEYID}]. AI đang phân tích...`)
      setTimeout(handleReload, 2000)
    } else {
      ElMessage.error(res.data.message || "Upload thất bại!")
      row.STATUS = 'CANCEL'
    }
  } catch (err) {
    ElMessage.error("Mất kết nối tới Server FastAPI Worker!")
    row.STATUS = 'CANCEL'
  }
}

const handleReview = async (row, decision) => {
  const actionText = decision === 'APPROVED' ? 'Duyệt thanh toán' : 'Từ chối thanh toán'
  try {
    const { value: note } = await ElMessageBox.prompt(`Nhập ghi chú ${actionText}:`, 'Xác nhận Review', {
      confirmButtonText: 'Xác nhận',
      cancelButtonText: 'Hủy'
    })

    await axios.post(`${FASTAPI_BASE_URL}/mep_payment/review`, {
      keyid: row.KEYID,
      decision: decision,
      note: note || '',
      reviewer: 'PIC'
    })

    ElMessage.success(`Đã cập nhật: ${actionText}`)
    handleReload()
  } catch {
    // Người dùng bấm Hủy prompt
  }
}

const getDownloadUrl = (link) => {
  if (!link) return '#'
  return link.startsWith('http') ? link : `${FASTAPI_BASE_URL}${link}`
}
</script>

<style scoped>
.mep-container { padding: 12px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 15px; }
.table-container { width: 100%; overflow-x: auto; }
.font-bold { font-weight: 600; }
.download-link { color: #67C23A; font-weight: bold; text-decoration: underline; cursor: pointer; display: inline-block; }
.download-link:hover { color: #85ce61; }
.text-reason { color: #F56C6C; font-size: 11px; }
.pagination-bar { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 15px; }
.page-indicator { margin-left: 10px; color: #909399; }
</style>
```

---

# BƯỚC 4: QUY TRÌNH KẾT NỐI VÀ CHẠY THỬ NGHIỆM TỪNG BƯỚC

1. **Khởi chạy Oracle DB**: 
   - Chạy script tạo bảng và chèn 3 dòng dữ liệu mẫu ở Bước 1 trên DBeaver.
2. **Khởi động AI Worker (FastAPI)**:
   - Mở terminal tại thư mục `Payment_PDF`:
     ```bash
     python api.py
     ```
   - Xác nhận server đang lắng nghe tại: `http://127.0.0.1:8386`.
3. **Khởi động OneAI Web Portal**:
   - Chạy Vue frontend (`npm run serve` hoặc `npm run dev`).
   - Mở trình duyệt vào trang MEP. Màn hình Dark Theme sẽ hiện ra đúng 10 cột cùng 3 dòng mẫu.
4. **Kiểm tra Upload & Đối soát End-to-End**:
   - Tại dòng `WOR2512230006V`, bấm nút `[+ Upload File]`.
   - Chọn file Excel thanh toán thực tế (hoặc file mẫu có nhúng PDF).
   - Quan sát dòng chuyển sang màu vàng `Đang Xử Lý`.
   - Sau khoảng 30–35 giây, Polling 10s tự động cập nhật:
     - Dòng chuyển sang màu xanh `Hoàn Tất`.
     - Cột kết quả hiện: `✅ Khớp 100%` hoặc `❌ Lệch X lỗi`.
     - Cột chi tiết xuất hiện link: `📥 Tải Báo Cáo 2 Sheet`.
     - Bấm tải file Excel về kiểm tra các ô tô màu Đỏ/Xanh.
     - Kỹ sư bấm nút `[Duyệt]` $\rightarrow$ Cập nhật trạng thái `Đã Duyệt` vào Oracle DB.

