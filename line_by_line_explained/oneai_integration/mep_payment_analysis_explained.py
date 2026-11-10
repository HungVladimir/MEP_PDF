# ==============================================================================
# CẤU HÌNH TRUY VẤN ONEAI GATEWAY - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: oneai_integration/backend/menu_operation/mep_payment/mep_payment_analysis.py
# Chuẩn hóa 100% theo kiến trúc OneAI SDV (/crud/ui endpoint)
# ==============================================================================

# Dòng 1-2: Nhúng lớp QuerySettings từ thư viện nội bộ OneAI
# QuerySettings là lớp tiện ích do nền tảng OneAI cung cấp. Khi đăng ký câu truy vấn
# vào đối tượng này, cổng chung `/crud/ui` sẽ tự động thực thi SQL với DB Oracle mà không cần viết code API riêng.
from database.query_utils import QuerySettings

# ==============================================================================
# 1. CÂU LỆNH ĐẾM TỔNG SỐ DÒNG (PHỤC VỤ PHÂN TRANG TOTAL PAGE TRÊN UI)
# ==============================================================================
# Dòng 5-21: Khởi tạo đối tượng QuerySettings cho việc đếm tổng số dòng
searchTotalRow = QuerySettings(
    query="""
        -- Đếm tổng số dòng thỏa mãn các bộ lọc người dùng chọn trên Toolbar
        SELECT COUNT(*) AS TOTAL
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        -- Lọc theo trạng thái linh hoạt:
        -- 1. 'ALL': Lấy tất cả trạng thái
        -- 2. 'OK': Lấy các task COMPLETED không có lỗi (ERROR_COUNT = 0)
        -- 3. 'ERR': Lấy các task COMPLETED có lỗi chênh lệch (ERROR_COUNT > 0)
        -- 4. Trạng thái cụ thể khác: WAITING, RUNNING, CANCEL
        AND (
            :STATUS = 'ALL'
            OR (:STATUS = 'OK' AND STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0)
            OR (:STATUS = 'ERR' AND STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0)
            OR (STATUS = :STATUS)
        )
        -- Lọc theo tháng thanh toán (YYYY-MM): Nếu chọn 'ALL' thì bỏ qua
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        -- Tìm kiếm đa năng (Omni Search): KEYID, TASK_NAME, PIC, PART_NAME, GROUP_NAME
        AND (
            :KEYID = 'ALL'
            OR UPPER(KEYID) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(TASK_NAME) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(PIC) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(PART_NAME) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(GROUP_NAME) LIKE '%' || UPPER(:KEYID) || '%'
        )
    """,
    dns="MBLDB",  # Tên Data Source Name (DNS) kết nối vào cụm Oracle DB MBLDB của công ty
    note="Đếm tổng số dòng quản lý thanh toán MEP"
)

# ==============================================================================
# 2. CÂU LỆNH LẤY DỮ LIỆU TỪNG TRANG (PHÂN TRANG DỰA TRÊN ROW_NUMBER)
# ==============================================================================
# Dòng 24-63: Khởi tạo đối tượng QuerySettings phân trang cho bảng el-table
getdata_page = QuerySettings(
    query="""
    SELECT
        RN AS STT,          -- Số thứ tự động 1, 2, 3... liên tục theo từng trang
        KEYID,              -- Mã số Work Order duy nhất
        TASK_NAME,          -- Tên công việc / hạng mục thi công
        PAYMENT_MONTH,      -- Tháng thanh toán (YYYY-MM)
        PIC,                -- Người phụ trách
        PART_NAME,          -- Phân xưởng / Bộ phận (Part)
        GROUP_NAME,         -- Khối phòng ban (Group)
        STATUS,             -- Trạng thái: WAITING, RUNNING, COMPLETED, CANCEL
        NVL(PROGRESS, 0) AS PROGRESS, -- % Tiến độ xử lý (0 -> 100%)
        ERROR_COUNT,        -- Tổng số lỗi sai lệch AI phát hiện
        RESULT_LINK,        -- Đường dẫn tải file báo cáo Excel / Zip
        REASON,             -- Ghi chú chi tiết kết quả hoặc lỗi
        REVIEW_DECISION,    -- Quyết định duyệt: APPROVED hoặc REJECTED
        REVIEW_NOTE,        -- Ghi chú giải trình của người duyệt
        REVIEW_BY,          -- Knox ID thực tế của kỹ sư duyệt hồ sơ
        TO_CHAR(UPLOAD_TIME, 'YYYY-MM-DD HH24:MI') AS UPLOAD_TIME, -- Ngày giờ tải lên
        TO_CHAR(RESULT_TIME, 'YYYY-MM-DD HH24:MI') AS RESULT_TIME  -- Ngày giờ có kết quả
    FROM (
        SELECT A.*,
            -- Đánh số thứ tự tăng dần theo UPLOAD_TIME (dòng mới nhất ở dưới)
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
        AND (
            :KEYID = 'ALL'
            OR UPPER(KEYID) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(TASK_NAME) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(PIC) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(PART_NAME) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(GROUP_NAME) LIKE '%' || UPPER(:KEYID) || '%'
        )
    )
    -- Giới hạn dòng trả về theo phạm vi phân trang (ví dụ dòng 1 đến dòng 50)
    WHERE RN BETWEEN :start_row AND :end_row
    ORDER BY RN
    """,
    dns="MBLDB",
    note="Lấy danh sách phân trang bảng MEP"
)

# ==============================================================================
# 3. CÂU LỆNH THỐNG KÊ 5 CHỈ SỐ KPI TOÀN CỤC CỐ ĐỊNH
# ==============================================================================
# Dòng 66-81: Thống kê số lượng hồ sơ theo từng nhóm để hiển thị lên KPI Dashboard Header
searchKpiSummary = QuerySettings(
    query="""
        SELECT
            -- 1. Tổng số hồ sơ trong tháng
            COUNT(*) AS TOTAL,
            -- 2. Số hồ sơ khớp 100% (Hoàn thành và không có sai lệch)
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0 THEN 1 END) AS OK_COUNT,
            -- 3. Số hồ sơ có sai lệch cần xử lý (Hoàn thành và có ít nhất 1 lỗi)
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0 THEN 1 END) AS ERR_COUNT,
            -- 4. Số hồ sơ đang chạy bóc tách ngầm
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'RUNNING' THEN 1 END) AS RUNNING_COUNT,
            -- 5. Số hồ sơ đang ở trạng thái chờ
            COUNT(CASE WHEN UPPER(TRIM(STATUS)) = 'WAITING' OR STATUS IS NULL THEN 1 END) AS WAITING_COUNT
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (
            :KEYID = 'ALL'
            OR UPPER(KEYID) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(TASK_NAME) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(PIC) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(PART_NAME) LIKE '%' || UPPER(:KEYID) || '%'
            OR UPPER(GROUP_NAME) LIKE '%' || UPPER(:KEYID) || '%'
        )
    """,
    dns="MBLDB",
    note="Thống kê 5 chỉ số KPI toàn cục cố định MEP"
)
