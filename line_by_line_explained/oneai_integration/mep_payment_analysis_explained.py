# ==============================================================================
# CẤU HÌNH TRUY VẤN ONEAI GATEWAY - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
# Đường dẫn tương ứng: oneai_integration/backend/mep_payment_analysis.py
# ==============================================================================

# Dòng 1-6: Nhúng lớp QuerySettings từ thư viện nội bộ OneAI
# QuerySettings là lớp tiện ích do nền tảng OneAI cung cấp. Khi đăng ký câu truy vấn
# vào đối tượng này, cổng chung `/crud/ui` sẽ tự động thực thi SQL với DB Oracle mà không cần viết code API.
from database.query_utils import QuerySettings

# ==============================================================================
# 1. CÂU LỆNH ĐẾM TỔNG SỐ DÒNG (PHỤC VỤ PHÂN TRANG)
# ==============================================================================
searchTotalRow = QuerySettings(
    query="""
        -- Đếm tổng số dòng thỏa mãn các bộ lọc người dùng chọn trên Toolbar
        SELECT COUNT(*) AS TOTAL
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        -- Lọc theo trạng thái: Nếu chọn 'ALL' thì bỏ qua, ngược lại lọc chính xác STATUS
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        -- Lọc theo tháng thanh toán: Nếu chọn 'ALL' thì bỏ qua, ngược lại lọc theo PAYMENT_MONTH
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        -- Tìm kiếm gần đúng (LIKE) theo Mã số WO (KEYID) hoặc Tên công việc (TASK_NAME)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    """,
    dns="MBAYMS",  # Tên Data Source Name (DNS) kết nối vào cụm Oracle DB của công ty
    note="Đếm tổng số dòng quản lý thanh toán MEP"
)

# ==============================================================================
# 2. CÂU LỆNH LẤY DỮ LIỆU TỪNG TRANG (PHÂN TRANG DỰA TRÊN ROW_NUMBER)
# ==============================================================================
getdata_page = QuerySettings(
    query="""
    SELECT 
        RN AS STT,          -- Số thứ tự động 1, 2, 3... liên tục theo từng trang
        KEYID,              -- Mã số Work Order
        TASK_NAME,          -- Tên công việc
        PAYMENT_MONTH,      -- Tháng thanh toán
        PIC,                -- Người phụ trách
        PART_NAME,          -- Bộ phận (Part)
        GROUP_NAME,         -- Khối phòng ban (Group)
        STATUS,             -- Trạng thái: WAITING, RUNNING, COMPLETED, CANCEL
        ERROR_COUNT,        -- Tổng số lỗi sai lệch
        RESULT_LINK,        -- Đường dẫn tải file báo cáo Excel
        REASON,             -- Ghi chú chi tiết kết quả hoặc lỗi
        REVIEW_DECISION,    -- Quyết định duyệt: APPROVED hoặc REJECTED
        REVIEW_NOTE,        -- Ghi chú của người duyệt
        REVIEW_BY,          -- Tên tài khoản người duyệt
        -- Định dạng ngày giờ chuẩn hiển thị trên giao diện
        TO_CHAR(UPLOAD_TIME, 'YYYY-MM-DD HH24:MI') AS UPLOAD_TIME,
        TO_CHAR(RESULT_TIME, 'YYYY-MM-DD HH24:MI') AS RESULT_TIME
    FROM (
        SELECT A.*,
               -- Đánh số thứ tự RN tự động, sắp xếp các task mới upload lên đầu
               ROW_NUMBER() OVER(ORDER BY UPLOAD_TIME DESC NULLS LAST, KEYID DESC) RN
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS A
        WHERE 1 = 1
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    )
    -- Lấy chính xác các dòng nằm giữa start_row và end_row của trang hiện tại (VD: từ 1 đến 50)
    WHERE RN BETWEEN :start_row AND :end_row
    ORDER BY RN
    """,
    dns="MBAYMS",
    note="Lấy danh sách phân trang bảng MEP"
)

