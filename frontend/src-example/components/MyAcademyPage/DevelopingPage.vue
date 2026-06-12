<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>

<template>
  <div style="height: 720px">
    <el-scrollbar>
      <el-divider content-position="left">
        <el-text style="font-size: 22px">{{ title }}</el-text>
      </el-divider>
      <div class="glowing-container" style="margin-top: 36px; padding: 48px; text-align: center">
        <el-text size="large" type="info">{{ title }}功能开发中...</el-text>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>
</style>