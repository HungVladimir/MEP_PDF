
"""
Action query cho module AI Bill Check (đọc hoá đơn ChatGPT / Claude / Gemini).
========================================================================
  Bảng Oracle  : LOCAL_AI.AI_INVOICE_CHECK  (đã tồn tại, app KHÔNG tạo / không DROP)
  DNS mặc định : theo settings.env["dns"]  (dev = MBLDB, prod = MBAYMS - user LOCAL_AI)

Cách dùng (giống pattern `menu_operation.vision.humanoid` / `mcr`):
    from database import dataman
    rows = dataman.sql_execute(
        act_id = "menu_operation.ai_bill.invoiceCheck:getInvoiceById",
        params = {"ID": inv_id},
    )
"""
from database.query_utils import QuerySettings
from logs import logger
from typing import Dict, Any

TBL = "LOCAL_AI.AI_INVOICE_CHECK"

_COLS_PUBLIC = (
    "ID, CREATED_AT, MONTH, USERID, SUBMITTER_NAME, SUBMITTER_EMAIL, FILE_NAME, MIME, "
    "PROVIDER, INVOICE_NUMBER, INVOICE_DATE, BILLING_EMAIL, AMOUNT, PLAN, "
    "EMAIL_MATCH, WARNINGS, STATUS, ADMIN_NOTE, REVIEWED_AT"
)


# ------------------------------------------------------------------- SELECT
getInvoiceById = QuerySettings(
    query=f"""
        SELECT * FROM {TBL} WHERE ID = :ID
    """,
    note="Lấy 1 hoá đơn theo ID",
)

getMine = QuerySettings(
    query=f"""
        SELECT {_COLS_PUBLIC} FROM {TBL}
         WHERE USERID         = :USERID
           AND MONTH          = :MONTH
         ORDER BY CREATED_AT DESC
    """,
    note="Danh sách hoá đơn của người dùng trong 1 tháng",
)

def getList(params: Dict[str, Any]):
    """Admin: lọc theo MONTH (+ STATUS nếu truyền vào)."""
    try:
        status_exist = bool(params.get("STATUS"))
        return QuerySettings(
            query=f"""
                SELECT {_COLS_PUBLIC} FROM {TBL}
                 WHERE MONTH = :MONTH
                 {"AND STATUS = :STATUS" if status_exist else ""}
                 ORDER BY SUBMITTER_NAME, CREATED_AT
            """,
            note="Admin list hoá đơn theo tháng (tuỳ chọn lọc STATUS)",
        )
    except Exception as e:
        logger.error(e)


getRowsByMonth = QuerySettings(
    query=f"""
        SELECT * FROM {TBL}
         WHERE MONTH = :MONTH
         ORDER BY SUBMITTER_NAME
    """,
    note="Lấy toàn bộ cột theo tháng (dùng cho summary / export CSV)",
)

listPendingByMonth = QuerySettings(
    query=f"""
        SELECT ID, WARNINGS FROM {TBL}
         WHERE MONTH  = :MONTH
           AND STATUS = 'pending'
    """,
    note="ID + cảnh báo của các hoá đơn pending trong 1 tháng",
)

countDupInvoiceNumber = QuerySettings(
    query=f"""
        SELECT SUBMITTER_NAME FROM {TBL}
         WHERE INVOICE_NUMBER = :INVOICE_NUMBER
           AND NVL(PROVIDER, ' ') = NVL(:PROVIDER, ' ')
           AND ID            <>  :ID
           AND STATUS        <>  'rejected'
    """,
    note="Kiểm tra trùng số hoá đơn giữa các hoá đơn chưa bị từ chối",
)


# ------------------------------------------------------------------- INSERT
insertInvoice = QuerySettings(
    query=f"""
        INSERT INTO {TBL}
            (ID, CREATED_AT, MONTH, SUBMITTER_NAME, SUBMITTER_EMAIL,
             FILE_NAME, FILE_PATH, MIME, DELETE_TOKEN, USERID, STATUS)
        VALUES
            (:ID, :CREATED_AT, :MONTH, :SUBMITTER_NAME, :SUBMITTER_EMAIL,
             :FILE_NAME, :FILE_PATH, :MIME, :DELETE_TOKEN, :USERID, 'pending')
    """,
    note="Lưu mới 1 hoá đơn (trạng thái pending)",
)


# ------------------------------------------------------------------- UPDATE
updateAnalysis = QuerySettings(
    query=f"""
        UPDATE {TBL}
           SET PROVIDER       = :PROVIDER,
               INVOICE_NUMBER = :INVOICE_NUMBER,
               INVOICE_DATE   = :INVOICE_DATE,
               BILLING_EMAIL  = :BILLING_EMAIL,
               AMOUNT         = :AMOUNT,
               PLAN           = :PLAN,
               EMAIL_MATCH    = :EMAIL_MATCH,
               WARNINGS       = :WARNINGS,
               AI_RAW         = :AI_RAW
         WHERE ID = :ID
    """,
    note="Ghi kết quả đọc AI vào hoá đơn",
)

updateAdminEdit = QuerySettings(
    query=f"""
        UPDATE {TBL}
           SET PROVIDER       = :PROVIDER,
               INVOICE_NUMBER = :INVOICE_NUMBER,
               INVOICE_DATE   = :INVOICE_DATE,
               BILLING_EMAIL  = :BILLING_EMAIL,
               AMOUNT         = :AMOUNT,
               PLAN           = :PLAN,
               STATUS         = :STATUS,
               ADMIN_NOTE     = :ADMIN_NOTE,
               EMAIL_MATCH    = :EMAIL_MATCH,
               WARNINGS       = :WARNINGS,
               REVIEWED_AT    = :REVIEWED_AT
         WHERE ID = :ID
    """,
    note="Admin sửa 1 hoá đơn (các cột edit + trạng thái + reviewed_at)",
)

confirmOneInvoice = QuerySettings(
    query=f"""
        UPDATE {TBL}
           SET STATUS      = 'confirmed',
               REVIEWED_AT = :REVIEWED_AT
         WHERE ID = :ID
    """,
    note="Chuyển 1 hoá đơn sang confirmed",
)


# ------------------------------------------------------------------- DELETE
deleteInvoice = QuerySettings(
    query=f"""
        DELETE FROM {TBL} WHERE ID = :ID
    """,
    note="Xoá 1 hoá đơn (kèm file được xoá ở tầng router, DB chỉ xoá record)",
)