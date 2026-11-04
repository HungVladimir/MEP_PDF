"""Quy trình xử lý 1 workorder: Excel -> PDF -> ảnh -> AI -> so sánh -> lưu kết quả."""
import glob
import os
import shutil
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from .. import db
from ..config import DATA_DIR, WORKERS
from .ai import mock_read, read_page
from .bom import parse_bom
from .compare import compare
from .extract import extract_from_xlsx
from .render import pdf_to_jpegs, to_jpeg

EXECUTOR = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="wo")


def wo_dir(wo_id):
    return os.path.join(DATA_DIR, "wo", wo_id)


def source_path(wo_id):
    return os.path.join(wo_dir(wo_id), "source.xlsx")


def extra_path(wo_id):
    f = glob.glob(os.path.join(wo_dir(wo_id), "extra.*"))
    return f[0] if f else None


def page_path(wo_id, n):
    return os.path.join(wo_dir(wo_id), "pages", f"p{n:03d}.jpg")


def submit(wo_id):
    db.update_wo(wo_id, status="running", fail_reason="", result=None, error_count=None, log=[],
                 review_decision=None, review_by=None, review_by_name=None, review_note=None, review_at=None)
    EXECUTOR.submit(run, wo_id)


def run(wo_id):
    logs = []
    last = [0.0]

    def log(m, force=False):
        logs.append(time.strftime("%H:%M:%S") + "  " + m)
        if force or time.time() - last[0] > 1:  # ghi DB tối đa 1 lần/giây
            db.update_wo(wo_id, log=logs)
            last[0] = time.time()

    st = db.get_settings()
    try:
        w = db.get_wo(wo_id, full=False)
        log("Đọc file Excel: " + (w["file_name"] or ""), True)
        bom = parse_bom(source_path(wo_id), st)
        if not bom or not bom["items"]:
            raise RuntimeError('Không tìm thấy sheet danh sách vật tư (không thấy cột "Mã vật tư"). Kiểm tra Cài đặt Excel.')
        log(f'Sheet vật tư: "{bom["sheet"]}", dòng tiêu đề {bom["hdr"]}, {len(bom["items"])} vật tư, {len(bom["dcols"])} cột bản vẽ')

        pdf_list, pages = [], []
        extra = extra_path(wo_id)
        if extra:
            log("Dùng file PDF/ảnh upload riêng: " + (w["pdf_name"] or ""))
            data = open(extra, "rb").read()
            if extra.lower().endswith(".pdf"):
                pdf_list.append(data)
                pages = pdf_to_jpegs(data, st["res"])
            else:
                pages = [to_jpeg(data)]
        else:
            pdfs, images = extract_from_xlsx(source_path(wo_id), log)
            for _, b in pdfs:
                pdf_list.append(b)
                pages += pdf_to_jpegs(b, st["res"])
            if not pages and images:
                log(f"Không có PDF nhúng, dùng {len(images)} ảnh trong Excel")
                pages = [to_jpeg(b) for b in images]
        if not pages:
            raise RuntimeError("Không tìm thấy PDF hay ảnh nhúng trong Excel. Hãy upload PDF riêng.")

        pdir = os.path.join(wo_dir(wo_id), "pages")
        shutil.rmtree(pdir, ignore_errors=True)
        os.makedirs(pdir)
        for i, b in enumerate(pages, 1):
            open(page_path(wo_id, i), "wb").write(b)
        db.update_wo(wo_id, page_count=len(pages))

        if st.get("mock"):
            if not pdf_list:
                raise RuntimeError("Chế độ thử chỉ đọc được PDF có lớp chữ. Tắt chế độ thử để dùng AI.")
            log(f"CHẾ ĐỘ THỬ: đọc chữ trong {len(pages)} trang PDF (không gọi AI)")
            drawings = mock_read(pdf_list, log)
        else:
            log(f"Gửi {len(pages)} trang cho AI ({st['model']}) đọc...", True)
            with ThreadPoolExecutor(max_workers=max(1, int(st.get("conc") or 1))) as ex:
                parts = list(ex.map(lambda a: read_page(st, a[1], a[0], log), enumerate(pages)))
            drawings = [d for p in parts for d in p]

        res = compare(drawings, bom, st)
        res.update(sheet=bom["sheet"], excel_items=len(bom["items"]), excel_dwgs=len(bom["dcols"]), pages=len(pages), at=time.time(),
                   mode="Chế độ thử" if st.get("mock") else st.get("model"))
        log(f"Xong: {len(res['errors'])} lỗi", True)
        db.update_wo(wo_id, status="error" if res["errors"] else "ok", result=res, error_count=len(res["errors"]), log=logs)
    except Exception as e:
        traceback.print_exc()
        log("THẤT BẠI: " + str(e), True)
        db.update_wo(wo_id, status="failed", fail_reason=str(e), log=logs)