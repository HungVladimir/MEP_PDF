v<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../api'
import { fmtDate, toast } from '../store'
import StatusBadges from '../components/StatusBadges.vue'
import AddWorkorderModal from '../components/AddWorkorderModal.vue'
import WorkorderDetail from '../components/WorkorderDetail.vue'

const items = ref([])
const stats = ref({})
const q = ref('')
const status = ref('')
const loading = ref(false)
const showAdd = ref(false)
const openId = ref(null)

async function load() {
  loading.value = true
  try {
    const r = await api.list({ q: q.value.trim(), status: status.value })
    items.value = r.items
    stats.value = r.stats
  } catch (e) {
    toast(e.message)
  } finally {
    loading.value = false
  }
}

// Tìm kiếm có độ trễ để không gọi API mỗi lần gõ phím
let qTimer
watch(q, () => { clearTimeout(qTimer); qTimer = setTimeout(load, 300) })
watch(status, load)

// Tự làm mới: 3 giây khi có WO đang xử lý, 20 giây khi không
let timer
const anyRunning = computed(() => items.value.some((w) => w.status === 'running' || w.status === 'new'))
function schedule() {
  clearTimeout(timer)
  timer = setTimeout(async () => { if (!document.hidden) await load(); schedule() }, anyRunning.value ? 3000 : 20000)
}
onMounted(async () => { await load(); schedule() })
onUnmounted(() => clearTimeout(timer))

const statCards = computed(() => [
  ['Tổng workorder', stats.value.total, ''],
  ['Chờ duyệt', stats.value.review, 'review'],
  ['AI báo có lỗi', stats.value.error, 'error'],
  ['Đã duyệt', stats.value.approved, 'approved'],
  ['Thất bại / cần chạy lại', stats.value.failed, 'failed'],
])

function onCreated(w) {
  showAdd.value = false
  openId.value = w.id
  load()
}
</script>

<template>
  <div>
    <div class="stats">
      <div v-for="[label, val, f] in statCards" :key="label" class="stat" style="cursor:pointer" @click="status = f">
        <b>{{ val ?? '–' }}</b><span>{{ label }}</span>
      </div>
    </div>

    <div class="card">
      <div class="row" style="margin-bottom:12px">
        <button class="btn primary" @click="showAdd = true">+ Thêm workorder</button>
        <a class="btn" :href="api.exportUrl({ q, status })">Xuất báo cáo Excel</a>
        <div class="spacer"></div>
        <input v-model="q" placeholder="Tìm WO / mô tả / người tạo..." style="max-width:240px">
        <select v-model="status" style="max-width:180px">
          <option value="">Tất cả trạng thái</option>
          <option value="review">Chờ duyệt</option>
          <option value="error">Có lỗi</option>
          <option value="approved">Đã duyệt</option>
          <option value="rejected">Từ chối</option>
          <option value="running">Đang xử lý</option>
          <option value="failed">Xử lý thất bại</option>
        </select>
      </div>

      <div class="tablewrap">
        <table>
          <thead>
            <tr>
              <th>Workorder</th><th>Mô tả</th><th>File</th><th>Người tạo</th><th>Ngày</th>
              <th>Kết quả AI</th><th>Số lỗi</th><th>Trạng thái duyệt</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="w in items" :key="w.id" class="click" @click="openId = w.id">
              <td><b>{{ w.wo }}</b></td>
              <td>{{ w.description }}</td>
              <td class="small">{{ w.file_name }}</td>
              <td>{{ w.created_by_name }} <span class="muted small">{{ w.created_by }}</span></td>
              <td class="small">{{ fmtDate(w.created_at) }}</td>
              <td><StatusBadges :wo="w" /></td>
              <td>
                <b v-if="w.error_count" class="c-err">{{ w.error_count }}</b>
                <span v-else-if="w.error_count === 0" class="c-ok">0</span>
              </td>
              <td><StatusBadges :wo="w" kind="review" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!items.length && !loading" class="muted small">
        Chưa có workorder phù hợp. Bấm "+ Thêm workorder" để upload file Excel.
      </p>
    </div>

    <AddWorkorderModal v-if="showAdd" @close="showAdd = false" @created="onCreated" />
    <WorkorderDetail v-if="openId" :id="openId" @close="openId = null" @changed="load" @deleted="openId = null; load()" />
  </div>
</template>