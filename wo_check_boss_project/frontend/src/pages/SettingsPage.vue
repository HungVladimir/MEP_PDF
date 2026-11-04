<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { store, toast } from '../store'

const emit = defineEmits(['saved'])
const s = ref(null)
const apiKey = ref('')
const testMsg = ref('')
const saving = ref(false)
const canEdit = computed(() => !!store.me?.can_review)

onMounted(async () => {
  try { s.value = await api.settings() } catch (e) { toast(e.message) }
})

async function save(silent = false) {
  saving.value = true
  try {
    const body = { ...s.value, api_key: apiKey.value ? apiKey.value : null }
    delete body.api_key_set
    s.value = await api.saveSettings(body)
    apiKey.value = ''
    emit('saved', s.value)
    if (!silent) toast('Đã lưu cài đặt')
    return true
  } catch (e) {
    toast(e.message)
    return false
  } finally {
    saving.value = false
  }
}

async function test() {
  testMsg.value = 'Đang gọi...'
  if (canEdit.value && !(await save(true))) { testMsg.value = ''; return }
  const r = await api.testAi().catch((e) => ({ ok: false, error: e.message }))
  testMsg.value = r.ok ? '✓ Kết nối được. AI trả lời: ' + r.reply : '✗ ' + r.error
}
</script>

<template>
  <div v-if="s">
    <p v-if="!canEdit" class="warnbox" style="margin-top:0">Chỉ người duyệt được thay đổi cài đặt. Bạn đang xem ở chế độ chỉ đọc.</p>
    <fieldset :disabled="!canEdit" style="border:0;padding:0;margin:0">
      <div class="card">
        <h3>Kết nối AI (OpenAI-compatible: vLLM, Ollama, OpenAI…)</h3>
        <label class="check" style="background:var(--warn-bg);padding:8px 10px;border-radius:8px">
          <input v-model="s.mock" type="checkbox"> <b>Chế độ thử – không gọi AI</b>: đọc chữ trực tiếp trong PDF (chỉ dùng với file mẫu có lớp chữ).
          Bỏ chọn khi chạy thật với PDF dạng ảnh.
        </label>
        <div class="grid2">
          <div><label>Base URL (server backend gọi tới, không phải trình duyệt)</label><input v-model="s.base_url" placeholder="http://10.0.0.5:8000/v1"></div>
          <div><label>Model (phải là model đọc được ảnh / vision)</label><input v-model="s.model" placeholder="Qwen/Qwen2.5-VL-72B-Instruct"></div>
          <div>
            <label>API key {{ s.api_key_set ? '(đã đặt – để trống = giữ nguyên)' : '(để trống nếu vLLM không đặt key)' }}</label>
            <input v-model="apiKey" type="password" autocomplete="new-password">
          </div>
          <div><label>Số trang gửi AI song song</label><input v-model.number="s.conc" type="number" min="1" max="16"></div>
          <div><label>Độ phân giải ảnh gửi AI (cạnh dài, px)</label><input v-model.number="s.res" type="number" min="800" max="4000"></div>
          <div><label>max_tokens mỗi trang</label><input v-model.number="s.max_tokens" type="number" min="512"></div>
          <div><label>Timeout mỗi lần gọi AI (giây)</label><input v-model.number="s.timeout" type="number" min="30"></div>
        </div>
        <label>Ghi chú thêm cho AI (VD: mã vật tư luôn dạng 10 ký tự, số bản vẽ nằm ở góc phải dưới…)</label>
        <textarea v-model="s.hint"></textarea>
        <div class="row" style="margin-top:12px">
          <button class="btn" type="button" @click="test">Kiểm tra kết nối</button>
          <span class="small muted">{{ testMsg }}</span>
        </div>
      </div>

      <div class="card">
        <h3>Cấu trúc sheet danh sách vật tư trong Excel</h3>
        <p class="muted small" style="margin-top:0">Để trống = tự nhận diện. Chỉ điền khi file có cấu trúc cố định mà tự nhận diện sai.</p>
        <div class="grid2">
          <div><label>Tên sheet (chứa chuỗi)</label><input v-model="s.sheet" placeholder="VD: vật tư"></div>
          <div><label>Dòng tiêu đề (số dòng Excel, 0 = tự động)</label><input v-model.number="s.hdr" type="number" min="0"></div>
          <div><label>Cột mã vật tư (chữ cột)</label><input v-model="s.code_col" placeholder="VD: B"></div>
          <div><label>Cột bản vẽ đầu tiên (chữ cột)</label><input v-model="s.first_col" placeholder="VD: E"></div>
        </div>
        <label class="check"><input v-model="s.compare_qty" type="checkbox"> So sánh cả số lượng (bỏ chọn = chỉ kiểm tra vật tư có/không)</label>
        <label class="check"><input v-model="s.missing_col_is_error" type="checkbox"> Tính lỗi khi Excel có cột bản vẽ mà PDF không có</label>
        <div class="row" style="margin-top:12px">
          <button class="btn primary" :disabled="saving" @click="save()">Lưu cài đặt</button>
          <span class="small muted">Cài đặt áp dụng cho các lần kiểm tra sau (bấm "Chạy lại AI" để áp dụng cho WO cũ).</span>
        </div>
      </div>
    </fieldset>
  </div>
  <p v-else class="muted">Đang tải cài đặt...</p>
</template>