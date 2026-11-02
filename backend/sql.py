# ==========================================
# THAO TÁC CƠ SỞ DỮ LIỆU ORACLE (SQL HELPER)
# ==========================================
import oracledb
import os

# CẤU HÌNH THÔNG SỐ DATABASE ORACLE CỦA CÔNG TY
DB_USER     = os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mat_khau_db")
DB_HOST     = os.getenv("DB_HOST", "107.126.xx.xx")
DB_PORT     = int(os.getenv("DB_PORT", 1521))
DB_SERVICE  = os.getenv("DB_SERVICE", "MBAYMS")

def get_connection():
    """Khởi tạo kết nối tới Oracle Database."""
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
    Cập nhật trạng thái công việc vào bảng MEP_PAYMENT_ANALYSIS:
    - status: 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL'
    """
    conn = get_connection()
    if not conn:
        print(f"⚠️ [DB Mock] KEYID={keyid} -> STATUS={status} (Chưa có kết nối DB)")
        return

    cursor = conn.cursor()
    try:
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
        conn.commit()
        print(f"📊 [Oracle DB] Đã cập nhật KEYID={keyid} -> STATUS={status}")
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi update_task_status: {e}")
    finally:
        cursor.close()
        conn.close()

def update_review_decision(keyid: str, decision: str, note: str, reviewer: str):
    """
    Cập nhật quyết định phê duyệt (Approve / Reject) của kỹ sư:
    - decision: 'APPROVED' hoặc 'REJECTED'
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

def batch_upsert_tasks(rows: list):
    """
    Thực hiện MERGE INTO để vừa hỗ trợ Insert dòng mới vừa hỗ trợ Update dòng cũ vào Oracle DB.
    """
    conn = get_connection()
    if not conn:
        print(f"⚠️ [DB Mock] Đã lưu mock {len(rows)} dòng.")
        return len(rows)

    cursor = conn.cursor()
    try:
        sql = """
            MERGE INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS T
            USING (
                SELECT :keyid AS KEYID,
                       :task_name AS TASK_NAME,
                       :payment_month AS PAYMENT_MONTH,
                       :pic AS PIC,
                       :part_name AS PART_NAME,
                       :group_name AS GROUP_NAME,
                       :status AS STATUS
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
        for r in rows:
            cursor.execute(sql, {
                "keyid": str(r.get("KEYID", "")).strip(),
                "task_name": str(r.get("TASK_NAME", "")).strip(),
                "payment_month": str(r.get("PAYMENT_MONTH", "")).strip(),
                "pic": str(r.get("PIC", "")).strip(),
                "part_name": str(r.get("PART_NAME", "")).strip(),
                "group_name": str(r.get("GROUP_NAME", "")).strip(),
                "status": str(r.get("STATUS", "WAITING")).strip()
            })
        conn.commit()
        print(f"✅ [Oracle DB] Đã lưu thành công {len(rows)} dòng vào MEP_PAYMENT_ANALYSIS.")
        return len(rows)
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi batch_upsert_tasks: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def delete_tasks(keyids: list):
    """Xóa các dòng được chọn khỏi Oracle DB theo danh sách KEYID."""
    if not keyids:
        return 0
    conn = get_connection()
    if not conn:
        print(f"⚠️ [DB Mock] Đã xóa mock {len(keyids)} dòng.")
        return len(keyids)

    cursor = conn.cursor()
    try:
        for k in keyids:
            cursor.execute("DELETE FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE KEYID = :keyid", {"keyid": str(k).strip()})
        conn.commit()
        print(f"🗑️ [Oracle DB] Đã xóa {len(keyids)} dòng khỏi MEP_PAYMENT_ANALYSIS.")
        return len(keyids)
    except Exception as e:
        print(f"❌ [Oracle DB Error] Lỗi delete_tasks: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


