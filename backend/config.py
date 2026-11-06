# ==========================================
# CẤU HÌNH HỆ THỐNG MEP AI (CONFIG)
# ==========================================
import os

# 1. CẤU HÌNH API & AI MODEL (NextAI-SDV)
API_URL = os.getenv(
    "MEP_API_URL", "http://107.126.11.129:32200/api/v1/chat/completions")
API_KEY = os.getenv(
    "MEP_API_KEY", "sk-pEqadpi8UZjOr2RWUTdXliuxXcTFVc-dezojIsgbJ0Y")
MODEL_NAME = os.getenv("MEP_MODEL_NAME", "NextAI-SDV")
TEMPERATURE = 0.0
MAX_RETRIES = 3
MAX_AI_WORKERS = 5          # Số luồng gọi AI song song tối đa

# ==========================================
# 2. CẤU HÌNH XỬ LÝ & CẮT ẢNH (OPENCV)
# ==========================================
JPEG_QUALITY = 100          # Chất lượng nén ảnh JPG gửi lên AI (1-100)
MAX_CHUNK_HEIGHT = 150      # Chiều cao tối đa của 1 khúc ảnh cắt ngang (px)
TARGET_IMG_HEIGHT = 600     # Chiều cao mục tiêu khi phóng to khúc ảnh cho AI đọc
MAX_IMG_WIDTH = 6000        # Chốt chặn chiều ngang tối đa tránh quá tải Server

# Chế độ lấy ảnh nhúng OLE (Case 1):
# - True: Ưu tiên kiểm tra thẳng image[1] siêu tốc, nếu không phải bảng mới quét toàn trang.
# - False: Luôn quét và chấm điểm đường kẻ ngang cho toàn bộ ảnh nhúng.
OLE_FAST_MODE = True

# Tọa độ vùng cắt (ROI) góc dưới bên phải để đọc "SỐ BẢN VẼ" (Drawing No)
# Định dạng: (X_start, Y_start, X_end, Y_end) tính theo tỷ lệ phần trăm (0.0 -> 1.0)
ROI_DRAWING_NO = (0.7, 0.85, 1.0, 1.0)

# ==========================================
# 3. CẤU HÌNH ĐƯỜNG DẪN THƯ MỤC
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- THƯ MỤC ĐẦU VÀO PDF (HỖ TRỢ CẢ 2 CHẾ ĐỘ VẬN HÀNH) ---
# Cách 1 (Thả chung): Thả tất cả PDF vào DIR_PDF_INPUT, hệ thống tự đọc Text phân loại Bản vẽ vs Gate Pass.
# Cách 2 (Tách riêng / Web Server): Bỏ Bản vẽ vào DIR_PDF_DRAWINGS, bỏ Gate Pass vào DIR_PDF_GATEPASS.
DIR_PDF_INPUT = os.path.join(BASE_DIR, "input_pdf")
DIR_PDF_DRAWINGS = os.path.join(BASE_DIR, "input_pdf", "drawings")
DIR_PDF_GATEPASS = os.path.join(BASE_DIR, "input_pdf", "gate_pass")

# --- THƯ MỤC LƯU TRỮ TRUNG GIAN (IMAGES & CSV) ---
DIR_IMG_EXTRACTED = os.path.join(BASE_DIR, "output", "images")
DIR_CSV_EXTRACTED = os.path.join(
    BASE_DIR, "output", "extracted_csv")   # Lưu CSV của Bản vẽ CAD
# Lưu CSV của Biên bản vật tư (Gate Pass)
DIR_GATEPASS_CSV = os.path.join(BASE_DIR, "output", "gatepass_csv")

# --- THƯ MỤC CHỨA DỮ LIỆU EXCEL THỰC TẾ & BÁO CÁO ĐẦU RA ---
DIR_VENDOR_EXCEL = r"D:/Private_Documents/Doc/AI-Infra"
DIR_FINAL_REPORT = r"D:/Private_Documents/Doc/AI-Infra/FinalReport"

# Tự động tạo toàn bộ thư mục nếu chưa tồn tại
for folder in [
    DIR_PDF_INPUT, DIR_PDF_DRAWINGS, DIR_PDF_GATEPASS,
    DIR_IMG_EXTRACTED, DIR_CSV_EXTRACTED, DIR_GATEPASS_CSV,
    DIR_VENDOR_EXCEL, DIR_FINAL_REPORT
]:
    os.makedirs(folder, exist_ok=True)

# ==========================================
# 4. CẤU HÌNH FILE VENDOR (BẢNG KHỐI QLƯỢNG)
# ==========================================
VENDOR_FILE_NAME = "Sample 3. 03.PAYMENT WOR2512230006V.xlsx"
VENDOR_SHEET_NAME = "3.Bảng khối lượng"
VENDOR_COL_CODE = "Code"
VENDOR_COL_EXTRA = "Phụ trội"
VENDOR_COL_REMARK = "Remark"

# ==========================================
# 5. CẤU HÌNH FILE MAPPING (SHEET BOQ TRONG FILE THANH TOÁN)
# ==========================================
MASTER_DATA_FILE_NAME = "Sample 3. 03.PAYMENT WOR2512230006V.xlsx"
MASTER_SHEET_NAME = "BOQ"

# Từ điển ánh xạ cột chuẩn của hệ thống (Bên trái) với tên cột thực tế trên sheet BOQ (Bên phải)
MASTER_COL_MAP = {
    # Cột chứa SDAC Code dùng để dò tìm
    "Code_Master":         "Code SDAC vật tư",
    "SDAC Code nhân công": "Code SDAC nhân công",
    "Description":         "Description",
    "Specification":       "Specification",
    "Unit":                "Unit",
    "Material Cost":       "Material Cost",         # Cột chứa Đơn giá vật tư
    "Labor Cost":          "Labor Cost"             # Cột chứa Đơn giá nhân công
}

# ==========================================
# CẤU HÌNH TỪ KHÓA TÌM SHEET CHỨA PDF
# ==========================================
SHEET_KEYWORDS_DRAWING = ['bản vẽ', 'ban ve', 'drawing', 'bv']
SHEET_KEYWORDS_GATEPASS = ['bbgn', 'gate', 'mang vào', 'biên bản']

# ==========================================
# 6. CẤU HÌNH VẬN HÀNH PIPELINE & GIỚI HẠN UPLOAD
# ==========================================
# True: File nào đã có sẵn .csv thì bỏ qua không gọi lại AI
SKIP_EXTRACTED_CSV = False
# Giới hạn dung lượng file Excel upload tối đa (MB)
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 50))
