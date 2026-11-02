# BÍ KÍP TÍCH HỢP HỆ THỐNG MEP AI VÀO ONEAI PORTAL
*Tài liệu hướng dẫn Fullstack (Database -> Backend -> Frontend) dành cho Hệ thống Bóc tách Khối lượng MEP.*

---

## PHẦN 1: THIẾT LẬP DATABASE (ORACLE VIA DBEAVER)

Mọi hệ thống Web đều bắt đầu từ Database. Dựa trên form 10 cột của em, chúng ta sẽ tạo bảng `LOCAL_AI.MEP_WORK_ORDERS`.

### Bước 1.1: Chạy Script SQL tạo bảng
Mở DBeaver, kết nối vào Database Oracle của công ty, mở SQL Editor và chạy đoạn code sau:

```sql
CREATE TABLE LOCAL_AI.MEP_WORK_ORDERS (
    STT NUMBER GENERATED ALWAYS AS IDENTITY, -- Tự động tăng (Oracle 12c+)
    SO_WO VARCHAR2(50) PRIMARY KEY,          -- Khóa chính: Số Work Order (VD: INV2610050006V)
    TEN_CONG_VIEC VARCHAR2(255),             -- Tên task
    THANG_TT VARCHAR2(20),                   -- Tháng thanh toán (VD: 2026-10)
    PIC_NAME VARCHAR2(100),                  -- Người phụ trách
    PIC_PART VARCHAR2(100),                  -- Part tự nhảy
    PIC_GROUP VARCHAR2(100),                 -- Group tự nhảy
    STATUS VARCHAR2(50) DEFAULT 'WAITING',   -- Trạng thái: WAITING, RUNNING, COMPLETED, ERROR
    TOTAL_ERRORS NUMBER DEFAULT 0,           -- Kết quả kiểm tra: Tổng số lỗi
    ERROR_DETAILS VARCHAR2(500),             -- Tóm tắt lỗi (Mã mồ côi, sai lệch...)
    RESULT_LINK VARCHAR2(500),               -- Đường dẫn tải file Excel Report
    CREATE_TIME TIMESTAMP DEFAULT SYSTIMESTAMP -- Thời gian tạo
);

-- Thêm comment cho bảng để team IT khác đọc dễ hiểu
COMMENT ON TABLE LOCAL_AI.MEP_WORK_ORDERS IS 'Bảng quản lý quy trình check MEP Payment';
```

---

## PHẦN 2: THIẾT LẬP BACKEND (FASTAPI & SQL)

Ở môi trường OneAI, file `main_2.py` (chứa Database ảo RAM `TASKS_DB`) của em sẽ bị loại bỏ. Chúng ta sẽ thay nó bằng sự kết hợp giữa **`api.py` (API Endpoint)** và **`sql.py` (Thao tác Oracle)**.

### Bước 2.1: Tham khảo cấu trúc file `sql_mep.py` (Mới)
*File này làm nhiệm vụ nói chuyện với Oracle thay cho `TASKS_DB`.*

```python
# sql_mep.py (Tham khảo)
import cx_Oracle # Thư viện kết nối Oracle

def update_wo_status(so_wo: str, status: str, total_errors: int = 0, error_details: str = "", result_link: str = ""):
    """Cập nhật trạng thái và kết quả sau khi AI chạy xong."""
    # (Đoạn này mô phỏng, em dùng hàm connect DB có sẵn của công ty)
    sql = """
        UPDATE LOCAL_AI.MEP_WORK_ORDERS 
        SET STATUS = :status, 
            TOTAL_ERRORS = :errors, 
            ERROR_DETAILS = :details, 
            RESULT_LINK = :link
        WHERE SO_WO = :wo
    """
    # cursor.execute(sql, status=status, errors=total_errors, details=error_details, link=result_link, wo=so_wo)
    # db.commit()
    print(f"[DB] Đã cập nhật {so_wo} thành {status}")
```

### Bước 2.2: Nhúng vào file `api.py` của hệ thống OneAI
Em sẽ tạo thêm 1 Endpoint mới trong file `api.py` hiện tại của công ty, gọi trực tiếp vào Lõi AI của em.

```python
# api.py (Thêm endpoint này vào)
from fastapi import BackgroundTasks, UploadFile, File, Form
from core.engine_3 import run_mep_pipeline
from sql_mep import update_wo_status
import shutil
import uuid
import os

@app.post("/mep_analysis/uploadfile")
async def upload_mep_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    SO_WO: str = Form(...) # Nhận số WO từ Frontend truyền lên
):
    try:
        # 1. Khởi tạo thư mục Session theo tên SO_WO
        session_dir = f"./tmp_sessions/{SO_WO}"
        os.makedirs(session_dir, exist_ok=True)
        
        excel_path = os.path.join(session_dir, file.filename)
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Cập nhật Oracle Database thành RUNNING
        update_wo_status(so_wo=SO_WO, status="RUNNING")
        
        # 3. Định nghĩa hàm chạy ngầm
        def background_ai_task():
            try:
                # Gọi Core 4 file của Hùng
                final_excel = run_mep_pipeline(
                    pdf_drawing_dir=f"{session_dir}/drawings",
                    pdf_gatepass_dir=f"{session_dir}/gatepass",
                    vendor_excel_path=excel_path,
                    master_data_path=excel_path,
                    output_dir=session_dir,
                    csv_drawing_dir=f"{session_dir}/csv_drawings",
                    csv_gatepass_dir=f"{session_dir}/csv_gatepass",
                    skip_existing=False
                )
                
                # TODO: (Hùng code thêm đoạn đọc file Excel Report để đếm số dòng tô đỏ ra biến total_err)
                total_err = 3 # Ví dụ
                error_msg = "Phát hiện sai số tại 3 mã vật tư"
                link_download = f"/mep_analysis/download/{os.path.basename(final_excel)}"
                
                # Thành công -> Báo DB
                update_wo_status(SO_WO, "COMPLETED", total_err, error_msg, link_download)
                
            except Exception as e:
                # Lỗi sập luồng -> Báo DB
                update_wo_status(SO_WO, "ERROR", 0, str(e), "")

        # 4. Quăng task vào luồng chạy ngầm của FastAPI
        background_tasks.add_task(background_ai_task)
        
        return {"status": "accepted", "message": "Bắt đầu bóc tách AI..."}

    except Exception as e:
        return {"status": "error", "message": str(e)}
```

---

## PHẦN 3: THIẾT LẬP FRONTEND (VUE.JS + ELEMENT PLUS)

Ở thư mục Frontend của OneAI, em sẽ clone file `operation.vue` thành `MepAnalysis.vue`. Code Vue sẽ gồm 3 phần chính: Khung bảng (Table), Hàm Upload, và Hàm Polling.

### Bước 3.1: Mã nguồn UI `MepAnalysis.vue` (Lõi hiển thị)

```vue
<template>
  <div class="table-container">
    <!-- Bảng Grid nền tối của Element Plus -->
    <el-table :data="tableData" border height="700" size="small" style="width: 100%">
      
      <!-- CÁC CỘT THÔNG TIN CƠ BẢN -->
      <el-table-column prop="STT" label="STT" width="60" />
      <el-table-column prop="SO_WO" label="Số Công Việc (WO)" width="150" font-weight="bold"/>
      <el-table-column prop="TEN_CONG_VIEC" label="Tên Công Việc" min-width="150" />
      <el-table-column prop="THANG_TT" label="Tháng TT" width="100" />
      <el-table-column prop="PIC_NAME" label="Người Phụ Trách" width="120" />
      <el-table-column prop="PIC_PART" label="Part" width="100" />
      <el-table-column prop="PIC_GROUP" label="Group" width="100" />

      <!-- CỘT KẾT QUẢ AI -->
      <el-table-column label="Kết Quả Kiểm Tra" width="200">
        <template #default="{ row }">
            <span v-if="row.STATUS === 'COMPLETED' && row.TOTAL_ERRORS === 0" style="color: #67C23A">✅ Hợp lệ 100%</span>
            <span v-else-if="row.STATUS === 'COMPLETED'" style="color: #F56C6C">❌ Có {{ row.TOTAL_ERRORS }} Lỗi</span>
            <span v-else>{{ row.ERROR_DETAILS }}</span> <!-- Hiển thị thông báo khi đang chạy hoặc lỗi -->
        </template>
      </el-table-column>
      
      <el-table-column prop="STATUS" label="Trạng Thái" width="120">
        <template #default="{ row }">
           <el-tag :type="getStatusType(row.STATUS)">{{ row.STATUS }}</el-tag>
        </template>
      </el-table-column>

      <!-- CỘT HÀNH ĐỘNG (UPLOAD & DOWNLOAD) -->
      <el-table-column label="Action" width="120" align="center">
        <template #default="{ row }">
          
          <!-- Trạng Thái 1: Nút Upload khi chưa chạy -->
          <el-upload 
            v-if="row.STATUS === 'WAITING' || row.STATUS === 'ERROR'"
            :show-file-list="false" 
            :auto-upload="false" 
            accept=".xlsx"
            :on-change="(file) => handleUpload(file, row)">
            <el-button type="primary" size="small">Upload File</el-button>
          </el-upload>
          
          <!-- Trạng Thái 2: Đang chạy -> Vòng xoay Loading -->
          <el-button v-else-if="row.STATUS === 'RUNNING'" type="warning" size="small" :loading="true">
            AI Analyzing
          </el-button>
          
          <!-- Trạng Thái 3: Chạy xong -> Nút Tải file -->
          <a v-else-if="row.STATUS === 'COMPLETED' && row.RESULT_LINK" :href="row.RESULT_LINK" download>
             <el-button type="success" size="small">Tải Chi Tiết</el-button>
          </a>

        </template>
      </el-table-column>

    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";

// Biến lưu dữ liệu bảng (Gọi từ API get_data_page_mep của em)
const tableData = ref([]); 
let pollingTimer = null;

// Hàm tô màu cái nhãn Trạng Thái
const getStatusType = (status) => {
    if (status === 'COMPLETED') return 'success';
    if (status === 'RUNNING') return 'warning';
    if (status === 'ERROR') return 'danger';
    return 'info';
};

// Hàm Load Data từ DB (Mỗi 10 giây chạy 1 lần để làm mới giao diện)
const loadData = async () => {
    // Thay bằng API query CSDL MEP_WORK_ORDERS thực tế của em
    // const res = await axios.get('/mep_analysis/get_table_data');
    // tableData.value = res.data;
};

// Bật chế độ Tự động làm mới UI (Polling)
onMounted(() => {
    loadData();
    pollingTimer = setInterval(() => { loadData(); }, 10 * 1000); // 10 giây Reload ngầm
});

onUnmounted(() => { clearInterval(pollingTimer); });

// Kích hoạt khi PIC chọn file Excel
const handleUpload = async (file, row) => {
    const formData = new FormData();
    formData.append("file", file.raw);
    formData.append("SO_WO", row.SO_WO); // Đẩy mã WO lên cho Backend tạo thư mục

    // 1. Cập nhật UI tạm thời thành RUNNING ngay lập tức để user đỡ bấm đúp
    row.STATUS = 'RUNNING'; 
    
    try {
        const res = await axios.post("/mep_analysis/uploadfile", formData);
        if (res.data.status === "accepted") {
            ElMessage.success("Đã gửi File cho AI phân tích. Vui lòng đợi...");
        } else {
            row.STATUS = 'ERROR';
            ElMessage.error(res.data.message);
        }
    } catch (err) {
        row.STATUS = 'ERROR';
        ElMessage.error("Mất kết nối đến Server AI!");
    }
};
</script>
```

---

## TỔNG KẾT LUỒNG HOẠT ĐỘNG (Dành cho Hùng review)

1. **PIC truy cập Web:** Giao diện `MepAnalysis.vue` gọi API lấy data từ Oracle lên, vẽ ra cái bảng 10 cột, trạng thái mặc định là `WAITING`.
2. **PIC bấm nút Upload File:** Tại dòng WO số `INV2610...`, PIC đính kèm file Excel (chứa PDF).
3. **Frontend Hành động:** Hàm `handleUpload` trong Vue được kích hoạt. Nó đổi giao diện thành vòng quay `AI Analyzing` màu vàng (RUNNING), rồi bắn file qua mạng vào cổng `/mep_analysis/uploadfile` của FastAPI.
4. **Backend FastAPI tiếp quản:** Nhận file -> Lưu vào thư mục `tmp_sessions/INV2610...` -> Đẩy tiến trình gọi 4 file Core Python vào chạy ngầm (Background Task). Đồng thời FastAPI chọc vào Oracle Update trạng thái `RUNNING`.
5. **Core Engine làm việc (30 giây):** Rạch file Excel -> Móc PDF -> Cắt OpenCV -> Bắn lên API Vision AI -> Đối soát Excel. Trả ra 1 file Report tô đỏ.
6. **Backend hoàn tất:** Ghi đè vào Oracle: Trạng thái `COMPLETED`, số lỗi, link Download.
7. **Frontend tự động cập nhật:** Hàm `setInterval` trên Vue.js cứ 10 giây quét DB 1 lần. Nó phát hiện trạng thái đã chuyển sang `COMPLETED`, lập tức đổi màu dòng đó thành xanh lá cây và hiện nút **Tải Chi Tiết**.
8. **PIC bấm Tải về:** Hoàn tất chu trình kiểm toán tự động!