# 09. HƯỚNG DẪN CHI TIẾT LUỒNG CODE HIỂN THỊ GIAO DIỆN & BẢN ĐỒ ÁNH XẠ DỮ LIỆU TOÀN PHẦN

> **Tài liệu Kỹ thuật Chuyên sâu (Code-to-UI Mapping Guide)**  
> **Dự án:** MEP Payment AI Analysis System (`MEP_OneAI_System`)  
> **Mục tiêu:** Phân tích giải phẫu 100% từng con số, từng thẻ badge, từng cột bảng trên giao diện người dùng (UI): Code kiểu gì, gọi từ đâu, backend nào cung cấp, SQL/Excel nào trích xuất ra.  
> **Ngày lập:** Tháng 11/2026

---

## MỤC LỤC
1. [Bản Đồ Kiến Trúc Luồng Dữ Liệu (End-to-End Data Flow)](#1-bản-đồ-kiến-trúc-luồng-dữ-liệu-end-to-end-data-flow)
2. [Phân Tích Hình 1: Màn Hình Bảng Điều Khiển Quản Trị & 5 Thẻ KPI](#2-phân-tích-hình-1-màn-hình-bảng-điều-khiển-quản-trị--5-thẻ-kpi)
3. [Phân Tích Hình 2: Header Modal, 4 Thẻ Thống Kê & Tab 1: Danh Sách Lỗi](#3-phân-tích-hình-2-header-modal-4-thẻ-thống-kê--tab-1-danh-sách-lỗi)
4. [Phân Tích Hình 3: Tab 2: Đối Chiếu Theo Bản Vẽ (Accordion Đa Tầng)](#4-phân-tích-hình-3-tab-2-đối-chiếu-theo-bản-vẽ-accordion-đa-tầng)
5. [Phân Tích Chi Tiết Tab 3: Soi Bản Vẽ / Ảnh Trích Xuất (Lightbox Viewer)](#5-phân-tích-chi-tiết-tab-3-soi-bản-vẽ--ảnh-trích-xuất-lightbox-viewer)
6. [Phân Tích Chi Tiết Tab 4: Nhật Ký AI (Terminal Console Logs Realtime)](#6-phân-tích-chi-tiết-tab-4-nhật-ký-ai-terminal-console-logs-realtime)
7. [Phân Tích Khung Phê Duyệt & Thao Tác Hồ Sơ (Footer Modal)](#7-phân-tích-khung-phê-duyệt--thao-tác-hồ-sơ-footer-modal)
8. [Bảng Ma Trận Ánh Xạ Tổng Thể (Master UI-to-Code Mapping Matrix)](#8-bảng-ma-trận-ánh-xạ-tổng-thể-master-ui-to-code-mapping-matrix)

---

## 1. BẢN ĐỒ KIẾN TRÚC LUỒNG DỮ LIỆU (END-TO-END DATA FLOW)

Mọi dữ liệu hiển thị trên màn hình OneAI được điều phối qua 2 luồng độc lập:

```mermaid
flowchart TD
    subgraph UI["GIAO DIỆN NGƯỜI DÙNG (operation.vue)"]
        KPI_CARDS["5 Thẻ KPI trên cùng"]
        MAIN_TABLE["Bảng Danh Sách 41 Hồ Sơ"]
        MODAL_DETAIL["Hộp Thoại Modal Đối Soát 4 Tab"]
    end

    subgraph FLOW_A["LUỒNG A: QUẢN TRỊ BẢNG & PHÂN TRANG (OneAI Gateway)"]
        API_JS["mepPayment.js / mep_payment.js"]
        GW["OneAI Gateway: POST /crud/ui"]
        QS["QuerySettings (mep_payment_analysis.py)"]
        ORA[("Oracle DB: LOCAL_AI.MEP_PAYMENT_ANALYSIS")]
        
        MAIN_TABLE -->|1. loadData| API_JS
        KPI_CARDS -->|2. loadKpiSummary| API_JS
        API_JS --> GW --> QS --> ORA
    end

    subgraph FLOW_B["LUỒNG B: XỬ LÝ AI & CHI TIẾT HỒ SƠ (FastAPI Worker :8000)"]
        FASTAPI["FastAPI Backend (api.py)"]
        BUILDER["detail_builder.py (parse_dwg_segments)"]
        MINIO_S3[("MinIO S3 / Local Cache: detail.json")]
        EXCEL_RPT[("Báo Cáo Excel 2 Sheet / ZIP")]
        
        MODAL_DETAIL -->|3. GET /mep_payment/detail/{id}| FASTAPI
        MODAL_DETAIL -->|4. GET /mep_payment/image/{id}/{f}| FASTAPI
        MODAL_DETAIL -->|5. POST /mep_payment/review| FASTAPI
        FASTAPI --> MINIO_S3
        FASTAPI --> BUILDER --> EXCEL_RPT
    end
```

---

## 2. PHÂN TÍCH HÌNH 1: MÀN HÌNH BẢNG ĐIỀU KHIỂN QUẢN TRỊ & 5 THẺ KPI

![Hình 1: Màn hình bảng điều khiển Operation](/d:/Project/Payment_PDF/MEP_OneAI_System/preview_ui_hinh1.png)
*(Tham chiếu ảnh đính kèm của người dùng: `81756566.webp`)*

### 2.1. Khối 5 Thẻ Thống Kê KPI Trên Cùng

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     📦 41       │ │      ✅ 5       │ │      ⚠️ 7       │ │      ⚙️ 0       │ │      ⏳ 29      │
│  Tổng số hồ sơ  │ │ Khớp 100% (0 lỗi)│ │   Có sai lệch   │ │ Đang đối soát AI│ │  Chờ duyệt / Mới │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

#### Code giao diện (Template `operation.vue` dòng 16–55):
```html
<div class="kpi-card" :class="{ active: selectedStatus === 'ALL' }" @click="filterByKpi('ALL')">
  <div class="kpi-num">{{ kpiSummary.total }}</div>
  <div class="kpi-label">Tổng số hồ sơ</div>
</div>
<div class="kpi-card text-success" :class="{ active: selectedStatus === 'OK' }" @click="filterByKpi('OK')">
  <div class="kpi-num text-success">{{ kpiSummary.matched }}</div>
  <div class="kpi-label">Khớp 100% (0 lỗi)</div>
</div>
<div class="kpi-card text-danger" :class="{ active: selectedStatus === 'ERR' }" @click="filterByKpi('ERR')">
  <div class="kpi-num text-danger">{{ kpiSummary.error }}</div>
  <div class="kpi-label">Có sai lệch</div>
</div>
<div class="kpi-card text-warning" :class="{ active: selectedStatus === 'RUNNING' }" @click="filterByKpi('RUNNING')">
  <div class="kpi-num text-warning">{{ kpiSummary.running }}</div>
  <div class="kpi-label">Đang đối soát AI</div>
</div>
<div class="kpi-card text-info" :class="{ active: selectedStatus === 'WAITING' }" @click="filterByKpi('WAITING')">
  <div class="kpi-num text-info">{{ kpiSummary.waiting }}</div>
  <div class="kpi-label">Chờ duyệt / Mới</div>
</div>
```

#### Dữ liệu lấy từ đâu?
* **Hàm gọi Frontend:** `loadKpiSummary()` trong `operation.vue` gọi hàm `get_kpi_summary()` từ file [`mepPayment.js`](file:///d:/Project/Payment_PDF/MEP_OneAI_System/oneai_integration/frontend/operation/js/mepPayment.js).
* **Gateway Endpoint:** Gọi Gateway OneAI: `api.get("/crud/ui", { params: { query_patch: "mep_payment_analysis", query_name: "get_kpi_summary", ... } })`.
* **SQL Backend Oracle (`mep_payment_analysis.py`):**
  ```sql
  SELECT
      COUNT(*) AS TOTAL,
      COUNT(CASE WHEN STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) = 0 THEN 1 END) AS MATCHED,
      COUNT(CASE WHEN STATUS = 'COMPLETED' AND NVL(ERROR_COUNT, 0) > 0 THEN 1 END) AS ERROR,
      COUNT(CASE WHEN STATUS = 'RUNNING' THEN 1 END) AS RUNNING,
      COUNT(CASE WHEN STATUS IN ('WAITING', 'NEW') OR STATUS IS NULL THEN 1 END) AS WAITING
  FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS
  ```
* **Bản đồ con số thực tế:**
  - `TOTAL = 41`: Tổng toàn bộ bản ghi trong bảng Oracle.
  - `MATCHED = 5`: Các hồ sơ đã chạy xong và `ERROR_COUNT = 0`.
  - `ERROR = 7`: Các hồ sơ đã chạy xong và `ERROR_COUNT > 0`.
  - `RUNNING = 0`: Hiện không có tác vụ nào đang chạy ngầm.
  - `WAITING = 29`: Hồ sơ mới tạo đang chờ nạp file Excel.
  - Kiểm tra tính toàn vẹn: $5 + 7 + 0 + 29 = 41$ (Khớp tuyệt đối).

---

### 2.2. Thanh Bộ Lọc & Các Nút Thao Tác (Action Toolbar)
* **Total 41 rows:** Lấy từ biến `total.value`, trả về bởi câu lệnh SQL `searchTotalRow` trong `mep_payment_analysis.py`:
  ```sql
  SELECT COUNT(*) AS TOTAL FROM LOCAL_AI.MEP_PAYMENT_ANALYSIS WHERE ...
  ```
* **Nút `Reload`:** Gọi `loadData()` tải lại bảng ngay lập tức.
* **Nút `+ Insert`:** Gọi `handleInsertRow()` đẩy 1 object rỗng vào đầu bảng `tableData.value.unshift({ isNew: true, STATUS: 'WAITING', ... })`.
* **Nút `Save`:** Thu thập các dòng `isNew` hoặc `isEditing`, gửi payload lên Worker endpoint: `POST http://localhost:8000/mep_payment/save_rows`. Worker gọi `sql.py` thực thi lệnh `INSERT` hoặc `UPDATE` vào Oracle DB.
* **Nút `Delete`:** Lấy danh sách các dòng có checkbox được tích chọn, gọi Worker `POST /mep_payment/delete_rows`. Worker thực hiện xóa trong Oracle và đồng thời dọn dẹp sạch toàn bộ file trên MinIO Storage.

---

### 2.3. Bảng Dữ Liệu Quản Trị Chính (Main Table)

Từng cột trong bảng được bóc tách từ mảng `tableData.value` (sinh ra bởi truy vấn SQL phân trang `getdata_page`):

| Tên Cột Trên Giao Diện | Template Vue (`operation.vue`) | Thuộc Tính DB Oracle | Nguồn Dữ Liệu / Giải Thích |
| :--- | :--- | :--- | :--- |
| **STT** | `{{ row.STT }}` | `RN` (Row Number) | Sinh tự động bằng SQL `ROW_NUMBER() OVER(ORDER BY UPLOAD_TIME ASC NULLS LAST, KEYID ASC)`. |
| **SỐ CÔNG VIỆC (WO)** | `<span class="font-bold font-mono">{{ row.KEYID }}</span>` | `KEYID` (VARCHAR2) | Khóa chính duy nhất đại diện cho hồ sơ thanh toán (VD: `WO825101500403H`, `4444444444442`, `DEmo`). Đã là text tĩnh, chống click nhầm. |
| **TÊN CÔNG VIỆC** | `{{ row.TASK_NAME }}` | `TASK_NAME` | Mô tả gói thầu do kỹ sư nhập (VD: `Lắp đặt đường ống Chiller Phase 2`). Hỗ trợ nhấp đúp chuột để sửa inline. |
| **THÁNG TT** | `{{ row.PAYMENT_MONTH }}` | `PAYMENT_MONTH` | Tháng thanh toán định dạng `YYYY-MM` (VD: `2026-10`, `2026-11`). |
| **NGƯỜI PHỤ TRÁCH** | `{{ row.PIC }}` | `PIC` | Tên kỹ sư phụ trách gói thầu (VD: `Trần Văn B`, `Lê Thị C`). |
| **PART** | `{{ row.PART_NAME }}` | `PART_NAME` | Phân hệ kỹ thuật (VD: `HVAC Part`, `Fire Safety`, `MEP`). |
| **GROUP** | `{{ row.GROUP_NAME }}` | `GROUP_NAME` | Nhóm thi công / Nhà thầu (VD: `Infra Group`, `EHS Groupp`). |
| **TRẠNG THÁI** | `<el-tag>` hoặc `<el-progress>` | `STATUS`, `PROGRESS` | - `COMPLETED`: Tag xanh "Hoàn Tất"<br>- `RUNNING`: Thanh tiến độ % động `PROGRESS` (5% $\rightarrow$ 100%)<br>- `WAITING`: Tag xám "Chờ Duyệt"<br>- `CANCEL`: Tag đỏ "Thất Bại". |
| **TÀI LIỆU ĐÍNH KÈM** | Nút `Upload` (`<el-upload>`) | Sự kiện `handleUploadExcel` | Người dùng chọn file `.xlsx/.xlsm`. Frontend gửi FormData lên Worker: `POST /mep_payment/upload` (gồm file + `KEYID`). Kích hoạt tiến trình AI bóc tách ngầm. |
| **KẾT QUẢ KIỂM TRA** | Badge `<el-tag>` có click | `STATUS`, `ERROR_COUNT` | - Nếu `ERROR_COUNT == 0`: Badge xanh **`✅ Khớp 100%`**.<br>- Nếu `ERROR_COUNT > 0`: Badge đỏ **`❌ Lệch {N} lỗi`**.<br>👉 **Click vào badge này gọi hàm `openDetailModal(row)` để mở Popup chi tiết đối soát.** |
| **CHI TIẾT BÁO CÁO** | Nút tải file & Badge phê duyệt | `RESULT_LINK`, `REVIEW_DECISION` | - Nút `📥 Tải Báo Cáo (.zip)`: Gọi `handleDownloadFile(row)` tải file nén kết quả 2 sheet.<br>- Badge duyệt: `Đã Duyệt` (Approved), `Từ Chối` (Rejected) hoặc cụm 2 nút `Duyệt`/`Hủy` nếu chưa duyệt. |

---

## 3. PHÂN TÍCH HÌNH 2: HEADER MODAL, 4 THẺ THỐNG KÊ & TAB 1: DANH SÁCH LỖI

![Hình 2: Modal Chi tiết - Tab Danh Sách Lỗi](/d:/Project/Payment_PDF/MEP_OneAI_System/preview_ui_hinh2.png)
*(Tham chiếu ảnh đính kèm của người dùng: `367e0b92.webp`)*

Khi người dùng click vào badge **`❌ Lệch 2 lỗi`** trên bảng chính:
1. Hàm `openDetailModal(row)` trong `operation.vue` được kích hoạt.
2. Frontend gọi API Worker:
   ```javascript
   GET http://localhost:8000/mep_payment/detail/{KEYID}?status={STATUS}&error_count={ERROR_COUNT}
   ```
3. Worker kiểm tra cache trên MinIO Storage (`mep_payment/{KEYID}/cache/detail.json`) hoặc đọc file Excel báo cáo cục bộ (`detail_builder.py`). Trả về toàn bộ payload JSON `currentDetail`.

### 3.1. Header Của Hộp Thoại (Modal Header)
* **Tiêu đề lớn:** `Chi Tiết Đối Soát Hồ Sơ: {{ currentTask?.KEYID }}` (VD: `4444444444442`).
* **Dòng thông tin phụ:**
  - Tên công việc: `{{ currentTask?.TASK_NAME }}` (VD: `22222222`).
  - Mã WO: `{{ currentTask?.KEYID }}`.
  - Người phụ trách: `{{ currentTask?.PIC }}` (VD: `4`).
  - Phân việc: `{{ currentTask?.PART_NAME }} / {{ currentTask?.GROUP_NAME }}` (VD: `MEP / 4`).
  - Tháng: `{{ currentTask?.PAYMENT_MONTH }}` (VD: `2026-11`).
  - Công nghệ: `{{ currentDetail.mode }}` $\rightarrow$ Cố định: `MEP AI Vision (Qwen) + 2-Stage Reconciler`.
* **Badge trạng thái góc phải:**
  - Badge 1: `<el-tag type="success">COMPLETED</el-tag>` (Lấy từ `currentTask.STATUS`).
  - Badge 2: `<el-tag effect="plain">ĐÃ DUYỆT</el-tag>` (Lấy từ `currentTask.REVIEW_DECISION`).

---

### 3.2. Khối 4 Thẻ Thống Kê Nhanh (Modal Stats Grid)

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│        2        │ │        5        │ │       34        │ │ 1. Đối Soát...  │
│ Số lỗi phát hiện│ │Bản vẽ AI bóc tách│ │Dòng vật tư k/tra│ │Bảng d/mục nguồn │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

* **Thẻ 1 (Số lỗi phát hiện - 2):**
  - Code: `currentDetail.error_count` (hoặc `currentDetail.errors.length`).
  - Nguồn sinh ra: Đếm số lượng dòng trong Sheet 1 của file Excel có ghi chú lỗi lệch tại cột `Note`.
* **Thẻ 2 (Bản vẽ AI bóc tách - 5):**
  - Code: `currentDetail.drawings_count` (hoặc `currentDetail.groups.length`).
  - Nguồn sinh ra: Đếm số lượng cột bản vẽ CAD thực tế (`0105`, `0205`, `0305`, `0405`, `0505`) sau khi đã loại trừ các cột metadata hệ thống.
* **Thẻ 3 (Dòng vật tư kiểm tra - 34):**
  - Code: `currentDetail.total_items`.
  - Nguồn sinh ra: Tổng số dòng (`len(df_s1)`) trong bảng vật tư Sheet 1 của file Excel.
* **Thẻ 4 (Bảng danh mục nguồn - 1. Đối Soát Bản Vẽ):**
  - Code: `currentDetail.sheet`.
  - Nguồn sinh ra: Tên Sheet đối soát chính trong file Excel báo cáo đầu ra.
* **Badge phân loại sai lệch:** `Lệch khối lượng: 2`:
  - Code: `v-for="[type, count] in errorTypeEntries"`.
  - Nguồn sinh ra: Từ dictionary `currentDetail.error_types` được gom nhóm tự động theo regex từ khóa trong cột `Note` (`lệch`, `mã mồ côi`, `thiếu`, `thừa`, `sai`).

---

### 3.3. Tab 1: Danh Sách Lỗi (Errors Table)

Bảng hiển thị danh sách chi tiết các điểm sai lệch (`currentDetail.errors`):

| STT | Phân Loại Lỗi | Bản Vẽ | Mã SDAC | Tên Vật Tư | ĐVT | SL Dự Toán | SL Bản Vẽ (AI) | Chênh Lệch | Chi Tiết Đối Chiếu |
| :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | `Lệch khối lượng` | **0405** | `M02-00728171` | `BEAM_CLAMP` | each | **59.0** | **58.0** *(Tooltip)* | `Thiếu 1.0` | `Lệch BV 0405 (AI:58.0 \| Ven:59.0)` |
| **2** | `Lệch khối lượng` | **0205** | `M02-21514325` | `U_SUPPORT_HANGER` | m | **1.8** | **1.4** *(Tooltip)* | `Thiếu 0.4` | `Lệch BV 0205 (AI:1.4 \| Ven:1.8)` |

#### Cơ chế code bóc tách chi tiết từng cột:
1. **Bản vẽ (`row.dwg` = `0405`, `0205`):**
   - Hàm `parse_dwg_segments` quét cột `Note` bằng regex: `re.search(r'Lệch BV\s+([\w\-\.]+)', seg)` $\rightarrow$ Trích xuất ra đúng bản vẽ phát sinh sai lệch (`0405`).
2. **Mã SDAC & Tên vật tư (`row.code`, `row.name`):**
   - Đọc từ cột `SDAC Code` và `Description` của dòng bị lỗi trong Sheet 1.
3. **ĐVT (`row.unit`):**
   - Đọc từ cột `Unit` (Đơn vị tính: `each`, `m`, `set`).
4. **SL Dự toán (`row.vendor_qty` = `59.0`, `1.8`):**
   - Regex quét trực tiếp từ phân đoạn lỗi: `re.search(r'Ven(?:dor)?.*?([\d\.]+)', seg)` $\rightarrow$ Lấy ra con số **59.0** mà nhà thầu kê khai riêng cho bản vẽ `0405` (thay vì lấy số tổng cả hồ sơ 101).
5. **SL Bản vẽ (AI) (`row.ai_qty` = `58.0`, `1.4`):**
   - Regex quét từ phân đoạn lỗi: `re.search(r'AI.*?([\d\.]+)', seg)` $\rightarrow$ Lấy ra con số **58.0** mà AI đếm được trên bản vẽ `0405`.
   - **Tooltip icon (i):** Khi rê chuột vào, hiển thị phân rã tất cả các bản vẽ:
     `Bóc tách từ: BV 0305: 10, BV 0405: 58, BV 0505: 33 (Tổng hồ sơ: Dự toán 101.0 | AI 101)`.
6. **Chênh lệch (`row.diff` = `Thiếu 1.0`, `Thiếu 0.4`):**
   - Tính toán trực tiếp bằng công thức toán học: $\Delta = \text{AI} - \text{Vendor} = 58.0 - 59.0 = -1.0 \rightarrow$ Ghi nhãn `Thiếu 1.0` (in màu đỏ đậm).
7. **Chi tiết đối chiếu (`row.msg`):**
   - Ghi nguyên văn nội dung kiểm toán kỹ thuật từ thuật toán reconciler để kỹ sư dễ tra cứu.

---

## 4. PHÂN TÍCH HÌNH 3: TAB 2: ĐỐI CHIẾU THEO BẢN VẼ (ACCORDION ĐA TẦNG)

![Hình 3: Modal Chi tiết - Tab Đối Chiếu Theo Bản Vẽ](/d:/Project/Payment_PDF/MEP_OneAI_System/preview_ui_hinh3.png)
*(Tham chiếu ảnh đính kèm của người dùng: `7e098064.webp`)*

Tab này tổ chức dữ liệu theo từng Bản vẽ kỹ thuật riêng biệt (`currentDetail.groups`), giúp kỹ sư MEP có thể lật mở từng bản vẽ để nghiệm thu:

### 4.1. Thanh Tiêu Đề Accordion (Collapse Item Header)
Mỗi bản vẽ là một thẻ Accordion gập mở:
```html
<el-collapse-item v-for="(g, idx) in currentDetail.groups" :key="idx" :name="String(idx)">
  <template #title>
    <b>Bản vẽ: {{ g.drawing_no }}</b>
    <span class="text-muted ms-3">({{ g.total_items }} vật tư)</span>
    <el-tag v-if="g.error_count > 0" type="danger" size="mini">{{ g.error_count }} lỗi</el-tag>
    <el-tag v-else type="success" size="mini">Khớp 100%</el-tag>
  </template>
```
* **Bản vẽ: 0105:** `(6 vật tư)` - Tag xanh `Khớp 100%`.
* **Bản vẽ: 0205:** `(19 vật tư)` - Tag đỏ `1 lỗi`.
* **Bản vẽ: 0305:** `(14 vật tư)` - Tag xanh `Khớp 100%`.
* **Bản vẽ: 0405:** `(16 vật tư)` - Tag đỏ `1 lỗi`.
* **Bản vẽ: 0505:** `(13 vật tư)` - Tag xanh `Khớp 100%`.

---

### 4.2. Bảng Vật Tư Chi Tiết Trong Từng Bản Vẽ

Dữ liệu của bảng con bên trong (`g.rows`):

| Mã Vật Tư | Tên Vật Tư | ĐVT | SL Dự Toán | SL Bản Vẽ Này | Kết Quả Đối Chiếu |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Bản vẽ 0205:** | | | | | |
| `M02-21514290` | `SHANK_BOLT` | set | **54.0** | **54** | `✓ Khớp` *(Xanh)* |
| `M02-21514325` | `U_SUPPORT_HANGER` | m | **1.8** | **1.4** | `Lệch BV 0205 (AI:1.4 \| Ven:1.8)` *(Đỏ)* |
| `M02-21514366` | `FIRE_STOP_SILICON_SEALANT` | each | **0.4** | **0.4** | `✓ Khớp` *(Xanh)* |
| **Bản vẽ 0405:** | | | | | |
| `M02-00728171` | `BEAM_CLAMP` | each | **59.0** | **58** | `Lệch BV 0405 (AI:58.0 \| Ven:59.0)` *(Đỏ)* |
| `M02-00728171` | `BEAM_CLAMP` (dòng 2) | each | **2.0** | **2** | `✓ Khớp` *(Xanh)* |
| `M02-07354924` | `CR_CLAMP` | each | **58.0** | **58** | `✓ Khớp` *(Xanh)* |

#### Quy tắc gán số liệu của code Python (`detail_builder.py` dòng 180–230):
* **Số lượng AI bóc tách (`row.qty` = `SL Bản vẽ này`):**
  Lấy trực tiếp từ giá trị số tại cột mang tên bản vẽ đó (ví dụ tại cột `0205` dòng đó có số `1.4` hoặc `0.4`).
* **Số lượng Dự toán (`row.vendor_qty` = `SL Dự toán`):**
  - **Trường hợp vật tư Khớp (`ok = True`):**
    Vì không phát sinh sai lệch ở bản vẽ này, nghĩa là Nhà thầu kê khai và AI bóc tách bằng nhau 100%. Do đó, `vendor_qty` được gán chính bằng `f"{num_qty:g}"` (Ví dụ: `0.4` và `0.4`, `58` và `58`).
    👉 *Triệt tiêu hoàn toàn sự vô lý của phiên bản cũ khi vác con số tổng 3.0 hay 101 của cả dự án đặt vào đây.*
  - **Trường hợp vật tư Lệch (`ok = False`):**
    Hệ thống lấy giá trị `matched_seg['ven']` được bóc tách từ chuỗi note (Ví dụ: `1.8` hoặc `59.0`).
* **Kết quả đối chiếu (`row.why`):**
  - Khớp: In ra chữ màu xanh **`✓ Khớp`**.
  - Lệch: In ra dòng cảnh báo màu đỏ chi tiết.

---

## 5. PHÂN TÍCH CHI TIẾT TAB 3: SOI BẢN VẼ / ẢNH TRÍCH XUẤT (LIGHTBOX VIEWER)

Tab 3 phục vụ tính năng "Soi chứng cứ" dành cho Kỹ sư và Lãnh đạo thẩm tra:

```
┌────────────────────────────────────────────────────────────────────────┐
│  🖼️ Tab 3: Soi Bản Vẽ / Ảnh Trích Xuất (19)                            │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │
│  │ 📐 Toàn cảnh 0105  │  │ 📐 Toàn cảnh 0205  │  │ 🔍 Khúc ảnh ROI 1 │  │
│  │ [Ảnh Bản Vẽ CAD]  │  │ [Ảnh Bản Vẽ CAD]  │  │ [Crop Bảng BOM]   │  │
│  │ (Click để phóng to│  │ (Click để phóng to│  │ (Click để phóng to│  │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.1. Code hiển thị giao diện (`operation.vue` dòng 420–460)
```html
<el-tab-pane name="images">
  <template #label>
    <span><i class="bi bi-images me-1"></i> Soi Bản Vẽ / Ảnh Trích Xuất ({{ currentDetail.images?.length || 0 }})</span>
  </template>
  <div class="evidence-grid">
    <div v-for="(img, idx) in currentDetail.images" :key="idx" class="img-card">
      <div class="img-thumb-box">
        <el-image :src="getImageUrl(img.url)" :preview-src-list="[getImageUrl(img.url)]"
          :preview-teleported="true" fit="contain" class="thumb-img" />
      </div>
      <div class="img-caption" :title="img.title">{{ img.title }}</div>
    </div>
  </div>
</el-tab-pane>
```

### 5.2. Luồng gọi dữ liệu & Tải ảnh
1. **Danh sách ảnh (`currentDetail.images`):**
   Trong `detail_builder.py`, hệ thống tự động quét các thư mục ảnh được sinh ra trong quá trình chạy:
   - Thư mục session: `storage/session_{KEYID}/`
   - Thư mục ảnh bản vẽ: `storage/session_{KEYID}/drawings/`
   - Thư mục ảnh bằng chứng: `storage/session_{KEYID}/evidence_images/`
   Trích xuất toàn bộ các file `.png`, `.jpg` thành mảng:
   ```json
   [
     { "url": "drawing_preview_0105.png", "title": "Toàn cảnh Bản vẽ (0105)" },
     { "url": "crop_table_0105_chunk_1.png", "title": "Bảng Danh Mục Vật Tư (0105 - Khúc 1)" }
   ]
   ```
2. **API phục vụ tải ảnh (`api.py` endpoint `/mep_payment/image/{keyid}/{filename}`):**
   - **Ưu tiên 1 (MinIO Storage):** Nếu MinIO đang hoạt động, Worker mở stream `minio_storage.open_object("mep_payment/{KEYID}/images/{filename}")` và trả về `StreamingResponse` với header `Cache-Control: public, max-age=86400`.
   - **Ưu tiên 2 (Local Disk):** Nếu chạy chế độ máy local công ty (DLP), Worker quét trong `PROJECT_STORAGE_DIR / session_{KEYID}` và trả về file bằng `FileResponse`.
3. **Cơ chế chống rung giật (Flicker Fix):**
   Thuộc tính `:preview-teleported="true"` đưa popup phóng to ra ngoài thẻ `<body>`, triệt tiêu hoàn toàn xung đột CSS hover của container cha.

---

## 6. PHÂN TÍCH CHI TIẾT TAB 4: NHẬT KÝ AI (TERMINAL CONSOLE LOGS REALTIME)

Tab 4 là màn hình Console màu đen đóng vai trò là "Hộp đen kỹ thuật" ghi lại toàn bộ nhật ký bóc tách của AI:

```
┌────────────────────────────────────────────────────────────────────────┐
│  💻 Tab 4: Nhật Ký AI                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ > [13:17:58] 🚀 [TASK DEmo] Bắt đầu thực thi Pipeline MEP AI...    │  │
│  │ > [13:18:04] 📄 Đang quét Trang 1/5: Ban_Ve_4._ban_ve_File_1.pdf  │  │
│  │ > [13:18:08] -> ✅ AI đã đọc được Số Bản Vẽ (Tầng 2): '01/05'      │  │
│  │ > [13:18:25] ⏱️ HOÀN TẤT FILE Bản vẽ CAD trong 25.65s             │  │
│  │ > [13:18:35] 🔍 [Vòng 1] Đối soát Bản vẽ vs Bảng khối lượng Vendor  │  │
│  │ > [13:18:37] [KẾT LUẬN] Đã đối soát xong: Phát hiện 2 sai lệch.    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.1. Code hiển thị giao diện (`operation.vue` dòng 465–480)
```html
<el-tab-pane name="logs">
  <template #label>
    <span><i class="bi bi-terminal me-1"></i> Nhật Ký AI</span>
  </template>
  <div class="log-console-box">
    <div v-for="(logLine, lIdx) in currentDetail.logs" :key="lIdx" class="log-line">
      <span class="log-prefix">&gt;</span>
      <span class="log-text">{{ logLine }}</span>
    </div>
  </div>
</el-tab-pane>
```

### 6.2. Dữ liệu lấy từ đâu?
* **Mảng `currentDetail.logs`:**
  - Trong quá trình Worker chạy tác vụ ngầm (`run_ai_task_background` trong `api.py`), toàn bộ stdout/stderr của Python được bắt qua lớp đệm `TeeStream`.
  - Đồng thời, các log tiến trình được ghi liên tục vào file `pipeline.log` trong thư mục session.
  - Khi hoàn tất, mảng log này được đóng gói vào file `detail.json` và lưu lên MinIO Storage.
  - Khi mở Modal, frontend chỉ việc lặp qua mảng `currentDetail.logs` và render từng dòng chữ màu xanh lá/xanh dương trên nền đen `#0d1117`.

---

## 7. PHÂN TÍCH KHUNG PHÊ DUYỆT & THAO TÁC HỒ SƠ (FOOTER MODAL)

Phần chân của Modal chứa toàn bộ quyền hạn tương tác của Kỹ sư thẩm tra:

```
┌────────────────────────────────────────────────────────────────────────┐
│  ✍️ Phê Duyệt & Thao Tác Hồ Sơ                                         │
│  [ Nhập ghi chú duyệt (VD: Lỗi số 2 đã đối soát hiện trường...)      ] │
│                                                                        │
│  [📤 Upload File Excel]  [📥 Tải Báo Cáo (.zip)]  [🔄 Chạy Lại AI]   │
│                                  [✅ Duyệt (Approve)]  [❌ Từ Chối]   │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.1. Chức năng Phê duyệt (Approve / Reject)
* **Ô nhập ghi chú:** Ràng buộc với biến `reviewNote.value` (`<el-input placeholder="Nhập ghi chú duyệt...">`).
* **Nút `✓ Duyệt (Approve)` & `✕ Từ Chối (Reject)`:**
  Gọi hàm `submitReview(decision)`:
  ```javascript
  await api.post("/mep_payment/review", {
    keyid: currentTask.value.KEYID,
    decision: 'APPROVED', // hoặc 'REJECTED'
    note: reviewNote.value,
    reviewer: 'Kỹ sư Thẩm tra OneAI'
  })
  ```
* **Backend Oracle (`sql.py`):**
  Thực thi lệnh `UPDATE` vào bảng `LOCAL_AI.MEP_PAYMENT_ANALYSIS`:
  ```sql
  UPDATE LOCAL_AI.MEP_PAYMENT_ANALYSIS
  SET REVIEW_DECISION = :DECISION,
      REVIEW_NOTE     = :NOTE,
      REVIEW_BY       = :REVIEWER
  WHERE KEYID = :KEYID
  ```
  Sau khi lưu thành công, badge trên bảng tự động đổi sang màu xanh `Đã Duyệt` hoặc màu đỏ `Từ Chối`.

### 7.2. Chức năng Chạy lại AI (Rerun)
* **Nút `🔄 Chạy Lại AI (Rerun)`:**
  Gọi hàm `handleRerun(currentTask.value)`.
  - Frontend gọi Worker: `POST /mep_payment/upload` kích hoạt lại pipeline từ file Excel gốc đã lưu.
  - Trạng thái hồ sơ được reset về `RUNNING (5%)` và quy trình đối soát tự động kích hoạt lại từ đầu.

### 7.3. Chức năng Tải Báo Cáo (.zip)
* **Nút `📥 Tải Báo Cáo (.zip)`:**
  Gọi hàm `handleDownloadFile(currentTask.value)`.
  - Frontend gửi request GET: `http://localhost:8000/mep_payment/files/{KEYID}.zip`.
  - Worker mở stream từ MinIO Storage hoặc Local Disk, đính kèm header `Content-Disposition: attachment; filename={KEYID}.zip`.
  - Trình duyệt tự động mở hộp thoại lưu file zip về máy tính người dùng.

---

## 8. BẢNG MA TRẬN ÁNH XẠ TỔNG THỂ (MASTER UI-TO-CODE MAPPING MATRIX)

Bảng tổng hợp tra cứu nhanh toàn diện từ màn hình giao diện đến mã nguồn:

| Thành phần UI | Tên hiển thị trên màn hình | Biến trong Vue | API Endpoint gọi dữ liệu | File mã nguồn Backend | Cột Database / Nguồn file |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **KPI 1** | `Tổng số hồ sơ (41)` | `kpiSummary.total` | `POST /crud/ui` (Gateway) | `mep_payment_analysis.py` | `COUNT(*)` từ `LOCAL_AI.MEP_PAYMENT_ANALYSIS` |
| **KPI 2** | `Khớp 100% (5)` | `kpiSummary.matched` | `POST /crud/ui` (Gateway) | `mep_payment_analysis.py` | `STATUS='COMPLETED' AND ERROR_COUNT=0` |
| **KPI 3** | `Có sai lệch (7)` | `kpiSummary.error` | `POST /crud/ui` (Gateway) | `mep_payment_analysis.py` | `STATUS='COMPLETED' AND ERROR_COUNT>0` |
| **KPI 4** | `Đang đối soát AI (0)` | `kpiSummary.running` | `POST /crud/ui` (Gateway) | `mep_payment_analysis.py` | `STATUS='RUNNING'` |
| **KPI 5** | `Chờ duyệt / Mới (29)` | `kpiSummary.waiting` | `POST /crud/ui` (Gateway) | `mep_payment_analysis.py` | `STATUS IN ('WAITING', 'NEW')` |
| **Bảng chính** | STT, SỐ CÔNG VIỆC, TÊN CV... | `tableData` | `POST /crud/ui` (Gateway) | `mep_payment_analysis.py` | Câu truy vấn phân trang `getdata_page` |
| **Bảng chính** | Tiến độ % chạy ngầm | `row.PROGRESS` | `POST /crud/ui` (Polling 3s) | `api.py` / `sql.py` | Cột `PROGRESS` (5% $\rightarrow$ 100%) |
| **Bảng chính** | Badge `❌ Lệch 2 lỗi` | `row.ERROR_COUNT` | `POST /crud/ui` (Gateway) | `api.py` | Cột `ERROR_COUNT` trong Oracle DB |
| **Modal Header** | `Mã WO: 4444444444442` | `currentTask.KEYID` | Truyền từ dòng được click | `operation.vue` | Khóa chính `KEYID` |
| **Modal Stats 1** | `Số lỗi phát hiện: 2` | `currentDetail.error_count` | `GET /mep_payment/detail/{id}` | `detail_builder.py` | Đếm dòng có lỗi tại cột `Note` Sheet 1 |
| **Modal Stats 2** | `Bản vẽ AI bóc tách: 5` | `currentDetail.drawings_count`| `GET /mep_payment/detail/{id}` | `detail_builder.py` | Đếm cột bản vẽ CAD (`0105` $\rightarrow$ `0505`) |
| **Modal Stats 3** | `Dòng vật tư kiểm tra: 34` | `currentDetail.total_items` | `GET /mep_payment/detail/{id}` | `detail_builder.py` | `len(df_s1)` trong file Excel báo cáo |
| **Modal Tab 1** | Bảng chi tiết danh sách lỗi | `currentDetail.errors` | `GET /mep_payment/detail/{id}` | `detail_builder.py` | Hàm `parse_dwg_segments` quét cột `Note` |
| **Tab 1: Qty** | SL Dự toán (`59.0`), AI (`58.0`) | `row.vendor_qty`, `ai_qty` | `GET /mep_payment/detail/{id}` | `detail_builder.py` | Regex `Ven:...` và `AI:...` từ phân đoạn lỗi |
| **Tab 1: Tooltip** | `Bóc tách từ: BV 0305: 10...` | `row.ai_breakdown` | `GET /mep_payment/detail/{id}` | `detail_builder.py` | Gom số lượng từ các cột `0105`..`0505` |
| **Modal Tab 2** | Nhóm Accordion từng Bản vẽ | `currentDetail.groups` | `GET /mep_payment/detail/{id}` | `detail_builder.py` | Duyệt `for d in drawing_names:` |
| **Modal Tab 3** | Lưới ảnh bản vẽ / chứng cứ | `currentDetail.images` | `GET /mep_payment/image/{id}/{f}`| `api.py` / `minio_storage.py` | Quét thư mục ảnh hoặc MinIO `images/` |
| **Modal Tab 4** | Console dòng lệnh log AI | `currentDetail.logs` | `GET /mep_payment/detail/{id}` | `api.py` / `detail_builder.py`| File `pipeline.log` / Buffer `TeeStream` |
| **Modal Footer** | Phê duyệt (Approve / Reject) | `reviewNote` | `POST /mep_payment/review` | `api.py` / `sql.py` | Cập nhật `REVIEW_DECISION`, `REVIEW_NOTE` |
| **Modal Footer** | Tải Báo Cáo (.zip) | Trình duyệt Download | `GET /mep_payment/files/{id}.zip`| `api.py` / `minio_storage.py` | Stream file từ MinIO hoặc `FINAL_REPORT_DIR` |

---
*Tài liệu này được biên soạn chuẩn xác theo cấu trúc mã nguồn thực tế của hệ thống `MEP_OneAI_System`. Vui lòng giữ nguyên cấu trúc ánh xạ này khi tiến hành nâng cấp hoặc bàn giao cho các kỹ sư mới tham gia dự án.*

