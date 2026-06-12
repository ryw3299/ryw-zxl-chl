<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { generateDashboardData } from '@/momo/dashboardData'

const router = useRouter()

const courses = [
  { id: 'course-1', label: '人工智能导论' },
  { id: 'course-2', label: '机器学习基础' },
  { id: 'course-3', label: '数据结构与算法' },
  { id: 'course-4', label: 'Python 程序设计' },
]

const activeCourse = ref('course-1')
const data = computed(() => generateDashboardData(activeCourse.value))

const primaryKpis = computed(() => [
  {
    label: '累计交互次数',
    value: String(data.value.totalInteractions),
    unit: '次',
    trend: `较上节课 +${12 + Math.floor(data.value.totalInteractions % 10)}%`,
    trendUp: true,
    color: '#1677ff',
    bg: '#eef4ff',
    icon: 'chat-o',
  },
  {
    label: 'AI 聚类置信度',
    value: data.value.nlpConfidence,
    unit: '',
    trend: `${data.value.clusters.length} 项核心错因`,
    trendUp: true,
    color: '#7c3aed',
    bg: '#f5f0ff',
    icon: 'cluster-o',
  },
])

const alertCards = computed(() => [
  {
    label: '高频质询节点',
    value: `第 ${data.value.dangerPage} 页`,
    desc: `学生在第 ${data.value.dangerPage} 页提问密集，建议加强讲解`,
    tag: '需关注',
    tagColor: '#f53f3f',
    color: '#f53f3f',
    bg: 'linear-gradient(135deg, #fff5f5 0%, #ffeaea 100%)',
    icon: 'warning-o',
  },
  {
    label: '待处理教研建议',
    value: `${data.value.adviceCount} 项`,
    desc: '包含课件优化、讲解节奏调整等建议',
    tag: '去查看',
    tagColor: '#059669',
    color: '#059669',
    bg: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
    icon: 'orders-o',
  },
])

const maxBar = computed(() => Math.max(...data.value.barData.map((b) => b.val)))
</script>

<template>
  <div class="sd-page">

    <!-- 顶栏 -->
    <div class="sd-topbar">
      <button class="sd-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <span class="sd-topbar-title">学生数据</span>
      <div style="width:36px" />
    </div>

    <!-- 课程筛选 -->
    <div class="sd-filter">
      <button v-for="c in courses" :key="c.id" class="sd-chip" :class="{ active: activeCourse === c.id }"
        @click="activeCourse = c.id">{{ c.label }}</button>
    </div>

    <!-- 课程概况横幅 -->
    <div class="sd-banner">
      <div class="sd-banner__text">
        <p class="sd-banner__eyebrow">AI 学情诊断</p>
        <h2 class="sd-banner__title">{{ data.courseName }}</h2>
        <p class="sd-banner__sub">{{ data.courseUnit }}</p>
      </div>
      <div class="sd-banner__deco">
        <div class="deco-ring deco-ring--1" />
        <div class="deco-ring deco-ring--2" />
        <van-icon name="chart-trending-o" size="36" color="rgba(255,255,255,0.3)" />
      </div>
    </div>

    <!-- 核心指标（数值型，两列） -->
    <div class="sd-kpi-grid">
      <div v-for="k in primaryKpis" :key="k.label" class="sd-kpi-card">
        <div class="sd-kpi-card__icon" :style="{ background: k.bg }">
          <van-icon :name="k.icon" size="18" :color="k.color" />
        </div>
        <div class="sd-kpi-card__body">
          <span class="sd-kpi-label">{{ k.label }}</span>
          <div class="sd-kpi-val" :style="{ color: k.color }">
            {{ k.value }}<em v-if="k.unit">{{ k.unit }}</em>
          </div>
          <p class="sd-kpi-trend">
            <van-icon :name="k.trendUp ? 'arrow-up' : 'arrow-down'" size="10" />
            {{ k.trend }}
          </p>
        </div>
      </div>
    </div>

    <!-- 行动项（富文本卡片，单列全宽） -->
    <div class="sd-alert-list">
      <div
        v-for="a in alertCards"
        :key="a.label"
        class="sd-alert-card"
        :style="{ background: a.bg, borderLeftColor: a.color }"
      >
        <div class="sd-alert__icon" :style="{ background: '#fff', color: a.color }">
          <van-icon :name="a.icon" size="20" />
        </div>
        <div class="sd-alert__body">
          <div class="sd-alert__row">
            <span class="sd-alert__label">{{ a.label }}</span>
            <span class="sd-alert__tag" :style="{ background: a.tagColor }">{{ a.tag }}</span>
          </div>
          <div class="sd-alert__value" :style="{ color: a.color }">{{ a.value }}</div>
          <p class="sd-alert__desc">{{ a.desc }}</p>
        </div>
      </div>
    </div>

    <!-- 帧交互热力图 -->
    <div class="sd-card">
      <div class="sd-card__head">
        <strong>课件帧交互热力分布</strong>
        <span>X 轴：课件页 | Y 轴：提问频次</span>
      </div>
      <div class="sd-chart">
        <div v-for="bar in data.barData" :key="bar.page" class="sd-bar-col">
          <span class="sd-bar-val" :class="{ danger: bar.danger }">{{ bar.val }}</span>
          <div class="sd-bar-track">
            <div class="sd-bar-fill" :class="{ danger: bar.danger }"
              :style="{ height: `${Math.round(bar.val / maxBar * 100)}%` }" />
          </div>
          <span class="sd-bar-label" :class="{ danger: bar.danger }">{{ bar.page }}</span>
        </div>
      </div>
    </div>

    <!-- 错因聚类 -->
    <div class="sd-card">
      <div class="sd-card__head">
        <strong>NLP 错因聚类分析</strong>
        <span>无监督语义聚类</span>
      </div>
      <div class="sd-clusters">
        <div v-for="c in data.clusters" :key="c.label" class="sd-cluster">
          <div class="sd-cluster__bar-wrap">
            <div class="sd-cluster__label-row">
              <span class="sd-cluster__name">{{ c.label }}</span>
              <strong class="sd-cluster__pct" :style="{ color: c.color }">{{ c.pct }}%</strong>
            </div>
            <div class="sd-cluster__track">
              <div class="sd-cluster__fill" :style="{ width: c.pct + '%', background: c.color }" />
            </div>
            <p class="sd-cluster__desc">{{ c.desc }} · {{ c.count }} 人</p>
          </div>
        </div>
      </div>
    </div>

    <div style="height:24px" />
  </div>
</template>

<style scoped>
.sd-page {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, sans-serif;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

/* 顶栏 */
.sd-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
  position: sticky;
  top: 0;
  z-index: 10;
}

.sd-back {
  width: 36px;
  height: 36px;
  border: none;
  background: #f5f7fa;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1a2035;
  cursor: pointer;
}

.sd-topbar-title {
  font-size: 17px;
  font-weight: 800;
  color: #1a2035;
}

/* 筛选 */
.sd-filter {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  overflow-x: auto;
  scrollbar-width: none;
}

.sd-filter::-webkit-scrollbar {
  display: none;
}

.sd-chip {
  flex-shrink: 0;
  border: none;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7a90;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.sd-chip.active {
  color: #fff;
  background: #7c3aed;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
}

/* 横幅 */
.sd-banner {
  margin: 0 14px 14px;
  background: linear-gradient(135deg, #7c3aed 0%, #9f67ff 55%, #b794f4 100%);
  border-radius: 20px;
  padding: 20px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  position: relative;
  box-shadow: 0 6px 20px rgba(124, 58, 237, 0.28);
}

.sd-banner__eyebrow {
  margin: 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 0.12em;
}

.sd-banner__title {
  margin: 4px 0 4px;
  font-size: 20px;
  font-weight: 800;
  color: #fff;
}

.sd-banner__sub {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.sd-banner__deco {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.deco-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.14);
}

.deco-ring--1 {
  width: 64px;
  height: 64px;
}

.deco-ring--2 {
  width: 90px;
  height: 90px;
}

/* KPI 网格 */
.sd-kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 0 14px 10px;
}

.sd-kpi-card {
  min-width: 0;
  background: #fff;
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  display: flex;
  gap: 10px;
  align-items: flex-start;
  overflow: hidden;
}

/* 行动项列表 */
.sd-alert-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 14px 14px;
}

.sd-alert-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 14px;
  border-radius: 16px;
  border-left: 4px solid;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  min-width: 0;
  overflow: hidden;
}

.sd-alert__icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.sd-alert__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sd-alert__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sd-alert__label {
  font-size: 12px;
  color: #6b7a90;
  font-weight: 600;
}

.sd-alert__tag {
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  padding: 2px 8px;
  border-radius: 8px;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.sd-alert__value {
  font-size: 20px;
  font-weight: 800;
  line-height: 1.2;
}

.sd-alert__desc {
  margin: 0;
  font-size: 11.5px;
  color: #6b7a90;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.sd-kpi-card__icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sd-kpi-card__body {
  flex: 1;
  min-width: 0;
}

.sd-kpi-label {
  font-size: 11px;
  color: #9aa3b2;
  font-weight: 600;
}

.sd-kpi-val {
  font-size: 20px;
  font-weight: 800;
  line-height: 1.2;
  margin: 2px 0;
}

.sd-kpi-val em {
  font-style: normal;
  font-size: 12px;
  color: #9aa3b2;
  margin-left: 2px;
}

.sd-kpi-trend {
  margin: 0;
  font-size: 11px;
  color: #9aa3b2;
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 卡片 */
.sd-card {
  margin: 0 14px 12px;
  background: #fff;
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.sd-card__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}

.sd-card__head strong {
  font-size: 14px;
  font-weight: 800;
  color: #1a2035;
}

.sd-card__head span {
  font-size: 11px;
  color: #9aa3b2;
}

/* 柱状图 */
.sd-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 110px;
}

.sd-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  height: 100%;
}

.sd-bar-val {
  font-size: 9px;
  color: #9aa3b2;
  line-height: 1;
}

.sd-bar-val.danger {
  color: #f53f3f;
  font-weight: 700;
}

.sd-bar-track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
}

.sd-bar-fill {
  width: 100%;
  border-radius: 4px 4px 2px 2px;
  background: #93c5fd;
  transition: height 0.3s;
}

.sd-bar-fill.danger {
  background: #f87171;
}

.sd-bar-label {
  font-size: 8px;
  color: #b0b9c8;
}

.sd-bar-label.danger {
  color: #f53f3f;
  font-weight: 700;
}

/* 错因聚类 */
.sd-clusters {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sd-cluster__label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.sd-cluster__name {
  font-size: 13px;
  font-weight: 700;
  color: #1a2035;
}

.sd-cluster__pct {
  font-size: 14px;
  font-weight: 800;
}

.sd-cluster__track {
  height: 7px;
  border-radius: 999px;
  background: #f0f2f5;
  overflow: hidden;
  margin-bottom: 5px;
}

.sd-cluster__fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s;
}

.sd-cluster__desc {
  margin: 0;
  font-size: 11px;
  color: #9aa3b2;
}
</style>
