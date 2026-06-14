<template>
  <div class="report-page">
    <button type="button" class="back-link" @click="goBack">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回</span>
    </button>

    <div v-if="!hasProfile" class="empty-state-report">
      <el-icon :size="48" color="#94a3b8"><DataAnalysis /></el-icon>
      <h3>尚未生成学习报告</h3>
      <p>请先完成个人信息初始化，系统将根据你的学习数据生成详细的学习报告。</p>
      <el-button type="primary" @click="goInit">去初始化画像</el-button>
    </div>

    <template v-if="hasProfile">

    <section class="report-header">
      <div class="report-user">
        <div class="report-avatar">{{ (userStore.username || '用')[0] }}</div>
        <div class="report-user-info">
          <div class="report-name-row">
            <span class="report-name">{{ userStore.username || '同学' }}</span>
            <span class="report-level">Lv.6</span>
            <span class="report-grade">初二</span>
          </div>
          <p class="report-slogan">勤奋好学，善于思考，持续进步中！</p>
          <div class="report-meta">
            <span><el-icon><CollectionTag /></el-icon>智学号：ZX2024001025</span>
            <span><el-icon><Calendar /></el-icon>加入时间：2024-02-18</span>
            <span><el-icon><Clock /></el-icon>最近学习：今天 14:32</span>
          </div>
        </div>
      </div>

      <div class="report-filters">
        <el-select v-model="subjectFilter" size="small" style="width: 120px">
          <el-option label="全部学科" value="all" />
          <el-option label="数学" value="math" />
          <el-option label="编程" value="coding" />
        </el-select>
        <el-select v-model="rangeFilter" size="small" style="width: 108px">
          <el-option label="近30天" value="30d" />
          <el-option label="近7天" value="7d" />
        </el-select>
      </div>
    </section>

    <section class="top-grid">
      <article class="surface-card radar-card">
        <div class="section-head">
          <h2>综合能力雷达图</h2>
          <el-icon class="info-icon"><InfoFilled /></el-icon>
        </div>
        <div ref="radarRef" class="radar-chart"></div>
      </article>

      <article class="surface-card score-card">
        <div class="section-head">
          <h2>各维度得分</h2>
        </div>
        <div class="score-list">
          <div v-for="item in scores" :key="item.name" class="score-item">
            <div class="score-left">
              <span class="score-icon" :style="{ background: item.bg, color: item.color }">
                <el-icon><component :is="item.icon" /></el-icon>
              </span>
              <span class="score-name">{{ item.name }}</span>
            </div>
            <div class="score-bar">
              <div class="score-bar-fill" :style="{ width: `${item.score}%` }"></div>
            </div>
            <span class="score-value">{{ item.score }}分</span>
          </div>
        </div>
      </article>

      <div class="side-stack">
        <article class="surface-card mini-card">
          <div class="mini-head success">
            <span class="mini-dot"></span>
            <h3>优势标签</h3>
          </div>
          <div class="tag-group">
            <span v-for="item in strengths" :key="item" class="report-tag success">{{ item }}</span>
          </div>
        </article>

        <article class="surface-card mini-card">
          <div class="mini-head warning">
            <span class="mini-dot"></span>
            <h3>待提升项</h3>
          </div>
          <div class="tag-group">
            <span v-for="item in improvements" :key="item" class="report-tag warning">{{ item }}</span>
          </div>
        </article>
      </div>
    </section>

    <section class="bottom-grid">
      <article class="surface-card trend-card">
        <div class="section-head">
          <h2>能力趋势</h2>
          <el-icon class="info-icon"><InfoFilled /></el-icon>
        </div>
        <div ref="trendRef" class="trend-chart"></div>
      </article>

      <article class="surface-card evidence-card">
        <div class="section-head evidence-head">
          <div class="evidence-tabs">
            <button
              v-for="tab in evidenceTabs"
              :key="tab.key"
              type="button"
              :class="['evidence-tab', { active: activeEvidenceTab === tab.key }]"
              @click="activeEvidenceTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div class="evidence-list">
          <div v-for="item in activeEvidences" :key="item.title" class="evidence-item">
            <span class="evidence-icon" :style="{ background: item.bg, color: item.color }">
              <el-icon><component :is="item.icon" /></el-icon>
            </span>
            <div class="evidence-main">
              <div class="evidence-title">{{ item.title }}</div>
              <div class="evidence-desc">{{ item.desc }}</div>
            </div>
            <span class="evidence-date">{{ item.date }}</span>
          </div>
        </div>

        <button type="button" class="footer-link" @click="goResources">查看全部证据</button>
      </article>

      <article class="surface-card actions-card">
        <div class="section-head">
          <h2>推荐下一步行动</h2>
        </div>

        <div class="action-list">
          <div v-for="item in actions" :key="item.title" class="action-item">
            <span class="action-icon" :style="{ background: item.bg, color: item.color }">
              <el-icon><component :is="item.icon" /></el-icon>
            </span>
            <div class="action-main">
              <div class="action-title">{{ item.title }}</div>
              <div class="action-desc">{{ item.desc }}</div>
            </div>
            <el-button size="small" type="primary" @click="item.action">{{ item.btn }}</el-button>
          </div>
        </div>

        <button type="button" class="footer-link" @click="goLearningPath">查看完整学习计划</button>
      </article>
    </section>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  ArrowLeft,
  Calendar,
  Clock,
  CollectionTag,
  DataAnalysis,
  DocumentChecked,
  EditPen,
  Histogram,
  InfoFilled,
  Management,
  Promotion,
  Reading,
  Star,
  Stopwatch,
  TrendCharts,
} from '@element-plus/icons-vue'
import { useProfileStore } from '@/store/profileStore'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const profileStore = useProfileStore()
const userStore = useUserStore()
const radarRef = ref(null)
const trendRef = ref(null)
const subjectFilter = ref('all')
const rangeFilter = ref('30d')
const activeEvidenceTab = ref('system')
let radarChart = null
let trendChart = null

const hasProfile = computed(() => !!profileStore.profile)

function goBack() { router.push('/') }
function goInit() { router.push('/profile/init') }

// ── 真实画像数据 ──────────────────────────────────────
const profileDims = computed(() => {
  if (!profileStore.profile?.profile_json?.dimensions) return {}
  return profileStore.profile.profile_json.dimensions
})

const scores = computed(() => {
  const dims = profileDims.value
  const dimNames = {
    basic_knowledge: '知识掌握',
    engineering_ability: '工程能力',
    ai_data_ability: 'AI与数据',
    learning_goal: '学习目标',
    resource_preference: '资源偏好',
    learning_behavior: '学习行为',
  }
  return Object.entries(dimNames).map(([key, name]) => ({
    name,
    score: dims[key]?.score || 0,
    icon: Reading,
    bg: 'rgba(59, 130, 246, 0.12)',
    color: '#3b82f6',
    level: dims[key]?.level || '',
  }))
})

const strengths = computed(() => {
  const all = []
  Object.values(profileDims.value).forEach(d => {
    if (d.strengths) d.strengths.forEach(s => all.push(s))
  })
  return all.length ? all.slice(0, 5) : ['暂无数据']
})

const improvements = computed(() => {
  const all = []
  Object.values(profileDims.value).forEach(d => {
    if (d.weaknesses) d.weaknesses.forEach(w => all.push(w))
  })
  return all.length ? all.slice(0, 5) : ['暂无数据']
})

const evidenceTabs = [
  { key: 'system', label: '系统证据' },
  { key: 'study', label: '学习证据' },
]

const evidenceMap = {
  system: [
    { title: '知识点掌握率', desc: '基于画像分析的综合评估', date: '2025-05-20', icon: DataAnalysis, bg: 'rgba(59,130,246,0.12)', color: '#3b82f6' },
    { title: 'AI 分析依据', desc: profileStore.profile?.profile_json?.summary?.slice(0, 60) || '基于对话历史分析', date: '2025-05-20', icon: EditPen, bg: 'rgba(16,185,129,0.12)', color: '#10b981' },
  ],
  study: [
    { title: '学习时长', desc: '累计学习数据来自学习记录', date: '2025-05-20', icon: Stopwatch, bg: 'rgba(99,102,241,0.12)', color: '#6366f1' },
    { title: '活跃度', desc: '持续使用平台学习', date: '2025-05-20', icon: Reading, bg: 'rgba(59,130,246,0.12)', color: '#2563eb' },
  ],
}

const activeEvidences = computed(() => evidenceMap[activeEvidenceTab.value] || [])

const actions = [
  { title: '完成个性化路径', desc: '根据画像生成专属学习路线', btn: '去学习', icon: Promotion, bg: 'rgba(59,130,246,0.12)', color: '#3b82f6', action: () => router.push('/learning-path') },
  { title: '探索推荐资源', desc: '基于画像推荐最合适的资源', btn: '去资源', icon: Histogram, bg: 'rgba(16,185,129,0.12)', color: '#10b981', action: () => router.push('/resources') },
  { title: '更新学习画像', desc: '重新对话生成更准确的画像', btn: '去更新', icon: Calendar, bg: 'rgba(245,158,11,0.14)', color: '#f59e0b', action: () => router.push('/profile/init') },
]

function goResources() {
  router.push('/resources')
}

function goLearningPath() {
  router.push('/learning-path')
}

function initRadarChart() {
  if (!radarRef.value) return
  if (!radarChart) {
    radarChart = echarts.init(radarRef.value)
  }

  radarChart.setOption({
    radar: {
      center: ['50%', '54%'],
      radius: '64%',
      splitNumber: 4,
      axisName: {
        color: '#64748b',
        fontSize: 10,
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.24)',
        },
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.18)',
        },
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(43,108,255,0.02)', 'rgba(43,108,255,0.05)'],
        },
      },
      indicator: scores.value.map((item) => ({ name: item.name, max: 100 })),
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 5,
        data: [
          {
            value: scores.value.map((item) => item.score),
            areaStyle: { color: 'rgba(43,108,255,0.22)' },
            lineStyle: { color: '#2b6cff', width: 2 },
            itemStyle: { color: '#2b6cff' },
          },
        ],
      },
    ],
  })
}

function initTrendChart() {
  if (!trendRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendRef.value)
  }

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
    },
    grid: {
      top: 20,
      right: 16,
      bottom: 30,
      left: 28,
    },
    legend: {
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 8,
      textStyle: {
        color: '#64748b',
        fontSize: 11,
      },
      data: ['知识掌握', '思维能力', '应用能力'],
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['04-20', '04-27', '05-04', '05-11', '05-18', '05-25', '06-01', '06-08'],
      axisLabel: {
        color: '#98a2b3',
        fontSize: 10,
      },
      axisLine: {
        lineStyle: {
          color: '#edf2f8',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        color: '#98a2b3',
        fontSize: 10,
      },
      splitLine: {
        lineStyle: {
          color: '#edf2f8',
        },
      },
    },
    series: [
      {
        name: '知识掌握',
        type: 'line',
        smooth: true,
        data: [65, 68, 72, 75, 76, 77, 77, 85],
        lineStyle: { color: '#2b6cff', width: 2 },
        itemStyle: { color: '#2b6cff' },
      },
      {
        name: '思维能力',
        type: 'line',
        smooth: true,
        data: [42, 46, 50, 53, 56, 58, 60, 68],
        lineStyle: { color: '#10b981', width: 2 },
        itemStyle: { color: '#10b981' },
      },
      {
        name: '应用能力',
        type: 'line',
        smooth: true,
        data: [50, 54, 57, 60, 64, 66, 70, 74],
        lineStyle: { color: '#8b5cf6', width: 2 },
        itemStyle: { color: '#8b5cf6' },
      },
    ],
  })
}

function resizeCharts() {
  radarChart?.resize()
  trendChart?.resize()
}

onMounted(async () => {
  await profileStore.fetchProfile()
  nextTick(() => {
    initRadarChart()
    initTrendChart()
    window.addEventListener('resize', resizeCharts)
  })
})

watch(activeEvidenceTab, () => {
  nextTick(() => {
    resizeCharts()
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  radarChart?.dispose()
  trendChart?.dispose()
  radarChart = null
  trendChart = null
})
</script>

<style scoped>
.report-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.back-link {
  width: fit-content;
  border: 0;
  background: transparent;
  color: #5f7190;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: inherit;
  cursor: pointer;
}

.report-header,
.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.report-header {
  padding: 18px 22px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.report-user {
  display: flex;
  align-items: center;
  gap: 16px;
}

.report-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #9cb7ff, #5b8cff);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  font-weight: 700;
  box-shadow: 0 10px 22px rgba(91, 140, 255, 0.22);
}

.report-user-info {
  min-width: 0;
}

.report-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.report-name {
  font-size: 1.45rem;
  font-weight: 700;
  color: #27364f;
}

.report-level,
.report-grade {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
}

.report-level {
  background: #2b6cff;
  color: #fff;
}

.report-grade {
  background: #eef3ff;
  color: #5b7bc8;
}

.report-slogan {
  margin-top: 6px;
  font-size: 0.88rem;
  color: #5f7190;
}

.report-meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #8b98ab;
  font-size: 0.76rem;
}

.report-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.report-filters {
  display: flex;
  gap: 10px;
}

.top-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, 1.08fr) minmax(240px, 0.84fr);
  gap: 18px;
}

.bottom-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
}

.surface-card {
  padding: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h2,
.mini-head h3 {
  font-size: 1rem;
  color: #1e293b;
}

.info-icon {
  color: #94a3b8;
  font-size: 14px;
}

.radar-chart {
  width: 100%;
  height: 310px;
}

.score-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.score-item {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.score-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.score-name {
  font-size: 0.84rem;
  color: #4f5f79;
}

.score-bar {
  height: 8px;
  border-radius: 999px;
  background: #e9eff8;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2b6cff, #67a0ff);
}

.score-value {
  color: #4f5f79;
  font-size: 0.8rem;
}

.side-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.mini-card {
  min-height: 146px;
}

.mini-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.mini-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
}

.mini-head.success .mini-dot {
  background: #9be3ba;
}

.mini-head.warning .mini-dot {
  background: #ffc875;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.report-tag {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.76rem;
  line-height: 1;
}

.report-tag.success {
  background: #edf9f1;
  color: #2f9e60;
}

.report-tag.warning {
  background: #fff4e4;
  color: #d68518;
}

.trend-chart {
  width: 100%;
  height: 210px;
}

.evidence-head {
  margin-bottom: 10px;
}

.evidence-tabs {
  display: flex;
  gap: 18px;
}

.evidence-tab {
  border: 0;
  background: transparent;
  color: #8b98ab;
  font: inherit;
  cursor: pointer;
  padding-bottom: 8px;
  position: relative;
}

.evidence-tab.active {
  color: #2b6cff;
  font-weight: 600;
}

.evidence-tab.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: #2b6cff;
}

.evidence-list,
.action-list {
  display: flex;
  flex-direction: column;
}

.evidence-item,
.action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #edf2f8;
}

.evidence-item:last-child,
.action-item:last-child {
  border-bottom: 0;
}

.evidence-icon,
.action-icon {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  font-size: 14px;
}

.evidence-main,
.action-main {
  min-width: 0;
  flex: 1;
}

.evidence-title,
.action-title {
  color: #27364f;
  font-size: 0.84rem;
}

.evidence-desc,
.action-desc {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 0.74rem;
  line-height: 1.55;
}

.evidence-date {
  color: #94a3b8;
  font-size: 0.72rem;
}

.footer-link {
  width: fit-content;
  margin: 10px auto 0;
  border: 0;
  background: transparent;
  color: #2b6cff;
  font: inherit;
  cursor: pointer;
}

@media (max-width: 1280px) {
  .top-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .side-stack {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .report-header {
    flex-direction: column;
  }

  .report-user {
    align-items: flex-start;
  }

  .report-meta {
    flex-direction: column;
    gap: 8px;
  }

  .report-filters,
  .side-stack {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .score-item {
    grid-template-columns: 1fr;
  }

  .evidence-item,
  .action-item {
    align-items: flex-start;
  }
}
</style>
