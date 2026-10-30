# HƯỚNG DẪN CHI TIẾT TRIỂN KHAI HỆ THỐNG ĐỐI SOÁT MEP LÊN NỀN TẢNG ONEAI
## (TỪ THIẾT KẾ DATABASE, FRONTEND DARK THEME ĐẾN FASTAPI WORKER)

> **Mục tiêu:** Xây dựng màn hình chuyên nghiệp chuẩn giao diện **Dark Theme của OneAI** (như ảnh thực tế `1.jpg`) với 10 cột thông tin nghiệp vụ, tích hợp cơ chế bấm **Upload file Excel** trực tiếp trên từng dòng Work Order (WO), kích hoạt dịch vụ **FastAPI AI** chạy ngầm và tự động cập nhật kết quả đối soát.

---

## MỤC LỤC TỔNG QUAN

1. [KIẾN TRÚC TỔNG THỂ & LUỒNG VẬN HÀNH (DATA FLOW)](#1-kiến-trúc-tổng-thể--luồng-vận-hành-data-flow)
2. [BƯỚC 1: THIẾT KẾ BẢNG DATABASE TRÊN ORACLE (DBEAVER)](#2-bước-1-thiết-kế-bảng-database-trên-oracle-dbeaver)
3. [BƯỚC 2: XÂY DỰNG BACKEND ONEAI (CẤU HÌNH SQL QUERY)](#3-bước-2-xây-dựng-backend-oneai-cấu-hình-sql-query)
4. [BƯỚC 3: XÂY DỰNG FRONTEND ONEAI (GIAO DIỆN DARK THEME ELEMENT PLUS)](#4-bước-3-xây-dựng-frontend-oneai-giao-diện-dark-theme-element-plus)
5. [BƯỚC 4: XÂY DỰNG FASTAPI WORKER (PROJECT ĐỘC LẬP XỬ LÝ AI)](#5-bước-4-xây-dựng-fastapi-worker-project-độc-lập-xử-lý-ai)
6. [BƯỚC 5: GIẢI MÃ FILE SQL.PY & CÁCH KẾT NỐI ORACLE](#6-bước-5-giải-mã-file-sqlpy--cách-kết-nối-oracle)
7. [BƯỚC 6: QUY TRÌNH CHẠY THỬ NGHIỆM END-TO-END (CHECKLIST)](#7-bước-6-quy-trình-chạy-thử-nghiệm-end-to-end-checklist)
8. [BƯỚC 7: QUẢN LÝ ẢNH BẰNG CHỨNG (1-2 ẢNH/TRANG) & TỐI ƯU BỘ NHỚ](#8-bước-7-quản-lý-ảnh-bằng-chứng-1-2-ảnhtrang--tối-ưu-bộ-nhớ)

---

# 1. KIẾN TRÚC TỔNG THỂ & LUỒNG VẬN HÀNH (DATA FLOW)

Mô hình hoạt động giữa **OneAI Portal**, **Oracle Database** và **FastAPI Worker**:

```
                       ┌────────────────────────────────────────────────────────┐
                       │               ONEAI PORTAL (VUE.JS 3)                  │
                       │   Màn hình Dark Theme hiển thị Grid danh sách WO       │
                       └──────────┬─────────────────────────────▲───────────────┘
                                  │ (2) Bấm [+ Upload File]     │ (4) Polling (Mỗi 10s)
                                  │     Gửi Excel + KEYID       │     Hỏi thăm Oracle DB
                                  ▼                             │     (Tự đổi trạng thái)
       ┌──────────────────────────────────────────┐             │
       │    FASTAPI WORKER (Payment_PDF)          │             │
       │                                          │             │
       │ 1. Nhận file, lưu tạm theo session/KEYID │             │
       │ 2. Gọi SQL: Update STATUS = 'RUNNING' ───┼────────┐    │
       │ 3. Background Task:                      │        │    │
       │    • engine.extract_pdfs_from_excel()    │        │    │
       │    • pdf_extractor.process_single_pdf()  │        │    │
       │    • excel_reconciler: Đối soát 2 Vòng   │        │    │
       │    • Xuất báo cáo 2 Sheet & đếm số lỗi   │        │    │
       │ 4. Gọi SQL: Update STATUS = 'COMPLETED', │        ▼    │
       │             ERROR_COUNT = X,             │   ┌─────────────────────┐
       │             RESULT_LINK = '/files/...' ──┼──►│  ORACLE DATABASE    │
       │                                          │   │  (LOCAL_AI.MEP_...) │
       │ 5. Phục vụ tải file:                     │   └─────────────────────┘
       │    GET /mep_payment/files/{filename}     │
       └──────────────────────────────────────────┘
```

---

# 2. BƯỚC 1: THIẾT KẾ BẢNG DATABASE TRÊN ORACLE (DBEAVER)

Bảng này đóng vai trò là "Sổ cái trung tâm" để Frontend OneAI đọc danh sách hiển thị và FastAPI cập nhật kết quả.

### 1. Phân tích các trường dữ liệu theo Form yêu cầu:
1. `STT`: Sinh tự động khi query bằng `ROW_NUMBER()`.
2. `KEYID`: Mã định danh duy nhất (chính là Số WO hoặc Số Task, ví dụ: `WOR2512230006V`).
3. `TASK_NAME`: Tên công việc / Hạng mục thi công (ví dụ: `Lắp đặt hệ thống ống gió AHU Xưởng 1`).
4. `PAYMENT_MONTH`: Tháng thanh toán (ví dụ: `2026-10`).
5. `PIC`: Tên người phụ trách nghiệm thu (ví dụ: `Nguyễn Văn A`).
6. `PART_NAME`: Bộ phận (ví dụ: `MEP`, `Cơ điện`, `Xây dựng`).
7. `GROUP_NAME`: Khối/Phòng ban (ví dụ: `Infra Group`, `Facility`).
8. `STATUS`: Trạng thái xử lý (`WAITING`, `RUNNING`, `COMPLETED`, `CANCEL`).
9. `ERROR_COUNT`: Tổng số lỗi phát sinh sau khi đối soát (0: Khớp 100%, >0: Có sai lệch).
10. `RESULT_LINK`: Đường link tải file Excel báo cáo (ví dụ: `/mep_payment/files/Report_WOR2512230006V.xlsx`).
11. `REASON`: Ghi chú hoặc chi tiết lỗi nếu thất bại.
12. `UPLOAD_TIME`: Thời điểm tải file lên.
13. `RESULT_TIME`: Thời điểm AI xử lý xong.

### 2. Câu lệnh SQL tạo bảng (Chạy trong DBeaver):
Mở **DBeaver** $\rightarrow$ Kết nối Oracle Database $\rightarrow$ Nhấn tổ hợp phím `F3` (Mở SQL Editor) $\rightarrow$ Dán đoạn lệnh sau và bấm `Ctrl + Enter`:

```sql
-- 1. XÓA BẢNG CŨ NẾU ĐÃ TỒN TẠI (CHỈ DÙNG KHI CẦN TẠO LẠI TỪ ĐẦU)
-- DROP TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS CASCADE CONSTRAINTS;

-- 2. TẠO BẢNG CHÍNH THỨC
CREATE TABLE LOCAL_AI.MEP_PAYMENT_ANALYSIS (
    KEYID           VARCHAR2(100) NOT NULL,          -- Số công việc (Số WO / Task ID) - Khóa chính
    TASK_NAME       VARCHAR2(300),                   -- Tên công việc
    PAYMENT_MONTH   VARCHAR2(20),                    -- Tháng thanh toán (VD: 2026-10)
    PIC             VARCHAR2(100),                   -- Người phụ trách
    PART_NAME       VARCHAR2(100),                   -- Part (Tự động hoặc gán)
    GROUP_NAME      VARCHAR2(100),                   -- Group (Tự động hoặc gán)
    STATUS          VARCHAR2(30) DEFAULT 'WAITING',  -- Trạng thái: WAITING, RUNNING, COMPLETED, CANCEL
    ERROR_COUNT     NUMBER DEFAULT 0,                -- Tổng số lỗi sai lệch
    RESULT_LINK     VARCHAR2(500),                   -- Đường dẫn file báo cáo tải về
    REASON          VARCHAR2(1000),                  -- Ghi chú chi tiết kết quả hoặc lỗi
    UPLOAD_TIME     DATE,                            -- Ngày giờ upload
    RESULT_TIME     DATE,                            -- Ngày giờ hoàn tất
    CONSTRAINT PK_MEP_PAYMENT PRIMARY KEY (KEYID)
);

-- 3. TẠO CHỈ MỤC (INDEX) ĐỂ QUERY VÀ LỌC SIÊU TỐC
CREATE INDEX LOCAL_AI.IDX_MEP_PAYMENT_STATUS ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (STATUS);
CREATE INDEX LOCAL_AI.IDX_MEP_PAYMENT_MONTH  ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PAYMENT_MONTH);
CREATE INDEX LOCAL_AI.IDX_MEP_PAYMENT_PIC    ON LOCAL_AI.MEP_PAYMENT_ANALYSIS (PIC);

-- 4. CHÈN DỮ LIỆU MẪU ĐỂ TEST HIỂN THỊ TRÊN GIAO DIỆN
INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME)
VALUES ('WOR2512230006V', 'Thi công hệ thống điện chiếu sáng xưởng A', '2026-10', 'Nguyen Van A', 'MEP Part', 'Infra Group', 'WAITING', 0, NULL, 'Chờ tải file nghiệm thu', SYSDATE);

INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME)
VALUES ('WOR2510150002M', 'Lắp đặt đường ống làm mát Chiller Phase 2', '2026-10', 'Tran Van B', 'HVAC Part', 'Infra Group', 'COMPLETED', 2, '/mep_payment/files/Sample_Report.xlsx', 'Lệch 2 mã vật tư ở Bản vẽ 1', SYSDATE);

INSERT INTO LOCAL_AI.MEP_PAYMENT_ANALYSIS (KEYID, TASK_NAME, PAYMENT_MONTH, PIC, PART_NAME, GROUP_NAME, STATUS, ERROR_COUNT, RESULT_LINK, REASON, UPLOAD_TIME)
VALUES ('WOR2509010045E', 'Bảo trì hệ thống PCCC khu vực văn phòng', '2026-09', 'Le Thi C', 'Fire Safety', 'EHS Group', 'COMPLETED', 0, '/mep_payment/files/Sample_Report_2.xlsx', 'Khớp 100% không sai lệch', SYSDATE);

COMMIT;
```

---

# 3. BƯỚC 2: XÂY DỰNG BACKEND ONEAI (CẤU HÌNH SQL QUERY)

Trong project OneAI đã clone về, tìm thư mục cấu hình backend query (nơi chứa file `cdm_analysis.py`).
Tạo một file mới tên là: `mep_payment_analysis.py`.

```python
# File: mep_payment_analysis.py (Đặt trong thư mục backend của OneAI)
from database.query_utils import QuerySettings

# 1. QUERY ĐẾM TỔNG SỐ DÒNG (PHỤC VỤ PHÂN TRANG PAGINATION)
searchTotalRow = QuerySettings(
    query="""
        SELECT COUNT(*) AS TOTAL
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
        WHERE 1 = 1
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    """,
    dns="MBAYMS",  # Tên cấu hình kết nối DB Oracle của công ty
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
        ERROR_COUNT,
        RESULT_LINK,
        REASON,
        TO_CHAR(UPLOAD_TIME, 'YYYY-MM-DD HH24:MI') AS UPLOAD_TIME,
        TO_CHAR(RESULT_TIME, 'YYYY-MM-DD HH24:MI') AS RESULT_TIME
    FROM (
        SELECT A.*,
               ROW_NUMBER() OVER(ORDER BY UPLOAD_TIME DESC NULLS LAST, KEYID DESC) RN
        FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS A
        WHERE 1 = 1
        AND (:STATUS = 'ALL' OR STATUS = :STATUS)
        AND (:PAYMENT_MONTH = 'ALL' OR PAYMENT_MONTH = :PAYMENT_MONTH)
        AND (:KEYID = 'ALL' OR KEYID LIKE '%' || :KEYID || '%' OR TASK_NAME LIKE '%' || :KEYID || '%')
    )
    WHERE RN BETWEEN :start_row AND :end_row
    ORDER BY RN
    """,
    dns="MBAYMS",
    note="Lấy danh sách phân trang bảng MEP"
)
```

---

# 4. BƯỚC 3: XÂY DỰNG FRONTEND ONEAI (GIAO DIỆN DARK THEME ELEMENT PLUS)

### 1. File Javascript gọi API Gateway: `mepPayment.js`
Đặt trong thư mục `src/js/` (hoặc cùng chỗ với `paperImage.js`).

```javascript
// File: src/js/mepPayment.js
import { api } from '@/aiPlugins/aiApiConfig'

// Đổi tiền tố menu theo đúng đường dẫn thư mục khai báo trong OneAI
const BASE_REQ_ID = "menu_operation.mep_payment.mep_payment_analysis"

export async function get_total_row(status = "ALL", paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:searchTotalRow`
  const param = {
    STATUS: status || "ALL",
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const parameter = { [reqId]: param }
  const res = await api.get("/crud/ui", { params: parameter, loading: false })
  return res.data[reqId].VAL
}

export async function get_data_page(page = 1, pageSize = 50, status = "ALL", paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:getdata_page`
  const start = (page - 1) * pageSize + 1
  const end = page * pageSize

  const param = {
    start_row: start,
    end_row: end,
    STATUS: status || "ALL",
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }

  const parameter = { [reqId]: param }
  const res = await api.get("/crud/ui", { params: parameter, loading: false })
  return res.data[reqId].VAL
}
```

---

### 2. File Giao diện Vue 3 hoàn chỉnh: `mep_operation.vue`
File này kế thừa 100% phong cách của ảnh `1.jpg`: Dark background, Toolbar lọc, Bảng 10 cột, Countdown Reload, Tag trạng thái đổi màu thông minh và nút Upload trực tiếp.

```vue
<!-- File: src/views/mep_operation.vue -->
<template>
  <div class="mep-container">
    <!-- THANH CÔNG CỤ TÌM KIẾM & LỌC (TOOLBAR) -->
    <div class="toolbar">
      <!-- LỌC TRẠNG THÁI (STATUS) -->
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable style="width: 180px">
        <el-option v-for="item in statusList" :key="item" :label="item" :value="item" />
      </el-select>

      <!-- LỌC THÁNG THANH TOÁN -->
      <el-date-picker
        v-model="selectedMonth"
        type="month"
        placeholder="Chọn Tháng Thanh Toán"
        value-format="YYYY-MM"
        style="width: 200px"
      />

      <!-- TÌM KIẾM THEO SỐ WO HOẶC TÊN CÔNG VIỆC -->
      <el-input
        v-model="searchKeyword"
        placeholder="Nhập số WO hoặc tên công việc..."
        clearable
        style="width: 280px"
        @keyup.enter="handleSearch"
      />

      <!-- NÚT RELOAD & ĐẾM NGƯỢC (POLLING) -->
      <el-button type="primary" @click="handleReload">
        Reload ({{ countdown }}s)
      </el-button>
    </div>

    <!-- BẢNG DỮ LIỆU ĐỐI SOÁT (TABLE GRID GỒM 10 CỘT) -->
    <div class="table-container">
      <el-table
        :data="tableData"
        border
        height="720"
        size="small"
        style="width: 100%"
        show-overflow-tooltip
        empty-text="Không có dữ liệu đối soát"
      >
        <!-- CỘT 1: STT -->
        <el-table-column prop="STT" label="STT" width="60" align="center" />

        <!-- CỘT 2: SỐ CÔNG VIỆC (SỐ WO / TASK ID) -->
        <el-table-column prop="KEYID" label="Số Công Việc (WO)" width="160" sortable align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain" class="font-bold">{{ row.KEYID }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT 3: TÊN CÔNG VIỆC -->
        <el-table-column prop="TASK_NAME" label="Tên Công Việc" min-width="220" show-overflow-tooltip />

        <!-- CỘT 4: THÁNG THANH TOÁN -->
        <el-table-column prop="PAYMENT_MONTH" label="Tháng TT" width="100" align="center" sortable />

        <!-- CỘT 5: NGƯỜI PHỤ TRÁCH (PIC) -->
        <el-table-column prop="PIC" label="Người Phụ Trách" width="130" align="center" />

        <!-- CỘT 6: PART (TỰ ĐỘNG THEO TÊN) -->
        <el-table-column prop="PART_NAME" label="Part" width="100" align="center" />

        <!-- CỘT 7: GROUP (TỰ ĐỘNG THEO TÊN) -->
        <el-table-column prop="GROUP_NAME" label="Group" width="110" align="center" />

        <!-- CỘT TRẠNG THÁI XỬ LÝ (STATUS SYSTEM) -->
        <el-table-column prop="STATUS" label="Trạng Thái" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.STATUS === 'COMPLETED'" type="success" effect="dark">Hoàn Tất</el-tag>
            <el-tag v-else-if="row.STATUS === 'RUNNING'" type="warning" effect="dark">Đang Xử Lý</el-tag>
            <el-tag v-else-if="row.STATUS === 'WAITING'" type="info">Chờ Duyệt</el-tag>
            <el-tag v-else type="danger">{{ row.STATUS }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT 8: TÀI LIỆU ĐÍNH KÈM (UPLOAD FILE EXCEL) -->
        <el-table-column label="Tài Liệu Đính Kèm" width="130" align="center">
          <template #default="{ row }">
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              accept=".xlsx,.xlsm"
              :on-change="(file) => handleUploadExcel(file, row)"
              :disabled="row.STATUS === 'RUNNING'"
            >
              <el-button
                type="primary"
                size="small"
                :loading="row.STATUS === 'RUNNING'"
                :disabled="row.STATUS === 'RUNNING'"
              >
                {{ row.STATUS === 'RUNNING' ? 'Đang chạy...' : '+ Upload File' }}
              </el-button>
            </el-upload>
          </template>
        </el-table-column>

        <!-- CỘT 9: KẾT QUẢ KIỂM TRA (TỔNG SỐ LỖI PHÁT SINH) -->
        <el-table-column label="Kết Quả Kiểm Tra" width="150" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <el-tag v-if="row.ERROR_COUNT === 0" type="success" effect="light">
                ✅ Khớp 100% (0 lỗi)
              </el-tag>
              <el-tag v-else type="danger" effect="dark">
                ❌ Lệch {{ row.ERROR_COUNT }} lỗi
              </el-tag>
            </div>
            <span v-else-if="row.STATUS === 'RUNNING'" style="color: #E6A23C;">
              <i class="el-icon-loading"></i> Đang đối soát AI...
            </span>
            <span v-else style="color: #909399;">Chưa có kết quả</span>
          </template>
        </el-table-column>

        <!-- CỘT 10: CHI TIẾT KẾT QUẢ KIỂM TRA (LINK / NÚT TẢI BÁO CÁO) -->
        <el-table-column label="Chi Tiết Báo Cáo" min-width="160" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED' && row.RESULT_LINK">
              <a
                :href="getDownloadUrl(row.RESULT_LINK)"
                target="_blank"
                download
                class="download-btn"
              >
                📥 Tải Báo Cáo 2 Sheet
              </a>
            </div>
            <span v-else-if="row.REASON" class="text-reason">
              {{ row.REASON }}
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- PHÂN TRANG (PAGINATION BAR) -->
      <div class="pagination-bar">
        <el-button @click="goFirst" :disabled="page === 1">First</el-button>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
        <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
        <el-button @click="goLast" :disabled="page === totalPages">Last</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { get_total_row, get_data_page } from '../js/mepPayment'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// CẤU HÌNH ĐƯỜNG DẪN TỚI FASTAPI BACKEND WORKER
// (Nếu deploy chung server thì có thể để http://127.0.0.1:8386 hoặc IP server nội bộ)
const FASTAPI_BASE_URL = "http://127.0.0.1:8386"

const selectedStatus = ref('')
const selectedMonth = ref('')
const searchKeyword = ref('')
const tableData = ref([])

const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const countdown = ref(10) // Tự động reload mỗi 10 giây

const statusList = ref(['ALL', 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL'])

let timer = null
let countdownTimer = null

// TẢI DỮ LIỆU TỪ ORACLE QUA ONEAI GATEWAY
const loadData = async () => {
  try {
    tableData.value = await get_data_page(
      page.value,
      pageSize.value,
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
  } catch (err) {
    console.error("Lỗi khi load bảng dữ liệu:", err)
  }
}

const loadTotal = async () => {
  try {
    const res = await get_total_row(
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
    total.value = res?.[0]?.TOTAL ?? 0
  } catch (err) {
    console.error("Lỗi khi lấy tổng số dòng:", err)
  }
}

const handleReload = async () => {
  await loadData()
  await loadTotal()
  countdown.value = 10
}

const handleSearch = () => {
  page.value = 1
  handleReload()
}

// BẬT POLLING TỰ ĐỘNG HỎI THĂM TRẠNG THÁI MỖI 10 GIÂY
onMounted(() => {
  handleReload()

  timer = setInterval(() => {
    loadData()
    loadTotal()
    countdown.value = 10
  }, 10 * 1000)

  countdownTimer = setInterval(() => {
    if (countdown.value > 0) countdown.value--
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(countdownTimer)
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const handlePageChange = (p) => { page.value = p; loadData(); }
const handleSizeChange = (s) => { pageSize.value = s; page.value = 1; loadData(); }
const goFirst = () => { if (page.value > 1) { page.value = 1; loadData(); } }
const goLast = () => { if (page.value < totalPages.value) { page.value = totalPages.value; loadData(); } }

watch([selectedStatus, selectedMonth], () => {
  page.value = 1
  handleReload()
})

// HÀM XỬ LÝ UPLOAD EXCEL KHI BẤM NÚT TRÊN TỪNG DÒNG
const handleUploadExcel = async (file, row) => {
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xlsm')) {
    ElMessage.error("Chỉ chấp nhận file Excel (.xlsx hoặc .xlsm) có nhúng PDF!")
    return
  }

  const formData = new FormData()
  formData.append("file", file.raw)
  formData.append("KEYID", row.KEYID)
  formData.append("TASK_NAME", row.TASK_NAME || "")
  formData.append("PIC", row.PIC || "")

  // Cập nhật trạng thái tạm thời trên giao diện cho người dùng thấy ngay
  row.STATUS = 'RUNNING'
  row.REASON = 'Đang đẩy file lên AI Server...'

  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (res.data.status === "accepted") {
      ElMessage.success({ message: `Đã nạp file cho WO [${row.KEYID}]. AI đang tiến hành bóc tách...`, duration: 4000 })
      // Kích hoạt reload sau 2 giây để đồng bộ với DB
      setTimeout(handleReload, 2000)
    } else {
      ElMessage.error(res.data.message || "Upload thất bại!")
      row.STATUS = 'CANCEL'
    }
  } catch (err) {
    ElMessage.error("Không thể kết nối tới FastAPI Backend Worker!")
    row.STATUS = 'CANCEL'
    row.REASON = 'Lỗi kết nối Server AI'
  }
}

// FORMAT LINK TẢI BÁO CÁO HOÀN CHỈNH
const getDownloadUrl = (link) => {
  if (!link) return '#'
  if (link.startsWith('http')) return link
  return `${FASTAPI_BASE_URL}${link}`
}
</script>

<style scoped>
.mep-container {
  padding: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 15px;
}
.table-container {
  width: 100%;
  overflow-x: auto;
}
.font-bold {
  font-weight: 600;
}
.download-btn {
  color: #67C23A;
  font-weight: bold;
  text-decoration: underline;
  cursor: pointer;
  display: inline-block;
  padding: 2px 6px;
}
.download-btn:hover {
  color: #85ce61;
}
.text-reason {
  color: #F56C6C;
  font-size: 11px;
}
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 15px;
}
.page-indicator {
  margin-left: 10px;
  color: #909399;
}
</style>
```

---

# 5. BƯỚC 4: XÂY DỰNG FASTAPI WORKER (PROJECT ĐỘC LẬP XỬ LÝ AI)

Trong project `Payment_PDF` hiện tại của bạn, chúng ta sẽ refactor file `main.py` thành `api.py` chuyên nghiệp để vừa nhận request từ OneAI, vừa chạy tác vụ nặng và cập nhật kết quả vào Oracle Database.

### Cấu trúc file `api.py`:

```python
# File: api.py (Nằm trong root project Payment_PDF)
import os
import shutil
import time
import glob
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd

# Nhúng module lõi của chúng ta
import config
from engine import run_mep_pipeline
# Nhúng module cập nhật DB (sẽ được viết ở Bước 5)
from sql import update_task_status

app = FastAPI(title="MEP Payment AI Worker")

# 1. CẤU HÌNH CORS (CHO PHÉP ONEAI VUE.JS GỌI API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. KHAI BÁO CÁC THƯ MỤC LƯU TRỮ TẠM
STORAGE_DIR = Path(__file__).resolve().parent / "sessions"
FINAL_REPORT_DIR = Path(__file__).resolve().parent / "final_reports"
STORAGE_DIR.mkdir(exist_ok=True)
FINAL_REPORT_DIR.mkdir(exist_ok=True)

# 3. HÀM CHẠY NGẦM BACKGROUND TASK (XỬ LÝ TOÀN BỘ AI & ĐỐI SOÁT)
def run_ai_task_background(keyid: str, session_dir: Path, excel_path: str):
    """
    Hàm này chạy hoàn toàn độc lập trong Background.
    Không làm đơ hay timeout request của người dùng trên Web.
    """
    try:
        print(f"\n🚀 [TASK {keyid}] Bắt đầu thực thi Pipeline MEP...")
        # Cập nhật trạng thái Oracle DB sang RUNNING
        update_task_status(keyid=keyid, status="RUNNING", reason="AI đang bóc tách bản vẽ & đối soát...")

        pdf_drawings = session_dir / "drawings"
        pdf_gatepass = session_dir / "gatepass"
        csv_drawings = session_dir / "csv_drawings"
        csv_gatepass = session_dir / "csv_gatepass"

        # GỌI HÀM ENGINE LÕI
        final_excel_path = run_mep_pipeline(
            pdf_drawing_dir=str(pdf_drawings),
            pdf_gatepass_dir=str(pdf_gatepass),
            vendor_excel_path=excel_path,
            master_data_path=excel_path, # Sheet BOQ nằm chung file
            output_dir=str(FINAL_REPORT_DIR),
            csv_drawing_dir=str(csv_drawings),
            csv_gatepass_dir=str(csv_gatepass),
            skip_existing=False
        )

        # ĐẾM SỐ LỖI SAI LỆCH TRONG BÁO CÁO ĐỂ ĐƯA LÊN GIAO DIỆN
        # (Đọc sheet 1 xem có bao nhiêu dòng có chữ 'Lệch' hoặc 'Mã mồ côi' trong cột Note)
        error_count = 0
        try:
            df_check = pd.read_excel(final_excel_path, sheet_name="1. Đối Soát Bản Vẽ")
            if 'Note' in df_check.columns:
                error_count = int(df_check['Note'].astype(str).str.contains('Lệch|Mã mồ côi', na=False).sum())
        except Exception as read_err:
            print(f"⚠️ Không đọc được số lỗi: {read_err}")

        # TẠO ĐƯỜNG DẪN DOWNLOAD CHO CLIENT
        file_name = os.path.basename(final_excel_path)
        download_link = f"/mep_payment/files/{file_name}"

        # CẬP NHẬT TRẠNG THÁI HOÀN TẤT VÀO DATABASE
        update_task_status(
            keyid=keyid,
            status="COMPLETED",
            error_count=error_count,
            result_link=download_link,
            reason=f"Hoàn thành đối soát 2 vòng (Phát hiện {error_count} lỗi)"
        )
        print(f"🎉 [TASK {keyid}] HOÀN TẤT THÀNH CÔNG -> Lưu tại {final_excel_path}")

    except Exception as e:
        error_msg = f"Lỗi xử lý: {str(e)}"
        print(f"❌ [TASK {keyid}] THẤT BẠI: {error_msg}")
        update_task_status(
            keyid=keyid,
            status="CANCEL",
            error_count=0,
            result_link=None,
            reason=error_msg[:900]
        )

# 4. ENDPOINT TIẾP NHẬN FILE TỪ ONEAI VUE
@app.post("/mep_payment/upload")
async def upload_excel_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    KEYID: str = Form(...),
    TASK_NAME: str = Form(None),
    PIC: str = Form(None)
):
    try:
        if not file.filename.endswith(('.xlsx', '.xlsm')):
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file Excel .xlsx hoặc .xlsm")

        # Tạo thư mục session riêng cho mỗi Work Order
        safe_keyid = KEYID.replace('/', '_').replace('\\', '_')
        task_session_dir = STORAGE_DIR / f"session_{safe_keyid}_{int(time.time())}"
        task_session_dir.mkdir(parents=True, exist_ok=True)

        saved_excel_path = task_session_dir / file.filename
        with open(saved_excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Cập nhật trạng thái đầu vào: WAITING
        update_task_status(
            keyid=KEYID,
            status="WAITING",
            reason="File đã nạp thành công. Đang xếp hàng xử lý..."
        )

        # Đẩy vào BackgroundTasks để người dùng không phải chờ đợi
        background_tasks.add_task(
            run_ai_task_background,
            keyid=KEYID,
            session_dir=task_session_dir,
            excel_path=str(saved_excel_path)
        )

        return {"status": "accepted", "message": "Nạp file thành công, AI đang khởi chạy."}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await file.close()

# 5. ENDPOINT TRẢ FILE EXCEL BÁO CÁO VỀ CHO TRÌNH DUYỆT TẢI
@app.get("/mep_payment/files/{filename}")
async def download_report_file(filename: str):
    file_path = FINAL_REPORT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File báo cáo không tồn tại hoặc đã bị xóa.")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    print("🚀 Khởi động MEP Payment AI Server tại cổng 8386...")
    uvicorn.run("api:app", host="0.0.0.0", port=8386, reload=False)
```

---

# 6. BƯỚC 5: GIẢI MÃ FILE SQL.PY & CÁCH KẾT NỐI ORACLE

File `sql.py` thực chất **rất đơn giản và trực tiếp**. Nhiệm vụ duy nhất của nó là nhận các tham số từ FastAPI và thực thi lệnh `UPDATE` vào Oracle Database để cập nhật tiến độ cho OneAI đọc.

Chúng ta sử dụng thư viện chuẩn thế hệ mới của hãng Oracle dành cho Python: **`oracledb`** (thay thế cho `cx_Oracle` cũ, không cần cài đặt Oracle Instant Client rườm rà).

Cài đặt thư viện:
```bash
pip install oracledb
```

### Mã nguồn file `sql.py` hoàn chỉnh:

```python
# File: sql.py (Nằm trong root project Payment_PDF)
import oracledb
import os

# CẤU HÌNH THÔNG SỐ DATABASE ORACLE CỦA CÔNG TY
# (Bạn có thể điền thông tin giống hệt chuỗi kết nối trong DBeaver)
DB_USER     = os.getenv("DB_USER", "LOCAL_AI")
DB_PASSWORD = os.getenv("DB_PASSWORD", "MatKhauDB_CuaBan")
DB_HOST     = os.getenv("DB_HOST", "107.126.xx.xx")
DB_PORT     = int(os.getenv("DB_PORT", 1521))
DB_SERVICE  = os.getenv("DB_SERVICE", "MBAYMS")

def get_connection():
    """Khởi tạo kết nối tới Oracle Database."""
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            service_name=DB_SERVICE
        )
        return conn
    except Exception as e:
        print(f"❌ [DB ERROR] Không thể kết nối tới Oracle: {e}")
        return None

def update_task_status(keyid: str, status: str, error_count: int = 0, result_link: str = None, reason: str = ""):
    """
    Cập nhật trạng thái công việc vào bảng MEP_PAYMENT_ANALYSIS.
    - status: 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL'
    """
    conn = get_connection()
    if not conn:
        print("⚠️ Bỏ qua update DB vì không có kết nối.")
        return

    cursor = conn.cursor()
    try:
        sql = """
            UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
            SET STATUS       = :status,
                ERROR_COUNT  = :error_count,
                RESULT_LINK  = :result_link,
                REASON       = :reason,
                RESULT_TIME  = CASE WHEN :status IN ('COMPLETED', 'CANCEL') THEN SYSDATE ELSE RESULT_TIME END,
                UPLOAD_TIME  = CASE WHEN :status = 'WAITING' THEN SYSDATE ELSE UPLOAD_TIME END
            WHERE KEYID = :keyid
        """
        cursor.execute(sql, {
            "status": status,
            "error_count": error_count,
            "result_link": result_link,
            "reason": reason,
            "keyid": keyid
        })
        conn.commit()
        print(f"📊 [DB] Đã cập nhật KEYID={keyid} -> STATUS={status}")
    except Exception as e:
        print(f"❌ [DB ERROR] Lỗi khi execute update: {e}")
    finally:
        cursor.close()
        conn.close()
```

> **Ghi chú về file `sql.py` gốc ở công ty:** Khi bạn lên công ty tìm file `sql.py` mẫu của dự án khác, bạn sẽ thấy họ cũng làm tương tự như trên (chỉ khác chuỗi TNS Name hoặc account DB). Bạn chỉ cần copy thông số kết nối của họ paste vào file này là chạy mượt mà 100%.

---

# 7. BƯỚC 6: QUY TRÌNH CHẠY THỬ NGHIỆM END-TO-END (CHECKLIST)

Để đảm bảo hệ thống vận hành hoàn hảo, bạn thực hiện lần lượt theo 5 bước kiểm tra sau:

1. **Khởi tạo dữ liệu trên DBeaver**:
   - Chạy lệnh tạo bảng `MEP_PAYMENT_ANALYSIS` và chèn 1 dòng mẫu có `KEYID = 'Sample 3. 03.PAYMENT WOR2512230006V.xlsx'`.
2. **Khởi động Backend Worker FastAPI**:
   - Mở terminal tại thư mục `Payment_PDF`:
     ```bash
     python api.py
     ```
   - Xác nhận log hiện: `Khởi động MEP Payment AI Server tại cổng 8386...`
3. **Khởi động OneAI Frontend Portal**:
   - Chạy project Vue (`npm run serve` hoặc `npm run dev`).
   - Truy cập vào tab màn hình Đối soát MEP mới tạo.
   - Kiểm tra xem 3 dòng dữ liệu mẫu đã hiển thị lên Grid với Dark Theme và đúng 10 cột hay chưa.
4. **Bấm Thử Nghiệm Upload**:
   - Tìm dòng chứa số WO tương ứng, bấm nút `[+ Upload File]`.
   - Chọn file Excel thanh toán (có nhúng PDF bản vẽ & gatepass).
   - Quan sát dòng đó: Nút chuyển sang `Đang chạy...`, trạng thái chuyển sang `Đang Xử Lý` màu vàng.
5. **Kiểm tra Kết quả Tự động Hoàn tất**:
   - Sau ~33 giây, đồng hồ reload 10s sẽ kích hoạt.
   - Dòng đó tự động nhảy sang `Hoàn Tất` màu xanh.
   - Cột kết quả hiện: `✅ Khớp 100%` hoặc `❌ Lệch X lỗi`.
   - Cột báo cáo xuất hiện nút `📥 Tải Báo Cáo 2 Sheet`.
   - Bấm vào link và tải trực tiếp file `.xlsx` về máy kiểm tra tô màu Đỏ/Xanh.

---

# 8. BƯỚC 7: QUẢN LÝ ẢNH BẰNG CHỨNG (1-2 ẢNH/TRANG) & TỐI ƯU BỘ NHỚ

### 1. Nguyên tắc cốt lõi: Tập trung giá trị, loại bỏ rác thừa
- **Thực tế:** 1 file Excel chứa nhiều PDF (nhiều bản vẽ và nhiều biên bản Gate Pass).
- **Vấn đề trước đây:** Mỗi trang PDF bị băm ra hàng chục khúc nhỏ (`chunk_1.png`, `chunk_2.png`...), làm đầy ổ cứng Server rất nhanh.
- **Giải pháp tối ưu mới (Chốt):**
  - **KHÔNG LƯU ẢNH CHUNK:** Mọi khúc cắt nhỏ chỉ encode chuỗi Base64 trên bộ nhớ RAM để gửi lên AI Vision, tuyệt đối **không ghi ra đĩa**.
  - **CHỈ LƯU 1-2 ẢNH BẰNG CHỨNG GỐC CHO MỖI TRANG:**
    * **Đối với Bản vẽ CAD (2 ảnh/trang):**
      1. `Ảnh Bảng khối lượng gốc`: Vùng bảng hoàn chỉnh sau khi Magic Crop hoặc trích xuất OLE (chụp toàn bộ bảng gồm Code, QTY, Remark...).
      2. `Ảnh Khung tên số bản vẽ`: Vùng ROI góc dưới bên phải chứa chữ `DRAWING NO: 1, 2...` (chứng minh AI đọc đúng số bản vẽ).
    * **Đối với Biên bản Gate Pass / BBGN (1 ảnh/trang):**
      1. `Ảnh Bảng vật tư mang vào`: Vùng bảng hoàn chỉnh của trang đó.

### 2. Định dạng & Dung lượng tối ưu:
- Lưu dưới định dạng **JPEG với chất lượng 85%** (`.jpg`) thay vì PNG nặng nề:
  ```python
  cv2.imwrite(path_jpg, img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
  ```
- Mỗi bức ảnh chỉ nặng khoảng **100 KB - 200 KB**.
- Tổng dung lượng ảnh bằng chứng của cả một Work Order (gồm 3 bản vẽ + 1 BBGN) chỉ tốn khoảng **500 KB - 800 KB** (tiết kiệm **99%** so với 150 MB trước đây).

### 3. Vị trí lưu trữ quy củ theo từng Task (Audit Directory):
Để không bị lẫn lộn giữa các lượt chạy và các Work Order khác nhau, ảnh bằng chứng sẽ được gom gọn theo thư mục của chính Task đó:
```
sessions/
  └── session_WOR2512230006V/
        ├── evidence_images/              <-- CHỈ CHỨA 1-2 ẢNH GỐC / TRANG
        │     ├── BV_Trang1_BangKhoiLuong.jpg
        │     ├── BV_Trang1_SoBanVe.jpg
        │     └── BBGN_Trang1_VatTuMangVao.jpg
        ├── drawings/                     <-- PDF bản vẽ trích xuất tạm
        └── gatepass/                     <-- PDF gatepass trích xuất tạm
```

### 4. Dọn dẹp tự động định kỳ (15 - 30 ngày):
Sau khi thanh toán hoàn tất (15–30 ngày), toàn bộ thư mục `session_WOR...` (gồm cả ảnh bằng chứng lẫn PDF tạm) sẽ được hàm dọn dẹp quét theo `mtime` và xóa tự động, giữ cho ổ cứng luôn sạch sẽ và ổn định 100%.


