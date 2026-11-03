import os
import sys
from pathlib import Path
import oracledb

# Đảm bảo console Windows chạy đúng UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. NẠP CẤU HÌNH BIẾN MÔI TRƯỜNG TỪ .ENV
try:
    from dotenv import load_dotenv, find_dotenv
    env_file = find_dotenv()
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
except ImportError:
    pass

DB_USER_YMS = os.getenv("DB_USER_YMS")
DB_PASSWORD_YMS = os.getenv("DB_PASSWORD_YMS")
TNS_YMS = os.getenv("TNS_YMS")

# Tài khoản Local AI chuyên trách
DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI")

# 2. TỰ ĐỘNG TÌM THƯ MỤC ORACLE INSTANT CLIENT (CHỨA OCI.DLL)
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")
if not oracle_client_path or not os.path.exists(oracle_client_path):
    # Quét tự động các vị trí phổ biến chứa oracle_client
    candidates = [
        Path(__file__).resolve().parent / "oracle_client",
        Path(__file__).resolve().parent.parent / "oracle_client",
        Path(r"C:\oracle_client"),
        Path(r"C:\instantclient_19_19"),
        Path(r"C:\instantclient_23_7"),
        Path("/opt/oracle/instantclient_23_7"),
        Path("/service/oracle_client"),
    ]
    for cand in candidates:
        if cand.exists():
            oracle_client_path = str(cand)
            break

# 3. KHỞI TẠO ORACLE THICK CLIENT (BẮT BUỘC ĐỂ TRÁNH LỖI DPY-3015)
if oracle_client_path and os.path.exists(oracle_client_path):
    try:
        oracledb.init_oracle_client(lib_dir=oracle_client_path)
        print(
            f"[Oracle] Da khoi tao Oracle Thick Client tai: {oracle_client_path}")
    except Exception as e:
        pass
else:
    print(
        f"[CANH BAO] Chua tim thay thu muc Oracle Client tai: {oracle_client_path}")

# 4. KIỂM TRA THƯ VIỆN NỘI BỘ ONEAI SDV
try:
    from oneai_sdv import oracle_conn, result_type
    HAS_ONEAI_SDV = True
except ImportError:
    oracle_conn = None
    HAS_ONEAI_SDV = False

# 5. HÀM LẤY KẾT NỐI DỰ PHÒNG NẾU KHÔNG CÓ ONEAI_SDV


def get_native_conn():
    """Dùng oracledb native Thick Client kết nối qua TNS_YMS."""
    if not oracle_client_path or not os.path.exists(oracle_client_path):
        raise RuntimeError(
            f"Không tìm thấy thư mục Oracle Client chứa oci.dll tại: '{oracle_client_path}'. "
            "Vui lòng kiểm tra lại đường dẫn ORACLE_CLIENT_LIB_DIR trong file .env!"
        )
    return oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)

# 6. CÁC NGHIỆP VỤ DATABASE PHỤC VỤ BẢNG LOCAL_AI.MEP_PAYMENT_ANALYSIS


def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """Cập nhật trạng thái tiến độ vào bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS."""
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
        if HAS_ONEAI_SDV and oracle_conn is not None:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            cur.execute(sql, params=params)
            try:
                if hasattr(cur, 'commit'):
                    cur.commit()
                elif hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
                    cur.connection.commit()
            except Exception:
                pass
        else:
            conn = get_native_conn()
            c = conn.cursor()
            c.execute(sql, params)
            conn.commit()
            c.close()
            conn.close()
        print(f"[Oracle DB] Da cap nhat KEYID={keyid} -> STATUS={status}")
    except Exception as e:
        print(f"[Oracle DB Error] update_task_status: {e}")
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
        if HAS_ONEAI_SDV and oracle_conn is not None:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            cur.execute(sql, params=params)
            try:
                if hasattr(cur, 'commit'):
                    cur.commit()
                elif hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
                    cur.connection.commit()
            except Exception:
                pass
        else:
            conn = get_native_conn()
            c = conn.cursor()
            c.execute(sql, params)
            conn.commit()
            c.close()
            conn.close()
        print(f"[Oracle DB] Da luu Review cho KEYID={keyid} -> {decision}")
    except Exception as e:
        print(f"[Oracle DB Error] update_review_decision: {e}")
        raise


def check_keyid_exists(keyid: str) -> bool:
    """Kiểm tra xem KEYID đã tồn tại trong bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS hay chưa."""
    if not keyid or not str(keyid).strip():
        return False
    sql = "SELECT COUNT(*) FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params = {"KEYID": str(keyid).strip()}
    try:
        if HAS_ONEAI_SDV and oracle_conn is not None:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            cur.execute(sql, params=params)
            res = cur.fetchall()
            count = res[0][0] if res else 0
            return count > 0
        else:
            conn = get_native_conn()
            c = conn.cursor()
            c.execute(sql, params)
            res = c.fetchone()
            count = res[0] if res else 0
            c.close()
            conn.close()
            return count > 0
    except Exception as e:
        print(f"[Oracle DB Warning] check_keyid_exists: {e}")
        return False


def batch_upsert_tasks(rows: list) -> int:
    """MERGE INTO bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS (Insert dòng mới & Update dòng cũ)."""
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
        if HAS_ONEAI_SDV and oracle_conn is not None:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            for p in params_list:
                cur.execute(sql, params=p)
            try:
                if hasattr(cur, 'commit'):
                    cur.commit()
                elif hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
                    cur.connection.commit()
            except Exception:
                pass
        else:
            conn = get_native_conn()
            c = conn.cursor()
            for p in params_list:
                c.execute(sql, p)
            conn.commit()
            c.close()
            conn.close()

        print(
            f"[Oracle DB] Da MERGE thanh cong {len(rows)} dong vao MEP_PAYMENT_ANALYSIS.")
        return len(rows)
    except Exception as e:
        print(f"[Oracle DB Error] batch_upsert_tasks: {e}")
        raise


def delete_tasks(keyids: list) -> int:
    """Xóa các dòng được chọn khỏi bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS."""
    if not keyids:
        return 0

    sql = "DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params_list = [{"KEYID": str(k).strip()} for k in keyids]
    try:
        if HAS_ONEAI_SDV and oracle_conn is not None:
            cur = oracle_conn(
                dns="MBLDB",
                user_name=DB_USER_YMS_AI,
                password=DB_PASSWORD_YMS_AI,
                oracle_client_dir=oracle_client_path,
            )
            for p in params_list:
                cur.execute(sql, params=p)
            try:
                if hasattr(cur, 'commit'):
                    cur.commit()
                elif hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
                    cur.connection.commit()
            except Exception:
                pass
        else:
            conn = get_native_conn()
            c = conn.cursor()
            for p in params_list:
                c.execute(sql, p)
            conn.commit()
            c.close()
            conn.close()

        print(
            f"[Oracle DB] Da xoa {len(keyids)} dong khoi MEP_PAYMENT_ANALYSIS.")
        return len(keyids)
    except Exception as e:
        print(f"[Oracle DB Error] delete_tasks: {e}")
        raise
