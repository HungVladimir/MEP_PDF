# ====================================================================
# SCRIPT KIỂM TRA CHẨN ĐOÁN KẾT NỐI ORACLE DATABASE (DIAGNOSTIC TOOL)
# Chạy file này bằng lệnh: python test_oracle_connection.py
# ====================================================================
import os
import sys
import traceback
from pathlib import Path

# Đảm bảo mã hóa UTF-8 cho console Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=" * 70)
print("[DIAGNOSTIC] BAT DAU CHAN DOAN KET NOI ORACLE DATABASE (ONEAI / SDV)")
print("=" * 70)

# 1. TỰ ĐỘNG NẠP FILE .ENV (HỖ TRỢ CẢ KHI CHƯA CÀI PYTHON-DOTENV)
def load_env_file():
    candidates = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent / "backend" / ".env",
    ]
    env_found = None
    for p in candidates:
        if p.exists() and p.is_file():
            env_found = p.resolve()
            break

    if env_found:
        print(f"[OK] Da tim thay file .env tai: {env_found}")
        with open(env_found, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if k not in os.environ:
                        os.environ[k] = v
    else:
        print("[CANH BAO] Chua tim thay file .env! Dang su dung bien moi truong he thong...")

load_env_file()

# 2. KIỂM TRA CÁC BIẾN MÔI TRƯỜNG ĐÃ CẤU HÌNH
def mask(val):
    if not val:
        return "<CHUA CAU HINH / RONG>"
    if len(val) <= 4:
        return "***"
    return val[:2] + "*" * (len(val) - 4) + val[-2:]

user_yms = os.getenv("DB_USER_YMS")
pass_yms = os.getenv("DB_PASSWORD_YMS")
tns_yms = os.getenv("TNS_YMS")

user_ai = os.getenv("DB_USER_YMS_AI")
pass_ai = os.getenv("DB_PASSWORD_YMS_AI")

oracle_client_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
db_service = os.getenv("DB_SERVICE")

print("\n--- [1] CAC BIEN MOI TRUONG DUOC NAP ---")
print(f"  * DB_USER_YMS         : {user_yms or '<None>'}")
print(f"  * DB_PASSWORD_YMS     : {mask(pass_yms)}")
print(f"  * TNS_YMS             : {tns_yms or '<None>'}")
print(f"  * DB_USER_YMS_AI      : {user_ai or '<None>'}")
print(f"  * DB_PASSWORD_YMS_AI  : {mask(pass_ai)}")
print(f"  * DB_SERVICE          : {db_service or '<None>'}")
print(f"  * ORACLE_CLIENT_LIB_DIR: {oracle_client_dir or '<None>'}")

# 3. KIỂM TRA THƯ VIỆN ORACLE INSTANT CLIENT (THICK CLIENT)
print("\n--- [2] KIEM TRA ORACLE INSTANT CLIENT (THICK CLIENT) ---")
if not oracle_client_dir or not os.path.exists(oracle_client_dir):
    print(f"[CANH BAO] Duong dan trong .env khong ton tai: '{oracle_client_dir}'")
    # Tu dong quet tim thu muc oracle_client tren may
    found_cand = None
    for cand in [Path("oracle_client"), Path("../oracle_client"), Path(__file__).resolve().parent / "oracle_client", Path(r"C:\oracle_client"), Path(r"C:\instantclient_19_19"), Path(r"C:\instantclient_23_7")]:
        if cand.exists():
            found_cand = str(cand.resolve())
            break
    if found_cand:
        print(f"[TIM THAY TU DONG] Phat hien thu muc chua client tai: {found_cand}")
        oracle_client_dir = found_cand
    else:
        print("[NOTE] Khong tim thay thu muc Oracle Client. Thu vien oracledb se thu o che do Thin Mode.")

if oracle_client_dir and os.path.exists(oracle_client_dir):
    print(f"[OK] Thu muc ton tai: {oracle_client_dir}")
    oci_dll = Path(oracle_client_dir) / "oci.dll"
    clntsh = Path(oracle_client_dir) / "libclntsh.so"
    if oci_dll.exists():
        print(f"[OK] Da tim thay Windows Instant Client DLL: {oci_dll}")
    elif clntsh.exists():
        print(f"[OK] Da tim thay Linux Instant Client SO: {clntsh}")
    else:
        print("[CANH BAO] Khong thay oci.dll hoac libclntsh.so trong thu muc client!")

# Kiểm tra thư viện oracledb
try:
    import oracledb
    has_oracledb = True
    print("[OK] Da cai dat thu vien 'oracledb'.")
except ImportError:
    oracledb = None
    has_oracledb = False
    print("[ERROR] CHUA CAI DAT THU VIEN 'oracledb'! Hay chay: pip install oracledb")

if has_oracledb and oracle_client_dir and os.path.exists(oracle_client_dir):
    try:
        oracledb.init_oracle_client(lib_dir=oracle_client_dir)
        print("[OK] oracledb.init_oracle_client() khoi tao thanh cong!")
    except Exception as e:
        print(f"[NOTE] init_oracle_client: {e}")

# 4. KIỂM TRA THƯ VIỆN ONEAI_SDV NỘI BỘ
print("\n--- [3] KIEM TRA THU VIEN NOI BO ONEAI (oneai_sdv) ---")
try:
    from oneai_sdv import oracle_conn, result_type
    print("[OK] Tim thay module 'oneai_sdv' trong moi truong Python.")
    has_oneai_sdv = True
except ImportError as e:
    print(f"[NOTE] Khong co module 'oneai_sdv' ({e}). Se su dung ket noi direct 'oracledb'.")
    has_oneai_sdv = False

# 5. TIẾN HÀNH THỬ CÁC PHƯƠNG THỨC KẾT NỐI
print("\n--- [4] TIEN HANH THU NGHIEM KET NOI ORACLE ---")
success_method = None

# THỬ CÁCH 1: oneai_sdv.oracle_conn
if has_oneai_sdv:
    target_dns = "MBAYMS"
    target_user = user_ai or user_yms
    target_pass = pass_ai or pass_yms
    print(f"\n>> [THU NGHIEM 1] Dung oneai_sdv.oracle_conn(dns='{target_dns}', user='{target_user}')...")
    try:
        cur = oracle_conn(
            dns=target_dns,
            user_name=target_user,
            password=target_pass,
            oracle_client_dir=oracle_client_dir,
        )
        cur.execute("SELECT 1 FROM DUAL")
        print("[THANH CONG - Cach 1] oneai_sdv thuc thi thanh cong query 'SELECT 1 FROM DUAL'!")
        success_method = "oneai_sdv"
    except Exception as e:
        print(f"[THAT BAI - Cach 1]: {e}")
        traceback.print_exc(limit=2)

# THỬ CÁCH 2: oracledb với user=DB_USER_YMS và dsn=TNS_YMS
if has_oracledb:
    print(f"\n>> [THU NGHIEM 2] Dung oracledb.connect(user='{user_yms}', dsn='{tns_yms}')...")
    try:
        conn2 = oracledb.connect(
            user=user_yms,
            password=pass_yms,
            dsn=tns_yms
        )
        c2 = conn2.cursor()
        c2.execute("SELECT 1 FROM DUAL")
        print(f"[THANH CONG - Cach 2] oracledb YMS ket noi thanh cong! Ket qua: {c2.fetchone()}")
        c2.close()
        conn2.close()
        if not success_method:
            success_method = "oracledb_yms"
    except Exception as e:
        print(f"[THAT BAI - Cach 2]: {e}")

# THỬ CÁCH 3: oracledb với user=DB_USER_YMS_AI và dsn='MBAYMS'
if has_oracledb:
    print(f"\n>> [THU NGHIEM 3] Dung oracledb.connect(user='{user_ai}', dsn='MBAYMS')...")
    try:
        conn3 = oracledb.connect(
            user=user_ai or user_yms,
            password=pass_ai or pass_yms,
            dsn="MBAYMS"
        )
        c3 = conn3.cursor()
        c3.execute("SELECT 1 FROM DUAL")
        print(f"[THANH CONG - Cach 3] oracledb AI ket noi thanh cong! Ket qua: {c3.fetchone()}")
        c3.close()
        conn3.close()
        if not success_method:
            success_method = "oracledb_ai"
    except Exception as e:
        print(f"[THAT BAI - Cach 3]: {e}")

# 6. KIỂM TRA QUYỀN TRÊN BẢNG MEP_PAYMENT_ANALYSIS
print("\n--- [5] KIEM TRA BANG LOCAL_AI.MEP_PAYMENT_ANALYSIS ---")
if success_method:
    print(f"Dang kiem tra bang bang phuong thuc thanh cong: {success_method} ...")
    try:
        if success_method == "oneai_sdv":
            cur = oracle_conn(
                dns="MBAYMS",
                user_name=user_ai or user_yms,
                password=pass_ai or pass_yms,
                oracle_client_dir=oracle_client_dir,
            )
            cur.execute("SELECT COUNT(*) FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS")
            cnt = cur.fetchone() if hasattr(cur, "fetchone") else "OK"
            print(f"[THANH CONG] Bang LOCAL_AI.MEP_PAYMENT_ANALYSIS doc duoc! Tong so dong: {cnt}")
        else:
            u = user_yms if success_method == "oracledb_yms" else (user_ai or user_yms)
            p = pass_yms if success_method == "oracledb_yms" else (pass_ai or pass_yms)
            d = tns_yms if success_method == "oracledb_yms" else "MBAYMS"
            conn = oracledb.connect(user=u, password=p, dsn=d)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS")
            cnt = c.fetchone()
            print(f"[THANH CONG] Bang LOCAL_AI.MEP_PAYMENT_ANALYSIS doc duoc! Tong so dong: {cnt[0]}")
            c.close()
            conn.close()
    except Exception as e:
        print(f"[ERROR] Khong the truy cap bang LOCAL_AI.MEP_PAYMENT_ANALYSIS: {e}")
        print(">> Goi y: Kiem tra xem user ket noi da duoc cap quyen SELECT / INSERT / UPDATE / DELETE tren bang chua.")
else:
    print("[ERROR] Tat ca cac cach ket noi deu chua thanh cong. Vui long xem chi tiet loi o tren.")

print("\n" + "=" * 70)
print("[XONG] HAY COPY TOAN BO LOG TREN VA GUI LAI DE PHAN TICH!")
print("=" * 70)
