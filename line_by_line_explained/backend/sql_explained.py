# ==============================================================================
# THAO TÁC CƠ SỞ DỮ LIỆU ORACLE - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: backend/sql.py
# Chuẩn hóa theo kiến trúc OneAI SDV công ty
# ==============================================================================

# Dòng 1-15: Nhúng các thư viện nền tảng và tải biến môi trường
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Đảm bảo console Windows chạy đúng UTF-8 (không bị lỗi charmap encode khi print)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Dòng 20: Tự động tìm và nạp file .env từ thư mục hiện tại lên thư mục gốc
load_dotenv(find_dotenv())

# ==============================================================================
# CẤU HÌNH THÔNG SỐ DATABASE
# ==============================================================================
# Dòng 26-28: Tài khoản YMS và chuỗi TNS kết nối DB
DB_USER_YMS = os.getenv("DB_USER_YMS")
DB_PASSWORD_YMS = os.getenv("DB_PASSWORD_YMS")
TNS_YMS = os.getenv("TNS_YMS")

# Dòng 31-32: Tài khoản LOCAL_AI thao tác trên bảng MEP_PAYMENT_ANALYSIS
DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI")

# Dòng 34-45: Tự động nhận diện thư mục Oracle Instant Client (Thick Client)
# Hỗ trợ tự động:
# - Trên Dockerfile Linux của OneAI: nhận /opt/oracle/instantclient_23_7 hoặc /service/oracle_client
# - Trên Windows Local: tìm C:\instantclient_19_19 hoặc C:\instantclient_23_7
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")
if not oracle_client_path or not os.path.exists(oracle_client_path):
    if sys.platform == "win32":
        for cand in [r"C:\instantclient_19_19", r"C:\instantclient_23_7", r"C:\instantclient"]:
            if os.path.exists(cand):
                oracle_client_path = cand
                break
        if not oracle_client_path:
            oracle_client_path = r"C:\instantclient_19_19"
    else:
        for cand in ["/opt/oracle/instantclient_23_7", "/service/oracle_client", "/opt/oracle/instantclient_19_19"]:
            if os.path.exists(cand):
                oracle_client_path = cand
                break
        if not oracle_client_path:
            oracle_client_path = "/opt/oracle/instantclient_23_7"

# Dòng 37-43: Kiểm tra sự tồn tại của thư viện nội bộ oneai_sdv
try:
    from oneai_sdv import oracle_conn, result_type
    HAS_ONEAI_SDV = True
except ImportError:
    oracle_conn = None
    HAS_ONEAI_SDV = False

import oracledb

# ==============================================================================
# KHỞI TẠO THICK CLIENT ĐỂ TRÁNH LỖI DPY-3015 (10G VERIFIER)
# ==============================================================================
# Dòng 50-62: Khởi tạo Oracle Client. Nếu thiếu oci.dll, oracledb sẽ chạy ở Thin mode và bị lỗi DPY-3015
_thick_client_ready = False
if oracle_client_path and os.path.exists(oracle_client_path):
    try:
        oracledb.init_oracle_client(lib_dir=oracle_client_path)
        _thick_client_ready = True
        print(f"[Oracle] Da khoi tao Oracle Thick Client: {oracle_client_path}")
    except Exception as e:
        _thick_client_ready = True
        print(f"[Oracle Note] init_oracle_client: {e}")
else:
    print(f"[CANH BAO] Khong tim thay thu muc Oracle Client tai: {oracle_client_path}")

# ==============================================================================
# BỘ THỰC THI SQL ĐA NĂNG
# ==============================================================================
# Dòng 68-100: Hàm thực thi lệnh đơn (UPDATE/DELETE)
# Ưu tiên 1: Dùng cur = oracle_conn(dns="MBLDB", user_name=DB_USER_YMS_AI, ...)
# Ưu tiên 2: Dùng conn = oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)
def execute_sql(sql_str: str, params: dict = None):
    if params is None:
        params = {}

    if HAS_ONEAI_SDV and oracle_conn is not None:
        try:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            cur.execute(sql_str, params=params)
            return
        except Exception as e:
            print(f"[OneAI SDV Warning] {e}. Thu chuyen sang oracledb native...")

    if not os.path.exists(oracle_client_path):
        raise RuntimeError("Thư mục Oracle Client không tồn tại. Vui lòng copy thư mục instantclient_19_19 vào C:\\instantclient_19_19!")

    conn = oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)
    cursor = conn.cursor()
    try:
        cursor.execute(sql_str, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# Dòng 105-135: Hàm thực thi batch (Dành cho Insert/Delete nhiều dòng)
def execute_batch_sql(sql_str: str, params_list: list) -> int:
    if not params_list:
        return 0

    if HAS_ONEAI_SDV and oracle_conn is not None:
        try:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            for p in params_list:
                cur.execute(sql_str, params=p)
            return len(params_list)
        except Exception as e:
            print(f"[OneAI SDV Batch Warning] {e}. Thu chuyen sang oracledb native...")

    if not os.path.exists(oracle_client_path):
        raise RuntimeError("Thư mục Oracle Client không tồn tại. Vui lòng copy thư mục instantclient_19_19 vào C:\\instantclient_19_19!")

    conn = oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)
    cursor = conn.cursor()
    try:
        for p in params_list:
            cursor.execute(sql_str, p)
        conn.commit()
        return len(params_list)
    finally:
        cursor.close()
        conn.close()

# ==============================================================================
# CÁC NGHIỆP VỤ BẢNG MEP_PAYMENT_ANALYSIS
# ==============================================================================
def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
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
    execute_sql(sql, {
        "STATUS": status, "ERROR_COUNT": error_count, "RESULT_LINK": result_link, "REASON": reason, "KEYID": str(keyid).strip()
    })

def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    sql = """
        UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
        SET REVIEW_DECISION = :DECISION,
            REVIEW_NOTE     = :NOTE,
            REVIEW_BY       = :REVIEWER
        WHERE KEYID = :KEYID
    """
    execute_sql(sql, {
        "DECISION": decision, "NOTE": note, "REVIEWER": reviewer, "KEYID": str(keyid).strip()
    })

def batch_upsert_tasks(rows: list) -> int:
    sql = """
        MERGE INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS T
        USING (
            SELECT :KEYID AS KEYID, :TASK_NAME AS TASK_NAME, :PAYMENT_MONTH AS PAYMENT_MONTH,
                   :PIC AS PIC, :PART_NAME AS PART_NAME, :GROUP_NAME AS GROUP_NAME, :STATUS AS STATUS
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
    return execute_batch_sql(sql, params_list)

def delete_tasks(keyids: list) -> int:
    sql = "DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params_list = [{"KEYID": str(k).strip()} for k in keyids]
    return execute_batch_sql(sql, params_list)
