// Gọi backend FastAPI. Cookie/phiên đăng nhập được trình duyệt gửi kèm (cùng domain qua nginx).
const BASE = import.meta.env.VITE_API_BASE || `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api`

async function req(method, path, body) {
  const isForm = body instanceof FormData
  const r = await fetch(BASE + path, {
    method,
    credentials: 'same-origin',
    headers: body && !isForm ? { 'Content-Type': 'application/json' } : {},
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) {
    let msg = `Lỗi ${r.status}`
    try {
      const j = await r.json()
      if (j.detail) msg = typeof j.detail === 'string' ? j.detail : j.detail.map((d) => d.msg).join('; ')
    } catch { /* không phải JSON */ }
    throw new Error(msg)
  }
  return r.json()
}

const qs = (p) => new URLSearchParams(Object.entries(p || {}).filter(([, v]) => v !== '' && v != null)).toString()

export const api = {
  me: () => req('GET', '/me'),
  list: (params) => req('GET', `/workorders?${qs(params)}`),
  get: (id) => req('GET', `/workorders/${id}`),
  create: (formData) => req('POST', '/workorders', formData),
  rerun: (id) => req('POST', `/workorders/${id}/rerun`),
  replaceFile: (id, file) => { const fd = new FormData(); fd.append('file', file); return req('POST', `/workorders/${id}/file`, fd) },
  review: (id, decision, note) => req('POST', `/workorders/${id}/review`, { decision, note }),
  remove: (id) => req('DELETE', `/workorders/${id}`),
  settings: () => req('GET', '/settings'),
  saveSettings: (s) => req('PUT', '/settings', s),
  testAi: () => req('POST', '/settings/test-ai'),
  pageUrl: (id, n) => `${BASE}/workorders/${id}/pages/${n}.jpg`,
  sourceUrl: (id) => `${BASE}/workorders/${id}/source`,
  exportUrl: (params) => `${BASE}/export?${qs(params)}`,
}