<!-- ====================================================================
     ONEAI MODULE ENTRY POINT: ĐỐI SOÁT THANH TOÁN MEP
     File: src/views/main.vue
     Chức năng: Khung chứa chuẩn OneAI (<ai-body>), thanh Tab và nhúng Operation
     ==================================================================== -->
<template>
  <ai-body>
    <el-tabs v-model="activeTab">
      <!-- TAB 1: VẬN HÀNH & ĐỐI SOÁT (OPERATION) -->
      <el-tab-pane :label="$lang('operation') || 'Vận Hành Đối Soát'" name="operation">
        <Operation ref="operation" :activeTab="activeTab" />
      </el-tab-pane>
    </el-tabs>
  </ai-body>
</template>

<script>
import Operation from "./tab/operation.vue";

export default {
  name: "MEP Payment Analysis",
  components: { Operation },
  data() {
    return {
      activeTab: "operation",
    };
  },
  methods: {
    goToOperation() {
      this.activeTab = "operation";
      if (this.$refs.operation && this.$refs.operation.handleReload) {
        this.$refs.operation.handleReload();
      }
    },
  },
};
</script>

<style scoped>
/* Đồng bộ khoảng đệm và giao diện chuẩn OneAI */
:deep(.el-tabs__header) {
  margin-bottom: 8px;
}
</style>