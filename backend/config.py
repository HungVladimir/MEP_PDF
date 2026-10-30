# ==========================================
# CẤU HÌNH HỆ THỐNG MEP AI (CONFIG)
# ==========================================
import os

# 1. CẤU HÌNH API & AI MODEL (NextAI-SDV)
API_URL = os.getenv("MEP_API_URL", "http://107.126.11.129:32200/api/v1/chat/completions")
API_KEY = os.getenv("MEP_API_KEY", "sk-pEqadpi8UZjOr2RWUTdXliuxXcTFVc-dezojIsgbJ0Y")
MODEL_NAME = os.getenv("MEP_MODEL_NAME", "NextAI-SDV")
TEMPERATURE = 0.0
MAX_RETRIES = 3
MAX_AI_WORKERS = 5          # Số luồng gọi AI song song tối đa

# 2. CẤU HÌNH XỬ LÝ & CẮT ẢNH (OPENCV)
JPEG_QUALITY = 85           # Chất lượng nén ảnh JPG lưu bằng chứng (85% giúp tối ưu dung lượng)
MAX_CHUNK_HEIGHT = 150      # Chiều cao tối đa của 1 khúc ảnh cắt ngang (px)
TARGET_IMG_HEIGHT = 600     # Chiều cao mục tiêu khi phóng to khúc ảnh cho AI đọc
MAX_IMG_WIDTH = 6000        # Chốt chặn chiều ngang tối đa tránh quá tải Server
OLE_FAST_MODE = True        # Ưu tiên kiểm tra nhanh image[1] cho bản vẽ dán OLE

# Vùng ROI góc dưới bên phải đọc "SỐ BẢN VẼ" (X_start, Y_start, X_end, Y_end: 0.0 -> 1.0)
ROI_DRAWING_NO = (0.7, 0.85, 1.0, 1.0)

# 3. CẤU HÌNH ĐƯỜNG DẪN THƯ MỤC MẶC ĐỊNH (KHI CHẠY STANDALONE CLI)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIR_PDF_INPUT    = os.path.join(BASE_DIR, "data", "input_pdf")
DIR_PDF_DRAWINGS = os.path.join(BASE_DIR, "data", "input_pdf", "drawings")
DIR_PDF_GATEPASS = os.path.join(BASE_DIR, "data", "input_pdf", "gate_pass")

DIR_IMG_EXTRACTED = os.path.join(BASE_DIR, "data", "output", "images")
DIR_CSV_EXTRACTED = os.path.join(BASE_DIR, "data", "output", "extracted_csv")
DIR_GATEPASS_CSV  = os.path.join(BASE_DIR, "data", "output", "gatepass_csv")
DIR_FINAL_REPORT  = os.path.join(BASE_DIR, "data", "output", "final_reports")

# Tự động tạo thư mục mặc định
for folder in [
    DIR_PDF_INPUT, DIR_PDF_DRAWINGS, DIR_PDF_GATEPASS,
    DIR_IMG_EXTRACTED, DIR_CSV_EXTRACTED, DIR_GATEPASS_CSV,
    DIR_FINAL_REPORT
]:
    os.makedirs(folder, exist_ok=True)

# 4. TỪ KHÓA TÌM SHEET TRONG FILE EXCEL THANH TOÁN
VENDOR_SHEET_NAME = "3.Bảng khối lượng"
VENDOR_COL_CODE   = "Code"
VENDOR_COL_EXTRA  = "Phụ trội"
VENDOR_COL_REMARK = "Remark"

MASTER_SHEET_NAME = "BOQ"
MASTER_COL_MAP = {
    "Code_Master":         "Code SDAC vật tư",
    "SDAC Code nhân công": "Code SDAC nhân công",
    "Description":         "Description",
    "Specification":       "Specification",
    "Unit":                "Unit",
    "Material Cost":       "Material Cost",
    "Labor Cost":          "Labor Cost"
}

# Từ khóa quét định vị Sheet chứa PDF nhúng
SHEET_KEYWORDS_DRAWING  = ['bản vẽ', 'ban ve', 'drawing', 'bv']
SHEET_KEYWORDS_GATEPASS = ['bbgn', 'gate', 'mang vào', 'biên bản']

# 5. CỜ ĐIỀU KHIỂN
SKIP_EXTRACTED_CSV = False  # Mặc định trên Web luôn bóc tách mới mỗi lượt

