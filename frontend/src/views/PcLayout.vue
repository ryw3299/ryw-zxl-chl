<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChatDotRound,
  Collection,
  DataAnalysis,
  FolderOpened,
  HomeFilled,
  Management,
  Medal,
  Notebook,
  Switch,
  TrophyBase,
  UploadFilled,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const designScale = ref(1)

const navGroups = computed(() => {
  if (userStore.isTeacher) {
    return [
      {
        title: '教学工作',
        items: [
          { key: 'home', label: '首页', path: '/pc/teacher/home', icon: HomeFilled },
          { key: 'teacher-courses', label: '我的课程', path: '/pc/teacher/my-courses', icon: Management },
          { key: 'upload', label: '课程创建', path: '/pc/teacher/upload', icon: UploadFilled },
          { key: 'prep-center', label: '备课中心', path: '/pc/teacher/prep-center', icon: Notebook },
          { key: 'courses', label: '资源空间', path: '/pc/teacher/resources', icon: FolderOpened },
        ],
      },
      {
        title: '分析与支持',
        items: [
          { key: 'assistant', label: 'AI 助教', path: '/pc/assistant', icon: ChatDotRound },
          { key: 'analytics', label: '学情数据', path: '/pc/learning-analytics', icon: DataAnalysis },
          { key: 'leaderboard', label: '成绩排行', path: '/pc/leaderboard', icon: Medal },
        ],
      },
    ]
  }

  return [
    {
      title: '学习中心',
      items: [
        { key: 'home', label: '首页', path: '/pc/home', icon: HomeFilled },
        { key: 'my-courses', label: '我的课程', path: '/pc/my-courses', icon: Management },
        { key: 'courses', label: '资源空间', path: '/pc/resources', icon: FolderOpened },
      ],
    },
    {
      title: '学习工具',
      items: [
        { key: 'assistant', label: '学习助手', path: '/pc/assistant', icon: ChatDotRound },
        { key: 'knowledge', label: '知识图谱', path: '/pc/knowledge-graph', icon: Collection },
        { key: 'lesson-game', label: '练习闯关', path: '/pc/lesson/game', icon: TrophyBase },
        { key: 'leaderboard', label: '成绩排行', path: '/pc/leaderboard', icon: Medal },
      ],
    },
  ]
})

const activeKey = computed(() => {
  const path = route.path
  if (path === '/pc/home' || path === '/pc/teacher/home' || path === '/pc') return 'home'
  if (path.startsWith('/pc/my-courses')) return 'my-courses'
  if (path.startsWith('/pc/teacher/my-courses')) return 'teacher-courses'
  if (path.startsWith('/pc/teacher/upload')) return 'upload'
  if (path.startsWith('/pc/teacher/prep-center')) return 'prep-center'
  if (path === '/pc/resources' || path.startsWith('/pc/teacher/resources')) return 'courses'
  if (path.startsWith('/pc/assistant')) return 'assistant'
  if (path.startsWith('/pc/learning-analytics')) return 'analytics'
  if (path.startsWith('/pc/knowledge-graph')) return 'knowledge'
  if (path.startsWith('/pc/lesson/game')) return 'lesson-game'
  if (path.startsWith('/pc/leaderboard')) return 'leaderboard'
  return ''
})

const scrollableWorkspace = computed(() => {
  const path = route.path
  return (
    path.startsWith('/pc/my-courses') ||
    path.startsWith('/pc/teacher/my-courses') ||
    path.startsWith('/pc/teacher/upload') ||
    path.startsWith('/pc/teacher/prep-center') ||
    path === '/pc/resources' ||
    path.startsWith('/pc/teacher/resources') ||
    path.startsWith('/pc/leaderboard') ||
    path.startsWith('/pc/knowledge-graph') ||
    path.startsWith('/pc/lesson/game')
  )
})

const spacedWorkspace = computed(() => {
  const path = route.path
  return (
    path === '/pc/resources' ||
    path.startsWith('/pc/teacher/resources') ||
    path.startsWith('/pc/knowledge-graph')
  )
})

const updateDesignScale = () => {
  if (typeof window === 'undefined') return
  designScale.value = Math.min(window.innerWidth / 1920, window.innerHeight / 913, 1)
}

const navigate = (path) => {
  router.push({ path, query: route.query })
}

const handleLogout = () => {
  userStore.logout()
  router.replace('/login')
}

onMounted(() => {
  updateDesignScale()
  window.addEventListener('resize', updateDesignScale)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDesignScale)
})
</script>

<template>
  <div class="design-viewport">
    <div
      class="pc-workspace-shell home-shell"
      :style="{
        '--design-scale': designScale,
        transform: `scale(${designScale})`,
      }"
    >
      <aside class="study-sidebar">
        <div class="brand-block">
          <img src="/image/brand-logo.png" alt="知微智课 AI 智能教学" />
        </div>

        <nav class="sidebar-nav">
          <section v-for="group in navGroups" :key="group.title" class="nav-section">
            <p>{{ group.title }}</p>
            <button
              v-for="item in group.items"
              :key="item.key"
              type="button"
              :class="['nav-button', { active: activeKey === item.key }]"
              @click="navigate(item.path)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </button>
          </section>
        </nav>

        <div class="sidebar-footer">
          <div class="footer-line"></div>
          <button type="button" class="footer-action" @click="handleLogout">
            <el-icon><Switch /></el-icon>
            <span>退出登录</span>
          </button>
          <small>知微智课 v2.1</small>
        </div>
      </aside>

      <section class="workspace-main">
        <main :class="['workspace-content', { 'workspace-content--scroll': scrollableWorkspace, 'workspace-content--spaced': spacedWorkspace }]">
          <router-view />
        </main>
      </section>
    </div>
  </div>
</template>

<style scoped>
:global(html:has(.design-viewport)),
:global(body:has(.design-viewport)),
:global(#app:has(.design-viewport)),
:global(.app-shell:has(.design-viewport)) {
  width: 100vw;
  height: 100vh;
  min-height: 0 !important;
  overflow: hidden !important;
}

.design-viewport {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: #f6f8fc;
}

:global(.pc-workspace-shell.home-shell) {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  width: calc(100vw / var(--design-scale, 1));
  height: calc(100vh / var(--design-scale, 1));
  min-height: 0;
  overflow: hidden;
  background: #f6f8fc;
  transform-origin: left top;
}

:global(.pc-workspace-shell.home-shell .workspace-main) {
  grid-column: auto !important;
  flex: 1 1 auto !important;
  width: auto !important;
  height: calc(100vh / var(--design-scale, 1)) !important;
  max-width: none !important;
  min-width: 0 !important;
  overflow: hidden !important;
}

:global(.pc-workspace-shell.home-shell .workspace-content) {
  width: 100% !important;
  max-width: none !important;
  height: calc(100vh / var(--design-scale, 1)) !important;
  padding: 0 !important;
  overflow: hidden !important;
}

:global(.pc-workspace-shell.home-shell .workspace-content.workspace-content--spaced) {
  padding-top: 24px !important;
}

:global(.pc-workspace-shell.home-shell .workspace-content.workspace-content--scroll) {
  overflow-x: hidden !important;
  overflow-y: auto !important;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: #cbd7e6 transparent;
}

:global(.pc-workspace-shell.home-shell .workspace-content.workspace-content--scroll::-webkit-scrollbar) {
  width: 10px;
}

:global(.pc-workspace-shell.home-shell .workspace-content.workspace-content--scroll::-webkit-scrollbar-track) {
  background: transparent;
}

:global(.pc-workspace-shell.home-shell .workspace-content.workspace-content--scroll::-webkit-scrollbar-thumb) {
  border: 2px solid #f6f8fc;
  border-radius: 999px;
  background: #cbd7e6;
}

.study-sidebar {
  position: relative;
  z-index: 5;
  display: flex;
  flex: 0 0 248px;
  width: 248px;
  height: calc(100vh / var(--design-scale, 1));
  min-height: 0;
  flex-direction: column;
  padding: 32px 24px 29px 20px;
  border-right: 1px solid #e0e6ef;
  background: rgba(255, 255, 255, 0.93);
  box-shadow: 10px 0 30px rgba(70, 86, 112, 0.03);
}

.brand-block {
  display: flex;
  align-items: center;
  width: 204px;
  height: 92px;
  margin: 0 0 16px 0;
  overflow: hidden;
}

.brand-block img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: left center;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-section p {
  margin: 0 0 2px 15px;
  color: #9aa5b5;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.nav-button,
.footer-action {
  display: flex;
  align-items: center;
  width: 100%;
  border: 0;
  font-family: inherit;
  letter-spacing: 0;
  background: transparent;
  cursor: pointer;
}

.nav-button {
  height: 52px;
  gap: 15px;
  padding: 0 15px;
  border-radius: 10px;
  color: #596579;
  font-size: 16px;
  font-weight: 700;
}

.nav-button .el-icon {
  width: 21px;
  height: 21px;
  font-size: 21px;
}

.nav-button.active {
  color: #596579;
  background: transparent;
}

.nav-button.active .el-icon {
  width: 21px;
  height: 21px;
  color: inherit;
  font-size: 21px;
  background: transparent;
}

.sidebar-footer {
  margin-top: auto;
}

.footer-line {
  height: 1px;
  margin: 0 2px 18px;
  background: #dde3ed;
}

.footer-action {
  gap: 10px;
  min-height: 36px;
  padding: 0 10px;
  color: #667085;
  font-size: 12px;
  font-weight: 650;
}

.footer-action svg,
.footer-action .el-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  color: #71809a;
  font-size: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sidebar-footer small {
  display: block;
  margin: 17px 0 0 10px;
  color: #9aa3b2;
  font-size: 12px;
}
</style>
