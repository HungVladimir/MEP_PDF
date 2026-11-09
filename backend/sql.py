
import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, find_dotenv
import oracledb

# Đảm bảo console Windows chạy đúng UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. NẠP CẤU HÌNH BIẾN MÔI TRƯỜNG TỪ .ENV (CHUẨN ĐỒNG BỘ K8S & LOCAL)
load_dotenv(find_dotenv())
load_dotenv(Path(__file__).parent / ".env")

# Quy tắc đặt tên biến mật khẩu Database đồng bộ K8s & Local (Chu Đức Hải):
# Cú pháp: DB_[tên database]_[userName]__[mật khẩu] -> 2 dấu gạch dưới '__'
pwd_mbldb = os.getenv("DB_MBLDB_LOCAL_AI__PASSWORD") or os.getenv("DB_MBLDB_LOCAL_AI_PASSWORD")
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")

# 2. KHỞI TẠO ORACLE THICK CLIENT (NẾU CÓ ĐƯỜNG DẪN CLIENT)
if oracle_client_path and os.path.exists(oracle_client_path):
    try:
        oracledb.init_oracle_client(lib_dir=oracle_client_path)
    except Exception:
        pass

# 3. KẾT NỐI QUA THƯ VIỆN NỘI BỘ ONEAI SDV
try:
    from oneai_sdv import oracle_conn, result_type
except ImportError:
    oracle_conn = None
    result_type = None


def get_cur():
    """Hàm lấy con trỏ kết nối OneAI Oracle (MBLDB)."""
    # Khai báo trực tiếp userName dưới dạng string theo quy chuẩn K8s
    return oracle_conn(
        dns="MBLDB",
        user_name="LOCAL_AI",
        password=pwd_mbldb,
        oracle_client_dir=oracle_client_path,
    )


# ==============================================================================
# CÁC HÀM NGHIỆP VỤ THAO TÁC VỚI BẢNG LOCAL_AI.MEP_PAYMENT_ANALYSIS
# ==============================================================================

def check_keyid_exists(keyid: str) -> bool:
    """Kiểm tra xem KEYID đã tồn tại trong bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS hay chưa."""
    if not keyid or not str(keyid).strip():
        return False
    try:
        sql = "SELECT COUNT(*) FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
        cur = get_cur()
        cursor = cur.cursor() if hasattr(cur, 'cursor') else cur
        cursor.execute(sql, params={"KEYID": str(keyid).strip()})
        res = cursor.fetchall() if hasattr(cursor, 'fetchall') else None
        count = res[0][0] if res else 0
        if hasattr(cursor, 'close') and cursor != cur:
            try:
                cursor.close()
            except Exception:
                pass
        return count > 0
    except Exception as e:
        print(f"[Oracle DB Warning] check_keyid_exists: {e}")
        return False


# Bộ nhớ đệm RAM lưu tháng thanh toán theo KEYID để tránh gọi Oracle DB liên tục (Giảm 2-3s delay)
_TASK_MONTH_CACHE: dict = {}


def cache_task_month(keyid: str, month: Optional[str]):
    """Ghi nhớ nhanh tháng của task vào RAM để các request sau đọc tức thì trong 0ms."""
    if keyid and month:
        _TASK_MONTH_CACHE[str(keyid).strip()] = str(month).strip()


def get_task_payment_month(keyid: str) -> Optional[str]:
    """Lấy PAYMENT_MONTH (Tháng thanh toán) từ RAM Cache trước, nếu chưa có mới hỏi Oracle DB."""
    if not keyid or not str(keyid).strip():
        return None
    s_kid = str(keyid).strip()

    # 1. Trả về ngay nếu đã có trong RAM (0.0001ms)
    if s_kid in _TASK_MONTH_CACHE:
        return _TASK_MONTH_CACHE[s_kid]

    try:
        sql = "SELECT PAYMENT_MONTH FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
        cur = get_cur()
        cursor = cur.cursor() if hasattr(cur, 'cursor') else cur
        cursor.execute(sql, params={"KEYID": s_kid})
        res = cursor.fetchall() if hasattr(cursor, 'fetchall') else None
        if hasattr(cursor, 'close') and cursor != cur:
            try:
                cursor.close()
            except Exception:
                pass
        if res and res[0] and res[0][0]:
            val = str(res[0][0]).strip()
            _TASK_MONTH_CACHE[s_kid] = val
            return val
        return None
    except Exception as e:
        print(f"[Oracle DB Warning] get_task_payment_month: {e}")
        return None


def insert_task(cur, r: dict):
    """Thêm 1 dòng mới vào bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS (Chỉ INSERT)."""
    sql = """
        INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS
        (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, PROGRESS, ERROR_COUNT, UPLOAD_TIME)
        VALUES
        (:KEYID, :TASK_NAME, :PAYMENT_MONTH, :PIC, :PART_NAME, :GROUP_NAME, :STATUS, :PROGRESS, 0, SYSDATE)
    """
    params = {
        "KEYID": str(r.get("KEYID", "")).strip(),
        "TASK_NAME": str(r.get("TASK_NAME", "")).strip(),
        "PAYMENT_MONTH": str(r.get("PAYMENT_MONTH", "")).strip(),
        "PIC": str(r.get("PIC", "")).strip(),
        "PART_NAME": str(r.get("PART_NAME", "")).strip(),
        "GROUP_NAME": str(r.get("GROUP_NAME", "")).strip(),
        "STATUS": str(r.get("STATUS", "WAITING")).strip(),
        "PROGRESS": int(r.get("PROGRESS", 0) or 0)
    }
    cur.execute(sql, params=params)


def update_task(cur, r: dict):
    """Cập nhật thông tin các cột của dòng đã có trong DB (Chỉ UPDATE theo KEYID)."""
    sql = """
        UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
        SET TASK_NAME     = :TASK_NAME,
            PAYMENT_MONTH = :PAYMENT_MONTH,
            PIC           = :PIC,
            PART_NAME     = :PART_NAME,
            GROUP_NAME    = :GROUP_NAME
        WHERE KEYID = :KEYID
    """
    params = {
        "KEYID": str(r.get("KEYID", "")).strip(),
        "TASK_NAME": str(r.get("TASK_NAME", "")).strip(),
        "PAYMENT_MONTH": str(r.get("PAYMENT_MONTH", "")).strip(),
        "PIC": str(r.get("PIC", "")).strip(),
        "PART_NAME": str(r.get("PART_NAME", "")).strip(),
        "GROUP_NAME": str(r.get("GROUP_NAME", "")).strip()
    }
    cur.execute(sql, params=params)


def save_tasks(rows: list) -> int:
    """
    Hàm điều phối Lưu dữ liệu (Save):
    - Tách biệt rõ ràng:
      + Nếu dòng mới (isNew == True)  -> gọi insert_task()
      + Nếu dòng cũ sửa (isNew == False) -> gọi update_task()
    """
    if not rows:
        return 0

    cur = get_cur()
    ins_count = 0
    upd_count = 0

    try:
        for r in rows:
            if r.get("isNew"):
                insert_task(cur, r)
                ins_count += 1
            else:
                update_task(cur, r)
                upd_count += 1

        if hasattr(cur, 'commit'):
            cur.commit()
        if hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
            try:
                cur.connection.commit()
            except Exception:
                pass

        print(
            f"[Oracle DB] Da luu thanh cong: {ins_count} dong moi (INSERT), {upd_count} dong cap nhat (UPDATE).")
        return len(rows)
    except Exception as e:
        print(f"[Oracle DB Error] save_tasks: {e}")
        raise


# Tương thích ngược với mã nguồn api.py hiện tại
batch_upsert_tasks = save_tasks


def delete_tasks(keyids: list) -> int:
    """Xóa các dòng được chọn khỏi bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS (Chỉ DELETE)."""
    if not keyids:
        return 0

    sql = "DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :KEYID"
    params_list = [{"KEYID": str(k).strip()} for k in keyids]
    try:
        cur = get_cur()
        for p in params_list:
            cur.execute(sql, params=p)
        if hasattr(cur, 'commit'):
            cur.commit()
        if hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
            try:
                cur.connection.commit()
            except Exception:
                pass

        print(
            f"[Oracle DB] Da xoa {len(keyids)} dong khoi MEP_PAYMENT_ANALYSIS.")
        return len(keyids)
    except Exception as e:
        print(f"[Oracle DB Error] delete_tasks: {e}")
        raise


def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = "", progress: int = None):
    """Cập nhật trạng thái tiến độ vào bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS."""
    try:
        progress_sql = "PROGRESS = :PROGRESS," if progress is not None else ""
        sql = f"""
            UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
            SET STATUS       = :STATUS,
                {progress_sql}
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
        if progress is not None:
            params["PROGRESS"] = int(progress)
        cur = get_cur()
        cur.execute(sql, params=params)
        if hasattr(cur, 'commit'):
            cur.commit()
        if hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
            try:
                cur.connection.commit()
            except Exception:
                pass
        if hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
            try:
                cur.connection.commit()
            except Exception:
                pass
        print(
            f"[Oracle DB] Da cap nhat KEYID={keyid} -> STATUS={status}, PROGRESS={progress}%")
    except Exception as e:
        print(f"[Oracle DB Error] update_task_status: {e}")
        raise


def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    """Cập nhật quyết định phê duyệt (Approve / Reject) của kỹ sư."""
    try:
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
        cur = get_cur()
        cur.execute(sql, params=params)
        if hasattr(cur, 'commit'):
            cur.commit()
        if hasattr(cur, 'connection') and hasattr(cur.connection, 'commit'):
            try:
                cur.connection.commit()
            except Exception:
                pass
        print(f"[Oracle DB] Da luu Review cho KEYID={keyid} -> {decision}")
    except Exception as e:
        print(f"[Oracle DB Error] update_review_decision: {e}")
        raise


def get_kpi_summary(payment_month: str = "ALL", keyword: str = "ALL") -> dict:
    """Truy vấn 5 chỉ số KPI toàn cục cố định từ bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS."""
    sql = """
        SELECT
            COUNT(*) AS TOTAL,
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0 THEN 1 END) AS OK_COUNT,
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0 THEN 1 END) AS ERR_COUNT,
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'RUNNING' THEN 1 END) AS RUNNING_COUNT,
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'WAITING' OR STATUS IS NULL THEN 1 END) AS WAITING_COUNT
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    """
    params = {
        "PAYMENT_MONTH": str(payment_month or "ALL").strip(),
        "KEYID": str(keyword or "ALL").strip()
    }
    try:
        cur = get_cur()
        if result_type and hasattr(result_type, 'DATAFRAME'):
            try:
                df = cur.execute(sql=sql, params=params,
                                 res=result_type.DATAFRAME)
                if df is not None and not df.empty:
                    r = df.iloc[0]
                    return {
                        "total": int(r.get("TOTAL", 0)),
                        "ok": int(r.get("OK_COUNT", 0)),
                        "err": int(r.get("ERR_COUNT", 0)),
                        "running": int(r.get("RUNNING_COUNT", 0)),
                        "waiting": int(r.get("WAITING_COUNT", 0))
                    }
            except Exception:
                pass

        if hasattr(cur, 'cursor'):
            c = cur.cursor()
            c.execute(sql, params)
            r = c.fetchone()
            c.close()
            if r:
                return {
                    "total": int(r[0] or 0),
                    "ok": int(r[1] or 0),
                    "err": int(r[2] or 0),
                    "running": int(r[3] or 0),
                    "waiting": int(r[4] or 0)
                }

        res = cur.execute(sql, params=params)
        if hasattr(res, 'fetchone'):
            r = res.fetchone()
            if r:
                return {
                    "total": int(r[0] or 0),
                    "ok": int(r[1] or 0),
                    "err": int(r[2] or 0),
                    "running": int(r[3] or 0),
                    "waiting": int(r[4] or 0)
                }
    except Exception as e:
        print(f"[Oracle DB Warning] get_kpi_summary error: {e}")

    return {"total": 0, "ok": 0, "err": 0, "running": 0, "waiting": 0}
