# ====================================================================
# THAO TÁC CƠ SỞ DỮ LIỆU ORACLE (ORACLE SQL HELPER)
# Dự án: MEP Payment AI - Tích hợp OneAI Portal
# Hỗ trợ cả 2 chuẩn: Thư viện OneAI SDV nội bộ (oracle_conn) & oracledb Thick Client
# ====================================================================
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 1. TỰ ĐỘNG TẢI CẤU HÌNH TỪ .ENV (TÌM TỪ THƯ MỤC HIỆN TẠI LÊN GỐC)
load_dotenv(find_dotenv())

# 2. CẤU HÌNH THÔNG SỐ DATABASE THEO QUY CHUẨN CÔNG TY (YMS / ONEAI)
DB_USER_YMS = os.getenv("DB_USER_YMS")
DB_PASSWORD_YMS = os.getenv("DB_PASSWORD_YMS")
TNS_YMS = os.getenv("TNS_YMS")

# Tài khoản Local AI chuyên dụng (ưu tiên dùng AI, fallback sang YMS hoặc mặc định)
DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI") or DB_USER_YMS or os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI") or DB_PASSWORD_YMS or os.getenv("DB_PASSWORD", "")
DNS_NAME = os.getenv("DB_SERVICE") or TNS_YMS or "MBAYMS"
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")

# 3. KIỂM TRA THƯ VIỆN NỘI BỘ ONEAI SDV
try:
    from oneai_sdv import oracle_conn, result_type
    HAS_ONEAI_SDV = True
except ImportError:
    oracle_conn = None
    HAS_ONEAI_SDV = False

import oracledb

# 4. KHỞI TẠO ORACLE THICK CLIENT (NẾU CÓ ĐƯỜNG DẪN INSTANT CLIENT)
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

# 5. KẾT NỐI ORACLE NATIVE (FALLBACK KHI KHÔNG CÓ ONEAI_SDV)
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

    error_summary = " | ".join(errors) if errors else "Thiếu thông tin kết nối DB trong .env"
    raise RuntimeError(f"Lỗi kết nối Oracle Database ({error_summary})")

# 6. BỘ THỰC THI DML AN TOÀN (DÙNG ĐƯỢC CẢ ONEAI_SDV VÀ NATIVE ORACLEDB)
def execute_dml(sql: str, params: dict = None):
    """Thực thi câu lệnh DML đơn lẻ (UPDATE / DELETE / INSERT)."""
    if params is None:
        params = {}

    # Ưu tiên 1: Sử dụng thư viện nội bộ OneAI SDV
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

    # Ưu tiên 2: Sử dụng thư viện oracledb native
    conn = get_native_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def execute_dml_batch(sql: str, params_list: list) -> int:
    """Thực thi danh sách lệnh DML trong 1 transaction an toàn."""
    if not params_list:
        return 0

    # Ưu tiên 1: Thư viện OneAI SDV
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

    # Ưu tiên 2: Thư viện oracledb native
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

# 7. CÁC NGHIỆP VỤ DATABASE PHỤC VỤ MEP PAYMENT
def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """
    Cập nhật trạng thái công việc vào bảng MEP_PAYMENT_ANALYSIS:
    - status: 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL'
    """
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
    try:
        execute_dml(sql, params)
        print(f"📊 [Oracle DB] Đã cập nhật KEYID={keyid} -> STATUS={status}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_task_status: {e}")
        raise

def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    """Cập nhật quyết định phê duyệt (Approve / Reject) của kỹ sư."""
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
    try:
        execute_dml(sql, params)
        print(f"✅ [Oracle DB] Đã lưu Review cho KEYID={keyid} -> {decision}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_review_decision: {e}")
        raise

def batch_upsert_tasks(rows: list) -> int:
    """
    Thực hiện MERGE INTO để vừa hỗ trợ Insert dòng mới vừa hỗ trợ Update dòng cũ vào Oracle DB.
    Không dùng Mock khi DB gặp lỗi - Báo lỗi trung thực để giao diện hiển thị chính xác.
    """
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
    try:
        count = execute_dml_batch(sql, params_list)
        print(f"✅ [Oracle DB] Đã lưu thành công {count} dòng vào MEP_PAYMENT_ANALYSIS.")
        return count
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi batch_upsert_tasks: {e}")
        raise

def delete_tasks(keyids: list) -> int:
    """Xóa các dòng được chọn khỏi Oracle DB theo danh sách KEYID."""
    if not keyids:
        return 0

    sql = "DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params_list = [{"KEYID": str(k).strip()} for k in keyids]
    try:
        count = execute_dml_batch(sql, params_list)
        print(f"🗑️ [Oracle DB] Đã xóa {count} dòng khỏi MEP_PAYMENT_ANALYSIS.")
        return count
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi delete_tasks: {e}")
        raise
