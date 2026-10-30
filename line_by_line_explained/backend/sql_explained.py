# ==============================================================================
# THAO TÁC CƠ SỞ DỮ LIỆU ORACLE - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/sql.py
# ==============================================================================

# Dòng 1-2: Nhúng thư viện chính chủ Oracle (oracledb) và os
import oracledb   # Thư viện Python mới nhất của Oracle, chạy chế độ Thin Mode không cần cài Oracle Client
import os         # Đọc các thông số tài khoản và mật khẩu từ biến môi trường

# ==============================================================================
# CẤU HÌNH KẾT NỐI DATABASE ORACLE
# ==============================================================================

# Dòng 12-16: Khai báo 5 thông số cơ bản để nối vào Oracle DB của công ty
# - DB_USER: Tên Schema (ở đây là LOCAL_AI)
# - DB_PASSWORD: Mật khẩu truy cập
# - DB_HOST: Địa chỉ IP của máy chủ Database Oracle
# - DB_PORT: Cổng dịch vụ Oracle mặc định là 1521
# - DB_SERVICE: Service Name (Tên dịch vụ DB, ví dụ MBAYMS)
DB_USER     = os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mat_khau_db")
DB_HOST     = os.getenv("DB_HOST", "107.126.xx.xx")
DB_PORT     = int(os.getenv("DB_PORT", 1521))
DB_SERVICE  = os.getenv("DB_SERVICE", "MBAYMS")

def get_connection():
    """
    HÀM KHỞI TẠO KẾT NỐI ORACLE:
    Sử dụng oracledb.connect() để mở một phiên làm việc (Session) với Oracle.
    Nếu kết nối thất bại (do sai mật khẩu, rớt mạng...), hàm sẽ bắt ngoại lệ và trả về None.
    """
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            service_name=DB_SERVICE
        )
        return conn
    except Exception as e:
        print(f"❌ [Oracle DB Error] Không thể kết nối DB: {e}")
        return None

def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """
    HÀM CẬP NHẬT TRẠNG THÁI TIẾN ĐỘ VÀO BẢNG MEP_PAYMENT_ANALYSIS:
    - Khi bắt đầu nạp file: Gọi với status='WAITING' -> UPLOAD_TIME tự động lấy ngày giờ hiện tại (SYSDATE).
    - Khi AI đang bóc tách: Gọi với status='RUNNING' -> Báo cho giao diện OneAI hiển thị 'Đang Xử Lý'.
    - Khi AI chạy xong: Gọi với status='COMPLETED' kèm số lỗi (error_count), link tải file (result_link),
      RESULT_TIME tự động lấy SYSDATE.
    - Khi xảy ra lỗi: Gọi với status='CANCEL' kèm thông báo lỗi (reason) để kỹ sư biết nguyên nhân.
    """
    conn = get_connection()
    if not conn:
        print(f"⚠️ [DB Mock] KEYID={keyid} -> STATUS={status} (Chưa có kết nối DB)")
        return

    cursor = conn.cursor()
    try:
        # Sử dụng tham số có tên (:status, :error_count...) để chống tấn công SQL Injection
        sql = """
            UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
            SET STATUS       = :status,
                ERROR_COUNT  = :error_count,
                RESULT_LINK  = :result_link,
                REASON       = :reason,
                RESULT_TIME  = CASE WHEN :status IN ('COMPLETED', 'CANCEL') THEN SYSDATE ELSE RESULT_TIME END,
                UPLOAD_TIME  = CASE WHEN :status = 'WAITING' THEN SYSDATE ELSE UPLOAD_TIME END
            WHERE KEYID = :keyid
        """
        cursor.execute(sql, {
            "status": status,
            "error_count": error_count,
            "result_link": result_link,
            "reason": reason,
            "keyid": keyid
        })
        conn.commit() # Bắt buộc phải commit để lưu vĩnh viễn thay đổi vào CSDL
        print(f"📊 [Oracle DB] Đã cập nhật KEYID={keyid} -> STATUS={status}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_task_status: {e}")
    finally:
        # Luôn giải phóng cursor và đóng kết nối để chống rò rỉ tài nguyên (Connection Leak)
        cursor.close()
        conn.close()

def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    """
    HÀM LƯU QUYẾT ĐỊNH PHÊ DUYỆT (REVIEW WORKFLOW - TỪ Ý TƯỞNG CỦA SẾP):
    - Khi kỹ sư nghiệm thu kiểm tra xong báo cáo:
      + Bấm Duyệt -> decision='APPROVED'.
      + Bấm Từ chối -> decision='REJECTED'.
    - Ghi nhận tên người duyệt (reviewer) và nội dung giải trình (note) vào Oracle DB.
    """
    conn = get_connection()
    if not conn:
        print(f"⚠️ [DB Mock] Review KEYID={keyid} -> {decision}")
        return

    cursor = conn.cursor()
    try:
        sql = """
            UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
            SET REVIEW_DECISION = :decision,
                REVIEW_NOTE     = :note,
                REVIEW_BY       = :reviewer
            WHERE KEYID = :keyid
        """
        cursor.execute(sql, {
            "decision": decision,
            "note": note,
            "reviewer": reviewer,
            "keyid": keyid
        })
        conn.commit()
        print(f"✅ [Oracle DB] Đã lưu Review cho KEYID={keyid} -> {decision}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_review_decision: {e}")
    finally:
        cursor.close()
        conn.close()

