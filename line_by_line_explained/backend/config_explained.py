# ==============================================================================
# TẬP TIN CẤU HÌNH HỆ THỐNG - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/config.py
# ==============================================================================

# Dòng 1-3: Nhúng thư viện hệ điều hành tiêu chuẩn os để thao tác với đường dẫn thư mục và biến môi trường
import os

# ==============================================================================
# KHỐI 1: CẤU HÌNH API & AI MODEL (NextAI-SDV)
# ==============================================================================

# Dòng 10: Địa chỉ URL của cổng suy luận AI Vision (OpenAI-compatible) chạy trong mạng nội bộ công ty.
# os.getenv cho phép ghi đè bằng biến môi trường khi deploy lên server container.
API_URL = os.getenv("MEP_API_URL", "http://107.126.11.129:32200/api/v1/chat/completions")

# Dòng 14: Mã khóa bí mật (API Key) để xác thực quyền truy cập vào cổng AI NextAI.
API_KEY = os.getenv("MEP_API_KEY", "sk-pEqadpi8UZjOr2RWUTdXliuxXcTFVc-dezojIsgbJ0Y")

# Dòng 17: Tên mô hình AI Vision được cấu hình trên cụm vLLM / NextAI nội bộ.
MODEL_NAME = os.getenv("MEP_MODEL_NAME", "NextAI-SDV")

# Dòng 20: Nhiệt độ sáng tạo của AI = 0.0 nhằm triệt tiêu tối đa tính ngẫu nhiên (Zero Hallucination),
# bắt buộc mô hình chỉ trích xuất dữ liệu thực tế nhìn thấy trong ảnh.
TEMPERATURE = 0.0

# Dòng 24: Số lần thử lại tối đa (Max retries) nếu việc gọi API bị gián đoạn mạng hoặc quá tải.
MAX_RETRIES = 3

# Dòng 27: Số luồng gửi ảnh song song tối đa lên AI. Đặt là 5 để cân bằng giữa tốc độ (~33s/file)
# và không làm nghẽn hàng đợi (queue) của AI Server công ty.
MAX_AI_WORKERS = 5

# ==============================================================================
# KHỐI 2: CẤU HÌNH XỬ LÝ ẢNH & THỊ GIÁC MÁY TÍNH (OPENCV)
# ==============================================================================

# Dòng 35: Chất lượng nén ảnh JPEG (1-100). Đặt 85% để ảnh bằng chứng sắc nét nhưng dung lượng siêu nhẹ (~150KB/ảnh).
JPEG_QUALITY = 85

# Dòng 38: Chiều cao tối đa (pixel) của một khúc cắt ảnh (chunk).
# Nếu bảng cao hơn 150px, hệ thống sẽ tự động băm nhỏ để AI không bị đọc sót chữ li ti.
MAX_CHUNK_HEIGHT = 150

# Dòng 42: Chiều cao chuẩn khi scale phóng to khúc ảnh trước khi gửi AI để mô hình dễ nhận diện chữ.
TARGET_IMG_HEIGHT = 600

# Dòng 45: Chốt chặn chiều ngang tối đa (pixel) để tránh gửi ảnh quá khổ làm tràn VRAM của máy chủ AI.
MAX_IMG_WIDTH = 6000

# Dòng 48: Cờ OLE_FAST_MODE:
# - True: Ưu tiên bóc tách ngay khối ảnh nhúng index [1] của bản vẽ CAD dán OLE (tăng tốc độ gấp 3 lần).
# - False: Quét toàn bộ các ảnh nhúng và chấm điểm mật độ đường kẻ ngang.
OLE_FAST_MODE = True

# Dòng 53: Tọa độ vùng chữ nhật (ROI) ở góc dưới bên phải trang bản vẽ chứa khung tên "SỐ BẢN VẼ".
# Định dạng tỷ lệ phần trăm: (X_bắt_đầu: 70%, Y_bắt_đầu: 85%, X_kết_thúc: 100%, Y_kết_thúc: 100%).
ROI_DRAWING_NO = (0.7, 0.85, 1.0, 1.0)

# ==============================================================================
# KHỐI 3: CẤU HÌNH ĐƯỜNG DẪN THƯ MỤC LƯU TRỮ
# ==============================================================================

# Dòng 61: Lấy đường dẫn tuyệt đối tới thư mục chứa file config.py hiện tại.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dòng 64-66: Các thư mục đầu vào PDF (dùng khi chạy test CLI độc lập)
DIR_PDF_INPUT    = os.path.join(BASE_DIR, "data", "input_pdf")
DIR_PDF_DRAWINGS = os.path.join(BASE_DIR, "data", "input_pdf", "drawings")
DIR_PDF_GATEPASS = os.path.join(BASE_DIR, "data", "input_pdf", "gate_pass")

# Dòng 69-72: Các thư mục lưu trữ file trung gian (ảnh bằng chứng, file CSV bóc tách, báo cáo final)
DIR_IMG_EXTRACTED = os.path.join(BASE_DIR, "data", "output", "images")
DIR_CSV_EXTRACTED = os.path.join(BASE_DIR, "data", "output", "extracted_csv")
DIR_GATEPASS_CSV  = os.path.join(BASE_DIR, "data", "output", "gatepass_csv")
DIR_FINAL_REPORT  = os.path.join(BASE_DIR, "data", "output", "final_reports")

# Dòng 75-80: Tự động tạo các thư mục này nếu chúng chưa tồn tại trên ổ cứng.
for folder in [
    DIR_PDF_INPUT, DIR_PDF_DRAWINGS, DIR_PDF_GATEPASS,
    DIR_IMG_EXTRACTED, DIR_CSV_EXTRACTED, DIR_GATEPASS_CSV,
    DIR_FINAL_REPORT
]:
    os.makedirs(folder, exist_ok=True)

# ==============================================================================
# KHỐI 4: TỪ KHÓA ĐỊNH VỊ SHEET & CỘT DỮ LIỆU
# ==============================================================================

# Dòng 87: Tên Sheet chứa bảng kê khai khối lượng thanh toán của nhà thầu (Vendor).
VENDOR_SHEET_NAME = "3.Bảng khối lượng"

# Dòng 90-92: Tên tiêu đề các cột cần radar quét tìm trên file Vendor.
VENDOR_COL_CODE   = "Code"
VENDOR_COL_EXTRA  = "Phụ trội"
VENDOR_COL_REMARK = "Remark"

# Dòng 95: Tên Sheet Master Data chứa đơn giá và mô tả vật tư (thường là Sheet BOQ trong cùng file Excel).
MASTER_SHEET_NAME = "BOQ"

# Dòng 98-106: Bảng ánh xạ (Mapping) giữa tên cột chuẩn của hệ thống và tên cột thực tế trên file BOQ.
MASTER_COL_MAP = {
    "Code_Master":         "Code SDAC vật tư",
    "SDAC Code nhân công": "Code SDAC nhân công",
    "Description":         "Description",
    "Specification":       "Specification",
    "Unit":                "Unit",
    "Material Cost":       "Material Cost",
    "Labor Cost":          "Labor Cost"
}

# Dòng 109-110: Danh sách từ khóa để nhận diện Sheet nào chứa PDF Bản vẽ CAD và Sheet nào chứa Gate Pass.
SHEET_KEYWORDS_DRAWING  = ['bản vẽ', 'ban ve', 'drawing', 'bv']
SHEET_KEYWORDS_GATEPASS = ['bbgn', 'gate', 'mang vào', 'biên bản']

# Dòng 113: Cờ bỏ qua CSV đã có. Mặc định False để luôn luôn bóc tách mới mỗi khi có request từ Web.
SKIP_EXTRACTED_CSV = False

