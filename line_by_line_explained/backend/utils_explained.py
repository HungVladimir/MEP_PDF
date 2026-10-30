# ==============================================================================
# CÔNG CỤ PHỤ TRỢ - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/utils.py
# ==============================================================================

# Dòng 1-3: Nhúng thư viện unicodedata để chuẩn hóa ký tự Unicode và re để xử lý biểu thức chính quy (Regex).
import unicodedata
import re

def clean_vietnamese_filename(text):
    """
    HÀM CHUẨN HÓA TÊN FILE TIẾNG VIỆT
    Mục đích: Chuyển tên file hoặc tên sheet tiếng Việt có dấu thành dạng không dấu,
    thay khoảng trắng bằng dấu gạch dưới và loại bỏ các ký tự cấm của hệ điều hành Windows.
    Giúp tránh 100% lỗi crash thư viện OpenCV và đường dẫn file bị đứt gãy.
    """
    # Dòng 13: Nếu text truyền vào bị rỗng hoặc None, trả về chuỗi mặc định "Unknown".
    if not text:
        return "Unknown"

    # Dòng 17: BƯỚC 1: Xóa dấu tiếng Việt
    # unicodedata.normalize('NFKD', ...): Tách các ký tự có dấu thành ký tự gốc + dấu rời.
    # encode('ASCII', 'ignore'): Bỏ qua toàn bộ các ký tự dấu không thuộc bảng mã ASCII chuẩn.
    # decode('utf-8'): Chuyển mảng byte trở lại thành chuỗi chuỗi ký tự ASCII thuần túy.
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')

    # Dòng 23: BƯỚC 2: Loại bỏ các ký tự bị cấm bởi hệ thống file Windows
    # Các ký tự cấm gồm: gạch chéo ngược (\), gạch chéo (/), dấu sao (*), dấu hỏi (?),
    # hai chấm (:), ngoặc kép ("), dấu bé (<), dấu lớn (>), dấu sổ đứng (|).
    text = re.sub(r'[\\/*?:"<>|]', "", text)

    # Dòng 28: BƯỚC 3: Thay khoảng trắng bằng dấu gạch dưới và cắt bỏ dấu gạch dưới ở 2 đầu
    text = text.replace(" ", "_").strip("_")

    # Dòng 31: Trả về chuỗi tên file an toàn cho hệ thống.
    return text

