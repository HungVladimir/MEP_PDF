
from database.query_utils import QuerySettings

searchTotalRow=QuerySettings(
    query="""
        SELECT COUNT(*) TOTAL
        FROM LOCAL_AI.CDM_DATA_ANALYSIS
        WHERE 1 = 1
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        AND (:SITE = 'ALL' OR SITE = :SITE)
        AND (:EQPID = 'ALL' OR EQPID LIKE '%' || :EQPID || '%')
        AND (
                :FROM_DATE = 'ALL'
                OR AI_TIME >= CASE
                                WHEN :FROM_DATE = 'ALL' THEN AI_TIME
                                ELSE TO_DATE(:FROM_DATE, 'YYYY-MM-DD')
                            END
            )
        AND (
                :TO_DATE = 'ALL'
                OR AI_TIME < CASE
                            WHEN :TO_DATE = 'ALL' THEN AI_TIME + 1
                            ELSE TO_DATE(:TO_DATE, 'YYYY-MM-DD') + 1
                            END
            )
    """,
    dns="MBAYMS",
    note="search data CDM EQP plan",
)

searchTotalRowSpec=QuerySettings(
    query="""
        SELECT COUNT(*) TOTAL
        FROM LOCAL_AI.CDM_DATA_ANALYSIS
        WHERE 1 = 1
        AND (:STATUS_SPEC = 'ALL' OR STATUS_SPEC = :STATUS_SPEC)
    """,
    dns="MBAYMS",
    note="search data CDM EQP plan",
)

getdata_page=QuerySettings(
    query="""
    SELECT
    RN STT,
    KEYID,
    PROCESS,
    EQPID,
    PRODUCTID,
    SITE,
    ERR_CODE,
    DESCRIPTION,
    NG_QTY,
    RANGETIME_ERR,
    RANGETIME_REQ,
    TO_CHAR(AI_TIME,'MM/DD HH24:MI') AS AI_TIME,
    UPLOAD_TIME,
    TO_CHAR(RESULT_TIME,'MM/DD HH24:MI') AS RESULT_TIME,
    RESULT_LINK,
    REASON,
    STATUS,
    RESULT_SPEC,
    REASON_SPEC,
    STATUS_SPEC
FROM (
    SELECT A.*,
           ROW_NUMBER() OVER(ORDER BY NG_QTY DESC ,AI_TIME DESC) RN
    FROM LOCAL_AI.CDM_DATA_ANALYSIS A
    WHERE 1=1
    AND (:STATUS = 'ALL' OR STATUS = :STATUS)
    AND (:SITE = 'ALL' OR SITE = :SITE)
        AND (:EQPID = 'ALL' OR EQPID LIKE '%' || :EQPID || '%')
        AND (
                :FROM_DATE = 'ALL'
                OR AI_TIME >= CASE
                                WHEN :FROM_DATE = 'ALL' THEN AI_TIME
                                ELSE TO_DATE(:FROM_DATE, 'YYYY-MM-DD')
                            END
            )
        AND (
                :TO_DATE = 'ALL'
                OR AI_TIME < CASE
                            WHEN :TO_DATE = 'ALL' THEN AI_TIME + 1
                            ELSE TO_DATE(:TO_DATE, 'YYYY-MM-DD') + 1
                            END
            )
)
WHERE RN BETWEEN :start_row AND :end_row
ORDER BY RN
    """,
    dns="MBAYMS",
    note="search data CDM EQP plan",
)


getdata_page_spec=QuerySettings(
    query="""
    SELECT
    RN STT,
    KEYID,
    PROCESS,
    EQPID,
    PRODUCTID,
    SITE,
    ERR_CODE,
    DESCRIPTION,
    NG_QTY,
    RANGETIME_ERR,
    RANGETIME_REQ,
    TO_CHAR(AI_TIME,'MM/DD HH24:MI') AS AI_TIME,
    UPLOAD_TIME,
    TO_CHAR(RESULT_TIME,'MM/DD HH24:MI') AS RESULT_TIME,
    RESULT_LINK,
    REASON,
    STATUS,
    RESULT_SPEC,
    REASON_SPEC,
    STATUS_SPEC
FROM (
    SELECT A.*,
           ROW_NUMBER() OVER(ORDER BY NG_QTY DESC ,AI_TIME DESC) RN
    FROM LOCAL_AI.CDM_DATA_ANALYSIS A
    WHERE 1=1
    AND (:STATUS_SPEC = 'ALL' OR STATUS_SPEC = :STATUS_SPEC)
)
WHERE RN BETWEEN :start_row AND :end_row
ORDER BY RN
    """,
    dns="MBAYMS",
    note="search data CDM EQP plan",
)