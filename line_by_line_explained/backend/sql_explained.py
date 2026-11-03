# ==============================================================================
# THAO TÁC CƠ SỞ DỮ LIỆU ORACLE - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/sql.py
# ==============================================================================

# Dòng 1-10: Nhúng các thư viện nền tảng và nạp biến môi trường
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv # find_dotenv tự động quét file .env từ thư mục hiện tại lên gốc

# Dòng 11: Nạp tất cả thông số kết nối từ file .env vào os.environ
load_dotenv(find_dotenv())

# ==============================================================================
# CẤU HÌNH THÔNG SỐ DATABASE THEO QUY CHUẨN CÔNG TY (YMS / ONEAI)
# ==============================================================================
# Dòng 17-19: Tài khoản YMS cơ bản được cấu hình trên server
DB_USER_YMS = os.getenv("DB_USER_YMS")
DB_PASSWORD_YMS = os.getenv("DB_PASSWORD_YMS")
TNS_YMS = os.getenv("TNS_YMS")

# Dòng 22-25: Tài khoản chuyên dụng cho hệ thống OneAI Local AI (LOCAL_AI)
# Ưu tiên lấy tài khoản AI, nếu không có sẽ dùng tài khoản YMS hoặc fallback mặc định
DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI") or DB_USER_YMS or os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI") or DB_PASSWORD_YMS or os.getenv("DB_PASSWORD", "")
DNS_NAME = os.getenv("DB_SERVICE") or TNS_YMS or "MBAYMS"
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")

# Dòng 28-33: Kiểm tra xem có thư viện OneAI nội bộ công ty (oneai_sdv) hay không
# Thư viện này có sẵn khi deploy trên hạ tầng container của OneAI
try:
    from oneai_sdv import oracle_conn, result_type
    HAS_ONEAI_SDV = True
except ImportError:
    oracle_conn = None
    HAS_ONEAI_SDV = False

import oracledb

# ==============================================================================
# KHỞI TẠO ORACLE THICK CLIENT (NẾU CÓ INSTANT CLIENT)
# ==============================================================================
# Dòng 41-55: oracledb cần khởi tạo Thick Client khi kết nối qua TNS alias công ty
# Biến cờ _oracle_client_initialized ngăn ngừa lỗi gọi lặp lại init_oracle_client nhiều lần
_oracle_client_initialized = False

def init_oracle_client():
    """Khởi tạo Oracle Thick Client một lần duy nhất."""
    global _oracle_client_initialized
    if _oracle_client_initialized:
        return
    client_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    if client_dir and os.path.exists(client_dir):
        try:
            oracledb.init_oracle_client(lib_dir=client_dir)
            _oracle_client_initialized = True
            print(f"✅ [Oracle] Khởi tạo Thick Client thành công: {client_dir}")
        except Exception as e:
            _oracle_client_initialized = True
            print(f"ℹ️ [Oracle Thick Client Note] {e}")

# ==============================================================================
# HÀM KẾT NỐI NATIVE ORACLEDB (KHI KHÔNG CÓ THƯ VIỆN ONEAI_SDV)
# ==============================================================================
# Dòng 61-90: Mở kết nối trực tiếp bằng oracledb sử dụng DSN (MBAYMS / TNS_YMS)
def get_native_conn():
    """Tạo kết nối trực tiếp bằng oracledb (Hỗ trợ DSN / TNS_YMS hoặc Host:Port)."""
    init_oracle_client()
    user = DB_USER_YMS_AI
    password = DB_PASSWORD_YMS_AI
    dsn_target = TNS_YMS or DNS_NAME
    errors = []

    # Ưu tiên kết nối qua DSN / TNS Names (Chuẩn hệ thống công ty)
    if dsn_target:
        try:
            return oracledb.connect(user=user, password=password, dsn=dsn_target)
        except Exception as e1:
            errors.append(f"DSN '{dsn_target}': {e1}")

    # Fallback kết nối qua host/port nếu có cấu hình
    host = os.getenv("DB_HOST")
    if host:
        try:
            port = int(os.getenv("DB_PORT", 1521))
            return oracledb.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                service_name=DNS_NAME
            )
        except Exception as e2:
            errors.append(f"Host '{host}': {e2}")

    # Nếu tất cả kết nối thất bại, bắn Exception thật sự (Không giấu lỗi bằng Mock giả)
    error_summary = " | ".join(errors) if errors else "Thiếu thông tin kết nối DB trong .env"
    raise RuntimeError(f"Lỗi kết nối Oracle Database ({error_summary})")

# ==============================================================================
# BỘ THỰC THI DML ĐA NĂNG (DÙNG ĐƯỢC CẢ ONEAI_SDV VÀ NATIVE ORACLEDB)
# ==============================================================================
# Dòng 96-140: Thực thi câu lệnh đơn (UPDATE/DELETE/INSERT)
def execute_dml(sql: str, params: dict = None):
    """Thực thi câu lệnh DML đơn lẻ (UPDATE / DELETE / INSERT)."""
    if params is None:
        params = {}

    # ƯU TIÊN 1: Sử dụng thư viện nội bộ OneAI SDV (chuẩn như sếp/đồng nghiệp đang dùng)
    if HAS_ONEAI_SDV and oracle_conn is not None:
        try:
            try:
                cur = oracle_conn(
                    dns=DNS_NAME,
                    user_name=DB_USER_YMS_AI,
                    password=DB_PASSWORD_YMS_AI,
                    oracle_client_dir=oracle_client_path,
                )
            except TypeError:
                cur = oracle_conn(
                    dsn=DNS_NAME,
                    user_name=DB_USER_YMS_AI,
                    password=DB_PASSWORD_YMS_AI,
                    oracle_client_dir=oracle_client_path,
                )

            cur.execute(sql, params)

            # Đảm bảo commit dữ liệu xuống đĩa cứng DB
            if hasattr(cur, "connection") and cur.connection:
                try: cur.connection.commit()
                except Exception: pass
            elif hasattr(cur, "commit"):
                try: cur.commit()
                except Exception: pass

            if hasattr(cur, "close"):
                try: cur.close()
                except Exception: pass
            return
        except Exception as e:
            print(f"⚠️ [OneAI SDV Error] {e}. Tự động chuyển sang kết nối trực tiếp oracledb...")

    # ƯU TIÊN 2: Dùng oracledb native
    conn = get_native_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Dòng 145-195: Thực thi một danh sách lệnh DML trong cùng 1 Transaction (Merge/Batch Delete)
def execute_dml_batch(sql: str, params_list: list) -> int:
    """Thực thi danh sách lệnh DML trong 1 transaction an toàn."""
    if not params_list:
        return 0

    if HAS_ONEAI_SDV and oracle_conn is not None:
        try:
            try:
                cur = oracle_conn(
                    dns=DNS_NAME,
                    user_name=DB_USER_YMS_AI,
                    password=DB_PASSWORD_YMS_AI,
                    oracle_client_dir=oracle_client_path,
                )
            except TypeError:
                cur = oracle_conn(
                    dsn=DNS_NAME,
                    user_name=DB_USER_YMS_AI,
                    password=DB_PASSWORD_YMS_AI,
                    oracle_client_dir=oracle_client_path,
                )

            for p in params_list:
                cur.execute(sql, p)

            if hasattr(cur, "connection") and cur.connection:
                try: cur.connection.commit()
                except Exception: pass
            elif hasattr(cur, "commit"):
                try: cur.commit()
                except Exception: pass

            if hasattr(cur, "close"):
                try: cur.close()
                except Exception: pass
            return len(params_list)
        except Exception as e:
            print(f"⚠️ [OneAI SDV Batch Error] {e}. Tự động chuyển sang kết nối trực tiếp oracledb...")

    conn = get_native_conn()
    cursor = conn.cursor()
    try:
        for p in params_list:
            cursor.execute(sql, p)
        conn.commit()
        return len(params_list)
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# CÁC NGHIỆP VỤ DATABASE PHỤC VỤ MEP PAYMENT
# ==============================================================================
def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """Cập nhật trạng thái công việc (WAITING, RUNNING, COMPLETED, CANCEL) vào DB."""
    sql = """
        UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
        SET STATUS       = :STATUS,
            ERROR_COUNT  = :ERROR_COUNT,
            RESULT_LINK  = :RESULT_LINK,
            REASON       = :REASON,
            RESULT_TIME  = CASE WHEN :STATUS IN ('COMPLETED', 'CANCEL') THEN SYSDATE ELSE RESULT_TIME END,
            UPLOAD_TIME  = CASE WHEN :STATUS = 'WAITING' THEN SYSDATE ELSE UPLOAD_TIME END
        WHERE KEYID = :KEYID
    """
    params = {
        "STATUS": status,
        "ERROR_COUNT": error_count,
        "RESULT_LINK": result_link,
        "REASON": reason,
        "KEYID": str(keyid).strip()
    }
    execute_dml(sql, params)

def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    """Cập nhật quyết định phê duyệt (Approve / Reject) của kỹ sư vào DB."""
    sql = """
        UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
        SET REVIEW_DECISION = :DECISION,
            REVIEW_NOTE     = :NOTE,
            REVIEW_BY       = :REVIEWER
        WHERE KEYID = :KEYID
    """
    params = {
        "DECISION": decision,
        "NOTE": note,
        "REVIEWER": reviewer,
        "KEYID": str(keyid).strip()
    }
    execute_dml(sql, params)

def batch_upsert_tasks(rows: list) -> int:
    """MERGE INTO bảng MEP_PAYMENT_ANALYSIS (Hỗ trợ cả Insert dòng mới & Update dòng cũ)."""
    if not rows:
        return 0

    sql = """
        MERGE INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS T
        USING (
            SELECT :KEYID AS KEYID,
                   :TASK_NAME AS TASK_NAME,
                   :PAYMENT_MONTH AS PAYMENT_MONTH,
                   :PIC AS PIC,
                   :PART_NAME AS PART_NAME,
                   :GROUP_NAME AS GROUP_NAME,
                   :STATUS AS STATUS
            FROM DUAL
        ) S
        ON (T.KEYID = S.KEYID)
        WHEN MATCHED THEN
            UPDATE SET T.TASK_NAME     = S.TASK_NAME,
                       T.PAYMENT_MONTH = S.PAYMENT_MONTH,
                       T.PIC           = S.PIC,
                       T.PART_NAME     = S.PART_NAME,
                       T.GROUP_NAME    = S.GROUP_NAME
        WHEN NOT MATCHED THEN
            INSERT (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, UPLOAD_TIME)
            VALUES (S.KEYID, S.TASK_NAME, S.PAYMENT_MONTH, S.PIC, S.PART_NAME, S.GROUP_NAME, S.STATUS, SYSDATE)
    """
    params_list = [
        {
            "KEYID": str(r.get("KEYID", "")).strip(),
            "TASK_NAME": str(r.get("TASK_NAME", "")).strip(),
            "PAYMENT_MONTH": str(r.get("PAYMENT_MONTH", "")).strip(),
            "PIC": str(r.get("PIC", "")).strip(),
            "PART_NAME": str(r.get("PART_NAME", "")).strip(),
            "GROUP_NAME": str(r.get("GROUP_NAME", "")).strip(),
            "STATUS": str(r.get("STATUS", "WAITING")).strip()
        }
        for r in rows
    ]
    return execute_dml_batch(sql, params_list)

def delete_tasks(keyids: list) -> int:
    """Xóa các dòng được chọn khỏi Database theo danh sách KEYID."""
    if not keyids:
        return 0

    sql = "DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params_list = [{"KEYID": str(k).strip()} for k in keyids]
    return execute_dml_batch(sql, params_list)
