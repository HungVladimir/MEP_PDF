import os
import re
import glob
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font
from openpyxl.utils import get_column_letter
import config


def get_unique_path(base_path):
    """Tự động đổi tên file báo cáo nếu file cũ đang mở để chống lỗi PermissionError."""
    if not os.path.exists(base_path):
        return base_path

    folder, filename = os.path.split(base_path)
    name, ext = os.path.splitext(filename)
    counter = 1

    while True:
        new_path = os.path.join(folder, f"{name}_{counter}{ext}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1

# ==========================================
# 1A. HÀM GOM NHÓM DỮ LIỆU BẢN VẼ TỪ NHIỀU FILE CSV (PIVOT)
# ==========================================


def aggregate_ai_data(csv_dir):
    """Đọc hàng loạt file CSV Bản vẽ từ AI bóc ra, gom chung lại thành 1 bảng ngang (Pivot)."""
    if not os.path.exists(csv_dir):
        raise FileNotFoundError(f"❌ Thư mục {csv_dir} không tồn tại!")

    print("🔄 Đang gom nhóm dữ liệu Bản vẽ (Tách dòng chi tiết theo Code + Phụ trội + Ghi chú)...")

    # Lọc bỏ các file GATEPASS_ nếu vô tình lưu chung thư mục
    raw_files = [
        f for f in glob.glob(os.path.join(csv_dir, "*.csv"))
        if not os.path.basename(f).upper().startswith("GATEPASS_")
    ]

    all_files = sorted(
        raw_files,
        key=lambda x: [int(s) if s.isdigit() else s.lower()
                       for s in re.split(r'(\d+)', os.path.basename(x))]
    )

    if not all_files:
        raise FileNotFoundError(
            f"❌ Không tìm thấy file CSV Bản vẽ nào trong {csv_dir}")

    df_list = []
    drawing_names = []

    for file in all_files:
        base_name = os.path.splitext(os.path.basename(file))[0]
        new_drawing_name = f"{base_name}"
        drawing_names.append(new_drawing_name)

        df = pd.read_csv(file, dtype={'SDAC_CODE': str})
        df['Ban_Ve'] = new_drawing_name
        df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0)

        for col in ['PHU_TROI', 'REMARK']:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str).str.strip()
            df.loc[df[col].str.lower().isin(['nan', 'none']), col] = ""

        df_list.append(df)

    df_combined = pd.concat(df_list, ignore_index=True)

    df_final_pivot = df_combined.pivot_table(
        index=['SDAC_CODE', 'PHU_TROI', 'REMARK'],
        columns='Ban_Ve',
        values='QTY',
        aggfunc='sum'
    ).fillna(0).reset_index()

    for d_name in drawing_names:
        if d_name not in df_final_pivot.columns:
            df_final_pivot[d_name] = 0.0

    ordered_cols = ['SDAC_CODE', 'PHU_TROI', 'REMARK'] + drawing_names
    return df_final_pivot[ordered_cols], drawing_names

# ==========================================
# 1B. HÀM GOM NHÓM DỮ LIỆU GATE PASS (VẬT TƯ MANG VÀO)
# ==========================================


def aggregate_gate_pass_data(gatepass_csv_dir):
    """
    Đọc tất cả các file CSV bóc từ Biên bản vật tư mang vào (Gate Pass).
    Cộng dồn (SUM) cột Số lượng theo từng Item code.
    Trả về Dictionary: { 'M03-00726974': 15.0, ... }
    """
    if not gatepass_csv_dir or not os.path.exists(gatepass_csv_dir):
        print("ℹ️ Không tìm thấy thư mục CSV Gate Pass. Bỏ qua dữ liệu Gate Pass.")
        return {}

    # Tìm tất cả file CSV trong thư mục Gate Pass (hoặc file có tiền tố GATEPASS_)
    all_files = glob.glob(os.path.join(gatepass_csv_dir, "*.csv"))
    if gatepass_csv_dir == config.DIR_CSV_EXTRACTED:
        all_files = [f for f in all_files if os.path.basename(
            f).upper().startswith("GATEPASS_")]

    if not all_files:
        print("ℹ️ Chưa có file CSV Gate Pass nào để đối soát Vòng 2.")
        return {}

    print(
        f"📦 Đang gom nhóm dữ liệu từ {len(all_files)} trang Gate Pass CSV...")
    df_list = []
    for f in all_files:
        try:
            df = pd.read_csv(f, dtype={'SDAC_CODE': str})
            if 'SDAC_CODE' in df.columns and 'QTY' in df.columns:
                df['SDAC_CODE'] = df['SDAC_CODE'].astype(
                    str).str.strip().str.upper()
                df['QTY'] = pd.to_numeric(
                    df['QTY'], errors='coerce').fillna(0.0)
                df_list.append(df[['SDAC_CODE', 'QTY']])
        except Exception as e:
            print(f"   ⚠️ Lỗi đọc file Gate Pass {f}: {e}")

    if not df_list:
        return {}

    df_gp_all = pd.concat(df_list, ignore_index=True)
    gp_grouped = df_gp_all.groupby('SDAC_CODE')['QTY'].sum().round(2)
    return gp_grouped.to_dict()


def get_actual_sheet_name(excel_path, target_sheet_name):
    """Hàm so khớp mờ (Fuzzy Match) tên Sheet."""
    try:
        xls = pd.ExcelFile(excel_path, engine="calamine")
        all_sheets = xls.sheet_names
        target_clean = str(target_sheet_name).lower().replace(" ", "")

        for sheet in all_sheets:
            sheet_clean = str(sheet).lower().replace(" ", "")
            if target_clean == sheet_clean:
                if sheet != target_sheet_name:
                    print(
                        f"💡 Tự động nắn tên Sheet từ '{target_sheet_name}' thành '{sheet}'")
                return sheet
        return target_sheet_name
    except Exception:
        return target_sheet_name

# ==========================================
# 2. HÀM QUÉT RADAR ĐỘNG (BẢNG KHỐI LƯỢNG VENDOR)
# ==========================================


def load_vendor_data_dynamic(excel_path, sheet_name, drawing_names, code_col_name):
    """Rải Radar tìm tọa độ các cột trên file Vendor."""
    actual_sheet = get_actual_sheet_name(excel_path, sheet_name)
    print(
        f"-> Đang quét Radar tìm cột trên file Vendor (Sheet: {actual_sheet})...")

    df_raw = pd.read_excel(excel_path, sheet_name=actual_sheet,
                           header=None, nrows=20, engine="calamine")

    code_idx = None
    code_row = None
    extra_idx = None
    remark_idx = None
    drawing_indices = {}
    max_header_row = 0

    search_code = str(config.VENDOR_COL_CODE).lower().replace(' ', '')
    search_extra = str(config.VENDOR_COL_EXTRA).lower().replace(' ', '')
    search_remark = str(config.VENDOR_COL_REMARK).lower().replace(' ', '')

    remaining_drawings = set(drawing_names)

    for row_idx in range(len(df_raw)):
        if (code_idx is not None and extra_idx is not None and remark_idx is not None and len(remaining_drawings) == 0):
            print("+ Đã tìm đủ 100% mục tiêu trên Vendor. Thoát sớm!")
            break

        if code_idx is not None and row_idx > code_row + 1:
            break

        for col_idx in range(len(df_raw.columns)):
            if pd.isna(df_raw.iloc[row_idx, col_idx]):
                continue

            cell_val_clean = str(df_raw.iloc[row_idx, col_idx]).lower().replace(
                '\n', '').replace(' ', '')
            # Xử lý trường hợp Pandas đọc số 1 thành "1.0" trên dòng header
            if cell_val_clean.endswith('.0') and cell_val_clean[:-2].isdigit():
                cell_val_clean = cell_val_clean[:-2]

            # TÌM CỘT CODE
            if code_idx is None and search_code in cell_val_clean:
                code_idx = col_idx
                code_row = row_idx
                max_header_row = max(max_header_row, row_idx)
                print(f"+ Đã chốt cột Code tại vị trí: {col_idx}")
                continue

            # TÌM CỘT PHỤ TRỘI
            if extra_idx is None and (search_extra in cell_val_clean):
                extra_idx = col_idx
                max_header_row = max(max_header_row, row_idx)
                print(f"+ Đã chốt cột Phụ trội (Vendor) tại vị trí: {col_idx}")
                continue

            # TÌM CỘT REMARK
            if remark_idx is None and (search_remark in cell_val_clean):
                remark_idx = col_idx
                max_header_row = max(max_header_row, row_idx)
                print(f"+ Đã chốt cột Remark (Vendor) tại vị trí: {col_idx}")
                continue

            # TÌM CÁC CỘT BẢN VẼ (Hỗ trợ cả 'Bảnvẽ1', 'BV1' lẫn số '1' có khóa neo dòng)
            found_drawing = None
            for d_name in remaining_drawings:
                clean_name = str(d_name).lower().replace(' ', '')
                # Rút lõi số nếu tên file CSV có chữ bản vẽ (VD: "bảnvẽ1" -> "1")
                core_num = re.sub(r'^(?:bảnvẽ\-?|bv\-?)', '', clean_name)

                # Điều kiện 1: Khớp từ khóa có chữ "bảnvẽ1", "bảnvẽ-1", "bv1"
                is_keyword = (
                    f"bảnvẽ-{core_num}" in cell_val_clean
                    or f"bảnvẽ{core_num}" in cell_val_clean
                    or f"bv-{core_num}" in cell_val_clean
                    or f"bv{core_num}" in cell_val_clean
                )
                # Điều kiện 2: Khớp chính xác chuỗi chữ (không phải số thuần túy)
                is_exact_text = (
                    clean_name == cell_val_clean) and not clean_name.isdigit()
                # Điều kiện 3 (Phòng hộ): Nếu Vendor quên ghi chữ "Bảnvẽ" mà chỉ gõ số "1", "2"
                # Chỉ nhận nếu nằm cùng dòng (hoặc lệch 1 dòng) với ô chứa chữ "Code"
                is_anchored_number = (
                    core_num.isdigit()
                    and cell_val_clean == core_num
                    and code_row is not None
                    and abs(row_idx - code_row) <= 1
                )

                if is_keyword or is_exact_text or is_anchored_number:
                    drawing_indices[d_name] = col_idx
                    max_header_row = max(max_header_row, row_idx)
                    print(
                        f"+ Tóm được cột bản vẽ '{d_name}' tại vị trí cột số {col_idx}")
                    found_drawing = d_name
                    break

            if found_drawing:
                remaining_drawings.remove(found_drawing)

    if code_idx is None:
        raise ValueError(
            f"❌ Không tìm thấy cột '{code_col_name}' trong 20 dòng đầu của file Vendor!")

    base_pairs = [(code_idx, config.VENDOR_COL_CODE)]
    if extra_idx is not None:
        base_pairs.append((extra_idx, 'VENDOR_EXTRA'))
    else:
        print(
            "ℹ️ Bản Vendor hiện tại CHƯA có cột Phụ trội -> Tự động gộp chung khi đối soát.")

    if remark_idx is not None:
        base_pairs.append((remark_idx, 'VENDOR_REMARK'))
    else:
        print("ℹ️ Bản Vendor hiện tại CHƯA có cột Remark -> Tự động bỏ qua khi đối soát.")

    col_pairs = sorted(
        base_pairs + [(idx, name) for name, idx in drawing_indices.items()],
        key=lambda x: x[0]
    )
    usecols = [pair[0] for pair in col_pairs]
    col_names = [pair[1] for pair in col_pairs]

    df_vendor = pd.read_excel(
        excel_path,
        sheet_name=actual_sheet,
        usecols=usecols,
        skiprows=max_header_row + 1,
        names=col_names,
        dtype={config.VENDOR_COL_CODE: str},
        engine="calamine"
    )

    return df_vendor.dropna(subset=[config.VENDOR_COL_CODE])

# ==========================================
# 3. ĐỊNH DẠNG FORM & ÁNH XẠ SINGLE MAPPING (MAPDATA)
# ==========================================


def format_master_report(df_pivot, drawing_columns, master_data_path):
    """Đắp thêm các cột Thông tin (Mô tả, Đơn giá...) từ file MapData.xlsx."""
    print("📝 Đang thiết lập Form Báo cáo và Ánh xạ Master Mapping...")

    base_cols = [
        "No (STT)", "SDAC Code", "SDAC Code nhân công", "Description",
        "Specification", "Unit", "Material Cost", "Labor Cost"
    ]

    df_report = df_pivot.copy()
    df_report['SDAC Code'] = df_report['SDAC_CODE'].astype(
        str).str.strip().str.upper()
    valid_codes = set(df_report['SDAC Code'].unique())

    if master_data_path and os.path.exists(master_data_path):
        print("-> Đang ánh xạ thông tin vật tư & Giá từ MapData...")
        target_master_sheet = getattr(config, 'MASTER_SHEET_NAME', 0)
        actual_master_sheet = get_actual_sheet_name(
            master_data_path, target_master_sheet)
        print(
            f"   [+] Radar dò Master: Chốt đọc dữ liệu từ Sheet '{actual_master_sheet}'")

        master_key_col = config.MASTER_COL_MAP.get(
            "Code_Master", "Code_Master")
        search_key = str(master_key_col).lower().replace(" ", "")

        header_row_idx = 0
        is_header_found = False

        try:
            df_raw = pd.read_excel(
                master_data_path, sheet_name=actual_master_sheet, header=None, nrows=20, engine="calamine")
            for r_idx in range(len(df_raw)):
                for c_idx in range(len(df_raw.columns)):
                    cell_val = str(
                        df_raw.iloc[r_idx, c_idx]).lower().replace(" ", "")
                    if search_key == cell_val:
                        header_row_idx = r_idx
                        is_header_found = True
                        print(
                            f"   [+] Radar Master: Chốt cột '{master_key_col}' nằm tại dòng số {r_idx + 1}")
                        break
                if is_header_found:
                    break
        except Exception as e:
            print(f"   ⚠️ Lỗi khi quét Radar Master: {e}")

        # Đọc trực tiếp từ Excel bằng Calamine Rust Engine (nhanh, chuẩn xác và không tạo file rác .pkl)
        df_master = pd.read_excel(
            master_data_path,
            sheet_name=actual_master_sheet,
            header=header_row_idx,
            engine="calamine"
        )
        df_master.columns = df_master.columns.astype(str).str.strip()

        if master_key_col in df_master.columns:
            df_master[master_key_col] = df_master[master_key_col].astype(
                str).str.strip().str.upper()
            df_master = df_master.drop_duplicates(
                subset=[master_key_col], keep='first')
            df_master_sub = df_master[df_master[master_key_col].isin(
                valid_codes)].copy()

            rename_dict = {actual_col: std_col for std_col,
                           actual_col in config.MASTER_COL_MAP.items() if std_col != "Code_Master"}
            df_master_sub = df_master_sub.rename(columns=rename_dict)

            cols_to_keep = [master_key_col] + list(rename_dict.values())
            existing_cols = [
                c for c in cols_to_keep if c in df_master_sub.columns]
            df_master_sub = df_master_sub[existing_cols]

            df_report = pd.merge(
                df_report, df_master_sub, left_on='SDAC Code', right_on=master_key_col, how='left')
        else:
            print(
                f"⚠️ Lỗi: Không tìm thấy cột khóa '{master_key_col}' trong file Master!")
    else:
        print("⚠️ Chưa có file MapData. Bỏ qua bước ánh xạ giá.")

    for col in base_cols:
        if col not in df_report.columns:
            df_report[col] = ""
        else:
            df_report[col] = df_report[col].fillna("")

    df_report['Khối lượng tổng'] = df_report[drawing_columns].sum(axis=1)

    def format_qty(val):
        try:
            f_val = float(val)
            return "-" if f_val == 0 else f_val
        except Exception:
            return "-"

    for col in drawing_columns + ['Khối lượng tổng']:
        df_report[col] = df_report[col].apply(format_qty)

    df_report['Phụ trội'] = df_report.get('PHU_TROI', "")
    df_report['Remark'] = df_report.get('REMARK', "")
    df_report['Note'] = ""
    df_report['No (STT)'] = range(1, len(df_report) + 1)

    final_columns = base_cols + drawing_columns + \
        ["Khối lượng tổng", "Phụ trội", "Remark", "Note"]
    return df_report[final_columns].copy()

# ==========================================
# 4. ĐỐI SOÁT VÒNG 2: BẢN VẼ CHUẨN AI VS GATE PASS PDF
# ==========================================


def build_gate_pass_reconciliation_df(df_ai, drawing_columns, dict_gatepass):
    """
    Tạo bảng đối soát Vòng 2 (Sheet 2):
    - Cộng tổng tất cả các dòng có cùng SDAC Code (KHÔNG tính dòng có Remark = SDV).
    - Trường hợp chỉ có dòng Remark = SDV -> KL yêu cầu Vendor mang vào = 0.
    - So sánh với KL trên Biên bản vật tư (Gate Pass):
    + Nếu KL Bản vẽ (Vendor) <= KL Gate Pass -> ĐÚNG (Hợp lệ).
    + Nếu KL Bản vẽ (Vendor) > KL Gate Pass  -> SAI (Tô đỏ).
    """
    def safe_float(val):
        try:
            return round(float(val), 2)
        except Exception:
            return 0.0

    # Thu thập thông tin mô tả và tính toán khối lượng theo từng mã trên Bản vẽ
    drawing_summary = {}
    for _, row in df_ai.iterrows():
        code = str(row['SDAC Code']).strip().upper()
        remark = "SDV" if "SDV" in str(row.get('Remark', '')).upper() else ""
        row_qty = sum(safe_float(row[col]) for col in drawing_columns)

        if code not in drawing_summary:
            drawing_summary[code] = {
                "Description": row.get("Description", ""),
                "Specification": row.get("Specification", ""),
                "Unit": row.get("Unit", ""),
                "total_drawing_qty": 0.0,
                "sdv_qty": 0.0,
                "vendor_req_qty": 0.0
            }

        drawing_summary[code]["total_drawing_qty"] = round(
            drawing_summary[code]["total_drawing_qty"] + row_qty, 2)
        if remark == "SDV":
            drawing_summary[code]["sdv_qty"] = round(
                drawing_summary[code]["sdv_qty"] + row_qty, 2)
        else:
            # Chỉ cộng các dòng KHÔNG phải SDV
            drawing_summary[code]["vendor_req_qty"] = round(
                drawing_summary[code]["vendor_req_qty"] + row_qty, 2)

    # Logic so sánh với tất cả các code trong file excel
    # # Hợp nhất danh sách mã từ cả Bản vẽ và Gate Pass (để không sót mã nào)
    # all_codes = list(drawing_summary.keys())
    # for gp_code in dict_gatepass.keys():
    #     if gp_code not in drawing_summary:
    #         all_codes.append(gp_code)

    # Logic so sánh với những code có trên file pdf BBVT
    all_codes = list(dict_gatepass.keys())

    gp_rows = []
    # Lưu dòng bị lỗi (bắt đầu từ dòng 2 trên Excel) để tô đỏ
    gp_error_row_indices = []

    for idx, code in enumerate(all_codes, start=1):
        info = drawing_summary.get(code, {
            "Description": "(Không có trên bản vẽ)",
            "Specification": "",
            "Unit": "",
            "total_drawing_qty": 0.0,
            "sdv_qty": 0.0,
            "vendor_req_qty": 0.0
        })

        total_bv = info["total_drawing_qty"]
        sdv_q = info["sdv_qty"]
        # Đã loại trừ SDV (Nếu chỉ có SDV thì tự động = 0.0)
        ven_req = info["vendor_req_qty"]
        gp_actual = round(float(dict_gatepass.get(code, 0.0)), 2)
        diff = round(gp_actual - ven_req, 2)

        # Đánh giá theo đúng quy tắc: ven_req <= gp_actual là ĐÚNG, ven_req > gp_actual là SAI (Tô đỏ)
        if ven_req > gp_actual:
            missing_qty = round(ven_req - gp_actual, 2)
            status = f"SAI LỆCH: Mang vào thiếu {missing_qty} (Cần: {ven_req} | GatePass: {gp_actual})"
            gp_error_row_indices.append(idx + 1)  # +1 vì dòng 1 là Header
        else:
            if ven_req == 0 and sdv_q > 0:
                status = "Hợp lệ (100% Vật tư kho SDV cấp -> Vendor = 0)"
            elif total_bv == 0 and gp_actual > 0:
                status = "Hợp lệ (Vật tư mang dư/ngoài bản vẽ)"
            elif gp_actual == ven_req:
                status = "Hợp lệ (Khớp 100%)"
            else:
                status = f"Hợp lệ (Mang dư {diff} so với bản vẽ)"

        gp_rows.append({
            "No (STT)": idx,
            "SDAC Code": code,
            "Description": info["Description"],
            "Specification": info["Specification"],
            "Unit": info["Unit"],
            "Tổng KL Bản Vẽ": total_bv,
            "KL Vật Tư SDV": sdv_q,
            "KL Vendor Cần Mang Vào (Trừ SDV)": ven_req,
            "KL Thực Tế Gate Pass": gp_actual,
            "Chênh Lệch (Gate Pass - Cần Mang)": diff,
            "Kết Luận Đối Soát": status
        })

    return pd.DataFrame(gp_rows), gp_error_row_indices

def auto_fit_columns_and_rows(ws, default_row_height=24, header_row_height=28):
    """
    Tự động căn chỉnh độ rộng cột và chiều cao hàng tối ưu (chuẩn hóa hiển thị giống Excel 2):
    1. Cột Specification (quy cách) được mở rộng rộng rãi (~50 ký tự) như thao tác kéo chuột thủ công.
    2. Các cột khác tự động tính toán độ rộng theo nội dung và tiêu đề dài nhất (+ padding 3-4 ký tự).
    3. Toàn bộ hàng dữ liệu được đặt chiều cao chuẩn 24pt (thanh thoát, 1 dòng gọn gàng như excel2),
       hàng tiêu đề đặt 28pt.
    """
    # 1. Chiều cao hàng tiêu đề (Header row)
    ws.row_dimensions[1].height = header_row_height

    # 2. Bảng cấu hình độ rộng ưu tiên cho các cột phổ biến
    column_width_presets = {
        "sdac code nhân công": 19,
        "sdac code": 16,
        "no (stt)": 8,
        "stt": 8,
        "no": 8,
        "description": 28,
        "specification": 50,  # Kéo dài cột Specification ra một đoạn để chữ nằm gọn 1 dòng
        "unit": 8,
        "đvt": 8,
        "material cost": 14,
        "labor cost": 14,
        "khối lượng tổng": 16,
        "tổng kl bản vẽ": 16,
        "kl vật tư sdv": 15,
        "kl vendor cần mang vào (trừ sdv)": 22,
        "kl thực tế gate pass": 18,
        "chênh lệch (gate pass - cần mang)": 20,
        "phụ trội": 10,
        "remark": 10,
        "note": 35,
        "kết luận đối soát": 38,
    }

    # 3. Tính toán và gán độ rộng cho từng cột
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        header_val = str(col[0].value or "").strip().lower()

        # Kiểm tra xem có cấu hình preset cho tiêu đề cột này không (ưu tiên so khớp chuỗi dài trước)
        preset_w = None
        for key in sorted(column_width_presets.keys(), key=len, reverse=True):
            if key in header_val:
                preset_w = column_width_presets[key]
                break

        if preset_w is not None:
            ws.column_dimensions[col_letter].width = preset_w
        else:
            # Tự động tính độ dài lớn nhất trong cột
            max_len = 0
            for cell in col:
                if cell.value is not None:
                    lines = str(cell.value).split('\n')
                    for line in lines:
                        max_len = max(max_len, len(str(line).strip()))
            # Thêm 3 ký tự padding cho thoáng, tối thiểu 9 ký tự
            ws.column_dimensions[col_letter].width = max(max_len + 3, 9)

    # 4. Đặt chiều cao cho từng hàng dữ liệu (Data rows)
    for row_idx in range(2, ws.max_row + 1):
        max_lines = 1
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            val = str(cell.value or '')
            if '\n' in val:
                max_lines = max(max_lines, len(val.split('\n')))
            else:
                col_letter = get_column_letter(col_idx)
                w = ws.column_dimensions[col_letter].width or 10
                # Nếu chuỗi dài gấp rưỡi độ rộng cột (thường là Note hoặc Spec rất dài)
                if len(val) > w * 1.4 and col_idx not in [1, 2, 3]:
                    estimated = max(1, int(len(val) / w) + 1)
                    max_lines = max(max_lines, min(estimated, 3))

        if max_lines > 1:
            ws.row_dimensions[row_idx].height = max(default_row_height, max_lines * 18)
        else:
            ws.row_dimensions[row_idx].height = default_row_height


# ==========================================
# 5. ĐỐI SOÁT CHÉO ĐA ĐIỀU KIỆN & XUẤT BÁO CÁO 2 SHEET
# ==========================================


def reconcile_and_highlight(df_ai, df_vendor, output_excel_path, drawing_columns, dict_gatepass=None):
    """
    Thực hiện đồng thời:
    - Vòng 1 (Sheet 1): Bản vẽ AI vs Sheet 3. Bảng khối lượng Vendor.
    - Vòng 2 (Sheet 2): Bản vẽ AI (đã trừ SDV) vs Biên bản vật tư Gate Pass PDF.
    """
    use_extra = 'VENDOR_EXTRA' in df_vendor.columns
    use_remark = 'VENDOR_REMARK' in df_vendor.columns

    mode_desc = ["Code"]
    if use_extra:
        mode_desc.append("Phụ trội")
    if use_remark:
        mode_desc.append("Remark")
    print(
        f"🔍 [Vòng 1] Bắt đầu đối soát Bản vẽ vs Excel theo tổ hợp khóa: [{' + '.join(mode_desc)}]...")

    def safe_float(val):
        try:
            return round(float(val), 2)
        except Exception:
            return 0.0

    def norm_extra(val):
        if pd.isna(val):
            return ""
        s = str(val).strip().replace(" ", "")
        if s.lower() in ['nan', 'none', '', '-', '0', '0.0', '0%', '0.0%']:
            return ""
        if s.endswith('%'):
            try:
                f = float(s[:-1])
                if f == 0:
                    return ""
                return f"{int(f)}%" if f.is_integer() else f"{f}%"
            except:
                return s.upper()
        try:
            f = float(s)
            if f == 0:
                return ""
            if 0 < abs(f) <= 1.0:
                pct = round(f * 100, 2)
                return f"{int(pct)}%" if pct.is_integer() else f"{pct}%"
            return f"{int(f)}%" if f.is_integer() else f"{f}%"
        except:
            return s.upper()

    def norm_remark(val):
        if pd.isna(val):
            return ""
        return "SDV" if "SDV" in str(val).upper() else ""

    def build_key(code, extra_val="", remark_val=""):
        c = str(code).strip().upper()
        e = norm_extra(extra_val) if use_extra else ""
        r = norm_remark(remark_val) if use_remark else ""
        return (c, e, r)

    def format_cond_label(e_val, r_val):
        parts = []
        if use_extra:
            parts.append(f"PT:{e_val if e_val else 'Trống'}")
        if use_remark:
            parts.append(f"RM:{r_val if r_val else 'Trống'}")
        return ", ".join(parts)

    vendor_dict = {}
    vendor_code_details = {}

    for _, row in df_vendor.iterrows():
        raw_code = str(row[config.VENDOR_COL_CODE]).strip().upper()
        key = build_key(raw_code, row.get('VENDOR_EXTRA', ""),
                        row.get('VENDOR_REMARK', ""))

        if key not in vendor_dict:
            vendor_dict[key] = {col: 0.0 for col in drawing_columns}

        for col in drawing_columns:
            if pd.notnull(row.get(col)):
                vendor_dict[key][col] = round(
                    vendor_dict[key][col] + safe_float(row.get(col, 0)), 2)

        if raw_code not in vendor_code_details:
            vendor_code_details[raw_code] = {}
        vendor_code_details[raw_code][key] = vendor_dict[key]

    ai_group_totals = {}
    for _, row in df_ai.iterrows():
        key = build_key(row['SDAC Code'], row.get(
            'Phụ trội', ""), row.get('Remark', ""))
        if key not in ai_group_totals:
            ai_group_totals[key] = {col: 0.0 for col in drawing_columns}
        for col_name in drawing_columns:
            ai_group_totals[key][col_name] = round(
                ai_group_totals[key][col_name] + safe_float(row[col_name]), 2)

    error_cells = []

    for index, row in df_ai.iterrows():
        code = str(row['SDAC Code']).strip().upper()
        key = build_key(code, row.get('Phụ trội', ""), row.get('Remark', ""))
        _, ai_e, ai_r = key
        reconcile_logs = []

        if code not in vendor_code_details:
            reconcile_logs.append("Mã mồ côi (Chỉ có ở bản vẽ)")
            error_cells.append(f"ROW:{index + 2}")
        else:
            vendor_row_data = vendor_dict.get(
                key, {col: 0.0 for col in drawing_columns})
            for col_name in drawing_columns:
                total_ai_qty = ai_group_totals[key][col_name]
                vendor_qty = vendor_row_data.get(col_name, 0.0)

                if total_ai_qty != vendor_qty:
                    if (use_extra or use_remark) and vendor_qty == 0.0:
                        ai_cond_str = format_cond_label(ai_e, ai_r)
                        ven_variants = []
                        for (_, v_e, v_r), v_cols in vendor_code_details[code].items():
                            v_q = v_cols.get(col_name, 0.0)
                            if v_q != 0:
                                ven_variants.append(
                                    f"[{format_cond_label(v_e, v_r)}]={v_q}")

                        if ven_variants:
                            ven_info = ", ".join(ven_variants)
                            reconcile_logs.append(
                                f"Lệch BV {col_name}: AI [{ai_cond_str}]={total_ai_qty} | Vendor {ven_info}")
                        else:
                            reconcile_logs.append(
                                f"Lệch BV {col_name}: AI [{ai_cond_str}]={total_ai_qty} | Ven=0.0 (Không có dòng [{ai_cond_str}])")
                    else:
                        reconcile_logs.append(
                            f"Lệch BV {col_name} (AI:{total_ai_qty} | Ven:{vendor_qty})")

                    col_excel_idx = df_ai.columns.get_loc(col_name) + 1
                    error_cells.append((index + 2, col_excel_idx))

        df_ai.at[index, 'Note'] = " | ".join(reconcile_logs)

    # Chuẩn bị bảng đối soát Vòng 2 (Gate Pass)
    df_gp_report = None
    gp_error_rows = []
    if dict_gatepass is not None:
        print(
            "🔍 [Vòng 2] Đang tính toán khối lượng chuẩn (Trừ SDV) và đối soát với Gate Pass...")
        df_gp_report, gp_error_rows = build_gate_pass_reconciliation_df(
            df_ai, drawing_columns, dict_gatepass)

    # Xuất cả 2 bảng ra cùng 1 file Excel
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df_ai.to_excel(writer, sheet_name="1. Đối Soát Bản Vẽ", index=False)
        if df_gp_report is not None and not df_gp_report.empty:
            df_gp_report.to_excel(
                writer, sheet_name="2. Đối Soát Gate Pass", index=False)

    print("🎨 Đang trang trí (Center, Borders, tô màu Group Code & Highlight lỗi 2 Sheet)...")
    wb = load_workbook(output_excel_path)

    red_fill = PatternFill(start_color="FFC7CE",
                           end_color="FFC7CE", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFFF00",
                              end_color="FFFF00", fill_type="solid")
    green_fill = PatternFill(start_color="E2EFDA",
                             end_color="E2EFDA", fill_type="solid")
    group_fills = [
        PatternFill(start_color="FCE4D6",
                    end_color="FCE4D6", fill_type="solid"),
        PatternFill(start_color="E2EFDA",
                    end_color="E2EFDA", fill_type="solid")
    ]
    bold_font = Font(bold=True)
    center_middle = Alignment(
        horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # --- TRANG TRÍ SHEET 1: ĐỐI SOÁT BẢN VẼ ---
    ws1 = wb["1. Đối Soát Bản Vẽ"]
    code_counts = df_ai['SDAC Code'].astype(str).str.strip().value_counts()
    duplicated_codes = set(code_counts[code_counts > 1].index)

    code_color_map = {}
    color_toggle = 0
    for code_val in df_ai['SDAC Code'].astype(str).str.strip():
        if code_val in duplicated_codes and code_val not in code_color_map:
            code_color_map[code_val] = group_fills[color_toggle % 2]
            color_toggle += 1

    cols_to_format_float = drawing_columns + ['Khối lượng tổng']
    format_col_indices = [df_ai.columns.get_loc(
        c) + 1 for c in cols_to_format_float]
    price_col_indices = [df_ai.columns.get_loc(
        c) + 1 for c in ['Material Cost', 'Labor Cost'] if c in df_ai.columns]

    for row_idx in range(1, len(df_ai) + 2):
        row_group_fill = None
        if row_idx > 1:
            current_code = str(df_ai.iloc[row_idx - 2]['SDAC Code']).strip()
            row_group_fill = code_color_map.get(current_code, None)

        for col_idx in range(1, len(df_ai.columns) + 1):
            cell = ws1.cell(row=row_idx, column=col_idx)
            cell.alignment = center_middle
            cell.border = thin_border

            if row_idx == 1:
                cell.fill = yellow_fill
                cell.font = bold_font
                continue

            if row_group_fill is not None:
                cell.fill = row_group_fill

            if col_idx in format_col_indices and isinstance(cell.value, (int, float)):
                cell.number_format = '0.00'
            elif col_idx in price_col_indices and isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0'

    for err in error_cells:
        if isinstance(err, str) and err.startswith("ROW:"):
            row_idx = int(err.split(":")[1])
            for col_idx in range(1, len(df_ai.columns) + 1):
                ws1.cell(row=row_idx, column=col_idx).fill = red_fill
        else:
            r_idx, c_idx = err
            ws1.cell(row=r_idx, column=c_idx).fill = red_fill
            ws1.cell(row=r_idx, column=len(df_ai.columns)).fill = red_fill

    # Tự động căn chỉnh độ rộng cột và chiều cao hàng (Auto-fit chuẩn layout excel2)
    auto_fit_columns_and_rows(ws1)

    # --- TRANG TRÍ SHEET 2: ĐỐI SOÁT GATE PASS ---
    if "2. Đối Soát Gate Pass" in wb.sheetnames and df_gp_report is not None:
        ws2 = wb["2. Đối Soát Gate Pass"]
        gp_float_cols = [6, 7, 8, 9, 10]  # Các cột Khối lượng trên Sheet 2

        for row_idx in range(1, len(df_gp_report) + 2):
            is_err_row = row_idx in gp_error_rows
            for col_idx in range(1, len(df_gp_report.columns) + 1):
                cell = ws2.cell(row=row_idx, column=col_idx)
                cell.alignment = center_middle
                cell.border = thin_border

                if row_idx == 1:
                    cell.fill = yellow_fill
                    cell.font = bold_font
                    continue

                if col_idx in gp_float_cols and isinstance(cell.value, (int, float)):
                    cell.number_format = '0.00'

                # Nếu Vendor mang thiếu (KL Bản vẽ > KL Gate Pass) -> Bôi đỏ dòng cảnh báo
                if is_err_row:
                    cell.fill = red_fill
                elif col_idx == 11:
                    cell.fill = green_fill

        auto_fit_columns_and_rows(ws2)

    wb.save(output_excel_path)
    print(f"✅ Hoàn tất! Báo cáo Final (2 Sheet) lưu tại: {output_excel_path}")
    return output_excel_path


def run_reconciliation_pipeline():
    """Hàm khởi chạy toàn bộ quy trình đối soát Vòng 1 + Vòng 2."""
    vendor_excel_path = os.path.join(
        config.DIR_VENDOR_EXCEL, config.VENDOR_FILE_NAME)
    master_data_path = os.path.join(
        config.DIR_VENDOR_EXCEL, config.MASTER_DATA_FILE_NAME)
    gatepass_csv_dir = getattr(
        config, 'DIR_GATEPASS_CSV', config.DIR_CSV_EXTRACTED)

    os.makedirs(config.DIR_FINAL_REPORT, exist_ok=True)
    base_output_path = os.path.join(
        config.DIR_FINAL_REPORT, "Consolidated_Report.xlsx")
    output_excel_path = get_unique_path(base_output_path)

    try:
        # 1. Gom dữ liệu Bản vẽ (Pivot)
        df_pivot, drawing_list = aggregate_ai_data(config.DIR_CSV_EXTRACTED)

        # 2. Gom dữ liệu Gate Pass (Groupby SUM)
        dict_gatepass = aggregate_gate_pass_data(gatepass_csv_dir)

        # 3. Đọc file Excel thanh toán của Vendor
        df_vendor = load_vendor_data_dynamic(
            vendor_excel_path,
            config.VENDOR_SHEET_NAME,
            drawing_list,
            config.VENDOR_COL_CODE
        )

        # 4. Ánh xạ MapData & Định dạng chuẩn
        df_formatted = format_master_report(
            df_pivot, drawing_list, master_data_path)

        # 5. Đối soát 2 Vòng & Xuất 2 Sheet Excel
        reconcile_and_highlight(df_formatted, df_vendor,
                                output_excel_path, drawing_list, dict_gatepass)

    except Exception as e:
        print(f"\n❌ LỖI HỆ THỐNG: {e}")


if __name__ == "__main__":
    run_reconciliation_pipeline()
