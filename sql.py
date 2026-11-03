
from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path
import pandas as pd
import oracledb
from datetime import datetime, timedelta
from oneai_sdv import oracle_conn, result_type

load_dotenv(find_dotenv())
DB_USER_YMS = os.getenv("DB_USER_YMS")
DB_PASSWORD_YMS = os.getenv("DB_PASSWORD_YMS")
TNS_YMS = os.getenv("TNS_YMS")

# local AI
DB_USER_YMS_AI = os.getenv("DB_USER_YMS_AI")
DB_PASSWORD_YMS_AI = os.getenv("DB_PASSWORD_YMS_AI")

# ==========================
# Oracle
# ==========================
BASE_FOLDER = Path(__file__).resolve().parent / "init_data"
oracle_client_path = os.getenv("ORACLE_CLIENT_LIB_DIR")

oracledb.init_oracle_client(lib_dir=oracle_client_path)

conn = oracledb.connect(user=DB_USER_YMS, password=DB_PASSWORD_YMS, dsn=TNS_YMS)

cell_ng_sql = """
                SELECT GLASSID,PRODUCTID,EVENTVALUE FROM YMS_DW.DW_GLASSCELL_EVENTHIST
                WHERE ACTIVITY ='Rework'
                AND EVENTVALUE NOT IN ('-')
                AND EVENTTIME >= TO_DATE(:STARTTIME,'YYYYMMDD')
                AND EVENTTIME < TO_DATE(:ENDTIME,'YYYYMMDD')
                """

trackin_sql = """
                SELECT GLASSID,TKINTIME,EQPID,STEPID,CURRENTSITE,AREANAME FROM YMS_DW.DW_GLASSCELL_EVENTHIST
                WHERE ACTIVITY ='TrackIn'
                AND EVENTTIME >= TO_DATE(:STARTTIME,'YYYYMMDD')
                AND EVENTTIME < TO_DATE(:ENDTIME,'YYYYMMDD')
                """

err_sql = """
                SELECT DISTINCT ATTR10 STEPID,ATTR12 ERR_CODE  FROM BN3SPC_STD.I_USER_PRM
                WHERE INDEX_ID ='IB_FEEDBACK_WCON'
                AND INDEX_TYPE  = 'BAD'
                AND ATTR10 !='*'
                """              

def init_data(save_folder, query, day_range=1, batch_size=100000):

    BATCH_SIZE = batch_size
    save_path = os.path.join(BASE_FOLDER, save_folder)
    print(f"-----------------------------GET DATA-----------------------------------")
    print(f"\nĐang thao thác tại thư mục: {save_path}")
   
    os.makedirs(save_path, exist_ok=True)

    # lấy tên các file trong thư mục (8 ký tự đầu)
    file_list = [
        file.stem[:8]  # lấy tên file (không gồm phần mở rộng) rồi lấy 8 ký tự đầu
        for file in Path(save_path).iterdir()
        if file.is_file()
    ]

    batch_no = 1
    total_rows = 0

    end_date = datetime.now()
    time_list = []

    for i in range(day_range):
        start_date = end_date - timedelta(days=day_range - i)
        next_date = start_date + timedelta(days=1)
        start_date_str = start_date.strftime("%Y%m%d")
        next_date_str = next_date.strftime("%Y%m%d")
        time_list.append(start_date_str)

        if start_date_str in file_list:
            print(f"Đã có dữ liệu ngày: {start_date_str}")
            continue

        if day_range > 1:
            params = {"STARTTIME": start_date_str, "ENDTIME": next_date_str}
        else:
            params = {}
           
        cursor = conn.cursor()
        cursor.arraysize = BATCH_SIZE
        cursor.execute(query, parameters=params)
        columns = [c[0] for c in cursor.description]

        while True:
            rows = cursor.fetchmany(BATCH_SIZE)

            if not rows:
                break

            print(f"Thêm dữ liệu cho ngày: {start_date_str}")
            df = pd.DataFrame(rows, columns=columns)
            filename = os.path.join(
                save_path, f"{start_date_str}_{batch_no:04d}.parquet"
            )

            df.to_parquet(filename, engine="pyarrow", compression="snappy", index=False)

            total_rows += len(df)

            print(f"Saved {filename} ({len(df):,} rows)")

            batch_no += 1

        cursor.close()

    # xóa dữ liệu không cần thiết
    time_set = set(time_list)

    for file_name in os.listdir(save_path):
        file_path = os.path.join(save_path, file_name)

        if not os.path.isfile(file_path):
            continue

        file_date = os.path.splitext(file_name)[0][:8]

        if file_date not in time_set:
            print(f"Delete: {file_name}")
            os.remove(file_path)

    print(f"\nTotal rows = {total_rows:,} \n\n")


def insert_cmd_data_table(data_insert):
    try:
        SQL_Insert = """
           INSERT INTO LOCAL_AI.CDM_DATA_ANALYSIS
                  (
                   KEYID,
                   PROCESS,
                   EQPID,
                   ERR_CODE,
                   NG_QTY,
                   RANGETIME_ERR,
                   RANGETIME_REQ,
                   AI_TIME,
                   PRODUCTID,
                   ERR_TIME,
                   STATUS,
                   GLASSID_LIST,
                   DESCRIPTION,
                   SITE
                  )
                  VALUES
                  (
                   :KEYID,
                   :PROCESS,
                   :EQPID,
                   :ERR_CODE,
                   :NG_QTY,
                   :RANGETIME_ERR,
                   :RANGETIME_REQ,
                   :AI_TIME,
                   :PRODUCTID,
                   :ERR_TIME,
                   :STATUS,
                   :GLASSID_LIST,
                   :DESCRIPTION,
                   :SITE
                  ) 
           """
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        cur.execute(SQL_Insert, data_insert.to_dict("records"))
    except oracledb.DatabaseError as e:
        print("Error insert_cmd_data_table Oracle:", e)


def update_status(keyid, status):
    try:
        sql_update = """
                UPDATE LOCAL_AI.CDM_DATA_ANALYSIS
                SET
                    STATUS = :STATUS,
                    RESULT_TIME = SYSDATE
                WHERE KEYID = :KEYID
            """
        params = {"KEYID": keyid, "STATUS": status}
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        cur.execute(sql_update, params=params)

    except oracledb.DatabaseError as e:
        print("Error update_status Oracle:", e)


def update_status_reason(keyid, status, reason):
    try:
        sql_update = """
                UPDATE LOCAL_AI.CDM_DATA_ANALYSIS
                SET
                    STATUS = :STATUS,
                    REASON = :REASON,
                    RESULT_TIME = SYSDATE
                WHERE
                    KEYID = :KEYID
            """
        params = {"KEYID": keyid, "STATUS": status, "REASON": reason}
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        cur.execute(sql_update, params=params)

    except oracledb.DatabaseError as e:
        print("Error update_status_reason Oracle:", e)


def update_status_link(keyid, status, result_link,reason):
    try:
        sql_update = """
                UPDATE LOCAL_AI.CDM_DATA_ANALYSIS
                SET
                    STATUS = :STATUS,
                    RESULT_LINK = :RESULT_LINK,
                    RESULT_TIME = SYSDATE,
                    REASON = :REASON
                WHERE
                    KEYID = :KEYID
            """
        params = {"KEYID": keyid, "STATUS": status, "RESULT_LINK": result_link,"REASON": reason }
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        cur.execute(sql_update, params=params)

    except oracledb.DatabaseError as e:
        print("Error update_status_link Oracle:", e)


def get_cmd_data_by_key(keyid):
    try:
        query = """
           SELECT EQPID,ERR_TIME,STATUS FROM LOCAL_AI.CDM_DATA_ANALYSIS
            WHERE AI_TIME > SYSDATE - 30
            AND KEYID = :KEYID
           """
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        data = cur.execute(
            sql=query, params={"KEYID": keyid}, res=result_type.DATAFRAME
        )
        return data

    except oracledb.DatabaseError as e:
        print("Error get_cmd_data_by_key:", e)


def get_exits_plan():
    try:
        query = """
           SELECT EQPID, ERR_CODE, GLASSID_LIST FROM LOCAL_AI.CDM_DATA_ANALYSIS
           WHERE AI_TIME > SYSDATE - 30
           """
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        data = cur.execute(sql=query, res=result_type.DATAFRAME)
        return data

    except oracledb.DatabaseError as e:
        print("Error get_exits_plan:", e)

def get_description():
    try:
        query = """
           SELECT CODEID ERR_CODE,DESCRIPTION_VE DESCRIPTION FROM LOCAL_AI.CODE_CODE_MD
           WHERE CATEGORY = 'MD_DETAIL'
           """
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        data = cur.execute(sql=query, res=result_type.DATAFRAME)
        return data

    except oracledb.DatabaseError as e:
        print("Error get_description Oracle:", e)

def get_ng_lots_from_db(keyid):
    """
    Hàm chuyên dụng để kết nối DB và lấy dữ liệu thô theo KEYID.
    Trả về DataFrame với cột 'glass_ids' hoặc DataFrame rỗng nếu không có dữ liệu.
    """
    try:
        query = """
            SELECT GLASSID_LIST AS glass_ids
            FROM LOCAL_AI.CDM_DATA_ANALYSIS
            WHERE AI_TIME > SYSDATE - 30
              AND KEYID = :KEYID
              AND GLASSID_LIST IS NOT NULL
        """       
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
       
        df_raw = cur.execute(
            sql=query,
            params={"KEYID": keyid},
            res=result_type.DATAFRAME
        )
       
        if df_raw is None or df_raw.empty:
            return pd.DataFrame(columns=['glass_ids'])
           
        return df_raw
           
    except oracledb.DatabaseError as e:
        error_code, error_msg = e.args[0].code, e.args[0].message
        raise Exception(f"Lỗi truy vấn Oracle ORA-{error_code}: {error_msg}")
    except Exception as e:
        raise

def update_status_spec(keyid, status, result_link, reason):
    try:
        print("reason:="+reason)
        sql_update = """
                UPDATE LOCAL_AI.CDM_DATA_ANALYSIS
                SET
                    STATUS_SPEC = :STATUS,
                    RESULT_SPEC = :RESULT_LINK,
                    REASON_SPEC = :REASON
                WHERE
                    KEYID = :KEYID
            """
        params = {"KEYID": keyid, "STATUS": status, "RESULT_LINK": result_link, "REASON": reason}
        cur = oracle_conn(
            dns="MBAYMS",
            user_name=DB_USER_YMS_AI,
            password=DB_PASSWORD_YMS_AI,
            oracle_client_dir=oracle_client_path,
        )
        cur.execute(sql_update, params=params)

    except oracledb.DatabaseError as e:
        print("Error update_status_link Oracle:", e)