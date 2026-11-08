// ==============================================================================
// JAVASCRIPT GỌI GATEWAY /crud/ui & FASTAPI - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
// Đường dẫn tương ứng: oneai_integration/frontend/operation/js/mepPayment.js
// Chuẩn hóa 100% theo kiến trúc OneAI SDV Plugin
// ==============================================================================

// Dòng 1: Nhúng instance Axios cấu hình sẵn của nền tảng OneAI (chứa sẵn baseURL và token đăng nhập SSO)
import { api } from '@/aiPlugins/aiApiConfig'

// Dòng 3: Khai báo định danh tiền tố menu trỏ tới file mep_payment_analysis.py
// OneAI Gateway sẽ căn cứ vào chuỗi namespace này để gọi đúng QuerySettings trong backend
const BASE_REQ_ID = "menu_operation.mep_payment.mep_payment_analysis"

/**
 * Dòng 5-16: HÀM LẤY TỔNG SỐ DÒNG THỎA MÃN BỘ LỌC
 * - Tham số:
 *   + status: Trạng thái lọc ('ALL', 'WAITING', 'RUNNING', 'COMPLETED', 'OK', 'ERR'...)
 *   + paymentMonth: Tháng thanh toán ('ALL' hoặc định dạng 'YYYY-MM')
 *   + keyword: Từ khóa tìm kiếm theo WO hoặc tên công việc ('ALL' hoặc chuỗi nhập vào)
 * - Gửi GET request tới endpoint `/crud/ui` với param `[reqId]: param`
 * - Tham số loading: false giúp ngăn chặn vòng xoay Loading toàn trang khi hệ thống Polling ngầm
 * - Trả về: Giá trị mảng VAL chứa tổng số dòng từ Oracle DB
 */
export async function get_total_row(status = "ALL", paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:searchTotalRow`
  const param = {
    STATUS: status || "ALL",
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const parameter = { [reqId]: param }
  const res = await api.get(`/crud/ui?_t=${Date.now()}`, { params: parameter, loading: false })
  return res.data[reqId].VAL
}

/**
 * Dòng 18-35: HÀM LẤY DỮ LIỆU PHÂN TRANG CHO BẢNG EL-TABLE
 * - Tham số:
 *   + page: Số trang hiện tại (1, 2, 3...)
 *   + pageSize: Số lượng dòng trên mỗi trang (20, 50, 100...)
 *   + status, paymentMonth, keyword: Các bộ lọc tương ứng
 * - Thuật toán tính toán dòng bắt đầu và dòng kết thúc:
 *   + start_row = (page - 1) * pageSize + 1
 *   + end_row = page * pageSize
 * - Trả về: Danh sách các dòng dữ liệu để gán vào `tableData.value` trên Vue
 */
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
  const res = await api.get(`/crud/ui?_t=${Date.now()}`, { params: parameter, loading: false })
  return res.data[reqId].VAL
}

/**
 * Dòng 37-41: HÀM LƯU DANH SÁCH DÒNG (THÊM MỚI HOẶC SỬA) XUỐNG CƠ SỞ DỮ LIỆU
 * - Gửi danh sách các dòng cần lưu (cả dòng mới thêm isNew=true và dòng sửa isNew=false)
 *   tới endpoint FastAPI `/mep_payment/save_rows`.
 * - Backend tự động kiểm tra chống trùng KEYID và tự động dời thư mục MinIO nếu sửa tháng thanh toán.
 */
export async function save_mep_rows(rows = []) {
  const res = await api.post("/mep_payment/save_rows", { rows })
  return res.data
}

/**
 * Dòng 43-47: HÀM XÓA CÁC DÒNG ĐƯỢC CHỌN KHỎI HỆ THỐNG
 * - Nhận vào mảng các mã KEYID được chọn.
 * - Gửi yêu cầu tới FastAPI `/mep_payment/delete_rows`.
 * - Backend thực hiện Cascade Cleanup: Xóa MinIO + Xóa file local + Xóa DB Oracle.
 */
export async function delete_mep_rows(keyids = []) {
  const res = await api.post("/mep_payment/delete_rows", { keyids })
  return res.data
}

/**
 * Dòng 49-59: HÀM LẤY 5 CHỈ SỐ KPI TOÀN CỤC CỐ ĐỊNH CHO HEADER DASHBOARD
 * - Truy vấn 5 chỉ số: Tổng, Khớp 100%, Sai lệch, Đang chạy, Chờ duyệt.
 * - Cố định không bị biến thiên theo việc người dùng chuyển sang trang 2, trang 3 của bảng dữ liệu.
 */
export async function get_kpi_summary(paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:searchKpiSummary`
  const param = {
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const parameter = { [reqId]: param }
  const res = await api.get(`/crud/ui?_t=${Date.now()}`, { params: parameter, loading: false })
  return res.data[reqId].VAL
}
