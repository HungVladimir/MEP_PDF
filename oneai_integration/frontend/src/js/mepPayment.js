// ====================================================================
// JAVASCRIPT API GỌI GATEWAY /crud/ui CỦA ONEAI
// Copy file này vào src/js/ (cùng chỗ paperImage.js) trong OneAI Frontend
// ====================================================================
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

export async function save_mep_rows(rows = []) {
  // Gửi danh sách dòng mới / sửa xuống API Worker
  const res = await api.post("/mep_payment/save_rows", { rows })
  return res.data
}

export async function delete_mep_rows(keyids = []) {
  // Gửi danh sách KEYID cần xóa xuống API Worker
  const res = await api.post("/mep_payment/delete_rows", { keyids })
  return res.data
}
