<template>
  <div class="state-block">
    <div v-if="loading" class="state-loading">
      <el-icon class="loading-icon" :size="40"><Loading /></el-icon>
      <p>{{ loadingText || '加载中...' }}</p>
    </div>
    <div v-else-if="error" class="state-error">
      <el-icon :size="40" color="#ef4444"><WarningFilled /></el-icon>
      <p>{{ errorText || '加载失败' }}</p>
      <el-button v-if="retryText" type="primary" @click="$emit('retry')">{{ retryText }}</el-button>
    </div>
    <div v-else class="state-empty">
      <el-icon :size="40" color="#94a3b8"><InfoFilled /></el-icon>
      <p>{{ emptyText || '暂无数据' }}</p>
      <el-button v-if="actionText" type="primary" @click="$emit('action')">{{ actionText }}</el-button>
    </div>
  </div>
</template>

<script setup>
import { Loading, WarningFilled, InfoFilled } from '@element-plus/icons-vue'

defineProps({
  loading: Boolean,
  error: Boolean,
  loadingText: String,
  errorText: String,
  emptyText: String,
  retryText: String,
  actionText: String,
})

defineEmits(['retry', 'action'])
</script>

<style scoped>
.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
  gap: 12px;
}
.state-block p {
  margin: 8px 0;
  font-size: 14px;
}
.loading-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
