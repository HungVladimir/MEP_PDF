"""Cấu hình đọc từ biến môi trường."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.abspath(os.getenv("WO_DATA_DIR", os.path.join(BASE_DIR, "data")))
MAX_UPLOAD_MB = int(os.getenv("WO_MAX_UPLOAD_MB", "100"))
# Số workorder xử lý song song trên server
WORKERS = int(os.getenv("WO_WORKERS", "2"))

# User dùng khi chạy thử, khi không có header đăng nhập: "username|Họ tên|role1,role2"
# Để trống khi chạy thật.
DEV_USER = os.getenv("WO_DEV_USER", "")

# Giá trị mặc định của cài đặt (có thể sửa trên giao diện, lưu trong DB)
DEFAULT_SETTINGS = {
    "mock": os.getenv("WO_MOCK", "1") == "1",           # chế độ thử: đọc lớp chữ PDF thay cho AI
    "base_url": os.getenv("AI_BASE_URL", "http://localhost:8000/v1"),
    "model": os.getenv("AI_MODEL", ""),
    "api_key": os.getenv("AI_API_KEY", ""),
    "conc": 2,              # số trang gửi AI song song
    "res": 2000,            # cạnh dài ảnh gửi AI (px)
    "max_tokens": 4096,
    "timeout": 300,         # giây cho mỗi lần gọi AI
    "hint": "",
    "sheet": "",            # tên sheet vật tư (chứa chuỗi); trống = tự nhận diện
    "hdr": 0,               # dòng tiêu đề (1-based); 0 = tự nhận diện
    "code_col": "",         # chữ cột mã vật tư
    "first_col": "",        # chữ cột bản vẽ đầu tiên
    "compare_qty": True,
    "missing_col_is_error": True,
}

os.makedirs(DATA_DIR, exist_ok=True)