# ==============================================================================
# BỘ ĐIỀU PHỐI TỔNG TÀI - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/engine.py
# ==============================================================================

# Dòng 1-13: Nhúng các thư viện hệ thống và các module nội bộ của dự án
import os              # Thao tác đường dẫn, tạo thư mục
import glob            # Tìm kiếm file theo mẫu wildcard (*.pdf, *.csv)
import time            # Đo thời gian thực thi của từng bước
import traceback       # In đầy đủ vết ngăn xếp khi gặp lỗi hệ thống
import zipfile         # Giải nén cấu trúc file Excel (.xlsx thực chất là file nén zip)
import re              # Xử lý chuỗi bằng biểu thức chính quy
import struct          # Giải mã nhị phân byte dữ liệu OLE Compound File
import xml.etree.ElementTree as ET # Đọc và phân tích cây XML của Microsoft Office

# Nhúng 4 module chuyên trách của dự án
import config          # Đọc các thông số cấu hình
import pdf_extractor   # Module thị giác máy tính và gọi AI Vision
import excel_reconciler# Module não bộ toán học đối soát 2 vòng
import utils as ut     # Hàm chuẩn hóa tên file an toàn

# ==============================================================================
# KHU VỰC 1: THUẬT TOÁN GIẢI MÃ NHỊ PHÂN OLE COMPOUND FILE (TỪ CODE CỦA SẾP)
# ==============================================================================

# Dòng 26-28: Định nghĩa các hằng số nhận diện chữ ký nhị phân
# PDF_HEAD: Chữ ký bắt đầu của file PDF (%PDF-)
# PDF_EOF: Chữ ký kết thúc của file PDF (%%EOF)
# CFB_SIG: Chữ ký 8 byte đặc trưng của file Microsoft Compound File Binary (D0CF11E0A1B11AE1)
# ENDS: Ngưỡng sector đặc biệt của bảng FAT trong file OLE
PDF_HEAD, PDF_EOF = b"%PDF-", b"%%EOF"
CFB_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
ENDS = 0xFFFFFFFA

def find_pdf_bytes(b: bytes):
    """
    HÀM TÌM KIẾM CHUỖI NHỊ PHÂN PDF TRONG DỮ LIỆU THÔ
    - b.find(PDF_HEAD): Dò vị trí byte đầu tiên xuất hiện '%PDF-'.
    - b.rfind(PDF_EOF): Dò vị trí byte cuối cùng xuất hiện '%%EOF'.
    - Cắt chính xác khúc dữ liệu nằm giữa 2 mốc này để có được file PDF hợp lệ.
    """
    if not b: return None
    s = b.find(PDF_HEAD)
    if s < 0: return None
    e = b.rfind(PDF_EOF)
    return b[s:e + 5] if e > s else b[s:]

def cfb_streams(data: bytes):
    """
    HÀM GIẢI PHẪU CẤU TRÚC OLE COMPOUND FILE THEO TỪNG SECTOR
    Mục đích: Khi file PDF lớn được nhúng vào Excel, Windows có thể phân mảnh nó
    thành nhiều sector (khối 512 byte) nằm rời rạc nhau. Hàm này lần theo bảng FAT (File Allocation Table)
    để xâu chuỗi các sector lại đúng thứ tự, chống 100% tình trạng file PDF bị đứt gãy.
    """
    # Dòng 56: Kiểm tra 8 byte đầu có phải chữ ký Compound File Binary hay không
    if data[:8] != CFB_SIG: return []
    try:
        # Dòng 59-62: Đọc kích thước sector và vị trí các bảng chỉ mục từ Header OLE
        ssz = 1 << struct.unpack_from("<H", data, 30)[0]
        mssz = 1 << struct.unpack_from("<H", data, 32)[0]
        (n_fat, dir_start, _, mini_cutoff, minifat_start, n_minifat, difat_start, n_difat) = struct.unpack_from("<8I", data, 44)
        sec = lambda i: data[(i + 1) * ssz:(i + 2) * ssz]
        per = ssz // 4

        # Dòng 66-74: Xây dựng bảng FAT đầy đủ từ DIFAT
        difat = list(struct.unpack_from("<109I", data, 76))
        d, k = difat_start, 0
        while d < ENDS and k < n_difat:
            ent = struct.unpack(f"<{per}I", sec(d))
            difat += ent[:-1]
            d, k = ent[-1], k + 1
        fat = []
        for f in difat[:max(n_fat, 0) or len(difat)]:
            if f < ENDS: fat += struct.unpack(f"<{per}I", sec(f))

        # Dòng 77-83: Hàm đệ quy duyệt chuỗi liên kết các sector
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

        # Dòng 97-111: Đọc nội dung từng Stream con trong file OLE
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

# ==============================================================================
# KHU VỰC 2: RẠCH BỤNG EXCEL & PHÂN LOẠI PDF THEO SHEET
# ==============================================================================
def extract_pdfs_from_excel(excel_path, out_drawings_dir, out_gatepass_dir):
    """
    HÀM TIỀN XỬ LÝ (PRE-PROCESSOR):
    Mục đích: Mở file .xlsx dưới dạng file nén Zip, phân tích XML để xác định Sheet nào
    chứa bản vẽ CAD thì lưu PDF vào out_drawings_dir, Sheet nào chứa BBGN thì lưu vào out_gatepass_dir.
    """
    if not os.path.exists(excel_path): return 0
    os.makedirs(out_drawings_dir, exist_ok=True)
    os.makedirs(out_gatepass_dir, exist_ok=True)

    # Khai báo không gian tên XML chuẩn của OpenXML Microsoft
    ns = {
        'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'
    }

    extracted_count = 0
    try:
        with zipfile.ZipFile(excel_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            if 'xl/workbook.xml' not in file_list: return 0

            # 1. Đọc xl/workbook.xml để ánh xạ: Mã quan hệ (rId) -> Tên Sheet (VD: rId1 -> "Bản vẽ")
            wb_root = ET.fromstring(zip_ref.read('xl/workbook.xml'))
            sheet_map = {}
            for sheet in wb_root.findall('.//main:sheet', ns):
                name = sheet.attrib.get('name', '').lower()
                r_id = sheet.attrib.get(f"{{{ns['r']}}}id")
                if r_id: sheet_map[r_id] = name

            # 2. Đọc xl/_rels/workbook.xml.rels để ánh xạ: Mã quan hệ (rId) -> File XML nội bộ (VD: sheet1.xml)
            rels_root = ET.fromstring(zip_ref.read('xl/_rels/workbook.xml.rels'))
            sheet_file_map = {}
            for rel in rels_root.findall('.//rels:Relationship', ns):
                r_id = rel.attrib.get('Id')
                target = rel.attrib.get('Target')
                if r_id in sheet_map and target:
                    sheet_filename = target.split('/')[-1]
                    sheet_file_map[sheet_filename] = sheet_map[r_id]

            # 3. Quét từng file quan hệ của sheet (xl/worksheets/_rels/sheetX.xml.rels)
            for rel_file in file_list:
                if rel_file.startswith('xl/worksheets/_rels/') and rel_file.endswith('.rels'):
                    sheet_filename = rel_file.split('/')[-1].replace('.rels', '')
                    sheet_name = sheet_file_map.get(sheet_filename, "")
                    sheet_lower = sheet_name.lower()

                    # Phân loại thư mục lưu dựa theo từ khóa trong config
                    target_dir = None
                    prefix = ""
                    if any(kw in sheet_lower for kw in config.SHEET_KEYWORDS_DRAWING):
                        target_dir = out_drawings_dir; prefix = "Ban_Ve"
                    elif any(kw in sheet_lower for kw in config.SHEET_KEYWORDS_GATEPASS):
                        target_dir = out_gatepass_dir; prefix = "BBGN"

                    if not target_dir: continue

                    # Đọc các file oleObject.bin nhúng trong sheet này
                    s_rels_root = ET.fromstring(zip_ref.read(rel_file))
                    idx = 1
                    for rel in s_rels_root.findall('.//rels:Relationship', ns):
                        target_path = rel.attrib.get('Target', '')
                        if 'embeddings/' in target_path:
                            embed_filename = target_path.split('/')[-1]
                            zip_embed_path = f"xl/embeddings/{embed_filename}"

                            if zip_embed_path in file_list:
                                raw_bytes = zip_ref.read(zip_embed_path)
                                pdf_data = None

                                # Ưu tiên 1: Giải mã OLE Sector Streams (Chuẩn nhất từ code sếp)
                                for _, b in cfb_streams(raw_bytes):
                                    p = find_pdf_bytes(b)
                                    if p and (pdf_data is None or len(p) > len(pdf_data)):
                                        pdf_data = p

                                # Ưu tiên 2: Quét trực tiếp nếu OLE không phân mảnh
                                if pdf_data is None:
                                    pdf_data = find_pdf_bytes(raw_bytes)

                                if pdf_data:
                                    clean_sheet_name = ut.clean_vietnamese_filename(sheet_name)
                                    out_pdf_name = f"{prefix}_{clean_sheet_name}_File_{idx}.pdf"
                                    out_pdf_path = os.path.join(target_dir, out_pdf_name)
                                    with open(out_pdf_path, 'wb') as f_out:
                                        f_out.write(pdf_data)
                                    extracted_count += 1
                                    idx += 1
    except Exception as e:
        print(f"⚠️ Cảnh báo lỗi trích xuất: {e}")

    return extracted_count

# ==============================================================================
# KHU VỰC 3: ĐIỀU PHỐI TOÀN BỘ QUY TRÌNH END-TO-END (RUN_MEP_PIPELINE)
# ==============================================================================
def run_mep_pipeline(
    pdf_drawing_dir,     # Thư mục chứa PDF bản vẽ
    pdf_gatepass_dir,    # Thư mục chứa PDF gatepass
    vendor_excel_path,   # Đường dẫn file Excel vendor
    master_data_path,    # Đường dẫn file BOQ master (dùng chung file Excel)
    output_dir,          # Thư mục lưu báo cáo cuối cùng
    csv_drawing_dir,     # Thư mục lưu CSV bản vẽ
    csv_gatepass_dir,    # Thư mục lưu CSV gatepass
    skip_existing=False, # Cờ chạy lại hay dùng CSV cũ
    status_callback=None # Hàm gọi ngược cập nhật % tiến trình
):
    start_time = time.time()

    def update_status(msg, progress):
        print(f"\n{msg}")
        if status_callback: status_callback(msg, progress)

    try:
        # BƯỚC 0: Trích xuất PDF từ bụng file Excel
        update_status("BƯỚC 0: Đang quét file Excel trích xuất PDF đính kèm...", 0.05)
        extract_pdfs_from_excel(vendor_excel_path, pdf_drawing_dir, pdf_gatepass_dir)

        # BƯỚC 1: Xử lý PDF và gọi AI Vision bóc tách dữ liệu
        update_status("BƯỚC 1/4: Đang đọc hồ sơ PDF bằng AI Vision...", 0.15)
        pdf_drawings = glob.glob(os.path.join(pdf_drawing_dir, "*.pdf")) if os.path.exists(pdf_drawing_dir) else []
        pdf_gatepasses = glob.glob(os.path.join(pdf_gatepass_dir, "*.pdf")) if os.path.exists(pdf_gatepass_dir) else []

        if not pdf_drawings and not pdf_gatepasses:
            raise FileNotFoundError("❌ Không tìm thấy file PDF Bản vẽ hay Gate Pass nào để xử lý!")

        first_pdf_name = os.path.splitext(os.path.basename((pdf_drawings or pdf_gatepasses)[0]))[0]

        # 1A. Bóc tách bản vẽ CAD
        for i, pdf_path in enumerate(pdf_drawings):
            update_status(f"Đang bóc tách Bản vẽ ({i+1}/{len(pdf_drawings)}): {os.path.basename(pdf_path)}", 0.15 + (i+1)*0.05)
            pdf_extractor.process_single_pdf(pdf_path, force_mode="drawing", out_drawing_dir=csv_drawing_dir)

        # 1B. Bóc tách Gate Pass
        for i, pdf_path in enumerate(pdf_gatepasses):
            update_status(f"Đang bóc tách Gate Pass ({i+1}/{len(pdf_gatepasses)}): {os.path.basename(pdf_path)}", 0.30 + (i+1)*0.05)
            pdf_extractor.process_single_pdf(pdf_path, force_mode="gate_pass", out_gatepass_dir=csv_gatepass_dir)

        # BƯỚC 2: Gom nhóm dữ liệu CSV bằng Pandas (Pivot & Groupby)
        update_status("BƯỚC 2/4: Đang gom nhóm (Pivot & Groupby) dữ liệu AI...", 0.50)
        df_pivot, drawing_list = excel_reconciler.aggregate_ai_data(csv_drawing_dir)
        dict_gatepass = excel_reconciler.aggregate_gate_pass_data(csv_gatepass_dir)

        # BƯỚC 3: Quét Radar Vendor & Ánh xạ Master Data
        update_status("BƯỚC 3/4: Đang quét Radar file Vendor và Ánh xạ Master Data...", 0.65)
        df_vendor = excel_reconciler.load_vendor_data_dynamic(
            vendor_excel_path, config.VENDOR_SHEET_NAME, drawing_list, config.VENDOR_COL_CODE
        )
        df_formatted = excel_reconciler.format_master_report(df_pivot, drawing_list, master_data_path)

        # BƯỚC 4: Đối soát chéo 2 Vòng & Xuất Excel Báo cáo 2 Sheet tô màu
        update_status("BƯỚC 4/4: Đang đối soát 2 Vòng và tô màu báo cáo...", 0.85)
        base_output_path = os.path.join(output_dir, f"{first_pdf_name}_Report.xlsx")
        final_excel_path = excel_reconciler.get_unique_path(base_output_path)

        excel_reconciler.reconcile_and_highlight(
            df_ai=df_formatted,
            df_vendor=df_vendor,
            output_excel_path=final_excel_path,
            drawing_columns=drawing_list,
            dict_gatepass=dict_gatepass
        )

        total_time = time.time() - start_time
        update_status(f"🎉 Hoàn tất trong {total_time:.2f}s! Báo cáo: {os.path.basename(final_excel_path)}", 1.0)
        return final_excel_path

    except Exception as e:
        print("\n" + traceback.format_exc())
        if status_callback: status_callback(f"❌ LỖI: {str(e)}", 0.0)
        raise e

