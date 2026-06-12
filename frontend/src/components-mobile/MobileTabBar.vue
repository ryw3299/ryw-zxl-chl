<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const items = [
  { name: 'home', label: '首页', icon: 'wap-home-o', to: '/m' },
  { name: 'progress', label: '进度', icon: 'todo-list-o', to: '/m/progress' },
  { name: 'assistant', label: '助手', icon: 'chat-o', to: '/m/assistant' },
]

const active = computed(() => route.meta?.mobileTab || 'home')

const handleChange = (name) => {
  const target = items.find((item) => item.name === name)
  if (target && target.to !== route.path) {
    router.push(target.to)
  }
}
</script>

<template>
  <div class="mobile-tabbar-shell">
    <van-tabbar
      :model-value="active"
      safe-area-inset-bottom
      @change="handleChange"
    >
      <van-tabbar-item
        v-for="item in items"
        :key="item.name"
        :name="item.name"
        :icon="item.icon"
      >
        {{ item.label }}
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.mobile-tabbar-shell {
  position: sticky;
  bottom: 0;
  z-index: 30;
}

.mobile-tabbar-shell :deep(.van-tabbar) {
  height: 68px;
  background: rgba(247, 250, 255, 0.92);
  backdrop-filter: blur(18px);
  box-shadow: 0 -10px 30px rgba(15, 23, 42, 0.08);
}

.mobile-tabbar-shell :deep(.van-tabbar-item__icon) {
  font-size: 22px;
}

.mobile-tabbar-shell :deep(.van-tabbar-item) {
  color: #7b8794;
}

.mobile-tabbar-shell :deep(.van-tabbar-item--active) {
  color: #175cd3;
}
</style>
