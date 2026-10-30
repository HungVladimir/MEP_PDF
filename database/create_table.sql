-- ====================================================================
-- SCRIPT TẠO BẢNG ORACLE DATABASE CHO HỆ THỐNG MEP PAYMENT AI
-- Thao tác trên DBeaver (Schema: LOCAL_AI)
-- ====================================================================

-- 1. XÓA BẢNG CŨ NẾU CẦN RESET LẠI TỪ ĐẦU (UNCOMMENT ĐỂ DÙNG)
-- DROP TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS CASCADE CONSTRAINTS;

-- 2. TẠO BẢNG CHÍNH THỨC LOCAL_AI.MEP_PAYMENT_ANALYSIS
CREATE TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS (
    KEYID           VARCHAR2(100) NOT NULL,          -- Số công việc (Số WO / Task ID) - Khóa chính
    TASK_NAME       VARCHAR2(300),                   -- Tên công việc / hạng mục thi công
    PAYMENT_MONTH   VARCHAR2(20),                    -- Tháng thanh toán (Định dạng: YYYY-MM)
    PIC             VARCHAR2(100),                   -- Tên người phụ trách (Kỹ sư nghiệm thu)
    PART_NAME       VARCHAR2(100),                   -- Part (MEP, Cơ điện 1, Xây dựng...)
    GROUP_NAME      VARCHAR2(100),                   -- Group (Infra Group, EHS...)
    STATUS          VARCHAR2(30) DEFAULT 'WAITING',  -- Trạng thái: WAITING, RUNNING, COMPLETED, CANCEL
    ERROR_COUNT     NUMBER DEFAULT 0,                -- Tổng số lỗi sai lệch (0: Khớp 100%, >0: Có lỗi)
    RESULT_LINK     VARCHAR2(500),                   -- Đường link tải file Excel báo cáo 2 sheet
    REASON          VARCHAR2(1000),                  -- Ghi chú chi tiết kết quả hoặc nguyên nhân lỗi
    REVIEW_DECISION VARCHAR2(30),                    -- Quyết định duyệt: APPROVED, REJECTED, NULL
    REVIEW_NOTE     VARCHAR2(500),                   -- Ghi chú của người duyệt
    REVIEW_BY       VARCHAR2(100),                   -- Tên tài khoản người duyệt
    UPLOAD_TIME     DATE,                            -- Ngày giờ nạp file lên hệ thống
    RESULT_TIME     DATE,                            -- Ngày giờ AI xử lý xong
    CONSTRAINT PK_MEP_PAYMENT PRIMARY KEY (KEYID)
);

-- 3. CHÚ THÍCH CÁC CỘT (COMMENT ON COLUMN)
COMMENT ON TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS IS 'Bảng quản lý đối soát và nghiệm thu khối lượng vật tư MEP';
COMMENT ON COLUMN LOCAL_AI.MEP_PAYMENT_ANALYSIS.KEYID IS 'Mã định danh duy nhất (Số Work Order)';
COMMENT ON COLUMN LOCAL_AI.MEP_PAYMENT_ANALYSIS.STATUS IS 'Trạng thái xử lý của Worker AI';
COMMENT ON COLUMN LOCAL_AI.MEP_PAYMENT_ANALYSIS.ERROR_COUNT IS 'Số lượng sai lệch phát hiện qua 2 vòng';
COMMENT ON COLUMN LOCAL_AI.MEP_PAYMENT_ANALYSIS.REVIEW_DECISION IS 'Quyết định phê duyệt: APPROVED hoặc REJECTED';

-- 4. TẠO CHỈ MỤC (INDEX) TĂNG TỐC ĐỘ QUERY & FILTER
CREATE INDEX LOCAL_AI.IDX_MEP_STATUS ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (STATUS);
CREATE INDEX LOCAL_AI.IDX_MEP_MONTH  ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PAYMENT_MONTH);
CREATE INDEX LOCAL_AI.IDX_MEP_PIC    ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PIC);

-- 5. CHÈN DỮ LIỆU MẪU ĐỂ TEST HIỂN THỊ TRÊN GIAO DIỆN ONEAI
INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
(KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME)
VALUES 
('WOR2512230006V', 'Thi công hệ thống điện chiếu sáng xưởng A', '2026-10', 'Nguyen Van A', 'MEP Part', 'Infra Group', 'WAITING', 0, NULL, 'Chờ upload file kiểm tra', SYSDATE);

INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
(KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME, REVIEW_DECISION)
VALUES 
('WOR2510150002M', 'Lắp đặt đường ống Chiller Phase 2', '2026-10', 'Tran Van B', 'HVAC Part', 'Infra Group', 'COMPLETED', 2, '/mep_payment/files/Sample_Report.xlsx', 'Lệch 2 mã vật tư ở Bản vẽ 1', SYSDATE, 'REJECTED');

INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
(KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME, REVIEW_DECISION)
VALUES 
('WOR2509010045E', 'Bảo trì hệ thống PCCC khu văn phòng', '2026-09', 'Le Thi C', 'Fire Safety', 'EHS Group', 'COMPLETED', 0, '/mep_payment/files/Sample_Report_2.xlsx', 'Khớp 100% không sai lệch', SYSDATE, 'APPROVED');

COMMIT;

