# ====================================================================
# SCRIPT TỰ ĐỘNG KHỞI TẠO BẢNG LOCAL_AI.MEP_PAYMENT_ANALYSIS TRÊN ORACLE DB
# Chạy lệnh: python init_oracle_table.py
# ====================================================================
import os
import sys
from pathlib import Path

# Đảm bảo console Windows chạy đúng UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. NẠP BIẾN MÔI TRƯỜNG TỪ .ENV
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

DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI")

oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR", r"C:\oracle_client")

# Khởi tạo Thick Client
import oracledb
if oracle_client_path and os.path.exists(oracle_client_path):
    try:
        oracledb.init_oracle_client(lib_dir=oracle_client_path)
    except Exception:
        pass

try:
    from oneai_sdv import oracle_conn
    HAS_ONEAI_SDV = True
except ImportError:
    oracle_conn = None
    HAS_ONEAI_SDV = False

print("=" * 70)
print("🚀 BẮT ĐẦU TẠO BẢNG LOCAL_AI.MEP_PAYMENT_ANALYSIS TRÊN ORACLE DB")
print("=" * 70)

create_table_sql = """
CREATE TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS (
    KEYID           VARCHAR2(100) NOT NULL,
    TASK_NAME       VARCHAR2(300),
    PAYMENT_MONTH   VARCHAR2(20),
    PIC             VARCHAR2(100),
    PART_NAME       VARCHAR2(100),
    GROUP_NAME      VARCHAR2(100),
    STATUS          VARCHAR2(30) DEFAULT 'WAITING',
    ERROR_COUNT     NUMBER DEFAULT 0,
    RESULT_LINK     VARCHAR2(500),
    REASON          VARCHAR2(1000),
    REVIEW_DECISION VARCHAR2(30),
    REVIEW_NOTE     VARCHAR2(500),
    REVIEW_BY       VARCHAR2(100),
    UPLOAD_TIME     DATE,
    RESULT_TIME     DATE,
    CONSTRAINT PK_MEP_PAYMENT PRIMARY KEY (KEYID)
)
"""

sample_inserts = [
    """
    INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
    (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME)
    VALUES 
    ('WOR2512230006V', 'Thi công hệ thống điện chiếu sáng xưởng A', '2026-10', 'Nguyen Van A', 'MEP Part', 'Infra Group', 'WAITING', 0, NULL, 'Chờ upload file kiểm tra', SYSDATE)
    """,
    """
    INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
    (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME, REVIEW_DECISION)
    VALUES 
    ('WOR2510150002M', 'Lắp đặt đường ống Chiller Phase 2', '2026-10', 'Tran Van B', 'HVAC Part', 'Infra Group', 'COMPLETED', 2, '/mep_payment/files/Sample_Report.xlsx', 'Lệch 2 mã vật tư ở Bản vẽ 1', SYSDATE, 'REJECTED')
    """,
    """
    INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS 
    (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME, REVIEW_DECISION)
    VALUES 
    ('WOR2509010045E', 'Bảo trì hệ thống PCCC khu văn phòng', '2026-09', 'Le Thi C', 'Fire Safety', 'EHS Group', 'COMPLETED', 0, '/mep_payment/files/Sample_Report_2.xlsx', 'Khớp 100% không sai lệch', SYSDATE, 'APPROVED')
    """
]

# Thực hiện tạo bảng qua kết nối
def run_init():
    # Thử qua oracledb Thick Client kết nối bằng user YMS hoặc AI
    conn = None
    try:
        if TNS_YMS and DB_USER_YMS and DB_PASSWORD_YMS:
            conn = oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)
        else:
            conn = oracledb.connect(user=DB_USER_YMS_AI, password=DB_PASSWORD_YMS_AI, dsn="MBAYMS")
    except Exception as e:
        print(f"❌ Không thể mở connection oracledb: {e}")
        return

    cursor = conn.cursor()

    # 1. Kiểm tra bảng đã tồn tại chưa
    try:
        cursor.execute("SELECT COUNT(*) FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS")
        cnt = cursor.fetchone()[0]
        print(f"ℹ️ Bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS đã tồn tại từ trước (Hiện có {cnt} dòng).")
        cursor.close()
        conn.close()
        return
    except Exception:
        print(">> Bảng chưa tồn tại. Đang tiến hành tạo mới bảng...")

    # 2. Tạo bảng
    try:
        cursor.execute(create_table_sql)
        print("✅ [1/3] Đã tạo thành công bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS!")
    except Exception as e:
        print(f"❌ Lỗi tạo bảng: {e}")
        cursor.close()
        conn.close()
        return

    # 3. Tạo Index
    try:
        cursor.execute("CREATE INDEX LOCAL_AI.IDX_MEP_STATUS ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (STATUS)")
        cursor.execute("CREATE INDEX LOCAL_AI.IDX_MEP_MONTH  ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PAYMENT_MONTH)")
        cursor.execute("CREATE INDEX LOCAL_AI.IDX_MEP_PIC    ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PIC)")
        print("✅ [2/3] Đã tạo xong các Index tối ưu tìm kiếm!")
    except Exception as e:
        print(f"ℹ️ Index note: {e}")

    # 4. Chèn 3 dòng dữ liệu mẫu
    try:
        for ins in sample_inserts:
            cursor.execute(ins)
        conn.commit()
        print("✅ [3/3] Đã chèn thành công 3 dòng dữ liệu mẫu và COMMIT!")
    except Exception as e:
        print(f"⚠️ Chèn dữ liệu mẫu note: {e}")

    # 5. Kiểm tra lại
    cursor.execute("SELECT COUNT(*) FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS")
    total = cursor.fetchone()[0]
    print(f"\n🎉 HOÀN TẤT 100%! Bảng LOCAL_AI.MEP_PAYMENT_ANALYSIS đã sẵn sàng (Tổng số dòng: {total}).")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_init()

