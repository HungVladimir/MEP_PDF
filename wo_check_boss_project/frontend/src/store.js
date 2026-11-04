import { reactive } from 'vue'

export const store = reactive({
  me: null,          // { username, name, roles, can_review }
  toasts: [],
})

let tid = 0
export function toast(msg) {
  const id = ++tid
  store.toasts.push({ id, msg })
  setTimeout(() => { store.toasts = store.toasts.filter((t) => t.id !== id) }, 3500)
}

export const fmtDate = (t) => (t ? new Date(t * 1000).toLocaleString('vi-VN') : '')

export const AI_STATUS = {
  new: ['b-new', 'Chưa xử lý'],
  running: ['b-run', 'Đang xử lý…'],
  ok: ['b-ok', 'Khớp'],
  error: ['b-err', 'Có lỗi'],
  failed: ['b-warn', 'Thất bại'],
}