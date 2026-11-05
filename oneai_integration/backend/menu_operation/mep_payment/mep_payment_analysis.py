
from database.query_utils import QuerySettings

# 1. QUERY ĐẾM TỔNG SỐ DÒNG (PHỤC VỤ PHÂN TRANG TOTAL PAGE)
# Hỗ trợ lọc chi tiết: ALL, WAITING, RUNNING, COMPLETED, CANCEL, OK (Khớp 100%), ERR (Có sai lệch)
searchTotalRow = QuerySettings(
    query="""
        SELECT COUNT(*) AS TOTAL
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        AND (
            :STATUS = 'ALL'
            OR (:STATUS = 'OK' AND STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0)
            OR (:STATUS = 'ERR' AND STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0)
            OR (STATUS = :STATUS)
        )
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    """,
    dns="MBLDB",
    note="Đếm tổng số dòng quản lý thanh toán MEP"
)

# 2. QUERY LẤY DỮ LIỆU TỪNG TRANG (PHÂN TRANG DỰA THEO ROW_NUMBER)
getdata_page = QuerySettings(
    query="""
    SELECT
        RN AS STT,
        KEYID,
        TASK_NAME,
        PAYMENT_MONTH,
        PIC,
        PART_NAME,
        GROUP_NAME,
        STATUS,
        NVL(PROGRESS, 0) AS PROGRESS,
        ERROR_COUNT,
        RESULT_LINK,
        REASON,
        REVIEW_DECISION,
        REVIEW_NOTE,
        REVIEW_BY,
        TO_CHAR(UPLOAD_TIME, 'YYYY-MM-DD HH24:MI') AS UPLOAD_TIME,
        TO_CHAR(RESULT_TIME, 'YYYY-MM-DD HH24:MI') AS RESULT_TIME
    FROM (
        SELECT A.*,
            ROW_NUMBER() OVER(ORDER BY UPLOAD_TIME ASC NULLS LAST, KEYID ASC) RN
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS A
        WHERE 1 = 1
        AND (
            :STATUS = 'ALL'
            OR (:STATUS = 'OK' AND STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0)
            OR (:STATUS = 'ERR' AND STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0)
            OR (STATUS = :STATUS)
        )
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    )
    WHERE RN BETWEEN :start_row AND :end_row
    ORDER BY RN
    """,
    dns="MBLDB",
    note="Lấy danh sách phân trang bảng MEP"
)

# 3. QUERY THỐNG KÊ 5 CHỈ SỐ KPI TOÀN CỤC (CỐ ĐỊNH KHÔNG BỊ THAY ĐỔI THEO PHÂN TRANG)
searchKpiSummary = QuerySettings(
    query="""
        SELECT
            COUNT(*) AS TOTAL,
            COUNT(CASE WHEN STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0 THEN 1 END) AS OK_COUNT,
            COUNT(CASE WHEN STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0 THEN 1 END) AS ERR_COUNT,
            COUNT(CASE WHEN STATUS = 'RUNNING' THEN 1 END) AS RUNNING_COUNT,
            COUNT(CASE WHEN STATUS = 'WAITING' OR STATUS IS NULL THEN 1 END) AS WAITING_COUNT
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    """,
    dns="MBLDB",
    note="Thống kê 5 chỉ số KPI toàn cục cố định MEP"
)
