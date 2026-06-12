<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const userStore = useUserStore()

const currentUserName = computed(() => userStore.userInfo.userId || '学生用户')
const userInitial = computed(() => (
  currentUserName.value ? String(currentUserName.value).slice(0, 1).toUpperCase() : 'U'
))

const overviewStats = [
  { label: '本周学习时长', value: '18.5', unit: '小时', trend: '+2.5h' },
  { label: '掌握知识点', value: '42', unit: '个', trend: '+12%' },
  { label: '平均掌握度', value: '86', unit: '%', trend: '+3%' },
]

const activeCourses = [
  { name: 'MATLAB 数值分析与实践', progress: 85, total: 24, done: 20, color: '#2563eb' },
  { name: '电路分析基础 (ELEC1201)', progress: 62, total: 40, done: 25, color: '#0891b2' },
  { name: '计算机网络原理', progress: 45, total: 32, done: 14, color: '#7c3aed' },
]

const aiFeedback = '本周你的整体节奏稳定，MATLAB 课程表现最好。相对薄弱点集中在电路分析中的综合应用题，建议优先补齐概念到推导的连接，再进入针对性练习。'

const goHome = () => router.push('/home')
const goAssistant = () => router.push('/assistant')
</script>

<template>
  <div class="progress-page">
    <header class="top-nav">
      <div class="nav-left">
        <div class="nav-logo" @click="goHome">智悉云擎</div>
        <nav class="nav-links">
          <a class="nav-link" @click="goHome">已有课程</a>
          <a class="nav-link active">学习进度</a>
          <a class="nav-link" @click="goAssistant">学习助手</a>
        </nav>
      </div>
      <div class="nav-right">
        <div class="user-mini">
          <span class="user-name">{{ currentUserName }}</span>
          <div class="avatar">{{ userInitial }}</div>
        </div>
      </div>
    </header>

    <main class="dashboard-container">
      <div class="page-header">
        <h1 class="page-title">学习进度总览</h1>
        <p class="page-subtitle">基于你的学习行为与阶段结果，系统持续更新你的当前状态与下一步建议。</p>
      </div>

      <section class="stats-grid">
        <div
          v-for="(stat, index) in overviewStats"
          :key="stat.label"
          class="stat-card"
          :style="{ animationDelay: `${index * 0.08}s` }"
        >
          <p class="stat-label">{{ stat.label }}</p>
          <div class="stat-main">
            <span class="stat-value">{{ stat.value }}</span>
            <span class="stat-unit">{{ stat.unit }}</span>
          </div>
          <div class="stat-trend">较上周 <span class="trend-up">{{ stat.trend }}</span></div>
        </div>
      </section>

      <div class="main-content-grid">
        <section class="panel-card course-panel">
          <h2 class="panel-title">课程完成情况</h2>
          <div class="course-list">
            <div v-for="course in activeCourses" :key="course.name" class="course-item">
              <div class="course-info">
                <span class="c-name">{{ course.name }}</span>
                <span class="c-count">{{ course.done }} / {{ course.total }} 节</span>
              </div>
              <div class="progress-wrapper">
                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: `${course.progress}%`, background: course.color }" />
                </div>
                <span class="progress-pct" :style="{ color: course.color }">{{ course.progress }}%</span>
              </div>
            </div>
          </div>
        </section>

        <section class="panel-card ai-panel">
          <div class="ai-header">
            <div class="ai-icon">AI</div>
            <h2 class="panel-title">本周学习建议</h2>
          </div>
          <div class="ai-content">
            <p class="ai-text">{{ aiFeedback }}</p>
          </div>
          <button class="action-btn" @click="goAssistant">
            打开学习助手
            <span>→</span>
          </button>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.progress-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(30, 95, 168, 0.14), transparent 24%),
    radial-gradient(circle at top right, rgba(33, 150, 243, 0.12), transparent 20%),
    linear-gradient(180deg, #f5f8fd 0%, #eef4fb 100%);
  font-family: 'Sora', sans-serif;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  height: 64px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  position: sticky;
  top: 0;
  z-index: 50;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 28px;
}

.nav-logo {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
}

.nav-links {
  display: flex;
  gap: 14px;
}

.nav-link {
  padding: 8px 14px;
  border-radius: 999px;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-link.active,
.nav-link:hover {
  color: #1565c0;
  background: rgba(30, 95, 168, 0.08);
}

.nav-right,
.user-mini {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e5fa8, #2196f3);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
}

.dashboard-container {
  width: min(1240px, calc(100% - 48px));
  margin: 32px auto 60px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.03em;
}

.page-subtitle {
  margin-top: 8px;
  color: #64748b;
  font-size: 15px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 24px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.04);
  animation: slide-up 0.5s ease forwards;
  opacity: 0;
  transform: translateY(10px);
}

.stat-label {
  font-size: 14px;
  color: #64748b;
  font-weight: 600;
}

.stat-main {
  margin: 12px 0;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1;
}

.stat-unit {
  font-size: 14px;
  color: #64748b;
}

.stat-trend {
  font-size: 13px;
  color: #94a3b8;
}

.trend-up {
  color: #059669;
  font-weight: 600;
}

.main-content-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 24px;
}

.panel-card {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 28px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 20px 42px rgba(15, 23, 42, 0.05);
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 20px;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.course-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  align-items: center;
}

.c-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.c-count {
  font-size: 13px;
  color: #64748b;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-pct {
  width: 40px;
  text-align: right;
  font-size: 14px;
  font-weight: 700;
}

.ai-panel {
  background: linear-gradient(145deg, #0d1f3c 0%, #1e5fa8 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.ai-header .panel-title {
  color: #fff;
  margin: 0;
}

.ai-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  font-size: 12px;
  font-weight: 700;
}

.ai-content {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  padding: 20px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  margin-bottom: 24px;
}

.ai-text {
  font-size: 15px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.9);
}

.action-btn {
  border: none;
  padding: 14px;
  border-radius: 12px;
  background: #fff;
  color: #1e5fa8;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f8fafc;
  transform: translateY(-2px);
}

@keyframes slide-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 960px) {
  .stats-grid,
  .main-content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .top-nav {
    height: auto;
    padding: 14px 16px;
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }

  .nav-left,
  .nav-right,
  .nav-links {
    width: 100%;
    flex-wrap: wrap;
  }

  .dashboard-container {
    width: calc(100% - 24px);
    margin-top: 20px;
  }
}
</style>
