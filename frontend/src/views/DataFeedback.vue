<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { generateDashboardData } from '@/momo/dashboardData'

const route = useRoute()
const router = useRouter()

const courseOptions = [
  { id: 'course-1', name: '人工智能导论' },
  { id: 'course-2', name: '机器学习基础' },
  { id: 'course-3', name: '数据结构与算法' },
  { id: 'course-4', name: 'Python 程序设计' },
]

const selectedCourseId = ref(route.query.courseId || courseOptions[0].id)
const data = computed(() => generateDashboardData(selectedCourseId.value))

watch(selectedCourseId, (val) => {
  router.replace({ query: { ...route.query, courseId: val } })
})
</script>

<template>
  <div class="analytics-page">
    <!-- hero -->
    <section class="analytics-hero">
      <div class="hero-top">
        <div class="hero-copy">
          <p class="hero-eyebrow">LEARNING ANALYTICS</p>
          <h2 style="font-size: 30px;">学情数据</h2>
          <p class="hero-subtitle">{{ data.courseUnit }} · {{ data.studentCount }} 名学生</p>
        </div>
        <div class="hero-course-picker">
          <span class="picker-label">当前课程</span>
          <div class="course-select-wrap">
            <svg class="cs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <select v-model="selectedCourseId" class="course-select">
              <option v-for="c in courseOptions" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <svg class="cs-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2.5">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>
      </div>

      <div class="hero-cards">
        <div class="hcard">
          <div class="hcard-icon" style="--hc-bg:rgba(94,234,212,0.18);--hc-color:#5eead4">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <span class="hcard-num">{{ data.totalInteractions }}<small> 次</small></span>
          <span class="hcard-label">课堂交互</span>
        </div>
        <div class="hcard">
          <div class="hcard-icon" style="--hc-bg:rgba(167,139,250,0.18);--hc-color:#c4b5fd">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
          </div>
          <span class="hcard-num">{{ data.totalPages }}<small> 页</small></span>
          <span class="hcard-label">课件页数</span>
        </div>
        <div class="hcard">
          <div class="hcard-icon" style="--hc-bg:rgba(251,191,36,0.18);--hc-color:#fbbf24">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20V10" />
              <path d="M18 20V4" />
              <path d="M6 20v-4" />
            </svg>
          </div>
          <span class="hcard-num">{{ data.clusters.length }}<small> 类</small></span>
          <span class="hcard-label">问题聚类</span>
        </div>
        <div class="hcard">
          <div class="hcard-icon" style="--hc-bg:rgba(52,211,153,0.18);--hc-color:#34d399">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <span class="hcard-num">{{ data.advices.length }}<small> 条</small></span>
          <span class="hcard-label">优化建议</span>
        </div>
      </div>
    </section>

    <!-- charts row -->
    <div class="panel-row">
      <!-- bar chart -->
      <div class="panel">
        <h3 class="panel-title">各页课件交互热度</h3>
        <div class="bar-wrap">
          <div class="bar-chart">
            <div v-for="bar in data.barData" :key="bar.page" class="bar-col">
              <span :class="['bar-val', { hot: bar.danger }]">{{ bar.val }}</span>
              <div :class="['bar', { hot: bar.danger }]" :style="{ height: bar.pct + '%' }" />
              <span :class="['bar-page', { hot: bar.danger }]">{{ bar.page }}</span>
            </div>
          </div>
        </div>
        <!-- student questions -->
        <div class="query-section">
          <p class="query-title">高频学生提问</p>
          <div class="query-tags">
            <span v-for="q in data.rawQueries" :key="q" class="query-tag">{{ q }}</span>
          </div>
        </div>
      </div>

      <!-- problem clusters + advice -->
      <div class="panel">
        <h3 class="panel-title">常见问题分布</h3>
        <div class="cluster-list">
          <div v-for="c in data.clusters" :key="c.label" class="cluster-item">
            <div class="ci-head">
              <span class="ci-name">{{ c.label }}</span>
              <span class="ci-pct" :style="{ color: c.color }">{{ c.pct }}% · {{ c.count }}人</span>
            </div>
            <p class="ci-desc">{{ c.desc }}</p>
            <div class="ci-bar">
              <div class="ci-fill" :style="{ width: c.pct + '%', background: c.color }" />
            </div>
          </div>
        </div>

        <div class="advice-section">
          <p class="advice-head">教学优化建议</p>
          <div v-for="adv in data.advices" :key="adv.title" class="advice-card">
            <span :class="['advice-badge', adv.tagClass]">{{ adv.tag }}</span>
            <div class="advice-body">
              <strong>{{ adv.title }}</strong>
              <p v-html="adv.content.replace(/\|([^|]+)\|/g, (_, m) => `<em>${m}</em>`)" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap');

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.analytics-page {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto;
  align-content: start;
  gap: 22px;
  padding: 8px 14px 18px;
  font-family: 'Sora', sans-serif;
  color: #0f172a;
}

/* ── Hero ── */
.analytics-hero {
  position: relative;
  overflow: hidden;
  padding: clamp(28px, 3.5vh, 34px) 36px;
  border-radius: 8px;
  margin-bottom: 0;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(255, 255, 255, 0.92) 46%, rgba(14, 165, 233, 0.16)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px);
  background-size: auto, 22px 22px, 22px 22px;
  border: 1px solid rgba(20, 184, 166, 0.16);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
}

.analytics-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 72% 22%, rgba(20, 184, 166, 0.14), transparent 24%),
    radial-gradient(circle at 95% 72%, rgba(59, 130, 246, 0.12), transparent 22%);
}

.hero-top {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.hero-eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  color: #0f766e;
  text-transform: uppercase;
}

.hero-title {
  margin: 0 0 8px;
  font-size: 30px;
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: 0;
  color: #0f172a;
}

.hero-subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.hero-course-picker {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.picker-label {
  font-size: 9.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #0f766e;
}

.course-select-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 9px;
  background: #fff;
  border: 1px solid #ccfbf1;
}

.cs-icon {
  color: #14b8a6;
  flex-shrink: 0;
}

.course-select {
  all: unset;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  min-width: 140px;
  appearance: none;
}

.cs-arrow {
  color: #14b8a6;
  flex-shrink: 0;
}

/* hero cards */
.hero-cards {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.hcard {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}

.hcard-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--hc-bg);
  color: var(--hc-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.hcard-num {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.hcard-num small {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
}

.hcard-label {
  display: block;
  font-size: 10.5px;
  font-weight: 600;
  color: #64748b;
}

/* panel row */
.panel-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  height: clamp(560px, calc((100vh / var(--design-scale, 1)) - 318px), 720px);
  min-height: 0;
}

.panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 20px;
}

/* bar chart */
.bar-wrap {
  flex: 1 1 auto;
  min-height: 210px;
  margin-bottom: 24px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 100%;
  padding-bottom: 6px;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  min-width: 0;
}

.bar-val {
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  margin-bottom: 4px;
}

.bar-val.hot {
  color: #ef4444;
  font-weight: 800;
}

.bar {
  width: 70%;
  max-width: 32px;
  background: linear-gradient(180deg, #5eead4, #99f6e4);
  border-radius: 5px 5px 0 0;
  transition: height 0.5s ease;
  min-height: 4px;
}

.bar.hot {
  background: linear-gradient(180deg, #ef4444, #f87171);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.3);
}

.bar-page {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  margin-top: 6px;
}

.bar-page.hot {
  color: #ef4444;
  font-weight: 700;
}

/* queries */
.query-section {
  border-top: 1px solid #f1f5f9;
  padding-top: 18px;
}

.query-title {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  margin-bottom: 10px;
}

.query-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.query-tag {
  padding: 5px 10px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 11.5px;
  font-weight: 500;
  color: #475569;
}

/* clusters */
.cluster-list {
  display: flex;
  flex-direction: column;
  gap: clamp(16px, 2vh, 22px);
  margin-bottom: clamp(24px, 3vh, 34px);
}

.ci-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
}

.ci-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.ci-pct {
  font-size: 12px;
  font-weight: 800;
}

.ci-desc {
  font-size: 11.5px;
  color: #64748b;
  margin-bottom: 8px;
}

.ci-bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}

.ci-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}

/* advice */
.advice-section {
  border-top: 1px solid #f1f5f9;
  padding-top: 18px;
}

.advice-head {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  margin-bottom: 12px;
}

.advice-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  margin-bottom: 8px;
}

.advice-badge {
  font-size: 10.5px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 5px;
  white-space: nowrap;
  flex-shrink: 0;
  height: fit-content;
}

.tag-visual {
  background: #f0fdfa;
  color: #0f766e;
}

.tag-branch {
  background: #eff6ff;
  color: #2563eb;
}

.advice-body strong {
  font-size: 12.5px;
  font-weight: 700;
  color: #1e293b;
  display: block;
  margin-bottom: 4px;
}

.advice-body p {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

.advice-body :deep(em) {
  font-style: normal;
  font-weight: 700;
  color: #0f766e;
  background: #f0fdfa;
  padding: 1px 4px;
  border-radius: 3px;
}

@media (max-width: 1100px) {
  .hero-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .panel-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .analytics-page {
    padding: 0 0 36px;
  }

  .analytics-hero {
    padding: 24px 18px;
  }

  .hero-top {
    flex-direction: column;
  }

  .hero-course-picker {
    align-items: flex-start;
  }

  .hero-cards {
    grid-template-columns: 1fr 1fr;
  }

  .panel-row {
    grid-template-columns: 1fr;
  }
}
</style>
