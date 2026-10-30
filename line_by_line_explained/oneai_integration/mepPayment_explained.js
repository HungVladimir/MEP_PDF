// ==============================================================================
// JAVASCRIPT GỌI GATEWAY /crud/ui - GIẢI THÍCH CHI TIẾT TỪNG DÒNG (LINE-BY-LINE)
// Đường dẫn tương ứng: oneai_integration/frontend/src/js/mepPayment.js
// ==============================================================================

// Dòng 1: Nhúng instance Axios cấu hình sẵn của nền tảng OneAI (chứa sẵn baseURL và token đăng nhập)
import { api } from '@/aiPlugins/aiApiConfig'

// Dòng 4: Khai báo định danh tiền tố menu trỏ tới file mep_payment_analysis.py
// OneAI sẽ căn cứ vào chuỗi này để tìm đến đúng file Python khai báo QuerySettings
const BASE_REQ_ID = "menu_operation.mep_payment.mep_payment_analysis"

/**
 * HÀM LẤY TỔNG SỐ DÒNG THỎA MÃN BỘ LỌC
 * - Nhận các tham số từ Vue: status, paymentMonth, keyword (mặc định là "ALL")
 * - Gửi GET request tới endpoint chung /crud/ui với param [reqId]: param
 * - Trả về mảng kết quả VAL từ Oracle DB
 */
export async function get_total_row(status = "ALL", paymentMonth = "ALL", keyword = "ALL") {
  // Tạo reqId đầy đủ: menu_operation.mep_payment.mep_payment_analysis:searchTotalRow
  const reqId = `${BASE_REQ_ID}:searchTotalRow`
  const param = {
    STATUS: status || "ALL",
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const parameter = { [reqId]: param }
  
  // loading: false để tránh hiển thị vòng xoay toàn màn hình khi polling ngầm
  const res = await api.get("/crud/ui", { params: parameter, loading: false })
  return res.data[reqId].VAL
}

/**
 * HÀM LẤY DỮ LIỆU BẢNG PHÂN TRANG
 * - page: Số trang hiện tại (1, 2, 3...)
 * - pageSize: Số dòng mỗi trang (20, 50, 100...)
 * - Tính toán start_row = (page - 1) * pageSize + 1 và end_row = page * pageSize
 * - Gửi request tới /crud/ui và trả về danh sách dòng để đưa vào tableData của Vue
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
  const res = await api.get("/crud/ui", { params: parameter, loading: false })
  return res.data[reqId].VAL
}

