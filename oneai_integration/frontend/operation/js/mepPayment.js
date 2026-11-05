import { api } from '@/aiPlugins/aiApiConfig'

const BASE_REQ_ID = "menu_operation.mep_payment.mep_payment_analysis"

// 1. LẤY TỔNG SỐ DÒNG
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

// 2. LẤY DỮ LIỆU PHÂN TRANG
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

// 3. LƯU CÁC DÒNG MỚI THÊM HOẶC CHỈNH SỬA XUỐNG DB
export async function save_mep_rows(rows = []) {
  const res = await api.post("/mep_payment/save_rows", { rows })
  return res.data
}

// 4. XÓA CÁC DÒNG ĐƯỢC CHỌN KHỎI DB
export async function delete_mep_rows(keyids = []) {
  const res = await api.post("/mep_payment/delete_rows", { keyids })
  return res.data
}

// 5. LẤY THỐNG KÊ 5 CHỈ SỐ KPI TOÀN CỤC CỐ ĐỊNH (KHÔNG BỊ ẢNH HƯỞNG BỞI PHÂN TRANG)
export async function get_kpi_summary(paymentMonth = "ALL", keyword = "ALL") {
  const reqId = `${BASE_REQ_ID}:searchKpiSummary`
  const param = {
    PAYMENT_MONTH: paymentMonth || "ALL",
    KEYID: keyword || "ALL"
  }
  const parameter = { [reqId]: param }
  const res = await api.get("/crud/ui", { params: parameter, loading: false })
  return res.data[reqId].VAL
}
