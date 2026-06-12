<script setup>
import { computed, ref } from 'vue'
import { useUserStore } from '@/store/userStore'

// 学生 Tabs
import StudentHomeTab from '@/views-mobile/home-tabs/student/HomeTab.vue'
import StudentAssistantTab from '@/views-mobile/home-tabs/student/AssistantTab.vue'
import StudentProfileTab from '@/views-mobile/home-tabs/student/ProfileTab.vue'

// 教师 Tabs
import TeacherHomeTab from '@/views-mobile/home-tabs/teacher/HomeTab.vue'
import TeacherCreateTab from '@/views-mobile/home-tabs/teacher/CreateTab.vue'
import TeacherProfileTab from '@/views-mobile/home-tabs/teacher/ProfileTab.vue'

const userStore = useUserStore()
const isTeacher = computed(() => userStore.userInfo.role === 'teacher')

// ── Tab 配置 ────────────────────────────────────────────────────────────
const studentTabs = [
  { name: 'home',      icon: 'wap-home-o',       label: '首页',    component: StudentHomeTab },
  { name: 'assistant', icon: 'chat-o',            label: 'AI 助手', component: StudentAssistantTab },
  { name: 'profile',   icon: 'user-circle-o',     label: '我的',    component: StudentProfileTab },
]

const teacherTabs = [
  { name: 'home',    icon: 'wap-home-o',       label: '首页',   component: TeacherHomeTab },
  { name: 'create',  icon: 'add-o',            label: '创课',   component: TeacherCreateTab },
  { name: 'profile', icon: 'user-circle-o',    label: '我的',   component: TeacherProfileTab },
]

const tabs = computed(() => isTeacher.value ? teacherTabs : studentTabs)
const activeTab = ref('home')

const activeComponent = computed(
  () => tabs.value.find((t) => t.name === activeTab.value)?.component ?? tabs.value[0].component,
)

// ── 角色切换 ────────────────────────────────────────────────────────────
const showRoleSheet = ref(false)
const roleActions = [
  { name: '学生', subname: '查看课程学习与 AI 助手', color: '#1677ff' },
  { name: '教师', subname: '管理智课与查看学情数据', color: '#7c3aed' },
]

const switchRole = ({ name }) => {
  const role = name === '教师' ? 'teacher' : 'student'
  userStore.login({ userId: userStore.userInfo.userId || 'demo-user', role }, userStore.token || 'demo-token')
  activeTab.value = 'home'
  showRoleSheet.value = false
}

// ── Header ──────────────────────────────────────────────────────────────
const headerTitle = computed(() => isTeacher.value ? '智悉云擎 · 教师端' : '智悉云擎 · 学生端')
const roleBadge = computed(() => isTeacher.value
  ? { label: '教师', color: '#7c3aed', bg: '#f5f0ff' }
  : { label: '学生', color: '#1677ff', bg: '#eef4ff' },
)
</script>

<template>
  <div class="home-root">
    <!-- 顶部 Header -->
    <header class="home-header">
      <div class="home-header__brand">
        <div class="brand-dot" />
        <span class="brand-title">{{ headerTitle }}</span>
      </div>
      <button class="role-btn" :style="{ background: roleBadge.bg, color: roleBadge.color }" @click="showRoleSheet = true">
        {{ roleBadge.label }}
        <van-icon name="exchange" size="13" style="margin-left:4px" />
      </button>
    </header>

    <!-- 内容区 -->
    <main class="home-body" :class="{ 'home-body--chat': activeTab === 'assistant' }">
      <transition name="tab-fade" mode="out-in">
        <component :is="activeComponent" :key="activeTab" />
      </transition>
    </main>

    <!-- 底部 TabBar -->
    <van-tabbar
      v-model="activeTab"
      safe-area-inset-bottom
      active-color="#1677ff"
      inactive-color="#9aa3b2"
      class="home-tabbar"
    >
      <van-tabbar-item
        v-for="tab in tabs"
        :key="tab.name"
        :name="tab.name"
        :icon="tab.icon"
      >
        {{ tab.label }}
      </van-tabbar-item>
    </van-tabbar>

    <!-- 角色切换 ActionSheet -->
    <van-action-sheet
      v-model:show="showRoleSheet"
      :actions="roleActions"
      title="切换角色"
      cancel-text="取消"
      close-on-click-action
      @select="switchRole"
    />
  </div>
</template>

<style scoped>
.home-root {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  overflow: hidden;
  background: #f5f7fa;
}

/* ── Header ── */
.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px 12px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
  position: sticky;
  top: 0;
  z-index: 20;
}

.home-header__brand {
  display: flex;
  align-items: center;
  gap: 9px;
}

.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #46aaff);
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.18);
}

.brand-title {
  font-size: 17px;
  font-weight: 800;
  color: #1a2035;
  letter-spacing: -0.02em;
}

.role-btn {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s;
}

.role-btn:active {
  opacity: 0.7;
}

/* ── Body ── */
.home-body {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 68px;
}

.home-body--chat {
  overflow: hidden;
  padding-bottom: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ── TabBar ── */
.home-tabbar :deep(.van-tabbar) {
  height: 60px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.home-tabbar :deep(.van-tabbar-item__text) {
  font-size: 11px;
  font-weight: 600;
}

/* ── Transition ── */
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.tab-fade-enter-from,
.tab-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
