
<template>
  <ai-body>
    <el-tabs v-model="activeTab">
      <el-tab-pane :label="$lang('operation')" name="operation">
        <Operation ref="operation" :activeTab="activeTab" />
      </el-tab-pane>
    </el-tabs>
  </ai-body>
</template>

<script>
import Operation from "./tab/operation.vue";

export default {
  name: "CMD analysis",
  components: { Operation },
  data() {
    return {
      activeTab: "operation",
    };
  },
  methods: {
    goToOperation() {
      this.activeTab = "operation";
      this.$refs.operation.search();
    },
  },
};
</script>