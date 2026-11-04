<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { store, toast } from '../store'

const emit = defineEmits(['close', 'created'])
const wo = ref('')
const description = ref('')
const file = ref(null)
const pdf = ref(null)
const over = ref(false)
const saving = ref(false)
const fileInput = ref(null)

function pick(f) {
  if (!f) return
  if (!/\.(xlsx|xlsm)$/i.test(f.name)) { toast('Chỉ nhận file .xlsx / .xlsm'); return }
  file.value = f
  if (!wo.value) {
    const m = f.name.match(/WO[-_ ]?[\w-]+/i)
    wo.value = (m ? m[0] : f.name.replace(/\.\w+$/, '')).replace(/_.*$/, '')
  }
}
function onDrop(e) { over.value = false; pick(e.dataTransfer.files[0]) }

async function save() {
  if (!wo.value.trim() || !file.value) { toast('Nhập mã WO và chọn file Excel'); return }
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('wo', wo.value.trim())
    fd.append('description', description.value.trim())
    fd.append('file', file.value)
    if (pdf.value) fd.append('pdf', pdf.value)
    const w = await api.create(fd)
    toast('Đã thêm ' + w.wo + ', đang kiểm tra...')
    emit('created', w)
  } catch (e) {
    toast(e.message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="modal-bg" @click.self="emit('close')">
    <div class="modal narrow">
      <h2>Thêm workorder</h2>
      <p class="muted small" style="margin-top:0">Sau khi lưu, hệ thống tự tách PDF trong Excel, cho AI đọc bảng vật tư và so sánh.</p>

      <label>Mã workorder *</label>
      <input v-model="wo" placeholder="WO-2026-1029-001">
      <label>Mô tả / model sản phẩm</label>
      <input v-model="description">
      <label>Người tạo</label>
      <input :value="store.me ? `${store.me.name} (${store.me.username})` : ''" readonly>

      <label>File Excel workorder *</label>
      <div class="drop" :class="{ over, has: file }" @click="fileInput.click()"
           @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop">
        {{ file ? '✓ ' + file.name : 'Bấm hoặc kéo thả file .xlsx / .xlsm' }}
      </div>
      <input ref="fileInput" type="file" accept=".xlsx,.xlsm" hidden @change="pick($event.target.files[0])">

      <label>File PDF / ảnh bảng vật tư (tuỳ chọn – chỉ dùng nếu PDF không nhúng trong Excel)</label>
      <input type="file" accept=".pdf,image/png,image/jpeg" @change="pdf = $event.target.files[0] || null">

      <div class="row" style="margin-top:16px;justify-content:flex-end">
        <button class="btn" @click="emit('close')">Huỷ</button>
        <button class="btn primary" :disabled="saving" @click="save">{{ saving ? 'Đang tải lên...' : 'Lưu & kiểm tra' }}</button>
      </div>
    </div>
  </div>
</template>