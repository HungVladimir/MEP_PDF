<!-- ==============================================================================
     GIAO DIỆN DARK THEME ELEMENT PLUS - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
     Đường dẫn tương ứng: oneai_integration/frontend/src/views/MepOperation.vue
     ============================================================================== -->
<template>
  <div class="mep-container">
    <!-- ====================================================================
         KHU VỰC 1: THANH CÔNG CỤ TÌM KIẾM VÀ LỌC DỮ LIỆU (TOOLBAR)
         ==================================================================== -->
    <div class="toolbar">
      <!-- 1. Bộ chọn Trạng thái (Status): Lọc theo ALL, WAITING, RUNNING, COMPLETED... -->
      <el-select v-model="selectedStatus" placeholder="Chọn Trạng Thái" clearable style="width: 170px">
        <el-option v-for="item in statusList" :key="item" :label="item" :value="item" />
      </el-select>

      <!-- 2. Bộ chọn Tháng thanh toán: Chọn theo định dạng YYYY-MM -->
      <el-date-picker
        v-model="selectedMonth"
        type="month"
        placeholder="Chọn Tháng Thanh Toán"
        value-format="YYYY-MM"
        style="width: 190px"
      />

      <!-- 3. Ô nhập từ khóa tìm kiếm nhanh theo Số WO hoặc Tên công việc -->
      <el-input
        v-model="searchKeyword"
        placeholder="Nhập số WO hoặc tên công việc..."
        clearable
        style="width: 270px"
        @keyup.enter="handleReload"
      />

      <!-- 4. Nút bấm Làm mới dữ liệu kèm đồng hồ đếm ngược tự động Polling (10s) -->
      <el-button type="primary" @click="handleReload">
        Reload ({{ countdown }}s)
      </el-button>
    </div>

    <!-- ====================================================================
         KHU VỰC 2: BẢNG LƯỚI DỮ LIỆU ĐỐI SOÁT GỒM 10 CỘT CHUẨN
         ==================================================================== -->
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
        <!-- CỘT 1: STT (Số thứ tự liên tục 1, 2, 3...) -->
        <el-table-column prop="STT" label="STT" width="55" align="center" />

        <!-- CỘT 2: SỐ CÔNG VIỆC (Mã Work Order định danh duy nhất) -->
        <el-table-column prop="KEYID" label="Số Công Việc (WO)" width="150" sortable align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain" class="font-bold">{{ row.KEYID }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT 3: TÊN CÔNG VIỆC (Mô tả hạng mục cơ điện) -->
        <el-table-column prop="TASK_NAME" label="Tên Công Việc" min-width="200" show-overflow-tooltip />

        <!-- CỘT 4: THÁNG THANH TOÁN (Kỳ thanh toán) -->
        <el-table-column prop="PAYMENT_MONTH" label="Tháng TT" width="95" align="center" sortable />

        <!-- CỘT 5: NGƯỜI PHỤ TRÁCH (Kỹ sư PIC) -->
        <el-table-column prop="PIC" label="Người Phụ Trách" width="125" align="center" />

        <!-- CỘT 6: PART (Tự động theo phòng ban kỹ sư) -->
        <el-table-column prop="PART_NAME" label="Part" width="95" align="center" />

        <!-- CỘT 7: GROUP (Tự động theo khối quản lý) -->
        <el-table-column prop="GROUP_NAME" label="Group" width="105" align="center" />

        <!-- CỘT TRẠNG THÁI HỆ THỐNG: Đổi màu theo WAITING (Xám), RUNNING (Vàng), COMPLETED (Xanh) -->
        <el-table-column prop="STATUS" label="Trạng Thái" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.STATUS === 'COMPLETED'" type="success" effect="dark">Hoàn Tất</el-tag>
            <el-tag v-else-if="row.STATUS === 'RUNNING'" type="warning" effect="dark">Đang Xử Lý</el-tag>
            <el-tag v-else-if="row.STATUS === 'WAITING'" type="info">Chờ Duyệt</el-tag>
            <el-tag v-else type="danger">{{ row.STATUS }}</el-tag>
          </template>
        </el-table-column>

        <!-- CỘT 8: TÀI LIỆU ĐÍNH KÈM: Nút bấm Upload file Excel trực tiếp trên từng dòng -->
        <el-table-column label="Tài Liệu Đính Kèm" width="125" align="center">
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

        <!-- CỘT 9: KẾT QUẢ KIỂM TRA: Hiển thị tag Xanh nếu 0 lỗi, tag Đỏ nếu phát hiện sai lệch -->
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

        <!-- CỘT 10: CHI TIẾT BÁO CÁO & DUYỆT (REVIEW WORKFLOW): Tải Excel 2 Sheet + Nút Duyệt/Hủy -->
        <el-table-column label="Chi Tiết Báo Cáo" min-width="210" align="center">
          <template #default="{ row }">
            <div v-if="row.STATUS === 'COMPLETED'">
              <!-- 1. Đường dẫn tải file Excel Báo cáo hoàn chỉnh -->
              <a v-if="row.RESULT_LINK" :href="getDownloadUrl(row.RESULT_LINK)" target="_blank" download class="download-link">
                📥 Tải Báo Cáo 2 Sheet
              </a>

              <!-- 2. Khu vực Review: Nút Duyệt / Từ chối hoặc nhãn đã duyệt -->
              <div style="margin-top: 4px;">
                <el-tag v-if="row.REVIEW_DECISION === 'APPROVED'" type="success" size="small">Đã Duyệt</el-tag>
                <el-tag v-else-if="row.REVIEW_DECISION === 'REJECTED'" type="danger" size="small">Từ Chối</el-tag>
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

      <!-- ====================================================================
           KHU VỰC 3: PHÂN TRANG (PAGINATION BAR)
           ==================================================================== -->
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
// ==============================================================================
// KHU VỰC LOGIC JAVASCRIPT (VUE 3 COMPOSITION API)
// ==============================================================================
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { get_total_row, get_data_page } from '../js/mepPayment'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// Địa chỉ cổng mạng của dịch vụ AI FastAPI Worker
const FASTAPI_BASE_URL = "http://127.0.0.1:8386"

// Khởi tạo các biến phản ứng (Reactive States)
const selectedStatus = ref('')
const selectedMonth = ref('')
const searchKeyword = ref('')
const tableData = ref([])

const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const countdown = ref(10) // Đếm ngược 10 giây tự làm mới bảng

const statusList = ref(['ALL', 'WAITING', 'RUNNING', 'COMPLETED', 'CANCEL'])

let timer = null
let countdownTimer = null

// Hàm tải dữ liệu bảng qua Gateway OneAI
const loadData = async () => {
  try {
    tableData.value = await get_data_page(
      page.value, pageSize.value,
      selectedStatus.value || 'ALL',
      selectedMonth.value || 'ALL',
      searchKeyword.value || 'ALL'
    )
  } catch (err) {
    console.error("Lỗi tải bảng dữ liệu MEP:", err)
  }
}

// Hàm lấy tổng số dòng để tính toán số trang
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

// Hàm làm mới dữ liệu và đặt lại bộ đếm về 10s
const handleReload = async () => {
  await loadData()
  await loadTotal()
  countdown.value = 10
}

// Khi component được mount lên màn hình: Tự động chạy Polling mỗi 10 giây
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

// Dọn dẹp Timer khi người dùng rời màn hình để tránh rò rỉ bộ nhớ
onUnmounted(() => {
  clearInterval(timer)
  clearInterval(countdownTimer)
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const handlePageChange = (p) => { page.value = p; loadData(); }
const handleSizeChange = (s) => { pageSize.value = s; page.value = 1; loadData(); }
const goFirst = () => { if (page.value > 1) { page.value = 1; loadData(); } }
const goLast = () => { if (page.value < totalPages.value) { page.value = totalPages.value; loadData(); } }

// Theo dõi khi người dùng đổi bộ lọc -> tự động nhảy về trang 1 và tải lại
watch([selectedStatus, selectedMonth], () => {
  page.value = 1
  handleReload()
})

// HÀM XỬ LÝ UPLOAD FILE EXCEL TRỰC TIẾP TỪ DÒNG
const handleUploadExcel = async (file, row) => {
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xlsm')) {
    ElMessage.error("Chỉ chấp nhận file Excel (.xlsx / .xlsm)")
    return
  }

  const formData = new FormData()
  formData.append("file", file.raw)
  formData.append("KEYID", row.KEYID)

  row.STATUS = 'RUNNING'
  row.REASON = 'Đang đẩy file lên AI Server...'

  try {
    const res = await axios.post(`${FASTAPI_BASE_URL}/mep_payment/upload`, formData)
    if (res.data.status === "accepted") {
      ElMessage.success(`Đã nạp file cho WO [${row.KEYID}]. AI đang phân tích...`)
      setTimeout(handleReload, 2000)
    } else {
      ElMessage.error(res.data.message || "Upload thất bại!")
      row.STATUS = 'CANCEL'
    }
  } catch (err) {
    ElMessage.error("Mất kết nối tới Server FastAPI Worker!")
    row.STATUS = 'CANCEL'
  }
}

// HÀM XỬ LÝ PHÊ DUYỆT (REVIEW)
const handleReview = async (row, decision) => {
  const actionText = decision === 'APPROVED' ? 'Duyệt thanh toán' : 'Từ chối thanh toán'
  try {
    const { value: note } = await ElMessageBox.prompt(`Nhập ghi chú ${actionText}:`, 'Xác nhận Review', {
      confirmButtonText: 'Xác nhận',
      cancelButtonText: 'Hủy'
    })

    await axios.post(`${FASTAPI_BASE_URL}/mep_payment/review`, {
      keyid: row.KEYID,
      decision: decision,
      note: note || '',
      reviewer: 'PIC'
    })

    ElMessage.success(`Đã cập nhật: ${actionText}`)
    handleReload()
  } catch {
    // Kỹ sư bấm nút Hủy
  }
}

// Hàm chuẩn hóa đường dẫn tải báo cáo
const getDownloadUrl = (link) => {
  if (!link) return '#'
  return link.startsWith('http') ? link : `${FASTAPI_BASE_URL}${link}`
}
</script>

<style scoped>
/* Định dạng CSS Dark Theme chuẩn Element Plus của OneAI */
.mep-container { padding: 12px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 15px; }
.table-container { width: 100%; overflow-x: auto; }
.font-bold { font-weight: 600; }
.download-link { color: #67C23A; font-weight: bold; text-decoration: underline; cursor: pointer; display: inline-block; }
.download-link:hover { color: #85ce61; }
.text-reason { color: #F56C6C; font-size: 11px; }
.pagination-bar { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 15px; }
.page-indicator { margin-left: 10px; color: #909399; }
</style>

