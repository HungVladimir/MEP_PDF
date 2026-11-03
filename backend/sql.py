# ====================================================================
# THAO TÁC CƠ SỞ DỮ LIỆU ORACLE (ORACLE SQL HELPER)
# Dự án: MEP Payment AI - Tích hợp OneAI Portal
# Hỗ trợ cả 2 chuẩn: Thư viện OneAI SDV nội bộ (oracle_conn) & oracledb Thick Client
# ====================================================================
import os
import sys
from pathlib import Path

# Đảm bảo mã hóa UTF-8 cho console Windows để không bị lỗi font Tiếng Việt
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. TỰ ĐỘNG TẢI CẤU HÌNH TỪ .ENV (HỖ TRỢ CẢ KHI CÓ HOẶC CHƯA CÓ THƯ VIỆN DOTENV)
def load_env_variables():
    # Thử dùng python-dotenv nếu đã cài
    try:
        from dotenv import load_dotenv, find_dotenv
        env_file = find_dotenv()
        if env_file:
            load_dotenv(env_file)
            return
    except ImportError:
        pass

    # Nếu chưa cài python-dotenv, tự quét và nạp file .env thủ công
    candidates = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if k not in os.environ:
                            os.environ[k] = v
            break

load_env_variables()

# 2. CẤU HÌNH THÔNG SỐ DATABASE THEO QUY CHUẨN CÔNG TY (YMS / ONEAI)
DB_USER_YMS = os.getenv("DB_USER_YMS")
DB_PASSWORD_YMS = os.getenv("DB_PASSWORD_YMS")
TNS_YMS = os.getenv("TNS_YMS")

# Tài khoản Local AI chuyên dụng
DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI") or DB_USER_YMS or os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI") or DB_PASSWORD_YMS or os.getenv("DB_PASSWORD", "")
DNS_NAME = "MBAYMS"  # Cố định MBAYMS theo đúng chuẩn hạ tầng OneAI / SDV công ty
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")

# 3. KIỂM TRA THƯ VIỆN NỘI BỘ ONEAI SDV
try:
    from oneai_sdv import oracle_conn, result_type
    HAS_ONEAI_SDV = True
except ImportError:
    oracle_conn = None
    HAS_ONEAI_SDV = False

# 4. KIỂM TRA THƯ VIỆN ORACLEDB
try:
    import oracledb
    HAS_ORACLEDB = True
except ImportError:
    oracledb = None
    HAS_ORACLEDB = False

# 5. KHỞI TẠO ORACLE THICK CLIENT (NẾU CÓ ĐƯỜNG DẪN INSTANT CLIENT)
_oracle_client_initialized = False

def init_oracle_client():
    """Khởi tạo Oracle Thick Client một lần duy nhất."""
    global _oracle_client_initialized
    if _oracle_client_initialized or not HAS_ORACLEDB:
        return
    client_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
    if client_dir and os.path.exists(client_dir):
        try:
            oracledb.init_oracle_client(lib_dir=client_dir)
            _oracle_client_initialized = True
            print(f"[Oracle] Khoi tao Thick Client thanh cong: {client_dir}")
        except Exception as e:
            _oracle_client_initialized = True
            print(f"[Oracle Thick Client Note] {e}")

# 6. KẾT NỐI ORACLE NATIVE (FALLBACK KHI KHÔNG CÓ ONEAI_SDV)
def get_native_conn():
    """
    Tạo kết nối trực tiếp bằng oracledb.
    Theo chuẩn code công ty:
      Cách A: Dùng user=DB_USER_YMS, pass=DB_PASSWORD_YMS, dsn=TNS_YMS
      Cách B: Dùng user=DB_USER_YMS_AI, pass=DB_PASSWORD_YMS_AI, dsn=MBAYMS
    """
    if not HAS_ORACLEDB:
        raise RuntimeError("Moi truong Python chua cai dat thu vien 'oracledb'. Hay chay: pip install oracledb")

    init_oracle_client()
    errors = []

    # CÁCH A: Kết nối bằng tài khoản YMS và chuỗi TNS_YMS (Đúng y hệt code anh Triệu Minh Đức)
    if DB_USER_YMS and DB_PASSWORD_YMS and TNS_YMS:
        try:
            return oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)
        except Exception as e:
            errors.append(f"Cach A (YMS + TNS_YMS): {e}")

    # CÁCH B: Kết nối bằng tài khoản AI và DSN MBAYMS
    if DB_USER_YMS_AI and DB_PASSWORD_YMS_AI:
        try:
            dsn_target = TNS_YMS or DNS_NAME
            return oracledb.connect(user=DB_USER_YMS_AI, password=DB_PASSWORD_YMS_AI, dsn=dsn_target)
        except Exception as e:
            errors.append(f"Cach B (AI + {DNS_NAME}): {e}")

    # CÁCH C: Kết nối bằng Host:Port nếu có khai báo
    host = os.getenv("DB_HOST")
    if host:
        try:
            port = int(os.getenv("DB_PORT", 1521))
            user = DB_USER_YMS or DB_USER_YMS_AI
            password = DB_PASSWORD_YMS or DB_PASSWORD_YMS_AI
            return oracledb.connect(user=user, password=password, host=host, port=port, service_name=DNS_NAME)
        except Exception as e:
            errors.append(f"Cach C (Host/Port): {e}")

    err_msg = " | ".join(errors) if errors else "Thieu thong tin ket noi trong .env (DB_USER_YMS, DB_PASSWORD_YMS, TNS_YMS)"
    raise RuntimeError(f"Khong the ket noi Oracle DB: {err_msg}")

# 7. BỘ THỰC THI DML AN TOÀN (DÙNG ĐƯỢC CẢ ONEAI_SDV VÀ NATIVE ORACLEDB)
def execute_dml(sql: str, params: dict = None):
    """Thực thi câu lệnh DML đơn lẻ (UPDATE / DELETE / INSERT)."""
    if params is None:
        params = {}

    # Ưu tiên 1: Sử dụng thư viện nội bộ OneAI SDV (chuẩn như update_status_spec)
    if HAS_ONEAI_SDV and oracle_conn is not None:
        try:
            cur = oracle_conn(
                dns=DNS_NAME,
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            cur.execute(sql, params=params)

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
            print(f"[OneAI SDV Warning] {e}. Dang chuyen sang oracledb native...")

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
            cur = oracle_conn(
                dns=DNS_NAME,
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            for p in params_list:
                cur.execute(sql, params=p)

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
            print(f"[OneAI SDV Batch Warning] {e}. Dang chuyen sang oracledb native...")

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

# 8. CÁC NGHIỆP VỤ DATABASE PHỤC VỤ MEP PAYMENT
def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """Cập nhật trạng thái công việc vào bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS."""
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
    print(f"[Oracle DB] Da cap nhat KEYID={keyid} -> STATUS={status}")

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
    execute_dml(sql, params)
    print(f"[Oracle DB] Da luu Review cho KEYID={keyid} -> {decision}")

def batch_upsert_tasks(rows: list) -> int:
    """MERGE INTO bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS (Insert & Update)."""
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
    count = execute_dml_batch(sql, params_list)
    print(f"[Oracle DB] Da luu thanh cong {count} dong vao MEP_PAYMENT_ANALYSIS.")
    return count

def delete_tasks(keyids: list) -> int:
    """Xóa các dòng được chọn khỏi Oracle DB theo danh sách KEYID."""
    if not keyids:
        return 0

    sql = "DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params_list = [{"KEYID": str(k).strip()} for k in keyids]
    count = execute_dml_batch(sql, params_list)
    print(f"[Oracle DB] Da xoa {count} dong khoi MEP_PAYMENT_ANALYSIS.")
    return count
