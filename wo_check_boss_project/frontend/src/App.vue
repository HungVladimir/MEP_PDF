<script setup>
import { onMounted, ref } from 'vue'
import { api } from './api'
import { store, toast } from './store'
import ListPage from './pages/ListPage.vue'
import SettingsPage from './pages/SettingsPage.vue'

const tab = ref('list')
const settings = ref(null)

async function loadSettings() {
  try { settings.value = await api.settings() } catch (e) { toast(e.message) }
}

onMounted(async () => {
  try { store.me = await api.me() } catch (e) { toast('Không lấy được người dùng: ' + e.message) }
  loadSettings()
})
</script>

<template>
  <header>
    <h1>🧾 Kiểm tra vật tư Workorder</h1>
    <nav>
      <button :class="{ active: tab === 'list' }" @click="tab = 'list'">Workorder</button>
      <button :class="{ active: tab === 'settings' }" @click="tab = 'settings'">Cài đặt AI &amp; Excel</button>
    </nav>
    <div class="spacer"></div>
    <span v-if="settings" class="small muted">
      {{ settings.mock ? '🧪 Chế độ thử (không gọi AI)' : settings.model ? 'AI: ' + settings.model : '⚠ Chưa cấu hình AI' }}
    </span>
    <span v-if="store.me" class="small">
      👤 <b>{{ store.me.name }}</b> <span class="muted">{{ store.me.username }}</span>
      <span v-if="store.me.can_review" class="badge b-ok" style="margin-left:6px">Người duyệt</span>
    </span>
  </header>

  <main>
    <ListPage v-show="tab === 'list'" />
    <SettingsPage v-if="tab === 'settings'" @saved="(s) => (settings = s)" />
  </main>

  <div class="toasts">
    <div v-for="t in store.toasts" :key="t.id" class="toast">{{ t.msg }}</div>
  </div>
</template>