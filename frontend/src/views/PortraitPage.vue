<template>
  <div class="portrait-page">
    <button type="button" class="back-link" @click="goBack">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回</span>
    </button>

    <section class="portrait-header">
      <div class="portrait-user">
        <div class="portrait-avatar">李</div>
        <div class="portrait-info">
          <div class="name-row">
            <span class="name">李同学</span>
            <span class="level">Lv.6</span>
            <span class="grade">初二</span>
          </div>
          <p class="summary">勤奋好学，善于思考，持续进步中！</p>
          <div class="meta-row">
            <span><el-icon><CollectionTag /></el-icon>智学号：ZX2024001025</span>
            <span><el-icon><Calendar /></el-icon>加入时间：2024-02-18</span>
            <span><el-icon><Clock /></el-icon>最近学习：今天 14:32</span>
          </div>
        </div>
      </div>

      <div class="header-filters">
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
            <div class="score-label">
              <span class="score-icon" :style="{ background: item.bg, color: item.color }">
                <el-icon><component :is="item.icon" /></el-icon>
              </span>
              <span>{{ item.name }}</span>
            </div>
            <div class="score-bar">
              <div class="score-fill" :style="{ width: `${item.score}%` }"></div>
            </div>
            <span class="score-value">{{ item.score }}分</span>
          </div>
        </div>
      </article>

      <div class="right-stack">
        <article class="surface-card mini-card">
          <div class="mini-head success">
            <span class="mini-dot"></span>
            <h3>优势标签</h3>
          </div>
          <div class="tag-group">
            <span v-for="item in strengths" :key="item" class="portrait-tag success">{{ item }}</span>
          </div>
        </article>

        <article class="surface-card mini-card">
          <div class="mini-head warning">
            <span class="mini-dot"></span>
            <h3>待提升项</h3>
          </div>
          <div class="tag-group">
            <span v-for="item in improvements" :key="item" class="portrait-tag warning">{{ item }}</span>
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
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
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

const router = useRouter()
const radarRef = ref(null)
const trendRef = ref(null)
const subjectFilter = ref('all')
const rangeFilter = ref('30d')
const activeEvidenceTab = ref('system')
let radarChart = null
let trendChart = null

const scores = [
  { name: '知识掌握', score: 78, icon: Reading, bg: 'rgba(59, 130, 246, 0.12)', color: '#3b82f6' },
  { name: '学习方法', score: 72, icon: TrendCharts, bg: 'rgba(16, 185, 129, 0.12)', color: '#10b981' },
  { name: '思维能力', score: 68, icon: Histogram, bg: 'rgba(245, 158, 11, 0.14)', color: '#f59e0b' },
  { name: '应用能力', score: 74, icon: Management, bg: 'rgba(139, 92, 246, 0.12)', color: '#8b5cf6' },
  { name: '学习态度', score: 85, icon: Star, bg: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa' },
  { name: '时间管理', score: 70, icon: Stopwatch, bg: 'rgba(16, 185, 129, 0.1)', color: '#14b8a6' },
]

const strengths = ['学习态度积极', '课堂参与度高', '坚持自律', '善于总结归纳', '基础知识扎实']
const improvements = ['复杂问题分析', '解题步骤规范性', '知识迁移能力', '时间分配合理性']

const evidenceTabs = [
  { key: 'system', label: '系统证据' },
  { key: 'study', label: '学习证据' },
]

const evidenceMap = {
  system: [
    { title: '知识点掌握率', desc: '近30天共掌握 142 个知识点，掌握率 78%', date: '2024-06-08', icon: DataAnalysis, bg: 'rgba(59,130,246,0.12)', color: '#3b82f6' },
    { title: '做题准确率', desc: '练习题平均正确率 82%，高于班级平均 12%', date: '2024-06-08', icon: EditPen, bg: 'rgba(16,185,129,0.12)', color: '#10b981' },
    { title: '学习时长', desc: '近30天累计学习时长 32.6 小时', date: '2024-06-08', icon: Stopwatch, bg: 'rgba(99,102,241,0.12)', color: '#6366f1' },
    { title: '错题情况', desc: '错题订正率 86%，较上月提升 8%', date: '2024-06-08', icon: DocumentChecked, bg: 'rgba(239,68,68,0.1)', color: '#ef4444' },
  ],
  study: [
    { title: '视频学习完成度', desc: '本周完成 5 节课程，完成率保持稳定', date: '2024-06-08', icon: Reading, bg: 'rgba(59,130,246,0.12)', color: '#2563eb' },
    { title: '练习活跃度', desc: '最近 7 天完成 8 次练习，连续打卡 6 天', date: '2024-06-07', icon: EditPen, bg: 'rgba(245,158,11,0.14)', color: '#f59e0b' },
    { title: '笔记整理质量', desc: '学习笔记完成度高，重点总结较完整', date: '2024-06-06', icon: Management, bg: 'rgba(16,185,129,0.12)', color: '#10b981' },
    { title: '复盘频率', desc: '每周至少完成 2 次复盘，保持良好习惯', date: '2024-06-05', icon: TrendCharts, bg: 'rgba(139,92,246,0.12)', color: '#8b5cf6' },
  ],
}

const activeEvidences = computed(() => evidenceMap[activeEvidenceTab.value] || [])

const actions = [
  { title: '专题提升：复杂问题分析', desc: '推荐完成《多步骤应用题专项训练》', btn: '去练习', icon: EditPen, bg: 'rgba(139,92,246,0.12)', color: '#8b5cf6', action: () => router.push('/resources?resource_type=quiz') },
  { title: '学习策略：解题规范训练', desc: '掌握解题步骤书写和思路拆解技巧', btn: '去学习', icon: Promotion, bg: 'rgba(59,130,246,0.12)', color: '#3b82f6', action: () => router.push('/resources') },
  { title: '能力拓展：知识迁移训练', desc: '尝试跨章节综合题，提升迁移能力', btn: '去挑战', icon: Histogram, bg: 'rgba(16,185,129,0.12)', color: '#10b981', action: () => router.push('/resources?resource_type=quiz') },
  { title: '时间管理：优化学习计划', desc: '建议制定更清晰的每日学习计划', btn: '去规划', icon: Calendar, bg: 'rgba(245,158,11,0.14)', color: '#f59e0b', action: () => router.push('/learning-path') },
]

function goBack() {
  router.back()
}

function goResources() {
  router.push('/resources')
}

function goLearningPath() {
  router.push('/learning-path')
}

function initRadarChart() {
  if (!radarRef.value) return
  if (!radarChart) radarChart = echarts.init(radarRef.value)

  radarChart.setOption({
    radar: {
      center: ['50%', '54%'],
      radius: '64%',
      splitNumber: 4,
      axisName: { color: '#64748b', fontSize: 10 },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.24)' } },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.18)' } },
      splitArea: { areaStyle: { color: ['rgba(43,108,255,0.02)', 'rgba(43,108,255,0.05)'] } },
      indicator: scores.map((item) => ({ name: item.name, max: 100 })),
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 5,
        data: [
          {
            value: scores.map((item) => item.score),
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
  if (!trendChart) trendChart = echarts.init(trendRef.value)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 16, bottom: 30, left: 28 },
    legend: {
      top: 0,
      right: 0,
      icon: 'circle',
      itemWidth: 8,
      textStyle: { color: '#64748b', fontSize: 11 },
      data: ['知识掌握', '思维能力', '应用能力'],
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['04-20', '04-27', '05-04', '05-11', '05-18', '05-25', '06-01', '06-08'],
      axisLabel: { color: '#98a2b3', fontSize: 10 },
      axisLine: { lineStyle: { color: '#edf2f8' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#98a2b3', fontSize: 10 },
      splitLine: { lineStyle: { color: '#edf2f8' } },
    },
    series: [
      { name: '知识掌握', type: 'line', smooth: true, data: [65, 68, 72, 75, 76, 77, 77, 85], lineStyle: { color: '#2b6cff', width: 2 }, itemStyle: { color: '#2b6cff' } },
      { name: '思维能力', type: 'line', smooth: true, data: [42, 46, 50, 53, 56, 58, 60, 68], lineStyle: { color: '#10b981', width: 2 }, itemStyle: { color: '#10b981' } },
      { name: '应用能力', type: 'line', smooth: true, data: [50, 54, 57, 60, 64, 66, 70, 74], lineStyle: { color: '#8b5cf6', width: 2 }, itemStyle: { color: '#8b5cf6' } },
    ],
  })
}

function handleResize() {
  radarChart?.resize()
  trendChart?.resize()
}

onMounted(() => {
  nextTick(() => {
    initRadarChart()
    initTrendChart()
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
  trendChart?.dispose()
  radarChart = null
  trendChart = null
})
</script>

<style scoped>
.portrait-page {
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

.portrait-header,
.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.portrait-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 22px;
}

.portrait-user {
  display: flex;
  align-items: center;
  gap: 16px;
}

.portrait-avatar {
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

.portrait-info {
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.name {
  font-size: 1.45rem;
  font-weight: 700;
  color: #27364f;
}

.level,
.grade {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
}

.level {
  background: #2b6cff;
  color: #fff;
}

.grade {
  background: #eef3ff;
  color: #5b7bc8;
}

.summary {
  margin-top: 6px;
  font-size: 0.88rem;
  color: #5f7190;
}

.meta-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #8b98ab;
  font-size: 0.76rem;
}

.meta-row span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.header-filters {
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

.score-label {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #4f5f79;
  font-size: 0.84rem;
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

.score-bar {
  height: 8px;
  border-radius: 999px;
  background: #e9eff8;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2b6cff, #67a0ff);
}

.score-value {
  color: #4f5f79;
  font-size: 0.8rem;
}

.right-stack {
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

.portrait-tag {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.76rem;
  line-height: 1;
}

.portrait-tag.success {
  background: #edf9f1;
  color: #2f9e60;
}

.portrait-tag.warning {
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

  .right-stack {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .portrait-header {
    flex-direction: column;
  }

  .portrait-user,
  .evidence-item,
  .action-item {
    align-items: flex-start;
  }

  .meta-row {
    flex-direction: column;
    gap: 8px;
  }

  .header-filters,
  .right-stack {
    width: 100%;
    grid-template-columns: 1fr;
  }

  .score-item {
    grid-template-columns: 1fr;
  }
}
</style>
