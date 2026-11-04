<script setup>
import { computed } from 'vue'
import { AI_STATUS } from '../store'

const props = defineProps({ wo: { type: Object, required: true }, kind: { type: String, default: 'ai' } })
const ai = computed(() => AI_STATUS[props.wo.status] || AI_STATUS.new)
const review = computed(() => {
  const d = props.wo.review?.decision
  if (d === 'approved') return ['b-done', 'Đã duyệt']
  if (d === 'rejected') return ['b-rej', 'Từ chối']
  if (props.wo.status === 'ok' || props.wo.status === 'error') return ['b-warn', 'Chờ duyệt']
  return null
})
</script>

<template>
  <span v-if="kind === 'ai'" class="badge" :class="ai[0]">{{ ai[1] }}</span>
  <template v-else>
    <span v-if="review" class="badge" :class="review[0]">{{ review[1] }}</span>
    <span v-else class="muted">—</span>
  </template>
</template>