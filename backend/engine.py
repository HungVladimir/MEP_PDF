# ==========================================
# ĐIỀU PHỐI TỔNG TÀI (MEP PIPELINE ENGINE)
# ==========================================
import os
import glob
import time
import traceback
import zipfile
import re
import struct
import xml.etree.ElementTree as ET

import config
import pdf_extractor
import excel_reconciler
import utils as ut

# --------------------------------------------------------------------------
# KHỐI GIẢI MÃ NHỊ PHÂN OLE COMPOUND FILE (NÂNG CẤP TỪ THIẾT KẾ CỦA SẾP)
# --------------------------------------------------------------------------
PDF_HEAD, PDF_EOF = b"%PDF-", b"%%EOF"
CFB_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
ENDS = 0xFFFFFFFA


def find_pdf_bytes(b: bytes):
    """Tìm chuỗi nhị phân PDF chuẩn trong stream dữ liệu."""
    if not b:
        return None
    s = b.find(PDF_HEAD)
    if s < 0:
        return None
    e = b.rfind(PDF_EOF)
    return b[s:e + 5] if e > s else b[s:]


def cfb_streams(data: bytes):
    """
    Giải mã cấu trúc OLE Compound Binary theo từng sector.
    Giúp ghép các sector PDF bị Excel phân mảnh rời rạc lại thành file toàn vẹn.
    """
    if data[:8] != CFB_SIG:
        return []
    try:
        ssz = 1 << struct.unpack_from("<H", data, 30)[0]
        mssz = 1 << struct.unpack_from("<H", data, 32)[0]
        (n_fat, dir_start, _, mini_cutoff, minifat_start, n_minifat,
         difat_start, n_difat) = struct.unpack_from("<8I", data, 44)

        def sec(i): return data[(i + 1) * ssz:(i + 2) * ssz]
        per = ssz // 4

        difat = list(struct.unpack_from("<109I", data, 76))
        d, k = difat_start, 0
        while d < ENDS and k < n_difat:
            ent = struct.unpack(f"<{per}I", sec(d))
            difat += ent[:-1]
            d, k = ent[-1], k + 1

        fat = []
        for f in difat[:max(n_fat, 0) or len(difat)]:
            if f < ENDS:
                fat += struct.unpack(f"<{per}I", sec(f))

        def chain(start, table):
            seen = set()
            while start < ENDS and start < len(table) and start not in seen:
                seen.add(start)
                yield start
                start = table[start]

        def read(start, size=None): return b"".join(sec(i)
                                                    for i in chain(start, fat))[:size]
        dirs = read(dir_start)
        entries = []
        for off in range(0, len(dirs) - 127, 128):
            e = dirs[off:off + 128]
            nlen = struct.unpack_from("<H", e, 64)[0]
            name = e[:max(nlen - 2, 0)].decode("utf-16-le", "ignore")
            typ = e[66]
            start, size = struct.unpack_from("<II", e, 116)
            entries.append((name, typ, start, size))
        if not entries:
            return []

        root = entries[0]
        mini_stream = read(root[2], root[3]) if root[2] < ENDS else b""
        minifat = []
        if n_minifat and minifat_start < ENDS:
            raw = read(minifat_start)
            minifat = list(struct.unpack(
                f"<{len(raw) // 4}I", raw[:len(raw) // 4 * 4]))

        out = []
        for name, typ, start, size in entries[1:]:
            if typ != 2 or size == 0:
                continue
            if size < mini_cutoff:
                b = b"".join(mini_stream[i * mssz:(i + 1) * mssz]
                             for i in chain(start, minifat))[:size]
            else:
                b = read(start, size)
            out.append((name, b))
        return out
    except Exception:
        return []

# --------------------------------------------------------------------------
# BƯỚC 0: TRÍCH XUẤT FILE PDF NHÚNG TỪ FILE EXCEL
# --------------------------------------------------------------------------


def extract_pdfs_from_excel(excel_path, out_drawings_dir, out_gatepass_dir):
    """
    Tiền xử lý (Pre-processor): Giải nén file Excel, đọc cấu trúc XML,
    tìm và lôi các file PDF đính kèm (OLE Objects) trong các Sheet quy định.
    """
    if not os.path.exists(excel_path):
        return 0

    os.makedirs(out_drawings_dir, exist_ok=True)
    os.makedirs(out_gatepass_dir, exist_ok=True)

    ns = {
        'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'
    }

    extracted_count = 0
    try:
        with zipfile.ZipFile(excel_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            if 'xl/workbook.xml' not in file_list:
                return 0

            # 1. Đọc workbook.xml để map: rId -> Tên Sheet
            wb_root = ET.fromstring(zip_ref.read('xl/workbook.xml'))
            sheet_map = {}
            for sheet in wb_root.findall('.//main:sheet', ns):
                name = sheet.attrib.get('name', '').lower()
                r_id = sheet.attrib.get(f"{{{ns['r']}}}id")
                if r_id:
                    sheet_map[r_id] = name

            # 2. Đọc workbook.xml.rels để map: sheetX.xml -> Tên Sheet
            rels_root = ET.fromstring(
                zip_ref.read('xl/_rels/workbook.xml.rels'))
            sheet_file_map = {}
            for rel in rels_root.findall('.//rels:Relationship', ns):
                r_id = rel.attrib.get('Id')
                target = rel.attrib.get('Target')
                if r_id in sheet_map and target:
                    sheet_filename = target.split('/')[-1]
                    sheet_file_map[sheet_filename] = sheet_map[r_id]

            # 3. Quét từng file .rels của các Sheet tìm embeddings
            for rel_file in file_list:
                if rel_file.startswith('xl/worksheets/_rels/') and rel_file.endswith('.rels'):
                    sheet_filename = rel_file.split(
                        '/')[-1].replace('.rels', '')
                    sheet_name = sheet_file_map.get(sheet_filename, "")
                    sheet_lower = sheet_name.lower()

                    target_dir = None
                    prefix = ""

                    if any(kw in sheet_lower for kw in config.SHEET_KEYWORDS_DRAWING):
                        target_dir = out_drawings_dir
                        prefix = "Ban_Ve"
                    elif any(kw in sheet_lower for kw in config.SHEET_KEYWORDS_GATEPASS):
                        target_dir = out_gatepass_dir
                        prefix = "BBGN"

                    if not target_dir:
                        continue

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

                                # Ưu tiên 1: Giải mã OLE Sector Streams (Chuẩn nhất)
                                for _, b in cfb_streams(raw_bytes):
                                    p = find_pdf_bytes(b)
                                    if p and (pdf_data is None or len(p) > len(pdf_data)):
                                        pdf_data = p

                                # Ưu tiên 2: Tìm header/footer trực tiếp
                                if pdf_data is None:
                                    pdf_data = find_pdf_bytes(raw_bytes)

                                if pdf_data:
                                    clean_sheet_name = ut.clean_vietnamese_filename(
                                        sheet_name)
                                    out_pdf_name = f"{prefix}_{clean_sheet_name}_File_{idx}.pdf"
                                    out_pdf_path = os.path.join(
                                        target_dir, out_pdf_name)

                                    with open(out_pdf_path, 'wb') as f_out:
                                        f_out.write(pdf_data)

                                    print(
                                        f"   [+] Móc thành công PDF từ Sheet '{sheet_name}' -> {out_pdf_name}")
                                    extracted_count += 1
                                    idx += 1

            if extracted_count > 0:
                print(
                    f"🎉 Đã trích xuất thành công {extracted_count} file PDF từ file Excel.")
            else:
                print("ℹ️ Không tìm thấy file PDF nhúng trong các Sheet Bản vẽ / BBGN.")

    except Exception as e:
        print(f"⚠️ Cảnh báo: Lỗi khi trích xuất PDF từ Excel: {e}")

    return extracted_count

# --------------------------------------------------------------------------
# HÀM ĐIỀU PHỐI CHÍNH TOÀN BỘ QUY TRÌNH (RUN_MEP_PIPELINE)
# --------------------------------------------------------------------------


def run_mep_pipeline(
    pdf_drawing_dir,  # Thư mục chứa các file PDF Bản vẽ CAD
    pdf_gatepass_dir,       # Thư mục chứa các file PDF Biên bản vật tư mang vào
    vendor_excel_path,      # Đường dẫn tới file Excel của nhà thầu (Vendor)
    master_data_path,       # Đường dẫn tới file MapData.xlsx
    output_dir,             # Thư mục sẽ lưu báo cáo Excel cuối cùng
    csv_drawing_dir,        # Thư mục lưu các file CSV của Bản vẽ
    csv_gatepass_dir,       # Thư mục lưu các file CSV của Gate Pass
    skip_existing=False,    # Cờ: Có dùng lại CSV cũ để chạy cho nhanh không?
    # Hàm gọi ngược (Callback) đẩy % lên thanh Loading của Web
    status_callback=None,
    evidence_dir=None       # Thư mục lưu ảnh trích xuất / bằng chứng đối soát
):
    """
    Quy trình End-to-End:
    1. Trích xuất PDF từ Excel
    2. Cắt bảng bằng OpenCV và gọi AI Vision bóc dữ liệu
    3. Gom nhóm dữ liệu CSV (Pivot & Groupby)
    4. Quét Radar Vendor & Ánh xạ Master Data
    5. Đối soát chéo 2 Vòng & Xuất Excel Báo cáo 2 Sheet tô màu
    """
    start_time = time.time()

    def update_status(msg, progress):
        print(f"\n{msg}")
        if status_callback:
            status_callback(msg, progress)

    try:
        # BƯỚC 0: TRÍCH XUẤT PDF
        update_status(
            "BƯỚC 0: Đang quét file Excel trích xuất PDF đính kèm...", 0.05)
        extract_pdfs_from_excel(
            vendor_excel_path, pdf_drawing_dir, pdf_gatepass_dir)

        # BƯỚC 1: XỬ LÝ PDF VÀ GỌI AI VISION
        update_status("BƯỚC 1/4: Đang đọc hồ sơ PDF bằng AI Vision...", 0.15)
        pdf_drawings = glob.glob(os.path.join(
            pdf_drawing_dir, "*.pdf")) if os.path.exists(pdf_drawing_dir) else []
        pdf_gatepasses = glob.glob(os.path.join(
            pdf_gatepass_dir, "*.pdf")) if os.path.exists(pdf_gatepass_dir) else []

        if not pdf_drawings and not pdf_gatepasses:
            raise FileNotFoundError(
                "❌ Không tìm thấy file PDF Bản vẽ hay Gate Pass nào để xử lý!")

        first_pdf_name = "MEP_Report"
        if pdf_drawings:
            first_pdf_name = os.path.splitext(
                os.path.basename(pdf_drawings[0]))[0]
        elif pdf_gatepasses:
            first_pdf_name = os.path.splitext(
                os.path.basename(pdf_gatepasses[0]))[0]

        # 1A. Xử lý Bản vẽ CAD
        existing_csv_drawings = glob.glob(
            os.path.join(csv_drawing_dir, "*.csv"))
        if skip_existing and len(existing_csv_drawings) > 0:
            update_status(
                f"-> ⚡ Đã có {len(existing_csv_drawings)} CSV Bản vẽ. Bỏ qua gọi AI...", 0.25)
        else:
            for i, pdf_path in enumerate(pdf_drawings):
                progress = 0.15 + (i / max(1, len(pdf_drawings))) * 0.15
                update_status(
                    f"Đang bóc tách Bản vẽ ({i+1}/{len(pdf_drawings)}): {os.path.basename(pdf_path)}", progress)
                pdf_extractor.process_single_pdf(
                    pdf_path, force_mode="drawing", out_drawing_dir=csv_drawing_dir, out_img_dir=evidence_dir)

        # 1B. Xử lý Gate Pass (Biên bản vật tư mang vào)
        existing_csv_gp = glob.glob(os.path.join(csv_gatepass_dir, "*.csv"))
        if skip_existing and len(existing_csv_gp) > 0:
            update_status(
                f"-> ⚡ Đã có {len(existing_csv_gp)} CSV Gate Pass. Bỏ qua gọi AI...", 0.40)
        else:
            for i, pdf_path in enumerate(pdf_gatepasses):
                progress = 0.30 + (i / max(1, len(pdf_gatepasses))) * 0.15
                update_status(
                    f"Đang bóc tách Gate Pass ({i+1}/{len(pdf_gatepasses)}): {os.path.basename(pdf_path)}", progress)
                pdf_extractor.process_single_pdf(
                    pdf_path, force_mode="gate_pass", out_gatepass_dir=csv_gatepass_dir, out_img_dir=evidence_dir)

        # BƯỚC 2: GOM NHÓM DỮ LIỆU CSV
        update_status(
            "BƯỚC 2/4: Đang gom nhóm (Pivot & Groupby) dữ liệu AI...", 0.50)
        df_pivot, drawing_list = excel_reconciler.aggregate_ai_data(
            csv_drawing_dir)
        dict_gatepass = excel_reconciler.aggregate_gate_pass_data(
            csv_gatepass_dir)

        # BƯỚC 3: QUÉT RADAR FILE VENDOR & MASTER DATA
        update_status(
            "BƯỚC 3/4: Đang quét Radar file Vendor và Ánh xạ Master Data...", 0.65)
        df_vendor = excel_reconciler.load_vendor_data_dynamic(
            vendor_excel_path,
            config.VENDOR_SHEET_NAME,
            drawing_list,
            config.VENDOR_COL_CODE
        )
        df_formatted = excel_reconciler.format_master_report(
            df_pivot,
            drawing_list,
            master_data_path
        )

        # BƯỚC 4: ĐỐI SOÁT CHÉO 2 VÒNG & XUẤT EXCEL 2 SHEET
        update_status(
            "BƯỚC 4/4: Đang đối soát 2 Vòng và tô màu báo cáo...", 0.85)

        # Đặt tên file báo cáo kết quả theo đúng tên file Excel Vendor upload lên
        vendor_stem = os.path.splitext(os.path.basename(vendor_excel_path))[0] if vendor_excel_path else first_pdf_name
        base_output_path = os.path.join(
            output_dir, f"{vendor_stem}_Report.xlsx")
        final_excel_path = excel_reconciler.get_unique_path(base_output_path)

        excel_reconciler.reconcile_and_highlight(
            df_ai=df_formatted,
            df_vendor=df_vendor,
            output_excel_path=final_excel_path,
            drawing_columns=drawing_list,
            dict_gatepass=dict_gatepass
        )

        total_time = time.time() - start_time
        final_msg = f"🎉 Hoàn tất quy trình trong {total_time:.2f}s! File: {os.path.basename(final_excel_path)}"
        update_status(final_msg, 1.0)

        return final_excel_path

    except Exception as e:
        error_msg = f"❌ LỖI PIPELINE: {str(e)}"
        print("\n" + traceback.format_exc())
        if status_callback:
            status_callback(error_msg, 0.0)
        raise e


if __name__ == "__main__":
    print("🚀 Đang chạy Engine kiểm tra ở chế độ CLI Standalone...")
    # test_vendor = os.path.join(config.BASE_DIR, "data", "test_vendor.xlsx")
    test_vendor = os.path.join(
        config.DIR_VENDOR_EXCEL, config.VENDOR_FILE_NAME)
    if os.path.exists(test_vendor):
        run_mep_pipeline(
            pdf_drawing_dir=config.DIR_PDF_DRAWINGS,
            pdf_gatepass_dir=config.DIR_PDF_GATEPASS,
            vendor_excel_path=test_vendor,
            master_data_path=test_vendor,
            output_dir=config.DIR_FINAL_REPORT,
            csv_drawing_dir=config.DIR_CSV_EXTRACTED,
            csv_gatepass_dir=config.DIR_GATEPASS_CSV
        )
    else:
        print(f"ℹ️ Đặt file vendor tại {test_vendor} để chạy thử nghiệm.")
