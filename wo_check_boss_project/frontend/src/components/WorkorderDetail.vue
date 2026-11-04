<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { fmtDate, store, toast } from '../store'
import StatusBadges from './StatusBadges.vue'

const props = defineProps({ id: { type: String, required: true } })
const emit = defineEmits(['close', 'changed', 'deleted'])

const w = ref(null)
const note = ref('')
const zoomSrc = ref('')
const busy = ref(false)

const r = computed(() => w.value?.result)
const running = computed(() => ['new', 'running'].includes(w.value?.status))
const canReview = computed(() => !!store.me?.can_review)
const canDelete = computed(() => canReview.value || store.me?.username === w.value?.created_by)
const pages = computed(() => Array.from({ length: w.value?.page_count || 0 }, (_, i) => api.pageUrl(props.id, i + 1)))
const errTypes = computed(() => {
  const m = {}
  for (const e of r.value?.errors || []) m[e.type] = (m[e.type] || 0) + 1
  return Object.entries(m)
})

let timer
async function load() {
  try {
    const prev = w.value?.status
    w.value = await api.get(props.id)
    if (prev && prev !== w.value.status) emit('changed')
    if (!note.value) note.value = w.value.review?.note || ''
  } catch (e) {
    toast(e.message)
  }
  clearTimeout(timer)
  if (running.value) timer = setTimeout(load, 2000)
}
onMounted(load)
onUnmounted(() => clearTimeout(timer))
watch(() => props.id, () => { w.value = null; note.value = ''; load() })

async function act(fn, msg) {
  busy.value = true
  try {
    w.value = await fn()
    if (msg) toast(msg)
    emit('changed')
    if (running.value) load()
  } catch (e) {
    toast(e.message)
  } finally {
    busy.value = false
  }
}
const decide = (d) => act(() => api.review(props.id, d, note.value), d === 'approved' ? 'Đã duyệt' : 'Đã từ chối')
const rerun = () => act(() => api.rerun(props.id), 'Đang chạy lại...')
const reupload = (e) => { const f = e.target.files[0]; if (f) act(() => api.replaceFile(props.id, f), 'Đã upload lại, đang kiểm tra...') }
async function remove() {
  if (!confirm(`Xoá workorder ${w.value.wo}?`)) return
  try { await api.remove(props.id); toast('Đã xoá'); emit('deleted') } catch (e) { toast(e.message) }
}
function openPage(p) {
  const n = parseInt(String(p).split(',')[0])
  if (n && n <= pages.value.length) zoomSrc.value = pages.value[n - 1]
}
</script>

<template>
  <div class="modal-bg" @click.self="emit('close')">
    <div class="modal">
      <div v-if="!w" class="muted">Đang tải...</div>
      <template v-else>
        <div class="row" style="justify-content:space-between;align-items:flex-start">
          <div>
            <h2>{{ w.wo }} <StatusBadges :wo="w" /> <StatusBadges :wo="w" kind="review" /></h2>
            <div class="muted small">
              {{ w.description }} · <a :href="api.sourceUrl(w.id)">{{ w.file_name }}</a>
              · tạo bởi {{ w.created_by_name }} ({{ w.created_by }}) lúc {{ fmtDate(w.created_at) }}
              <template v-if="r"> · đọc bằng {{ r.mode }}</template>
            </div>
          </div>
          <button class="btn sm" @click="emit('close')">Đóng</button>
        </div>

        <div v-if="running" class="card" style="margin-top:12px;background:var(--info-bg)">⏳ Đang xử lý, trang tự cập nhật...</div>
        <div v-if="w.status === 'failed'" class="warnbox"><b>Xử lý thất bại:</b> {{ w.fail_reason }}</div>

        <template v-if="r">
          <div class="stats" style="margin-top:14px">
            <div class="stat"><b :class="r.errors.length ? 'c-err' : 'c-ok'">{{ r.errors.length }}</b><span>Số lỗi</span></div>
            <div class="stat"><b>{{ r.pdf_drawings }}</b><span>Bản vẽ AI đọc được ({{ r.pages }} trang)</span></div>
            <div class="stat"><b>{{ r.excel_dwgs }}</b><span>Cột bản vẽ trong Excel</span></div>
            <div class="stat"><b>{{ r.pdf_items }}</b><span>Dòng vật tư trong PDF</span></div>
            <div class="stat"><b>{{ r.excel_items }}</b><span>Vật tư trong sheet "{{ r.sheet }}"</span></div>
          </div>
          <div v-if="errTypes.length" class="row" style="margin-bottom:10px">
            <span v-for="[t, n] in errTypes" :key="t" class="badge b-err">{{ t }}: {{ n }}</span>
          </div>

          <div class="card">
            <h3>{{ r.errors.length ? 'Danh sách lỗi' : '✅ Không phát hiện lỗi' }}</h3>
            <div v-if="r.errors.length" class="tablewrap" style="max-height:360px">
              <table>
                <thead><tr><th>#</th><th>Loại lỗi</th><th>Bản vẽ</th><th>Mã vật tư</th><th>SL PDF</th><th>SL Excel</th><th>Trang</th><th>Chi tiết</th></tr></thead>
                <tbody>
                  <tr v-for="(e, i) in r.errors" :key="i">
                    <td>{{ i + 1 }}</td>
                    <td><span class="badge b-err">{{ e.type }}</span></td>
                    <td class="mono">{{ e.dwg }}</td>
                    <td class="mono">{{ e.code }}</td>
                    <td>{{ e.pdf }}</td>
                    <td>{{ e.xl }}</td>
                    <td><a v-if="e.page" href="#" @click.prevent="openPage(e.page)">{{ e.page }}</a></td>
                    <td class="small">{{ e.msg }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="card">
            <h3>Chi tiết so sánh theo bản vẽ</h3>
            <details v-for="g in r.groups" :key="g.drawing_no" :open="g.rows.some((x) => !x.ok)">
              <summary>
                Bản vẽ <span class="mono">{{ g.drawing_no }}</span> · cột Excel {{ g.col || '—' }} · trang {{ g.pages }} · {{ g.rows.length }} dòng
                <span v-if="g.rows.some((x) => !x.ok)" class="badge b-err">{{ g.rows.filter((x) => !x.ok).length }} lỗi</span>
                <span v-else class="badge b-ok">khớp</span>
              </summary>
              <div class="tablewrap">
                <table>
                  <thead><tr><th>Mã vật tư</th><th>Tên (AI đọc)</th><th>SL PDF</th><th>SL Excel</th><th>Ô</th><th>Kết quả</th></tr></thead>
                  <tbody>
                    <tr v-for="(x, i) in g.rows" :key="i">
                      <td class="mono">{{ x.code }}</td>
                      <td class="small">{{ x.name }}</td>
                      <td>{{ x.qty }}</td>
                      <td>{{ x.xl }}</td>
                      <td class="mono small">{{ x.cell }}</td>
                      <td :class="x.ok ? 'c-ok' : 'c-err'">{{ x.ok ? '✓' : x.why }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        </template>

        <div v-if="pages.length" class="card">
          <h3>Ảnh trang PDF (bấm để phóng to, đối chiếu)</h3>
          <div class="pages">
            <div v-for="(p, i) in pages" :key="p">
              <img :src="p" loading="lazy" @click="zoomSrc = p">
              <div class="small muted">Trang {{ i + 1 }}</div>
            </div>
          </div>
        </div>

        <details v-if="w.log?.length">
          <summary>Nhật ký xử lý</summary>
          <div class="log">{{ w.log.join('\n') }}</div>
        </details>

        <div class="card" style="margin-top:12px">
          <h3>Duyệt kết quả</h3>
          <p v-if="w.review">
            {{ w.review.decision === 'approved' ? '✅ Đã duyệt' : '❌ Từ chối' }} bởi <b>{{ w.review.by_name }}</b> ({{ w.review.by }})
            lúc {{ fmtDate(w.review.at) }}<template v-if="w.review.note"> — “{{ w.review.note }}”</template>
          </p>
          <div class="grid2">
            <div>
              <label>Người duyệt</label>
              <input :value="store.me ? `${store.me.name} (${store.me.username})` : ''" readonly>
            </div>
            <div>
              <label>Ghi chú</label>
              <input v-model="note" placeholder="VD: lỗi số 3 là do AI đọc sai, chấp nhận" :disabled="!canReview">
            </div>
          </div>
          <div class="row" style="margin-top:12px">
            <button class="btn ok" :disabled="!r || !canReview || busy" @click="decide('approved')">Duyệt</button>
            <button class="btn danger" :disabled="!r || !canReview || busy" @click="decide('rejected')">Từ chối</button>
            <span v-if="!canReview" class="small muted">Tài khoản của bạn không có quyền duyệt</span>
            <div class="spacer"></div>
            <label class="btn sm" style="margin:0" :class="{ disabled: running }">
              Upload lại Excel
              <input type="file" accept=".xlsx,.xlsm" hidden :disabled="running" @change="reupload">
            </label>
            <button class="btn sm" :disabled="running || busy" @click="rerun">Chạy lại AI</button>
            <button v-if="canDelete" class="btn sm" :disabled="running" @click="remove">Xoá</button>
          </div>
        </div>
      </template>
    </div>

    <div v-if="zoomSrc" class="modal-bg zoom" @click.self="zoomSrc = ''">
      <div class="modal">
        <div class="row" style="justify-content:flex-end"><button class="btn sm" @click="zoomSrc = ''">Đóng</button></div>
        <img :src="zoomSrc">
      </div>
    </div>
  </div>
</template>