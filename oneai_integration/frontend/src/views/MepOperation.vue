<!-- ====================================================================
     GIAO DIỆN DARK THEME ELEMENT PLUS CHO ĐỐI SOÁT THANH TOÁN MEP
     Hỗ trợ đầy đủ: Toolbar Insert/Delete/Save, Inline Edit, Blob Download
     Copy file này vào src/views/ (hoặc src/views/tab/) trong OneAI Frontend
     ==================================================================== -->
<template>
  <div class="mep-container">
    <!-- 1. THANH TÌM KIẾM & BỘ LỌC (TOP FILTER) -->
    <div class="toolbar">
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable style="width: 170px">
        <el-option v-for="item in statusList" :key="item" :label="item" :value="item" />
      </el-select>

      <el-date-picker
        v-model="selectedMonth"
        type="month"
        placeholder="Chọn Tháng Thanh Toán"
        value-format="YYYY-MM"
        style="width: 190px"
      />

      <el-input
        v-model="searchKeyword"
        placeholder="Nhập số WO hoặc tên công việc..."
        clearable
        style="width: 270px"
        @keyup.enter="handleReload"
      />

      <el-button type="primary" @click="handleReload">
        Reload ({{ countdown }}s)
      </el-button>
    </div>

    <!-- 2. THANH CÔNG CỤ QUẢN TRỊ BẢNG (TOOLBAR THEO MẪU 3.WEBP & 4.WEBP) -->
    <div class="table-action-bar">
      <div class="total-count">
        Total: <span class="count-number">{{ total }} rows</span>
      </div>

      <div class="action-buttons">
        <!-- NÚT DELETE (ĐỎ) -->
        <el-button
          type="danger"
          size="small"
          class="btn-delete"
          :disabled="selectedRows.length === 0"
          @click="handleDelete"
        >
          <i class="el-icon-remove-outline"></i> Delete
        </el-button>

        <!-- NÚT INSERT (NỀN TỐI, VIỀN XÁM) -->
        <el-button size="small" class="btn-insert" @click="handleInsert">
          <i class="el-icon-circle-plus-outline"></i> Insert
        </el-button>

        <!-- NÚT EXPORT (.CSV) -->
        <el-button size="small" class="btn-export" @click="handleExportCsv">
          <i class="el-icon-download"></i> Export (.csv)
        </el-button>

        <!-- NÚT SAVE (XANH DƯƠNG) -->
        <el-button type="primary" size="small" class="btn-save" :loading="isSaving" @click="handleSave">
          <i class="el-icon-document-checked"></i> Save
        </el-button>
      </div>
    </div>

    <!-- 3. BẢNG DỮ LIỆU ĐỐI SOÁT (TABLE GRID HỖ TRỢ INLINE EDIT) -->
    <div class="table-container">
      <el-table
        :data="tableData"
        border
        height="680"
        size="small"
        style="width: 100%"
        show-overflow-tooltip
        empty-text="Không có dữ liệu đối soát"
        @selection-change="handleSelectionChange"
      >
        <!-- CỘT CHECKBOX CHỌN DÒNG -->
        <el-table-column type="selection" width="45" align="center" />

        <!-- CỘT STT -->
        <el-table-column prop="STT" label="STT" width="55" align="center" />

        <!-- CỘT: SỐ CÔNG VIỆC (SỐ WO) -->
        <el-table-column prop="KEYID" label="Số Công Việc (WO)" width="160" sortable align="center">
          <template #default="{ row }">
            <el-input
              v-if="row.isNew"
              v-model="row.KEYID"
              placeholder="Nhập số WO..."
              size="mini"
              class="inline-input"
            />
            <el-tag v-else type="info" effect="plain" class="font-bold">{{ row.KEYID }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT: TÊN CÔNG VIỆC -->
        <el-table-column prop="TASK_NAME" label="Tên Công Việc" min-width="190">
          <template #default="{ row }">
            <el-input
              v-if="row.isNew || row.isEditing"
              v-model="row.TASK_NAME"
              placeholder="Tên công việc..."
              size="mini"
              class="inline-input"
            />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.TASK_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: THÁNG THANH TOÁN -->
        <el-table-column prop="PAYMENT_MONTH" label="Tháng TT" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-input
              v-if="row.isNew || row.isEditing"
              v-model="row.PAYMENT_MONTH"
              placeholder="YYYY-MM"
              size="mini"
              class="inline-input"
            />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.PAYMENT_MONTH || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: NGƯỜI PHỤ TRÁCH (PIC) -->
        <el-table-column prop="PIC" label="Người Phụ Trách" width="130" align="center">
          <template #default="{ row }">
            <el-input
              v-if="row.isNew || row.isEditing"
              v-model="row.PIC"
              placeholder="PIC..."
              size="mini"
              class="inline-input"
            />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.PIC || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: PART -->
        <el-table-column prop="PART_NAME" label="Part" width="105" align="center">
          <template #default="{ row }">
            <el-input
              v-if="row.isNew || row.isEditing"
              v-model="row.PART_NAME"
              placeholder="Part..."
              size="mini"
              class="inline-input"
            />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.PART_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: GROUP -->
        <el-table-column prop="GROUP_NAME" label="Group" width="115" align="center">
          <template #default="{ row }">
            <el-input
              v-if="row.isNew || row.isEditing"
              v-model="row.GROUP_NAME"
              placeholder="Group..."
              size="mini"
              class="inline-input"
            />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.GROUP_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: TRẠNG THÁI (STATUS) -->
        <el-table-column prop="STATUS" label="Trạng Thái" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.STATUS === 'COMPLETED'" type="success" effect="dark">Hoàn Tất</el-tag>
            <el-tag v-else-if="row.STATUS === 'RUNNING'" type="warning" effect="dark">Đang Xử Lý</el-tag>
            <el-tag v-else-if="row.STATUS === 'WAITING'" type="info">Chờ Duyệt</el-tag>
            <el-tag v-else type="danger">{{ row.STATUS || 'Mới' }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT: TÀI LIỆU ĐÍNH KÈM (UPLOAD FILE EXCEL) -->
        <el-table-column label="Tài Liệu Đính Kèm" width="130" align="center">
          <template #default="{ row }">
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              accept=".xlsx,.xlsm"
              :on-change="(file) => handleUploadExcel(file, row)"
              :disabled="row.STATUS === 'RUNNING' || row.isNew"
            >
              <el-button
                type="primary"
                size="mini"
                :loading="row.STATUS === 'RUNNING'"
                :disabled="row.STATUS === 'RUNNING' || row.isNew"
              >
                {{ row.STATUS === 'RUNNING' ? 'Đang chạy...' : '+ Upload File' }}
              </el-button>
            </el-upload>
          </template>
        </el-table-column>

        <!-- CỘT: KẾT QUẢ KIỂM TRA -->
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
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>

        <!-- CỘT: CHI TIẾT BÁO CÁO & DUYỆT (BLOB DOWNLOAD CHỐNG CHẶN) -->
        <el-table-column label="Chi Tiết Báo Cáo" min-width="210" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <!-- Nút tải file báo cáo bằng Blob -->
              <el-button
                v-if="row.RESULT_LINK"
                type="text"
                size="small"
                class="download-btn"
                @click="handleDownloadFile(row)"
              >
                📥 Tải Báo Cáo (.zip)
              </el-button>

              <!-- Phê duyệt / Từ chối -->
              <div style="margin-top: 4px;">
                <el-tag v-if="row.REVIEW_DECISION === 'APPROVED'" type="success" size="mini">Đã Duyệt</el-tag>
                <el-tag v-else-if="row.REVIEW_DECISION === 'REJECTED'" type="danger" size="mini">Từ Chối</el-tag>
                <div v-else style="display: inline-flex; gap: 4px;">
                  <el-button type="success" size="mini" @click="handleReview(row, 'APPROVED')">Duyệt</el-button>
                  <el-button type="danger" size="mini" @click="handleReview(row, 'REJECTED')">Hủy</el-button>
                </div>
              </div>
            </div>
            <span v-else-if="row.REASON" class="text-reason">{{ row.REASON }}</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 4. THANH PHÂN TRANG -->
      <div class="pagination-bar">
        <el-button size="small" @click="goFirst" :disabled="page === 1">First</el-button>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[15, 30, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
        <el-button size="small" @click="goLast" :disabled="page >= totalPages">Last</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { get_total_row, get_data_page, save_mep_rows, delete_mep_rows } from '@/js/mepPayment'

// Địa chỉ Worker API (tự động thích ứng local hoặc reverse proxy)
const FASTAPI_BASE_URL = window.location.port === '8000' ? '' : 'http://127.0.0.1:8000'

// Bộ lọc
const selectedStatus = ref('')
const selectedMonth = ref('')
const searchKeyword = ref('')
const statusList = ['ALL', 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL']

// Bảng dữ liệu & Phân trang
const tableData = ref([])
const selectedRows = ref([])
const page = ref(1)
const pageSize = ref(15)
const total = ref(0)
const countdown = ref(10)
const isSaving = ref(false)
let timer = null
let countdownTimer = null

// 1. TẢI DỮ LIỆU TỪ BACKEND
const loadData = async () => {
  try {
    const data = await get_data_page(
      page.value, pageSize.value,
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
    tableData.value = (data || []).map(row => ({
      ...row,
      isNew: false,
      isEditing: false
    }))
  } catch (err) {
    console.error("Lỗi tải bảng dữ liệu MEP:", err)
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
    console.error("Lỗi lấy tổng số dòng:", err)
  }
}

const handleReload = async () => {
  await loadData()
  await loadTotal()
  countdown.value = 10
}

// 2. CHỌN DÒNG TRONG BẢNG (SELECTION)
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 3. THAO TÁC INSERT (THÊM DÒNG MỚI THEO ẢNH 4.WEBP - THÊM VÀO CUỐI BẢNG)
const handleInsert = () => {
  const newRow = {
    STT: (page.value - 1) * pageSize.value + tableData.value.length + 1,
    KEYID: '',
    TASK_NAME: '',
    PAYMENT_MONTH: selectedMonth.value || new Date().toISOString().slice(0, 7),
    PIC: '',
    PART_NAME: 'MEP',
    GROUP_NAME: '',
    STATUS: 'WAITING',
    ERROR_COUNT: 0,
    isNew: true,
    isEditing: true
  }
  // Thêm dòng mới vào CUỐI bảng hiện tại (Ví dụ đang có 3 dòng thì vào vị trí số 4, không đẩy dòng cũ)
  tableData.value.push(newRow)
  total.value += 1
  ElMessage.info("Đã thêm 1 dòng mới vào cuối bảng. Vui lòng nhập thông tin và bấm [Save].")
}

// 4. THAO TÁC SAVE (LƯU CÁC DÒNG MỚI HOẶC SỬA XUỐNG DB)
const handleSave = async () => {
  const modifiedRows = tableData.value.filter(r => r.isNew || r.isEditing)
  if (modifiedRows.length === 0) {
    ElMessage.info("Không có dòng nào thay đổi để lưu.")
    return
  }

  // Kiểm tra không để trống KEYID
  for (const r of modifiedRows) {
    if (!r.KEYID || !r.KEYID.trim()) {
      ElMessage.warning("Vui lòng nhập Số Công Việc (KEYID) trước khi lưu!")
      return
    }
  }

  isSaving.value = true
  try {
    // Gửi danh sách dòng xuống backend
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/save_rows`, {
      rows: modifiedRows.map(r => ({
        KEYID: r.KEYID,
        TASK_NAME: r.TASK_NAME,
        PAYMENT_MONTH: r.PAYMENT_MONTH,
        PIC: r.PIC,
        PART_NAME: r.PART_NAME,
        GROUP_NAME: r.GROUP_NAME,
        STATUS: r.STATUS || 'WAITING'
      }))
    })

    ElMessage.success(res.data?.message || "Lưu dữ liệu thành công!")
    await handleReload()
  } catch (err) {
    console.error("Lỗi khi lưu dòng:", err)
    ElMessage.error(err.response?.data?.detail || "Lỗi khi lưu dữ liệu xuống Database!")
  } finally {
    isSaving.value = false
  }
}

// 5. THAO TÁC DELETE (XÓA CÁC DÒNG ĐƯỢC CHỌN)
const handleDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("Vui lòng chọn ít nhất 1 dòng để xóa.")
    return
  }

  try {
    await ElMessageBox.confirm(
      `Bạn có chắc chắn muốn xóa ${selectedRows.value.length} dòng đã chọn?`,
      'Xác nhận xóa',
      { confirmButtonText: 'Xác nhận', cancelButtonText: 'Hủy', type: 'warning' }
    )

    // Tách dòng mới tạo (chưa lưu vào DB) và dòng đã có trong DB
    const newKeys = selectedRows.value.filter(r => r.isNew).map(r => r.KEYID)
    const dbKeys = selectedRows.value.filter(r => !r.isNew && r.KEYID).map(r => r.KEYID)

    // Xóa các dòng mới khỏi RAM
    if (newKeys.length > 0) {
      tableData.value = tableData.value.filter(r => !selectedRows.value.includes(r))
      total.value = Math.max(0, total.value - newKeys.length)
    }

    // Nếu có dòng trong DB, gọi API xóa
    if (dbKeys.length > 0) {
      const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/delete_rows`, { keyids: dbKeys })
      ElMessage.success(res.data?.message || `Đã xóa ${dbKeys.length} dòng thành công!`)
      await handleReload()
    } else {
      ElMessage.success("Đã xóa dòng tạm khỏi bảng.")
    }
  } catch (err) {
    if (err !== 'cancel') {
      console.error("Lỗi xóa dòng:", err)
      ElMessage.error(err.response?.data?.detail || err.message || "Không thể xóa dòng đã chọn!")
    }
  }
}

// 6. THAO TÁC TẢI BÁO CÁO (BLOB DOWNLOAD CHỐNG CHẶN)
const handleDownloadFile = async (row) => {
  if (!row.RESULT_LINK) return

  try {
    ElMessage.info("Đang chuẩn bị tải file báo cáo...")
    const url = row.RESULT_LINK.startsWith('http') 
      ? row.RESULT_LINK 
      : `${FASTAPI_BASE_URL}${row.RESULT_LINK}`

    // Tải mảng byte nhị phân Blob
    const res = await axios.get(url, { responseType: 'blob' })

    const contentType = res.headers['content-type'] || 'application/zip'
    const blob = new Blob([res.data], { type: contentType })
    const blobUrl = window.URL.createObjectURL(blob)

    const filename = row.RESULT_LINK.split('/').pop() || `Bao_Cao_${row.KEYID}.zip`
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)

    ElMessage.success("Tải file thành công!")
  } catch (err) {
    console.error("Lỗi download file:", err)
    ElMessage.error("Không thể tải file báo cáo. Vui lòng kiểm tra lại server!")
  }
}

// 7. XUẤT CSV (EXPORT .CSV)
const handleExportCsv = () => {
  if (tableData.value.length === 0) {
    ElMessage.warning("Không có dữ liệu để xuất file CSV.")
    return
  }

  const headers = ['STT', 'KEYID', 'TASK_NAME', 'PAYMENT_MONTH', 'PIC', 'PART_NAME', 'GROUP_NAME', 'STATUS', 'ERROR_COUNT']
  const csvContent = [
    headers.join(','),
    ...tableData.value.map(row => [
      row.STT,
      `"${row.KEYID || ''}"`,
      `"${row.TASK_NAME || ''}"`,
      `"${row.PAYMENT_MONTH || ''}"`,
      `"${row.PIC || ''}"`,
      `"${row.PART_NAME || ''}"`,
      `"${row.GROUP_NAME || ''}"`,
      `"${row.STATUS || ''}"`,
      row.ERROR_COUNT || 0
    ].join(','))
  ].join('\n')

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `MEP_Payment_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success("Đã xuất file CSV thành công!")
}

// 8. TIẾP NHẬN UPLOAD FILE EXCEL
const handleUploadExcel = async (file, row) => {
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xlsm')) {
    ElMessage.error("Chỉ chấp nhận file Excel (.xlsx / .xlsm)")
    return
  }

  const formData = new FormData()
  formData.append("file", file.raw)
  formData.append("KEYID", row.KEYID)

  row.STATUS = 'RUNNING'
  row.REASON = 'Đang đẩy file lên AI Worker...'

  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData)
    ElMessage.success(res.data.message || "Tải lên thành công! AI đang bóc tách ngầm.")
    countdown.value = 10
  } catch (err) {
    row.STATUS = 'WAITING'
    row.REASON = 'Lỗi upload file'
    ElMessage.error("Lỗi khi kết nối Worker: " + (err.response?.data?.detail || err.message))
  }
}

// 9. DUYỆT / TỪ CHỐI (REVIEW WORKFLOW)
const handleReview = async (row, decision) => {
  try {
    await axios.post(`${FASTAPI_BASE_URL}/mep_payment/review`, {
      keyid: row.KEYID,
      decision: decision,
      reviewer: 'Engineer'
    })
    row.REVIEW_DECISION = decision
    ElMessage.success(`Đã lưu trạng thái: ${decision}`)
  } catch (err) {
    ElMessage.error("Lỗi lưu quyết định duyệt: " + err.message)
  }
}

// Vòng đời Polling
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
</script>

<style scoped>
.mep-container {
  padding: 14px;
  background-color: #141414;
  color: #E5EAF3;
  min-height: 100vh;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

/* THANH CÔNG CỤ TOOLBAR THEO ẢNH 3.WEBP & 4.WEBP */
.table-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 0 4px;
}

.total-count {
  font-size: 13px;
  color: #A3A6AD;
}

.count-number {
  color: #E5EAF3;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-delete {
  background-color: #F56C6C;
  border-color: #F56C6C;
  color: #FFF;
  font-weight: 500;
}

.btn-insert, .btn-export {
  background-color: #262727;
  border-color: #4C4D4F;
  color: #E5EAF3;
}

.btn-insert:hover, .btn-export:hover {
  background-color: #363637;
  border-color: #606266;
  color: #409EFF;
}

.btn-save {
  background-color: #409EFF;
  border-color: #409EFF;
  color: #FFF;
  font-weight: 500;
}

.table-container {
  width: 100%;
  overflow-x: auto;
}

.font-bold {
  font-weight: 600;
}

.cell-text {
  cursor: pointer;
  display: inline-block;
  width: 100%;
}

.cell-text:hover {
  color: #409EFF;
  text-decoration: underline;
}

.inline-input :deep(.el-input__inner) {
  background-color: #1D1E1F;
  border-color: #409EFF;
  color: #FFF;
}

.download-btn {
  color: #67C23A;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}

.download-btn:hover {
  color: #85CE61;
}

.text-reason {
  color: #F56C6C;
  font-size: 11px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

/* =========================================================================
   TÙY CHỈNH CHECKBOX ALL TRÊN HEADER BẢNG:
   Khi chỉ chọn 1 hoặc vài dòng (Indeterminate), KHÔNG sáng xanh gây hiểu nhầm,
   Chỉ khi CHỌN TẤT CẢ (Select All) thì mới sáng xanh và hiện biểu tượng dấu tích (✓).
   ========================================================================= */
:deep(.el-table th.el-table__cell .el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: transparent !important;
  border-color: #4C4D4F !important;
}

:deep(.el-table th.el-table__cell .el-checkbox__input.is-indeterminate .el-checkbox__inner::before),
:deep(.el-table th.el-table__cell .el-checkbox__input.is-indeterminate .el-checkbox__inner::after) {
  display: none !important;
}
</style>
