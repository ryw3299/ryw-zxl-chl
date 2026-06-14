<template>
  <header class="page-header">
    <div class="header-search">
      <el-icon><Search /></el-icon>
      <input
        v-model="searchText"
        type="text"
        placeholder="搜索课程、资源、题目或知识点"
        @keyup.enter="onSearch"
      />
    </div>

    <div class="header-actions">
      <div class="header-user" @click="$router.push('/settings')">
        <div class="user-avatar">{{ (userStore.username || '李')[0] }}</div>
        <div class="user-meta">
          <span class="user-name">{{ userStore.username || '同学' }}</span>
          <span class="user-level">Lv.6</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { Search, Bell, ChatDotSquare, ArrowDown } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const userStore = useUserStore()
const searchText = ref('')

function onSearch() {
  if (searchText.value.trim()) {
    router.push(`/resources?keyword=${encodeURIComponent(searchText.value.trim())}`)
  }
}
</script>

<style scoped>
.page-header {
  height: 74px; padding: 18px 24px;
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  background: rgba(245, 247, 251, 0.92);
  backdrop-filter: blur(8px);
  position: sticky; top: 0; z-index: 20;
}
.header-search {
  width: min(560px, 100%); height: 42px;
  display: flex; align-items: center; gap: 10px;
  padding: 0 14px; border: 1px solid #dde5f0; border-radius: 999px;
  background: #fff; color: #8b98ab;
  box-shadow: 0 8px 20px rgba(59, 86, 145, 0.04);
}
.header-search input {
  flex: 1; border: 0; outline: none; background: transparent;
  font: inherit; color: #334155;
}
.header-search input::placeholder { color: #98a2b3; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.header-icon-button {
  position: relative; width: 40px; height: 40px;
  border: 1px solid #e3e9f2; border-radius: 50%;
  background: #fff; color: #5b6b84;
  display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
}
.notify-badge {
  position: absolute; top: -3px; right: -1px;
  min-width: 18px; height: 18px; padding: 0 5px; border-radius: 999px;
  background: #ff5b6e; color: #fff; font-size: 0.7rem;
  display: inline-flex; align-items: center; justify-content: center;
}
.notify-badge-alt { background: #ff7b57; }
.header-user {
  display: flex; align-items: center; gap: 10px; padding-left: 4px;
}
.user-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  background: linear-gradient(135deg, #89a9ff, #5b8cff);
  color: #fff; display: inline-flex; align-items: center;
  justify-content: center; font-weight: 600;
}
.user-meta { display: flex; flex-direction: column; line-height: 1.2; }
.user-name { font-size: 0.92rem; font-weight: 600; color: #1e293b; }
.user-level {
  width: fit-content; margin-top: 3px; padding: 2px 6px;
  border-radius: 999px; background: #2b6cff;
  color: #fff; font-size: 0.68rem;
}
.user-arrow { color: #94a3b8; }
</style>
