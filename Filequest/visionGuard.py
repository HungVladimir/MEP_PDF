
from database.query_utils import QuerySettings

DNS = "MBLDB"


# =========================================================
# JOB
# =========================================================

insertJob = QuerySettings(
    query="""
        INSERT INTO AIISG_JOBS (
            JOB_ID,
            JOB_CODE,
            USER_ID,
            USER_NAME,
            KNOX_ID,
            DEPARTMENT,
            STATUS,
            TOTAL_IMAGES,
            OK_IMAGES,
            NG_IMAGES,
            CREATED_BY,
            CREATED_AT,
            UPDATED_AT,
            EXPIRES_AT
        )
        VALUES (
            :JOB_ID,
            :JOB_CODE,
            :USER_ID,
            :USER_NAME,
            :KNOX_ID,
            :DEPARTMENT,
            'DRAFT',
            0,
            0,
            0,
            :CREATED_BY,
            SYSDATE,
            SYSDATE,
            SYSDATE + INTERVAL '1' DAY
        )
    """,
    # dns=DNS,
    note="Create VisionGuard draft job",
)


getJobById = QuerySettings(
    query="""
        SELECT
            JOB_ID,
            JOB_CODE,
            USER_ID,
            USER_NAME,
            KNOX_ID,
            DEPARTMENT,
            STATUS,
            TOTAL_IMAGES,
            OK_IMAGES,
            NG_IMAGES,
            CREATED_BY,
            CREATED_AT,
            UPDATED_AT,
            EXPIRES_AT,
            SUBMITTED_AT,
            APPROVED_BY,
            APPROVED_AT,
            REJECTED_BY,
            REJECTED_AT,
            REJECT_REASON,
            ADMIN_NOTE
        FROM AIISG_JOBS
        WHERE JOB_ID = :JOB_ID
          AND CREATED_BY = :CREATED_BY
    """,
    # dns=DNS,
    note="Get VisionGuard job by ID and owner",
)


getDraftJobForUpdate = QuerySettings(
    query="""
        SELECT
            JOB_ID,
            STATUS,
            TOTAL_IMAGES,
            CREATED_BY
        FROM AIISG_JOBS
        WHERE JOB_ID = :JOB_ID
          AND CREATED_BY = :CREATED_BY
          AND STATUS = 'DRAFT'
          AND (
              EXPIRES_AT IS NULL
              OR EXPIRES_AT > SYSDATE
          )
        FOR UPDATE
    """,
    # dns=DNS,
    note="Lock VisionGuard draft job for update",
)


deleteDraftJob = QuerySettings(
    query="""
        DELETE FROM AIISG_JOBS
        WHERE JOB_ID = :JOB_ID
          AND CREATED_BY = :CREATED_BY
          AND STATUS = 'DRAFT'
    """,
    # dns=DNS,
    note="Delete cancelled VisionGuard draft job",
)


# =========================================================
# IMAGE
# =========================================================

countJobImages = QuerySettings(
    query="""
        SELECT COUNT(*) AS IMAGE_COUNT
        FROM AIISG_IMAGES
        WHERE JOB_ID = :JOB_ID
    """,
    # dns=DNS,
    note="Count images in VisionGuard job",
)


getNextImageSortOrder = QuerySettings(
    query="""
        SELECT NVL(MAX(SORT_ORDER), 0) + 1 AS NEXT_SORT_ORDER
        FROM AIISG_IMAGES
        WHERE JOB_ID = :JOB_ID
    """,
    # dns=DNS,
    note="Get next VisionGuard image sort order",
)


insertImage = QuerySettings(
    query="""
        INSERT INTO AIISG_IMAGES (
            IMAGE_ID,
            JOB_ID,
            ORIGINAL_NAME,
            OBJECT_KEY,
            CONTENT_TYPE,
            FILE_SIZE,
            SORT_ORDER,
            AI_RESULT,
            AI_DETAIL,
            AI_STATUS,
            AI_MESSAGE,
            AI_CHECKED_AT,
            CREATED_AT,
            UPDATED_AT
        )
        VALUES (
            :IMAGE_ID,
            :JOB_ID,
            :ORIGINAL_NAME,
            :OBJECT_KEY,
            :CONTENT_TYPE,
            :FILE_SIZE,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            SYSDATE,
            SYSDATE
        )
    """,
    # dns=DNS,
    note="Insert VisionGuard image metadata",
)


getImageById = QuerySettings(
    query="""
        SELECT
            IMG.IMAGE_ID,
            IMG.JOB_ID,
            IMG.ORIGINAL_NAME,
            IMG.OBJECT_KEY,
            IMG.CONTENT_TYPE,
            IMG.FILE_SIZE,
            IMG.SORT_ORDER,
            IMG.AI_STATUS,
            IMG.AI_RESULT,
            IMG.AI_DETAIL,
            IMG.AI_MESSAGE,
            IMG.AI_CHECKED_AT,
            IMG.CREATED_AT,
            IMG.UPDATED_AT
        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE IMG.IMAGE_ID = :IMAGE_ID
          AND IMG.JOB_ID = :JOB_ID
          AND JOB.CREATED_BY = :CREATED_BY
    """,
    # dns=DNS,
    note="Get VisionGuard image by ID and owner",
)


getDraftImageById = QuerySettings(
    query="""
        SELECT
            IMG.IMAGE_ID,
            IMG.JOB_ID,
            IMG.ORIGINAL_NAME,
            IMG.OBJECT_KEY,
            IMG.CONTENT_TYPE,
            IMG.FILE_SIZE,
            IMG.SORT_ORDER,
            IMG.AI_RESULT,
            IMG.AI_DETAIL

        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE IMG.IMAGE_ID = :IMAGE_ID
          AND IMG.JOB_ID = :JOB_ID
          AND JOB.CREATED_BY = :CREATED_BY
          AND JOB.STATUS = 'DRAFT'
    """,
    # dns=DNS,
    note="Validate removable VisionGuard draft image",
)

getDraftImage = QuerySettings(
    query="""
        SELECT
            IMG.IMAGE_ID,
            IMG.JOB_ID,
            IMG.OBJECT_KEY
        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE IMG.IMAGE_ID = :IMAGE_ID
          AND IMG.JOB_ID = :JOB_ID
          AND JOB.CREATED_BY = :CREATED_BY
          AND JOB.STATUS = 'DRAFT'
    """,
    # dns=DNS,
    note="Get owned VisionGuard draft image",
)


deleteDraftImage = QuerySettings(
    query="""
        DELETE FROM AIISG_IMAGES IMG
        WHERE IMG.IMAGE_ID = :IMAGE_ID
          AND IMG.JOB_ID = :JOB_ID
          AND EXISTS (
              SELECT 1
              FROM AIISG_JOBS JOB
              WHERE JOB.JOB_ID = IMG.JOB_ID
                AND JOB.CREATED_BY = :CREATED_BY
                AND JOB.STATUS = 'DRAFT'
          )
    """,
    # dns=DNS,
    note="Delete VisionGuard draft image metadata",
)


syncJobImageCounts = QuerySettings(
    query="""
        UPDATE AIISG_JOBS JOB
        SET
            TOTAL_IMAGES = (
                SELECT COUNT(*)
                FROM AIISG_IMAGES IMG
                WHERE IMG.JOB_ID = JOB.JOB_ID
            ),
            OK_IMAGES = (
                SELECT COUNT(*)
                FROM AIISG_IMAGES IMG
                WHERE IMG.JOB_ID = JOB.JOB_ID
                  AND IMG.AI_RESULT = 'OK'
            ),
            NG_IMAGES = (
                SELECT COUNT(*)
                FROM AIISG_IMAGES IMG
                WHERE IMG.JOB_ID = JOB.JOB_ID
                  AND IMG.AI_RESULT = 'NG'
            ),
            UPDATED_AT = SYSDATE
        WHERE JOB.JOB_ID = :JOB_ID
    """,
    # dns=DNS,
    note="Synchronize VisionGuard job image counters",
)

updateImageAIResult = QuerySettings(
    query="""
        UPDATE AIISG_IMAGES
        SET
            AI_STATUS = :AI_STATUS,
            AI_MESSAGE = :AI_MESSAGE,
            AI_RESULT = :AI_RESULT,
            AI_DETAIL = :AI_DETAIL,
            AI_CHECKED_AT = SYSDATE,
            UPDATED_AT = SYSDATE
        WHERE IMAGE_ID = :IMAGE_ID
          AND JOB_ID = :JOB_ID
    """,
    # dns=DNS,
    note="Update VisionGuard AI result",
)

getDraftJob = QuerySettings(
    query="""
        SELECT
            JOB_ID,
            JOB_CODE,
            STATUS,
            CREATED_BY
        FROM AIISG_JOBS
        WHERE JOB_ID = :JOB_ID
          AND CREATED_BY = :CREATED_BY
          AND STATUS = 'DRAFT'
    """,
    # dns=DNS,
    note="Get VisionGuard draft Job",
)

getJobImages = QuerySettings(
    query="""
        SELECT
            IMG.IMAGE_ID,
            IMG.OBJECT_KEY,
            IMG.ORIGINAL_NAME,
            IMG.CONTENT_TYPE,
            IMG.AI_STATUS,
            IMG.AI_RESULT
        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE IMG.JOB_ID = :JOB_ID
          AND JOB.CREATED_BY = :CREATED_BY
          AND JOB.STATUS = 'DRAFT'
        ORDER BY IMG.CREATED_AT ASC
    """,
    # dns=DNS,
    note="Get VisionGuard Job images",
)
finalizeJobImageObjectKeys = QuerySettings(
    query="""
        UPDATE AIISG_IMAGES IMG
        SET
            IMG.OBJECT_KEY =
                'visionguard/prefix/'
                || SUBSTR(
                    IMG.OBJECT_KEY,
                    LENGTH('visionguard/draft/') + 1
                ),
            IMG.UPDATED_AT = SYSDATE
        WHERE IMG.JOB_ID = :JOB_ID
          AND IMG.OBJECT_KEY LIKE
              'visionguard/draft/'
              || :JOB_ID
              || '/%'
    """,
    # dns=DNS,
    note=(
        "Move VisionGuard image keys "
        "from draft to final prefix"
    ),
)

submitJob = QuerySettings(
    query="""
        UPDATE AIISG_JOBS
        SET
            STATUS = :JOB_STATUS,
            TOTAL_IMAGES = :TOTAL_IMAGES,
            OK_IMAGES = :OK_IMAGES,
            NG_IMAGES = :NG_IMAGES,
            SUBMITTED_AT = SYSDATE,
            UPDATED_AT = SYSDATE,
            EXPIRES_AT = NULL
        WHERE JOB_ID = :JOB_ID
          AND CREATED_BY = :CREATED_BY
          AND STATUS = 'DRAFT'
    """,
    # dns=DNS,
    note="Submit VisionGuard Job",
)

rollbackJobImageObjectKeys = QuerySettings(
    query="""
        UPDATE AIISG_IMAGES IMG
        SET
            IMG.OBJECT_KEY =
                'visionguard/draft/'
                || SUBSTR(
                    IMG.OBJECT_KEY,
                    LENGTH('visionguard/prefix/') + 1
                ),
            IMG.UPDATED_AT = SYSDATE
        WHERE IMG.JOB_ID = :JOB_ID
          AND IMG.OBJECT_KEY LIKE
              'visionguard/prefix/'
              || :JOB_ID
              || '/%'
    """,
    # dns=DNS,
    note=(
        "Rollback VisionGuard image keys "
        "from final prefix to draft"
    ),
)

getVisionGuardAdminPermission = QuerySettings(
    query="""
        SELECT
            ACCOUNT_ID
        FROM AIP_ACCOUNT_PERMISSION
        WHERE PERMISSION_ID = 'VISION_GUARD_ADMIN'
          AND ACCOUNT_ID = :ACCOUNT_ID
    """,
    # dns=DNS,
    note="Check VisionGuard Admin permission",
)

getViewableImage = QuerySettings(
    query="""
        SELECT
            IMG.IMAGE_ID,
            IMG.OBJECT_KEY,
            IMG.ORIGINAL_NAME,
            IMG.CONTENT_TYPE,
            IMG.FILE_SIZE
        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE IMG.IMAGE_ID = :IMAGE_ID
          AND :IS_ADMIN = 1
    """,
    note="Get authorized VisionGuard image",
)

getVisibleJobs = QuerySettings(
    query="""
        SELECT
            JOB.JOB_ID,
            JOB.JOB_CODE,
            JOB.USER_ID,
            JOB.USER_NAME,
            JOB.KNOX_ID,
            JOB.DEPARTMENT,
            JOB.STATUS,
            JOB.TOTAL_IMAGES,
            JOB.OK_IMAGES,
            JOB.NG_IMAGES,
            JOB.CREATED_BY,
            JOB.CREATED_AT,
            JOB.UPDATED_AT,
            JOB.SUBMITTED_AT,
            JOB.APPROVED_BY,
            JOB.APPROVED_AT,
            JOB.REJECTED_BY,
            JOB.REJECTED_AT,
            JOB.REJECT_REASON,
            JOB.ADMIN_NOTE,

            CASE
                WHEN JOB.NG_IMAGES > 0
                    THEN 'NG'
                ELSE 'OK'
            END AS AI_RESULT,

            CASE
                WHEN JOB.STATUS = 'PENDING_APPROVAL'
                    THEN 'Pending'
                WHEN JOB.STATUS = 'APPROVED'
                    THEN 'Approved'
                WHEN JOB.STATUS = 'REJECTED'
                    THEN 'Rejected'
                WHEN JOB.STATUS = 'AI_COMPLETED'
                    THEN 'Not Required'
                ELSE JOB.STATUS
            END AS CONFIRM_RESULT,

            CASE
                WHEN JOB.STATUS = 'APPROVED'
                    THEN JOB.APPROVED_BY
                WHEN JOB.STATUS = 'REJECTED'
                    THEN JOB.REJECTED_BY
                ELSE NULL
            END AS CONFIRM_BY,

            CASE
                WHEN JOB.STATUS = 'APPROVED'
                    THEN JOB.APPROVED_AT
                WHEN JOB.STATUS = 'REJECTED'
                    THEN JOB.REJECTED_AT
                ELSE NULL
            END AS CONFIRM_TIME,

            CASE
                WHEN JOB.STATUS = 'REJECTED'
                    THEN JOB.REJECT_REASON
                ELSE JOB.ADMIN_NOTE
            END AS CONFIRM_COMMENT

        FROM AIISG_JOBS JOB
        WHERE JOB.STATUS IN (
            'AI_COMPLETED',
            'PENDING_APPROVAL',
            'APPROVED',
            'REJECTED'
        )
          AND (
              :IS_ADMIN = 1
              OR JOB.CREATED_BY = :CURRENT_USER_ID
          )
          AND (
              (
                  :TIME_TYPE_REF = '7d'
                  AND JOB.CREATED_AT > (SYSDATE - 7)
                  AND JOB.CREATED_AT <= SYSDATE
              )
              OR
              (
                  :TIME_TYPE_REF = 'option'
                  AND JOB.CREATED_AT >= TO_DATE(
                      :START_TIME,
                      'YYYYMMDDHH24MI'
                  )
                  AND JOB.CREATED_AT < (
                      TO_DATE(
                          :END_TIME,
                          'YYYYMMDDHH24MI'
                      ) + INTERVAL '1' MINUTE
                  )
              )
          )
        ORDER BY
            NVL(
                JOB.SUBMITTED_AT,
                JOB.CREATED_AT
            ) DESC
    """,
    # dns=DNS,
    note="Get visible VisionGuard Jobs by time",
)

getVisibleJobDetail = QuerySettings(
    query="""
        SELECT
            JOB.JOB_ID,
            JOB.JOB_CODE,
            JOB.USER_ID,
            JOB.USER_NAME,
            JOB.KNOX_ID,
            JOB.DEPARTMENT,
            JOB.STATUS,
            JOB.TOTAL_IMAGES,
            JOB.OK_IMAGES,
            JOB.NG_IMAGES,
            JOB.CREATED_BY,
            JOB.CREATED_AT,
            JOB.UPDATED_AT,
            JOB.SUBMITTED_AT,
            JOB.APPROVED_BY,
            JOB.APPROVED_AT,
            JOB.REJECTED_BY,
            JOB.REJECTED_AT,
            JOB.REJECT_REASON,
            JOB.ADMIN_NOTE
        FROM AIISG_JOBS JOB
        WHERE JOB.JOB_ID = :JOB_ID
          AND JOB.STATUS IN (
              'AI_COMPLETED',
              'PENDING_APPROVAL',
              'APPROVED',
              'REJECTED'
          )
          AND (
              :IS_ADMIN = 1
              OR JOB.CREATED_BY =
                  :CURRENT_USER_ID
          )
    """,
    # dns=DNS,
    note=("Get visible VisionGuard Job detail"),
)


getVisibleJobImages = QuerySettings(
    query="""
        SELECT
            IMG.IMAGE_ID,
            IMG.JOB_ID,
            IMG.ORIGINAL_NAME,
            IMG.OBJECT_KEY,
            IMG.CONTENT_TYPE,
            IMG.FILE_SIZE,
            IMG.SORT_ORDER,
            IMG.AI_STATUS,
            IMG.AI_RESULT,
            IMG.AI_MESSAGE,
            IMG.AI_CHECKED_AT,
            IMG.CREATED_AT,
            IMG.UPDATED_AT
        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE IMG.JOB_ID = :JOB_ID
          AND JOB.STATUS IN (
              'AI_COMPLETED',
              'PENDING_APPROVAL',
              'APPROVED',
              'REJECTED'
          )
          AND (
              :IS_ADMIN = 1
              OR JOB.CREATED_BY =
                  :CURRENT_USER_ID
          )
        ORDER BY
            CASE
                WHEN IMG.AI_RESULT = 'NG'
                    THEN 0
                WHEN IMG.AI_RESULT = 'OK'
                    THEN 1
                ELSE 2
            END,
            IMG.SORT_ORDER NULLS LAST,
            IMG.CREATED_AT ASC
    """,
    # dns=DNS,
    note=("Get visible VisionGuard Job images"),
)

reviewAndApproveJob = QuerySettings(
    query="""
        BEGIN
            UPDATE AIISG_IMAGES
            SET
                AI_RESULT = 'OK',
                AI_STATUS = 'SUCCESS',
                AI_MESSAGE =
                    'Admin changed NG to OK.',
                UPDATED_AT = SYSDATE
            WHERE JOB_ID = :JOB_ID
              AND AI_RESULT = 'NG'
              AND INSTR(
                  :OVERRIDE_IMAGE_IDS_JSON,
                  '"'
                  || IMAGE_ID
                  || '"'
              ) > 0;

            DELETE FROM AIISG_IMAGES
            WHERE JOB_ID = :JOB_ID
              AND AI_RESULT = 'NG'
              AND INSTR(
                  :DELETED_IMAGE_IDS_JSON,
                  '"'
                  || IMAGE_ID
                  || '"'
              ) > 0;

            UPDATE AIISG_JOBS
            SET
                STATUS = 'APPROVED',
                TOTAL_IMAGES = (
                    SELECT COUNT(*)
                    FROM AIISG_IMAGES
                    WHERE JOB_ID = :JOB_ID
                ),
                OK_IMAGES = (
                    SELECT COUNT(*)
                    FROM AIISG_IMAGES
                    WHERE JOB_ID = :JOB_ID
                      AND AI_RESULT = 'OK'
                ),
                NG_IMAGES = 0,
                APPROVED_BY =
                    :CURRENT_USER_ID,
                APPROVED_AT = SYSDATE,
                UPDATED_AT = SYSDATE,
                REJECTED_BY = NULL,
                REJECTED_AT = NULL,
                REJECT_REASON = NULL
            WHERE JOB_ID = :JOB_ID
              AND STATUS =
                  'PENDING_APPROVAL'
              AND EXISTS (
                  SELECT 1
                  FROM AIISG_IMAGES
                  WHERE JOB_ID = :JOB_ID
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM AIISG_IMAGES
                  WHERE JOB_ID = :JOB_ID
                    AND NVL(
                        AI_RESULT,
                        'NG'
                    ) <> 'OK'
              );

            IF SQL%ROWCOUNT = 0 THEN
                RAISE_APPLICATION_ERROR(
                    -20004,
                    'JOB_APPROVE_FAILED'
                );
            END IF;
        END;
    """,
    # dns=DNS,
    note=("Resolve NG images and approve " "VisionGuard Job"),
)

# download


getDownloadableJobImages = QuerySettings(
    query="""
        SELECT
            JOB.JOB_ID,
            JOB.JOB_CODE,
            JOB.STATUS,
            IMG.IMAGE_ID,
            IMG.ORIGINAL_NAME,
            IMG.OBJECT_KEY,
            IMG.CONTENT_TYPE,
            IMG.FILE_SIZE,
            IMG.SORT_ORDER,
            IMG.AI_STATUS,
            IMG.AI_RESULT
        FROM AIISG_IMAGES IMG
        INNER JOIN AIISG_JOBS JOB
            ON JOB.JOB_ID = IMG.JOB_ID
        WHERE JOB.JOB_ID = :JOB_ID
          AND JOB.CREATED_BY = :CREATED_BY
          AND JOB.STATUS IN (
              'AI_COMPLETED',
              'PENDING_APPROVAL',
              'APPROVED'
          )
          AND IMG.AI_STATUS = 'SUCCESS'
          AND IMG.AI_RESULT = 'OK'
        ORDER BY
            IMG.SORT_ORDER NULLS LAST,
            IMG.CREATED_AT ASC
    """,
    # dns=DNS,
    note="Get downloadable OK images of owned VisionGuard Job",
)