<template>
  <div class="mep-container">
    <!-- 1. THANH TÌM KIẾM & BỘ LỌC (TOP FILTER) -->
    <div class="toolbar">
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable style="width: 170px">
        <el-option v-for="item in statusList" :key="item" :label="item" :value="item" />
      </el-select>

      <el-date-picker v-model="selectedMonth" type="month" placeholder="Chọn Tháng Thanh Toán" value-format="YYYY-MM"
        style="width: 190px" />

      <el-input v-model="searchKeyword" placeholder="Nhập số WO hoặc tên công việc..." clearable style="width: 270px"
        @keyup.enter="handleReload" />
    </div>

    <!-- 2. THANH CÔNG CỤ QUẢN TRỊ BẢNG (ACTION BAR THEO THỨ TỰ & MÀU SẮC UX CHUẨN) -->
    <div class="table-action-bar">
      <div class="total-count">
        Total: <span class="count-number">{{ total }} rows</span>
      </div>

      <div class="action-buttons">
        <!-- 1. NÚT RELOAD (LÀM MỚI BẢNG) -->
        <el-button :size="buttonSize" class="btn-reload" :loading="isLoading" @click="handleReload">
          <i class="bi bi-arrow-repeat me-1"></i> Reload
        </el-button>

        <!-- 2. NÚT INSERT (THÊM DÒNG MỚI VÀO CUỐI BẢNG) -->
        <el-button :size="buttonSize" class="btn-insert" @click="handleInsert">
          <i class="bi bi-plus-circle me-1"></i> Insert
        </el-button>

        <!-- 3. NÚT SAVE (LƯU VÀO DB - NÚT CHÍNH NỔI BẬT NHẤT) -->
        <el-button type="primary" :size="buttonSize" class="btn-save" :loading="isSaving" @click="handleSave">
          <i class="bi bi-floppy me-1"></i> Save
        </el-button>

        <!-- 4. NÚT EXPORT (.CSV) -->
        <el-button :size="buttonSize" class="btn-export" @click="handleExportCsv">
          <i class="bi bi-box-arrow-in-down me-1"></i> Export (.csv)
        </el-button>

        <!-- VẠCH NGĂN CÁCH NHẸ TRÁNH BẤM NHẦM NÚT XÓA -->
        <span class="btn-divider"></span>

        <!-- 5. NÚT DELETE (XÓA DÒNG - ĐẶT Ở CUỐI CÙNG, MÀU ĐỎ CẢNH BÁO) -->
        <el-button type="danger" :size="buttonSize" class="btn-delete" :disabled="selectedRows.length === 0"
          @click="handleDelete">
          <i class="bi bi-dash-circle me-1"></i> Delete
        </el-button>
      </div>
    </div>

    <!-- 3. BẢNG DỮ LIỆU ĐỐI SOÁT (TABLE GRID HỖ TRỢ INLINE EDIT) -->
    <div class="table-container">
      <el-table ref="tableRef" :data="tableData" border height="680" size="small" style="width: 100%"
        show-overflow-tooltip empty-text="Không có dữ liệu đối soát" @selection-change="handleSelectionChange">
        <!-- CỘT CHECKBOX CHỌN DÒNG -->
        <el-table-column type="selection" width="45" align="center" />

        <!-- CỘT STT -->
        <el-table-column prop="STT" label="STT" width="55" align="center" />

        <!-- CỘT: SỐ CÔNG VIỆC (SỐ WO) -->
        <el-table-column prop="KEYID" label="SỐ CÔNG VIỆC (WO)" width="160" sortable align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew" v-model="row.KEYID" placeholder="Nhập số WO..." size="mini"
              class="inline-input" />
            <el-tag v-else type="info" effect="plain" class="font-bold">{{ row.KEYID }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT: TÊN CÔNG VIỆC -->
        <el-table-column prop="TASK_NAME" label="TÊN CÔNG VIỆC" min-width="190">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.TASK_NAME" placeholder="Tên công việc..."
              size="mini" class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.TASK_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: THÁNG THANH TOÁN -->
        <el-table-column prop="PAYMENT_MONTH" label="THÁNG TT" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.PAYMENT_MONTH" placeholder="YYYY-MM" size="mini"
              class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.PAYMENT_MONTH || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: NGƯỜI PHỤ TRÁCH (PIC) -->
        <el-table-column prop="PIC" label="NGƯỜI PHỤ TRÁCH" width="130" align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.PIC" placeholder="PIC..." size="mini"
              class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.PIC || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: PART -->
        <el-table-column prop="PART_NAME" label="PART" width="105" align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.PART_NAME" placeholder="Part..." size="mini"
              class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.PART_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: GROUP -->
        <el-table-column prop="GROUP_NAME" label="GROUP" width="115" align="center">
          <template #default="{ row }">
            <el-input v-if="row.isNew || row.isEditing" v-model="row.GROUP_NAME" placeholder="Group..." size="mini"
              class="inline-input" />
            <span v-else class="cell-text" @dblclick="row.isEditing = true">{{ row.GROUP_NAME || '-' }}</span>
          </template>
        </el-table-column>

        <!-- CỘT: TRẠNG THÁI (STATUS) -->
        <el-table-column prop="STATUS" label="TRẠNG THÁI" width="135" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.STATUS === 'COMPLETED'" type="success" effect="light">Hoàn Tất</el-tag>
            <div v-else-if="row.STATUS === 'RUNNING'" class="progress-cell">
              <el-tag type="warning" effect="dark" size="mini">Đang Xử Lý</el-tag>
              <el-progress :percentage="Number(row.PROGRESS) || 0" :stroke-width="6" :show-text="true"
                class="progress-bar-inline" />
            </div>
            <el-tag v-else-if="row.STATUS === 'WAITING'" type="info">Chờ Duyệt</el-tag>
            <el-tag v-else type="danger">{{ row.STATUS || 'Mới' }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT: TÀI LIỆU ĐÍNH KÈM (UPLOAD FILE EXCEL) -->
        <el-table-column label="TÀI LIỆU ĐÍNH KÈM" width="135" align="center">
          <template #default="{ row }">
            <el-upload :show-file-list="false" :auto-upload="false" accept=".xlsx,.xlsm"
              :on-change="(file) => handleUploadExcel(file, row)"
              :disabled="row.STATUS === 'RUNNING' || row.isNew">
              <el-button class="btn-upload-file" :size="buttonSize" :loading="row.STATUS === 'RUNNING'"
                :disabled="row.STATUS === 'RUNNING' || row.isNew">
                <i class="bi bi-cloud-arrow-up me-1"></i>
                {{ row.STATUS === 'RUNNING' ? 'Đang chạy...' : 'Upload' }}
              </el-button>
            </el-upload>
          </template>
        </el-table-column>

        <!-- CỘT: KẾT QUẢ KIỂM TRA -->
        <el-table-column label="KẾT QUẢ KIỂM TRA" width="150" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <el-tag v-if="row.ERROR_COUNT === 0" type="success" effect="light">
                ✅ Khớp 100% (0 lỗi)
              </el-tag>
              <el-tag v-else type="danger" effect="light">
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
        <el-table-column label="CHI TIẾT BÁO CÁO" min-width="210" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <!-- Nút tải file báo cáo bằng Blob -->
              <el-button v-if="row.RESULT_LINK" type="text" size="small" class="download-btn"
                @click="handleDownloadFile(row)">
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
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 30, 50, 100]"
          :total="total" layout="total, sizes, prev, pager, next, jumper" @current-change="handlePageChange"
          @size-change="handleSizeChange" />
        <el-button size="small" @click="goLast" :disabled="page >= totalPages">Last</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { get_total_row, get_data_page, save_mep_rows, delete_mep_rows } from '../js/mepPayment'

// Địa chỉ Worker API & Kích thước nút bấm
const FASTAPI_BASE_URL = 'http://127.0.0.1:8000'
const buttonSize = ref('small')
const MAX_UPLOAD_SIZE_MB = 50 // Giới hạn file Excel upload tối đa 50MB

// Bộ lọc
const selectedStatus = ref('')
const selectedMonth = ref('')
const searchKeyword = ref('')
const statusList = ['ALL', 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL']

// Bảng dữ liệu & Phân trang
const tableRef = ref(null)
const tableData = ref([])
const selectedRows = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const isSaving = ref(false)
const isLoading = ref(false)

// Biến Smart Polling (Thăm dò thông minh tự động bật/tắt)
let smartPollTimer = null
let smartPollCount = 0
const MAX_POLL_COUNT = 200 // Tối đa 10 phút (200 * 3s)

const stopSmartPolling = () => {
  if (smartPollTimer) {
    clearInterval(smartPollTimer)
    smartPollTimer = null
    smartPollCount = 0
  }
}

const startSmartPollingIfNeeded = () => {
  const hasRunning = tableData.value.some(r => r.STATUS === 'RUNNING')
  if (!hasRunning) {
    stopSmartPolling()
    return
  }

  if (smartPollTimer) return // Đã bật rồi thì không tạo thêm interval trùng lặp

  smartPollCount = 0
  console.log("⚡ [Smart Polling] Kích hoạt thăm dò tiến độ mỗi 3 giây...")

  smartPollTimer = setInterval(async () => {
    smartPollCount++
    if (smartPollCount > MAX_POLL_COUNT) {
      console.warn("⚠️ [Smart Polling] Quá thời gian chờ (10 phút), tự động dừng.")
      stopSmartPolling()
      return
    }

    // Nếu người dùng đang thêm dòng mới (isNew), tạm ngưng không đè dữ liệu
    const hasNewRow = tableData.value.some(r => r.isNew)
    if (hasNewRow) return

    try {
      const data = await get_data_page(
        page.value, pageSize.value,
        selectedStatus.value || 'ALL',
        selectedMonth.value || 'ALL',
        searchKeyword.value || 'ALL'
      )
      if (data && data.length > 0) {
        tableData.value = data.map(newRow => {
          const oldRow = tableData.value.find(r => r.KEYID === newRow.KEYID)
          return {
            ...newRow,
            isNew: false,
            isEditing: oldRow ? oldRow.isEditing : false
          }
        })
      }

      // Khi không còn dòng nào RUNNING nữa -> Dừng polling ngay lập tức
      const stillRunning = tableData.value.some(r => r.STATUS === 'RUNNING')
      if (!stillRunning) {
        console.log("🎉 [Smart Polling] Tất cả tác vụ AI đã hoàn tất. Tắt polling.")
        stopSmartPolling()
        loadTotal()
      }
    } catch (err) {
      console.error("[Smart Polling Error]", err)
    }
  }, 3000)
}

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
    startSmartPollingIfNeeded()
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
  isLoading.value = true
  try {
    await loadData()
    await loadTotal()
  } finally {
    isLoading.value = false
  }
}

// 2. CHỌN DÒNG TRONG BẢNG (SELECTION)
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 3. THAO TÁC INSERT (THÊM DÒNG MỚI VÀO CUỐI BẢNG)
const handleInsert = () => {
  const newRow = {
    STT: tableData.value.length + 1,
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
  // Thêm dòng mới vào cuối bảng
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

  // 1. Kiểm tra không để trống KEYID
  for (const r of modifiedRows) {
    if (!r.KEYID || !String(r.KEYID).trim()) {
      ElMessage.warning("Vui lòng nhập Số Công Việc (KEYID) trước khi lưu!")
      return
    }
  }

  // 2. Kiểm tra trùng lặp Số Công Việc (KEYID) ngay trên bảng giao diện
  for (const r of modifiedRows) {
    if (r.isNew) {
      const isDuplicate = tableData.value.some(
        item => item !== r && String(item.KEYID).trim().toUpperCase() === String(r.KEYID).trim().toUpperCase()
      )
      if (isDuplicate) {
        ElMessage.error(`Số công việc (KEYID) "${r.KEYID}" đã tồn tại! Vui lòng nhập mã khác.`)
        return
      }
    }
  }

  isSaving.value = true
  try {
    const payload = {
      rows: modifiedRows.map(r => ({
        KEYID: String(r.KEYID).trim(),
        TASK_NAME: String(r.TASK_NAME || '').trim(),
        PAYMENT_MONTH: String(r.PAYMENT_MONTH || '').trim(),
        PIC: String(r.PIC || '').trim(),
        PART_NAME: String(r.PART_NAME || '').trim(),
        GROUP_NAME: String(r.GROUP_NAME || '').trim(),
        STATUS: r.STATUS || 'WAITING',
        isNew: !!r.isNew
      }))
    }
    console.log("👉 [Save] Đang gửi payload xuống backend:", payload)
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/save_rows`, payload)
    console.log("👉 [Save] Phản hồi thành công từ backend:", res.data)

    ElMessage.success(res.data?.message || "Lưu dữ liệu thành công!")
    await handleReload()
  } catch (err) {
    console.error("Lỗi khi lưu dòng:", err)
    ElMessage.error(err.response?.data?.detail || err.message || "Lỗi khi lưu dữ liệu xuống Database!")
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

// 8. TIẾP NHẬN UPLOAD FILE EXCEL (CÓ CHECK DUNG LƯỢNG FILE TỐI ĐA 50MB)
const handleUploadExcel = async (file, row) => {
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xlsm')) {
    ElMessage.error("Chỉ chấp nhận file Excel (.xlsx / .xlsm)")
    return
  }

  if (file.size && file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
    ElMessage.error(`Dung lượng file (${(file.size / (1024 * 1024)).toFixed(1)}MB) vượt quá giới hạn cho phép ${MAX_UPLOAD_SIZE_MB}MB!`)
    return
  }

  const formData = new FormData()
  formData.append("file", file.raw)
  formData.append("KEYID", row.KEYID)

  row.STATUS = 'RUNNING'
  row.PROGRESS = 5
  row.REASON = 'Đang đẩy file lên AI Worker...'
  startSmartPollingIfNeeded()

  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData)
    ElMessage.success(res.data.message || "Tải lên thành công! AI đang bóc tách ngầm.")
    startSmartPollingIfNeeded()
  } catch (err) {
    row.STATUS = 'WAITING'
    row.PROGRESS = 0
    row.REASON = 'Lỗi upload file'
    stopSmartPolling()
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

// Vòng đời
onMounted(() => {
  handleReload()
})

onUnmounted(() => {
  stopSmartPolling()
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
  color: #E5EAF3;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

/* THANH CÔNG CỤ QUẢN TRỊ BẢNG (ACTION BAR) */
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
  align-items: center;
  gap: 8px;
}

/* Vạch ngăn cách nhẹ để tách biệt nút Delete ra khỏi các nút khác */
.btn-divider {
  display: inline-block;
  width: 1px;
  height: 20px;
  background-color: #4C4D4F;
  margin: 0 4px;
}

/* 1. Nút Reload: Nền tối, viền xám trung tính */
.btn-reload {
  background-color: #262727;
  border-color: #4C4D4F;
  color: #E5EAF3;
}
.btn-reload:hover {
  background-color: #363637;
  border-color: #606266;
  color: #409EFF;
}

/* 2. Nút Insert: Nền tối viền xanh ngọc nổi bật nét thêm mới tích cực */
.btn-insert {
  background-color: #1A2E22;
  border-color: #2E7D32;
  color: #4ADE80;
  font-weight: 500;
}
.btn-insert:hover {
  background-color: #2E7D32;
  border-color: #4ADE80;
  color: #FFF;
}

/* 3. Nút Save: Nút Primary trung tâm CTA, màu xanh dương nổi bật nhất */
.btn-save {
  background-color: #409EFF;
  border-color: #409EFF;
  color: #FFF;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.25);
}
.btn-save:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

/* 4. Nút Export: Nền tối, viền xám tiện ích */
.btn-export {
  background-color: #262727;
  border-color: #4C4D4F;
  color: #E5EAF3;
}
.btn-export:hover {
  background-color: #363637;
  border-color: #606266;
  color: #409EFF;
}

/* 5. Nút Delete: Đặt cuối cùng, màu đỏ cảnh báo nguy hiểm */
.btn-delete {
  background-color: #F56C6C;
  border-color: #F56C6C;
  color: #FFF;
  font-weight: 500;
}
.btn-delete:hover:not(:disabled) {
  background-color: #f78989;
  border-color: #f78989;
}
.btn-delete:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* NÚT UPLOAD FILE TRONG TỪNG DÒNG CỦA BẢNG: DÙNG MÀU TÍM XANH DỊU MẮT */
.btn-upload-file {
  background-color: #2c3e50;
  border-color: #34495e;
  color: #409EFF;
  font-weight: 500;
}
.btn-upload-file:hover:not(:disabled) {
  background-color: #34495e;
  border-color: #409EFF;
  color: #66b1ff;
}

.table-container {
  width: 100%;
  overflow-x: auto;
}
.table-container::-webkit-scrollbar {
  height: 12px;
}
.table-container::-webkit-scrollbar-track {
  background: #1D1E1F;
  border-radius: 6px;
}
.table-container::-webkit-scrollbar-thumb {
  background: #4C4D4F;
  border-radius: 6px;
}
.table-container::-webkit-scrollbar-thumb:hover {
  background: #606266;
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

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: center;
  width: 100%;
  padding: 2px 0;
}
.progress-bar-inline {
  width: 100%;
}
.progress-cell :deep(.el-progress__text) {
  font-size: 11px !important;
  color: #E6A23C !important;
  font-weight: 600;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

:deep(.el-table th.el-table__cell .el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: transparent !important;
  border-color: #4C4D4F !important;
}
:deep(.el-table th.el-table__cell .el-checkbox__input.is-indeterminate .el-checkbox__inner::before),
:deep(.el-table th.el-table__cell .el-checkbox__input.is-indeterminate .el-checkbox__inner::after) {
  display: none !important;
}
</style>
