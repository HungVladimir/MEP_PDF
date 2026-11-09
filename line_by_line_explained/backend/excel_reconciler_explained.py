# ==============================================================================
# NÃO BỘ TOÁN HỌC & ĐỐI SOÁT 2 VÒNG - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/excel_reconciler.py
# Khớp 100% với 758 dòng của file gốc (Gồm Cache Calamine, Tô màu xen kẽ, OpenPyXL, CLI runner)
# ==============================================================================

# Dòng 1-9: Thư viện chuẩn và thư viện xử lý số liệu
import os                       # Xử lý đường dẫn file và kiểm tra thư mục
import re                       # Regular Expression: tách số tự nhiên (Natural Sort)
import glob                     # Quét danh sách các file CSV
import pandas as pd             # DataFrame, Pivot Table, Groupby, Merge bảng dữ liệu
from openpyxl import load_workbook # Mở và chỉnh sửa định dạng file Excel trực tiếp
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font # Định dạng ô: màu sắc, căn lề, kẻ bảng, phông chữ
from openpyxl.utils import get_column_letter # Chuyển đổi số thứ tự cột (1, 2, 3...) thành chữ cái (A, B, C...) để chỉnh độ rộng cột
import config                   # Cấu hình đường dẫn, tên cột, tên sheet mặc định


# Dòng 12-25: Hàm tự động đổi tên file báo cáo nếu file cũ đang mở
def get_unique_path(base_path):
    """
    Tự động đổi tên file báo cáo nếu file cũ đang mở để chống lỗi PermissionError.
    Nếu file 'Final_Report.xlsx' đang được mở bởi Excel, hàm sẽ trả về
    'Final_Report_1.xlsx', 'Final_Report_2.xlsx'... để chương trình không bị crash.
    """
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


# ==============================================================================
# KHỐI 1A. HÀM GOM NHÓM DỮ LIỆU BẢN VẼ TỪ NHIỀU FILE CSV (PIVOT)
# ==============================================================================
def aggregate_ai_data(csv_dir):
    """
    Đọc hàng loạt file CSV Bản vẽ từ AI bóc ra, gom chung lại thành 1 bảng ngang (Pivot).
    - Lọc bỏ các file GATEPASS_ (nếu lưu chung).
    - Sắp xếp tự nhiên (Natural Sort) theo số thứ tự bản vẽ: Bản vẽ 1 -> Bản vẽ 2 -> Bản vẽ 10.
    - Gom nhóm theo bộ 3 khóa: [SDAC_CODE, PHU_TROI, REMARK].
    - Xoay trục (Pivot) để mỗi bản vẽ trở thành 1 CỘT NGANG.
    - Tính cột 'Tổng AI (Bản vẽ)' = tổng tất cả các cột bản vẽ.
    """
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
        key=lambda x: [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', os.path.basename(x))]
    )

    if not all_files:
        raise FileNotFoundError(f"❌ Không tìm thấy file CSV Bản vẽ nào trong {csv_dir}")

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
            else:
                df[col] = df[col].fillna("").astype(str).str.strip()

        df_list.append(df)

    df_combined = pd.concat(df_list, ignore_index=True)

    # Tạo bảng Pivot Table xoay các bản vẽ thành các cột
    df_final_pivot = df_combined.pivot_table(
        index=['SDAC_CODE', 'PHU_TROI', 'REMARK'],
        columns='Ban_Ve',
        values='QTY',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Tính tổng khối lượng bản vẽ AI
    df_final_pivot['TOTAL_DRAWINGS'] = df_final_pivot[drawing_names].sum(axis=1)

    column_order = ['SDAC_CODE', 'PHU_TROI', 'REMARK', 'TOTAL_DRAWINGS'] + drawing_names
    df_final_pivot = df_final_pivot[column_order]

    rename_dict = {
        'SDAC_CODE': 'SDAC Code',
        'PHU_TROI': 'Phụ trội',
        'REMARK': 'Remark',
        'TOTAL_DRAWINGS': 'Tổng AI (Bản vẽ)'
    }
    df_final_pivot.rename(columns=rename_dict, inplace=True)
    return df_final_pivot, drawing_names


# ==============================================================================
# KHỐI 1B. HÀM GOM NHÓM DỮ LIỆU BIÊN BẢN GIAO NHẬN (GATE PASS)
# ==============================================================================
def aggregate_gate_pass_data(gatepass_csv_dir=config.DIR_GATEPASS_CSV):
    """
    Đọc tất cả file CSV Gate Pass (Biên bản giao nhận hàng vào công trường),
    gom tổng số lượng theo từng mã SDAC_CODE thành Dictionary {Mã: Tổng_KL}.
    """
    if not os.path.exists(gatepass_csv_dir):
        print("ℹ️ Không tìm thấy thư mục CSV Gate Pass. Bỏ qua dữ liệu Gate Pass.")
        return {}

    all_files = glob.glob(os.path.join(gatepass_csv_dir, "*.csv"))
    if gatepass_csv_dir == config.DIR_CSV_EXTRACTED:
        all_files = [f for f in all_files if os.path.basename(f).upper().startswith("GATEPASS_")]

    if not all_files:
        print("ℹ️ Chưa có file CSV Gate Pass nào để đối soát Vòng 2.")
        return {}

    print(f"📦 Đang gom nhóm dữ liệu từ {len(all_files)} trang Gate Pass CSV...")
    df_list = []
    for f in all_files:
        try:
            df = pd.read_csv(f, dtype={'SDAC_CODE': str})
            if 'SDAC_CODE' in df.columns and 'QTY' in df.columns:
                df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0)
                df_list.append(df[['SDAC_CODE', 'QTY']])
        except Exception as e:
            print(f"⚠️ Lỗi đọc file Gate Pass CSV {f}: {e}")

    if not df_list:
        return {}

    df_all_gp = pd.concat(df_list, ignore_index=True)
    df_gp_sum = df_all_gp.groupby('SDAC_CODE')['QTY'].sum().reset_index()

    gatepass_dict = {}
    for _, row in df_gp_sum.iterrows():
        code = str(row['SDAC_CODE']).strip().upper()
        gatepass_dict[code] = float(row['QTY'])

    print(f"✅ Đã tổng hợp {len(gatepass_dict)} mã từ Gate Pass.")
    return gatepass_dict


# ==============================================================================
# KHỐI 2. SO KHỚP MỜ TÊN SHEET & QUÉT TỌA ĐỘ RADAR
# ==============================================================================
def get_actual_sheet_name(excel_path, target_sheet_name):
    """
    So khớp mờ (Fuzzy Match) tên Sheet:
    Loại bỏ dấu cách, không phân biệt chữ hoa thường để tìm đúng sheet trong file Excel.
    """
    try:
        xls = pd.ExcelFile(excel_path, engine="calamine")
        all_sheets = xls.sheet_names
        target_clean = str(target_sheet_name).lower().replace(" ", "")

        for sheet in all_sheets:
            sheet_clean = str(sheet).lower().replace(" ", "")
            if target_clean in sheet_clean or sheet_clean in target_clean:
                return sheet
        return all_sheets[0]
    except Exception as e:
        print(f"⚠️ Lỗi đọc tên sheet từ file {excel_path}: {e}")
        return target_sheet_name


def load_vendor_data_dynamic(excel_path, sheet_name, drawing_names):
    """
    Rải Radar quét 20 dòng đầu file Vendor:
    - Tìm tọa độ cột Mã sản phẩm (SDAC_CODE), cột Phụ trội (EXTRA), cột Ghi chú (REMARK).
    - Tìm tọa độ từng cột tương ứng với các bản vẽ (drawing_names).
    - Đọc chính xác các cột cần thiết bắt đầu từ hàng ngay sau header.
    """
    actual_sheet = get_actual_sheet_name(excel_path, sheet_name)
    print(f"-> Đang quét Radar tìm cột trên file Vendor (Sheet: {actual_sheet})...")

    df_raw = pd.read_excel(excel_path, sheet_name=actual_sheet, header=None, nrows=20, engine="calamine")

    code_idx = None
    extra_idx = None
    remark_idx = None
    drawing_indices = {}
    header_row_idx = None
    code_row = None

    col_names_map = {
        config.VENDOR_COL_CODE: ["MÃ SẢN PHẨM", "SDAC CODE", "MÃ SP", "PRODUCT CODE", "MÃ"],
        config.VENDOR_COL_EXTRA: ["PHỤ TRỘI", "PHU TROI", "EXTRA"],
        config.VENDOR_COL_REMARK: ["GHI CHÚ", "REMARK", "NOTE"]
    }

    remaining_drawings = set(drawing_names)

    for row_idx in range(len(df_raw)):
        if (code_idx is not None and extra_idx is not None and remark_idx is not None and len(remaining_drawings) == 0):
            break

        row_values = df_raw.iloc[row_idx].astype(str).tolist()

        if code_idx is not None and row_idx > code_row + 1:
            break

        for col_idx in range(len(df_raw.columns)):
            val = str(df_raw.iloc[row_idx, col_idx]).strip().upper()
            val_clean = re.sub(r'\s+', '', val)

            if code_idx is None:
                for alias in col_names_map[config.VENDOR_COL_CODE]:
                    if alias.replace(" ", "") in val_clean:
                        code_idx = col_idx
                        header_row_idx = row_idx
                        code_row = row_idx
                        break

            if extra_idx is None:
                for alias in col_names_map[config.VENDOR_COL_EXTRA]:
                    if alias.replace(" ", "") in val_clean:
                        extra_idx = col_idx
                        break

            if remark_idx is None:
                for alias in col_names_map[config.VENDOR_COL_REMARK]:
                    if alias.replace(" ", "") in val_clean:
                        remark_idx = col_idx
                        break

            for drw in list(remaining_drawings):
                drw_clean = re.sub(r'\s+', '', str(drw).upper())
                if drw_clean in val_clean or val_clean in drw_clean:
                    drawing_indices[drw] = col_idx
                    remaining_drawings.remove(drw)
                    break

    if code_idx is None:
        raise ValueError(f"❌ Không tìm thấy cột '{config.VENDOR_COL_CODE}' trên file Vendor (Sheet: {actual_sheet})!")

    cols_to_use = [code_idx]
    if extra_idx is not None: cols_to_use.append(extra_idx)
    if remark_idx is not None: cols_to_use.append(remark_idx)
    cols_to_use.extend(drawing_indices.values())
    cols_to_use = sorted(list(set(cols_to_use)))

    df_vendor = pd.read_excel(
        excel_path,
        sheet_name=actual_sheet,
        skiprows=header_row_idx + 1,
        usecols=cols_to_use,
        header=None,
        engine="calamine"
    )

    idx_map = {orig_idx: new_idx for new_idx, orig_idx in enumerate(cols_to_use)}
    rename_dict = {idx_map[code_idx]: config.VENDOR_COL_CODE}
    if extra_idx is not None: rename_dict[idx_map[extra_idx]] = 'VENDOR_EXTRA'
    if remark_idx is not None: rename_dict[idx_map[remark_idx]] = 'VENDOR_REMARK'

    for drw, c_idx in drawing_indices.items():
        rename_dict[idx_map[c_idx]] = drw

    df_vendor.rename(columns=rename_dict, inplace=True)
    df_vendor = df_vendor[df_vendor[config.VENDOR_COL_CODE].notnull()].copy()
    df_vendor[config.VENDOR_COL_CODE] = df_vendor[config.VENDOR_COL_CODE].astype(str).str.strip()

    if 'VENDOR_EXTRA' not in df_vendor.columns: df_vendor['VENDOR_EXTRA'] = ""
    if 'VENDOR_REMARK' not in df_vendor.columns: df_vendor['VENDOR_REMARK'] = ""

    for drw in drawing_names:
        if drw not in df_vendor.columns:
            df_vendor[drw] = 0.0

    return df_vendor


# ==============================================================================
# KHỐI 3. TRA CỨU MASTER DATA TRỰC TIẾP (KHÔNG DÙNG CACHE FILE RÁC)
# ==============================================================================
def format_master_report(df_reconciled, master_data_path, master_sheet_name):
    """
    Tra cứu thông tin từ file Master Data:
    - Tên sản phẩm, Kích thước, Đơn vị tính, Hệ số bù hao.
    - ĐỌC TRỰC TIẾP BẰNG CALAMINE (RUST ENGINE):
      Đọc thẳng từ file Excel gốc một cách chuẩn xác, không tạo các file đệm .cache.pkl
      gây rác thư mục hoặc xung đột khi người dùng cập nhật dữ liệu.
    """
    if not os.path.exists(master_data_path):
        print(f"⚠️ Không tìm thấy file Master Data tại {master_data_path}. Bỏ qua tra cứu.")
        return df_reconciled

    actual_master_sheet = get_actual_sheet_name(master_data_path, master_sheet_name)
    print(f"-> Đang tra cứu thông tin từ Master Data (Sheet: {actual_master_sheet})...")

    raw_head = pd.read_excel(master_data_path, sheet_name=actual_master_sheet, header=None, nrows=20, engine="calamine")
    master_header_row = 0
    for r_idx in range(len(raw_head)):
        row_str = " ".join(raw_head.iloc[r_idx].astype(str).str.upper().tolist())
        if "MÃ SẢN PHẨM" in row_str or "MÃ HÀNG" in row_str or "PRODUCT CODE" in row_str:
            master_header_row = r_idx
            break

    df_master = pd.read_excel(master_data_path, sheet_name=actual_master_sheet, skiprows=master_header_row, engine="calamine")

    master_col_code = None
    master_col_name = None
    master_col_dim = None
    master_col_unit = None
    master_col_waste = None

    for col in df_master.columns:
        c_clean = re.sub(r'\s+', '', str(col).upper())
        if not master_col_code and any(k in c_clean for k in ["MÃSẢNPHẨM", "MÃHÀNG", "PRODUCTCODE", "SDACCODE"]):
            master_col_code = col
        elif not master_col_name and any(k in c_clean for k in ["TÊNSẢNPHẨM", "TÊNHÀNG", "DESCRIPTION", "ITEMNAME"]):
            master_col_name = col
        elif not master_col_dim and any(k in c_clean for k in ["QUY CÁCH", "KÍCHTƯỚC", "DIMENSION", "SPEC"]):
            master_col_dim = col
        elif not master_col_unit and any(k in c_clean for k in ["ĐƠNVỊTÍNH", "ĐVT", "UNIT"]):
            master_col_unit = col
        elif not master_col_waste and any(k in c_clean for k in ["BÙHAO", "HỆSỐ", "WASTE", "HƯHAO"]):
            master_col_waste = col

    cols_to_merge = [master_col_code]
    for c in [master_col_name, master_col_dim, master_col_unit, master_col_waste]:
        if c: cols_to_merge.append(c)

    df_master_sub = df_master[cols_to_merge].drop_duplicates(subset=[master_col_code]).copy()
    df_master_sub[master_col_code] = df_master_sub[master_col_code].astype(str).str.strip()

    df_merged = pd.merge(df_reconciled, df_master_sub, left_on='SDAC Code', right_on=master_col_code, how='left')
    df_merged.drop(columns=[master_col_code], inplace=True, errors='ignore')
    return df_merged


# ==============================================================================
# KHỐI 4. ĐỐI SOÁT VÒNG 2 (GATE PASS VS BẢN VẼ VS VENDOR)
# ==============================================================================
def build_gate_pass_reconciliation_df(df_ai, drawing_columns, dict_gatepass):
    """
    Xây dựng Bảng đối soát Vòng 2 (Sheet 2):
    So sánh Tổng Khối lượng theo Bản vẽ AI với Khối lượng thực tế xuất tại Gate Pass.
    Đưa ra kết luận chi tiết:
    - ❌ Thiếu Gate Pass (Chưa có phiếu xuất tại cổng)
    - ⚠️ Thiếu X mét ở Gate Pass
    - ℹ️ Gate Pass thừa X mét so với Bản vẽ
    - ✅ Khớp 100%
    """
    if not dict_gatepass:
        return None, []

    df_gp_summary = df_ai.groupby('SDAC Code')[['Tổng AI (Bản vẽ)']].sum().reset_index()
    df_gp_summary.rename(columns={'Tổng AI (Bản vẽ)': 'Tổng KL Bản vẽ (m)'}, inplace=True)

    df_gp_summary['Tổng KL Gate Pass (m)'] = df_gp_summary['SDAC Code'].map(dict_gatepass).fillna(0.0)
    df_gp_summary['Chênh lệch (GP - BV)'] = (df_gp_summary['Tổng KL Gate Pass (m)'] - df_gp_summary['Tổng KL Bản vẽ (m)']).round(2)

    def evaluate_gatepass(row):
        gp_qty = row['Tổng KL Gate Pass (m)']
        dwg_qty = row['Tổng KL Bản vẽ (m)']
        if gp_qty == 0:
            return "❌ Thiếu Gate Pass (Chưa có phiếu xuất)"
        elif dwg_qty > gp_qty:
            return f"⚠️ Thiếu {round(dwg_qty - gp_qty, 2)}m ở Gate Pass"
        elif dwg_qty < gp_qty:
            return f"ℹ️ Gate Pass thừa {round(gp_qty - dwg_qty, 2)}m so với BV"
        return "✅ Khớp 100%"

    df_gp_summary['Đánh giá Gate Pass'] = df_gp_summary.apply(evaluate_gatepass, axis=1)

    error_rows = []
    for idx, row in df_gp_summary.iterrows():
        if "❌" in row['Đánh giá Gate Pass'] or "⚠️" in row['Đánh giá Gate Pass']:
            error_rows.append(idx + 2)

    return df_gp_summary, error_rows


# ==============================================================================
# KHỐI 5. HÀM CHÍNH ĐỐI SOÁT & TÔ MÀU PHÂN BIỆT DÒNG TRÙNG
# ==============================================================================
def format_cond_label(e, r):
    """Hàm tiện ích định dạng nhãn phụ trội và ghi chú: PT=SDV, RM=..."""
    parts = []
    if e: parts.append(f"PT={e}")
    if r: parts.append(f"RM={r}")
    return ", ".join(parts) if parts else "Gốc"


def auto_fit_columns_and_rows(ws, default_row_height=24, header_row_height=28):
    """
    Tự động căn chỉnh độ rộng cột và chiều cao hàng tối ưu (chuẩn hóa hiển thị giống Excel 2):
    1. Cột Specification (quy cách) được mở rộng rộng rãi (~50 ký tự) như thao tác kéo chuột thủ công.
    2. Các cột khác tự động tính toán độ rộng theo nội dung và tiêu đề dài nhất (+ padding 3-4 ký tự).
    3. Toàn bộ hàng dữ liệu được đặt chiều cao chuẩn 24pt (thanh thoát, 1 dòng gọn gàng như excel2),
       hàng tiêu đề đặt 28pt.
    """
    # 1. Đặt chiều cao hàng tiêu đề (Header row)
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

        preset_w = None
        for key in sorted(column_width_presets.keys(), key=len, reverse=True):
            if key in header_val:
                preset_w = column_width_presets[key]
                break

        if preset_w is not None:
            ws.column_dimensions[col_letter].width = preset_w
        else:
            max_len = 0
            for cell in col:
                if cell.value is not None:
                    lines = str(cell.value).split('\n')
                    for line in lines:
                        max_len = max(max_len, len(str(line).strip()))
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
                if len(val) > w * 1.4 and col_idx not in [1, 2, 3]:
                    estimated = max(1, int(len(val) / w) + 1)
                    max_lines = max(max_lines, min(estimated, 3))

        if max_lines > 1:
            ws.row_dimensions[row_idx].height = max(default_row_height, max_lines * 18)
        else:
            ws.row_dimensions[row_idx].height = default_row_height


def reconcile_and_highlight(df_ai, df_vendor, drawing_columns, dict_gatepass=None, output_excel_path="Final_Report.xlsx"):
    """
    Hàm đối soát cốt lõi:
    1. So khớp từng bản vẽ giữa AI bóc và Vendor khai báo.
    2. Tự động phát hiện trường hợp trùng mã nhưng khác điều kiện (Phụ trội / Ghi chú).
    3. Tô màu xen kẽ FCE4D6 (Cam nhạt) và E2EFDA (Xanh nhạt) cho các dòng trùng mã để dễ quan sát.
    4. Bôi đỏ ô lệch số lượng và ghi chú rõ ràng nguyên nhân lệch vào cột Note.
    5. Xuất đồng thời 2 Sheet: Sheet 1 (Đối Soát Bản Vẽ) và Sheet 2 (Đối Soát Gate Pass).
    """
    output_excel_path = get_unique_path(output_excel_path)

    def safe_float(val):
        try:
            return float(val) if pd.notnull(val) and str(val).strip() != '' else 0.0
        except (ValueError, TypeError):
            return 0.0

    has_pt_col = 'Phụ trội' in df_ai.columns
    has_rm_col = 'Remark' in df_ai.columns

    use_extra = has_pt_col and df_ai['Phụ trội'].astype(str).str.strip().ne('').any()
    use_remark = has_rm_col and df_ai['Remark'].astype(str).str.strip().ne('').any()

    mode_desc = ["Mã"]
    if use_extra: mode_desc.append("Phụ trội")
    if use_remark: mode_desc.append("Remark")
    print(f"🔍 [Vòng 1] Bắt đầu đối soát Bản vẽ vs Excel theo tổ hợp khóa: [{', '.join(mode_desc)}]...")

    def normalize_extra(val):
        if pd.isna(val): return ""
        return "SDV" if "SDV" in str(val).upper() else ""

    def build_key(code, extra_val="", remark_val=""):
        c = str(code).strip().upper()
        e = normalize_extra(extra_val) if use_extra else ""
        r = str(remark_val).strip().upper() if use_remark else ""
        return (c, e, r)

    # 1. Gom nhóm dữ liệu Vendor
    vendor_dict = {}
    vendor_code_details = {}

    for _, row in df_vendor.iterrows():
        raw_code = str(row[config.VENDOR_COL_CODE]).strip().upper()
        key = build_key(raw_code, row.get('VENDOR_EXTRA', ""), row.get('VENDOR_REMARK', ""))

        if key not in vendor_dict:
            vendor_dict[key] = {col: 0.0 for col in drawing_columns}

        for col in drawing_columns:
            if pd.notnull(row.get(col)):
                vendor_dict[key][col] = round(vendor_dict[key][col] + safe_float(row.get(col, 0)), 2)

        if raw_code not in vendor_code_details:
            vendor_code_details[raw_code] = {}
        vendor_code_details[raw_code][key] = vendor_dict[key]

    # 2. Gom nhóm dữ liệu AI
    ai_group_totals = {}
    for _, row in df_ai.iterrows():
        key = build_key(row['SDAC Code'], row.get('Phụ trội', ""), row.get('Remark', ""))
        if key not in ai_group_totals:
            ai_group_totals[key] = {col: 0.0 for col in drawing_columns}
        for col in drawing_columns:
            ai_group_totals[key][col] = round(ai_group_totals[key][col] + safe_float(row.get(col, 0)), 2)

    df_ai['Note'] = ""
    error_cells = []

    # 3. Tiến hành đối soát chi tiết từng dòng
    for index, row in df_ai.iterrows():
        code = str(row['SDAC Code']).strip().upper()
        key = build_key(code, row.get('Phụ trội', ""), row.get('Remark', ""))
        _, ai_e, ai_r = key
        reconcile_logs = []

        if code not in vendor_code_details:
            reconcile_logs.append("Mã mồ côi (Chỉ có ở bản vẽ)")
            error_cells.append(f"ROW:{index + 2}")
        elif key not in vendor_dict:
            ai_cond_str = format_cond_label(ai_e, ai_r)
            ven_variants = []
            for (_, ve, vr), v_drawings in vendor_code_details[code].items():
                v_tot = sum(v_drawings.values())
                ven_variants.append(f"{format_cond_label(ve, vr)} (Tổng={v_tot})")
            v_desc = "; ".join(ven_variants)
            reconcile_logs.append(f"Không khớp điều kiện: AI [{ai_cond_str}] vs Vendor [{v_desc}]")
            error_cells.append(f"ROW:{index + 2}")
        else:
            vendor_row_data = vendor_dict[key]
            for col_name in drawing_columns:
                total_ai_qty = ai_group_totals[key][col_name]
                vendor_qty = vendor_row_data.get(col_name, 0.0)

                if total_ai_qty != vendor_qty:
                    if (use_extra or use_remark) and vendor_qty == 0.0:
                        ai_cond_str = format_cond_label(ai_e, ai_r)
                        ven_variants = []
                        for (_, ve, vr), v_drawings in vendor_code_details[code].items():
                            v_val = v_drawings.get(col_name, 0.0)
                            if v_val > 0:
                                ven_variants.append(f"{format_cond_label(ve, vr)}={v_val}")
                        if ven_variants:
                            reconcile_logs.append(f"Lệch BV {col_name} (AI [{ai_cond_str}]:{total_ai_qty} | Vendor ở nhánh khác: {', '.join(ven_variants)})")
                        else:
                            reconcile_logs.append(f"Lệch BV {col_name} (AI:{total_ai_qty} | Ven:{vendor_qty})")
                    else:
                        reconcile_logs.append(f"Lệch BV {col_name} (AI:{total_ai_qty} | Ven:{vendor_qty})")

                    col_idx = df_ai.columns.get_loc(col_name) + 1
                    error_cells.append((index + 2, col_idx))

        df_ai.at[index, 'Note'] = " | ".join(reconcile_logs)

    # 4. Lấy kết quả Vòng 2 Gate Pass
    df_gp_report, gp_error_rows = None, []
    if dict_gatepass:
        df_gp_report, gp_error_rows = build_gate_pass_reconciliation_df(df_ai, drawing_columns, dict_gatepass)

    # 5. Xuất ra Excel và áp dụng định dạng cao cấp bằng OpenPyXL
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df_ai.to_excel(writer, sheet_name="1. Đối Soát Bản Vẽ", index=False)
        if df_gp_report is not None and not df_gp_report.empty:
            df_gp_report.to_excel(writer, sheet_name="2. Đối Soát Gate Pass", index=False)

    wb = load_workbook(output_excel_path)
    ws1 = wb["1. Đối Soát Bản Vẽ"]

    red_fill    = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    green_fill  = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    group_fills = [
        PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"), # Cam nhạt
        PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")  # Xanh lục nhạt
    ]
    bold_font   = Font(bold=True)
    center_middle = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # Phát hiện các mã xuất hiện nhiều lần (bị tách dòng do Phụ trội / Remark)
    code_counts = df_ai['SDAC Code'].astype(str).str.strip().value_counts()
    duplicated_codes = set(code_counts[code_counts > 1].index)

    code_color_map = {}
    color_toggle = 0
    for code in df_ai['SDAC Code'].astype(str).str.strip():
        if code in duplicated_codes and code not in code_color_map:
            code_color_map[code] = group_fills[color_toggle % len(group_fills)]
            color_toggle += 1

    note_col_idx = df_ai.columns.get_loc('Note') + 1

    # Format Sheet 1
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

    # Bôi đỏ các ô bị lệch
    for err in error_cells:
        if isinstance(err, str) and err.startswith("ROW:"):
            row_idx = int(err.split(":")[1])
            for col_idx in range(1, len(df_ai.columns) + 1):
                ws1.cell(row=row_idx, column=col_idx).fill = red_fill
        else:
            r_idx, c_idx = err
            ws1.cell(row=r_idx, column=c_idx).fill = red_fill
            ws1.cell(row=r_idx, column=note_col_idx).fill = red_fill

    # Tự động căn chỉnh độ rộng cột và chiều cao hàng (Auto-fit chuẩn layout excel2)
    auto_fit_columns_and_rows(ws1)

    # Format Sheet 2: Đối soát Gate Pass
    if "2. Đối Soát Gate Pass" in wb.sheetnames and df_gp_report is not None:
        ws2 = wb["2. Đối Soát Gate Pass"]
        gp_float_cols = [6, 7, 8, 9, 10]

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

                if is_err_row:
                    cell.fill = red_fill
                elif col_idx == 11 and cell.value == "✅ Khớp 100%":
                    cell.fill = green_fill

        auto_fit_columns_and_rows(ws2)

    wb.save(output_excel_path)
    print(f"✅ Hoàn tất! Báo cáo Final (2 Sheet) lưu tại: {output_excel_path}")
    return output_excel_path


# ==============================================================================
# KHỐI 6. HÀM CHẠY TOÀN BỘ TIẾN TRÌNH TỪ TERMINAL (CLI RUNNER)
# ==============================================================================
def run_reconciliation_pipeline():
    """Khởi chạy quy trình đối soát Vòng 1 và Vòng 2 độc lập qua Terminal."""
    vendor_excel_path = os.path.join(config.DIR_VENDOR_EXCEL, config.VENDOR_FILE_NAME)
    master_data_path  = os.path.join(config.DIR_VENDOR_EXCEL, config.MASTER_DATA_FILE_NAME)

    print("\n" + "="*60)
    print("🚀 KHỞI ĐỘNG HỆ THỐNG ĐỐI SOÁT TỰ ĐỘNG (PIPELINE VÒNG 1 + VÒNG 2)")
    print("="*60)

    # 1. Gom nhóm bản vẽ AI
    df_ai, drawing_names = aggregate_ai_data(config.DIR_CSV_EXTRACTED)

    # 2. Đọc file Vendor bằng radar
    df_vendor = load_vendor_data_dynamic(vendor_excel_path, config.VENDOR_SHEET_NAME, drawing_names)

    # 3. Tra cứu thông tin Master Data
    df_ai_master = format_master_report(df_ai, master_data_path, config.MASTER_DATA_SHEET_NAME)

    # 4. Gom nhóm Gate Pass
    dict_gatepass = aggregate_gate_pass_data(config.DIR_GATEPASS_CSV)

    # 5. Đối soát và xuất file báo cáo hoàn chỉnh
    reconcile_and_highlight(df_ai_master, df_vendor, drawing_names, dict_gatepass, config.OUTPUT_FINAL_EXCEL)


if __name__ == "__main__":
    run_reconciliation_pipeline()
