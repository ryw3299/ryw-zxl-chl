<template>
  <aside class="app-sidebar">
    <div class="sidebar-brand" @click="$router.push('/')">
      <div class="brand-mark">
        <svg width="30" height="30" viewBox="0 0 30 30" fill="none" aria-hidden="true">
          <rect x="2" y="2" width="26" height="26" rx="8" fill="#2b6cff" />
          <path d="M9.5 15.5L13 19L20.5 11.5" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <div class="brand-copy">
        <div class="brand-name">智学工坊</div>
        <div class="brand-tagline">AI赋能学习，成长看得见</div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.label"
        type="button"
        :class="['nav-item', { active: item.active }]"
        @click="$router.push(item.to)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="sidebar-bottom">
      <div class="streak-card">
        <div class="streak-heading">
          <span>连续学习</span>
          <span class="streak-fire">热</span>
        </div>
        <div class="streak-main">
          <strong>16</strong>
          <span>天</span>
        </div>
        <div class="streak-meta">
          <span>累计学习</span>
          <strong>128 小时</strong>
        </div>
        <button type="button" class="ghost-wide-button" @click="$router.push('/dashboard')">学习日历</button>
      </div>
      <button type="button" class="logout-button" @click="handleLogout">
        <el-icon><Switch /></el-icon>
        <span>退出登录</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  HomeFilled, Histogram, Compass, FolderOpened, DataAnalysis, Setting, Switch,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const navItems = computed(() => [
  { label: '首页', to: '/', icon: HomeFilled, active: route.path === '/' },
  { label: '工作台', to: '/dashboard', icon: Histogram, active: route.path.startsWith('/dashboard') },
  { label: '个性化路径', to: '/learning-path', icon: Compass, active: route.path.startsWith('/learning-path') },
  { label: '资源中心', to: '/resources', icon: FolderOpened, active: route.path.startsWith('/resources') },
  { label: '学习报告', to: '/profile', icon: DataAnalysis, active: route.path.startsWith('/profile') },
  { label: '设置', to: '/settings', icon: Setting, active: route.path.startsWith('/settings') },
  ...(userStore.user?.role === 'admin'
    ? [{ label: '管理员中心', to: '/admin', icon: Setting, active: route.path.startsWith('/admin') }]
    : []),
])

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-sidebar {
  position: sticky; top: 0; height: 100vh;
  background: #fff; border-right: 1px solid #e8edf5;
  padding: 18px 14px 16px;
  display: flex; flex-direction: column; gap: 14px;
}
.sidebar-brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.brand-copy { min-width: 0; }
.brand-name { font-size: 1.375rem; font-weight: 700; color: #2b6cff; line-height: 1.1; }
.brand-tagline { margin-top: 3px; font-size: 0.75rem; color: #98a2b3; }
.sidebar-nav { display: flex; flex-direction: column; gap: 6px; }
.nav-item {
  width: 100%; height: 44px; border: 0; border-radius: 12px;
  background: transparent; color: #4f5f79;
  display: flex; align-items: center; gap: 12px;
  padding: 0 12px; font: inherit; cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease;
}
.nav-item:hover { background: #f5f8ff; color: #2b6cff; }
.nav-item.active { background: #edf3ff; color: #2b6cff; font-weight: 600; }
.nav-item .el-icon { font-size: 16px; }
.sidebar-bottom { margin-top: auto; display: flex; flex-direction: column; gap: 8px; }
.streak-card {
  border: 1px solid #e8edf5; border-radius: 16px;
  background: #fff; padding: 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.03);
}
.streak-heading, .streak-meta { display: flex; align-items: center; justify-content: space-between; }
.streak-heading { font-size: 0.78rem; color: #7b8798; }
.streak-fire {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 28px; height: 20px; border-radius: 999px;
  background: #fff3df; color: #e08c1a; font-size: 0.72rem;
}
.streak-main { margin: 10px 0 8px; display: flex; align-items: baseline; gap: 6px; }
.streak-main strong { font-size: 2.25rem; line-height: 1; color: #16223b; }
.streak-main span { color: #7b8798; }
.streak-meta { font-size: 0.78rem; color: #7b8798; }
.streak-meta strong { color: #35445d; font-size: 0.82rem; font-weight: 600; }
.ghost-wide-button {
  width: 100%; margin-top: 14px; height: 36px;
  border: 1px solid #e0e7f2; border-radius: 999px;
  background: #f8fafc; color: #4f5f79;
  font: inherit; cursor: pointer;
}
.ghost-wide-button:hover { border-color: #2b6cff; color: #2b6cff; }
.logout-button {
  width: 100%; height: 36px; border: 1px solid #fee2e2; border-radius: 10px;
  background: #fff; color: #ef4444; font: inherit; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 0.82rem;
}
.logout-button:hover { background: #fef2f2; }
</style>
