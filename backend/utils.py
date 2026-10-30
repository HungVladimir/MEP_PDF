# ==========================================
# CÔNG CỤ PHỤ TRỢ (UTILS)
# ==========================================
import unicodedata
import re

def clean_vietnamese_filename(text):
    """
    Xóa dấu tiếng Việt, thay khoảng trắng bằng dấu gạch dưới,
    xóa các ký tự cấm của Windows file system để tránh crash OpenCV/OS.
    """
    if not text:
        return "Unknown"
    # 1. Bỏ dấu Tiếng Việt
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    # 2. Xóa các ký tự cấm của Windows file system
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    # 3. Thay khoảng trắng bằng gạch dưới
    text = text.replace(" ", "_").strip("_")
    return text

