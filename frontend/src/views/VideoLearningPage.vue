<template>
  <div class="video-page">
    <div class="breadcrumb">{{ breadcrumb }}</div>

    <div class="title-row">
      <div>
        <h1>{{ resource.title }}</h1>
      </div>
      <div class="title-actions">
        <el-button @click="$router.push('/resources/' + $route.params.id + '/read')"><el-icon><EditPen /></el-icon> 笔记</el-button>
        <el-button @click="handleFavorite"><el-icon><Star /></el-icon> 收藏</el-button>
        <el-button @click="handleDownload"><el-icon><Download /></el-icon> 下载资料</el-button>
      </div>
    </div>

    <section class="top-grid">
      <article class="video-panel">
        <div class="video-stage">
          <div class="video-overlay">
            <h2>{{ videoInfo.chapter }}</h2>
            <ul>
              <li v-for="item in videoInfo.points" :key="item">{{ item }}</li>
            </ul>
          </div>
        </div>
        <div class="video-controls">
          <div class="control-left">
            <el-icon><VideoPause /></el-icon>
            <span class="time">{{ videoInfo.currentTime }}</span>
            <span class="time">{{ videoInfo.totalTime }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${videoInfo.progress}%` }"></div>
          </div>
          <div class="control-right">
            <span>{{ videoInfo.speed }}</span>
            <span>超清</span>
          </div>
        </div>
      </article>

      <article class="catalog-card">
        <div class="section-head">
          <h2>课程目录</h2>
          <span class="muted">{{ catalog.length }}章</span>
        </div>

        <div class="catalog-list">
          <div v-for="section in catalog" :key="section.title" class="catalog-section">
            <div class="catalog-title">
              <span>{{ section.title }}</span>
              <span class="muted">{{ section.status }}</span>
            </div>
            <div
              v-for="lesson in section.lessons"
              :key="lesson.title"
              :class="['catalog-item', { active: lesson.active }]"
            >
              <span class="catalog-dot"></span>
              <span class="catalog-name">{{ lesson.title }}</span>
              <span class="catalog-time">{{ lesson.duration }}</span>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="bottom-grid">
      <article class="surface-card">
        <div class="section-head">
          <h2>学习进度</h2>
        </div>
        <div class="progress-summary">
          <div class="ring-wrap">
            <div class="ring" :style="{ '--progress': `${studyProgress.percent}%` }">
              <div class="ring-inner">
                <strong>{{ studyProgress.percent }}%</strong>
                <span>本章进度</span>
              </div>
            </div>
          </div>
          <div class="progress-list">
            <div class="progress-row" v-for="item in studyProgress.items" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </div>
        <button type="button" class="more-link" @click="goResources">查看学习报告</button>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>学习统计</h2>
        </div>
        <div ref="trendRef" class="trend-chart"></div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>学习工具</h2>
        </div>
        <div class="tool-list">
          <button v-for="tool in tools" :key="tool.title" type="button" class="tool-item" @click="tool.action">
            <span class="tool-icon" :style="{ background: tool.bg, color: tool.color }">
              <el-icon><component :is="tool.icon" /></el-icon>
            </span>
            <span class="tool-copy">
              <strong>{{ tool.title }}</strong>
              <small>{{ tool.desc }}</small>
            </span>
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  ChatDotSquare,
  Collection,
  Download,
  EditPen,
  Files,
  Notebook,
  Star,
  VideoPause,
} from '@element-plus/icons-vue'
import { getResourceDetail } from '@/api/resource'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const trendRef = ref(null)
const resource = ref({
  title: '3.1 变量的基本概念',
  direction: 'Python基础入门到实践',
})
let trendChart = null

const breadcrumb = computed(() => `课程学习 > ${resource.value.direction || 'Python基础入门到实践'} > ${resource.value.title}`)

const videoInfo = {
  chapter: '3.1 变量的基本概念',
  points: ['什么是变量', '变量的命名规则', '变量的赋值与使用', '变量在程序中的作用'],
  currentTime: '06:45',
  totalTime: '18:32',
  progress: 36,
  speed: '1.25x',
}

const catalog = [
  { title: '第1章 Python简介与环境搭建', status: '已学完', lessons: [{ title: '第1节 环境搭建', duration: '12:20' }] },
  { title: '第2章 Python基础语法', status: '已学完', lessons: [{ title: '第2节 Python基础语法', duration: '14:10' }] },
  {
    title: '第3章 变量与数据类型',
    status: '学习中',
    lessons: [
      { title: '3.1 变量的基本概念', duration: '18:32', active: true },
      { title: '3.2 数据类型概述', duration: '15:45' },
      { title: '3.3 字符串类型', duration: '20:11' },
      { title: '3.4 数值类型', duration: '22:08' },
    ],
  },
]

const studyProgress = {
  percent: 65,
  items: [
    { label: '已学章节', value: '2 / 4' },
    { label: '视频时长', value: '34 / 76 分钟' },
    { label: '完成练习', value: '8 / 15 题' },
  ],
}

const tools = [
  { title: '课程笔记', desc: '记录重点知识与心得', icon: Notebook, bg: 'rgba(16,185,129,0.12)', color: '#10b981', action: () => {} },
  { title: '课程资料', desc: '下载课程配套讲义', icon: Files, bg: 'rgba(59,130,246,0.12)', color: '#2b6cff', action: () => {} },
  { title: '随堂练习', desc: '巩固知识点与练习题', icon: Collection, bg: 'rgba(139,92,246,0.12)', color: '#8b5cf6', action: () => router.push(`/resources/${route.params.id}/quiz`) },
  { title: '讨论区', desc: '与同学交流学习心得', icon: ChatDotSquare, bg: 'rgba(245,158,11,0.14)', color: '#f59e0b', action: () => {} },
]

function renderTrend() {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  trendChart.setOption({
    grid: { top: 14, right: 10, bottom: 20, left: 24 },
    xAxis: {
      type: 'category',
      data: ['05-12', '05-13', '05-14', '05-15', '05-16', '05-17', '05-18'],
      axisLabel: { color: '#98a2b3', fontSize: 10 },
      axisLine: { lineStyle: { color: '#edf2f8' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#98a2b3', fontSize: 10 },
      splitLine: { lineStyle: { color: '#edf2f8' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: [18, 26, 34, 29, 31, 41, 44],
        lineStyle: { color: '#2b6cff', width: 2 },
        itemStyle: { color: '#2b6cff' },
        areaStyle: { color: 'rgba(43,108,255,0.08)' },
      },
    ],
  })
}

function goResources() {
  router.push('/profile')
}

function handleResize() {
  trendChart?.resize()
}

onMounted(async () => {
  try {
    resource.value = await getResourceDetail(route.params.id)
  } catch {
    resource.value = {
      title: '3.1 变量的基本概念',
      direction: 'Python基础入门到实践',
    }
  }
  nextTick(() => {
    renderTrend()
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  trendChart = null
})

function handleFavorite() {
  const favs = JSON.parse(localStorage.getItem('favorites') || '[]')
  const id = Number(route.params.id)
  if (!favs.includes(id)) { favs.push(id); localStorage.setItem('favorites', JSON.stringify(favs)); ElMessage.success('已收藏') }
  else { ElMessage.info('已在收藏中') }
}
function handleDownload() { ElMessage.success('下载已开始') }
</script>

<style scoped>
.video-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.breadcrumb {
  color: #94a3b8;
  font-size: 0.78rem;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.title-row h1 {
  color: #1e293b;
  font-size: 1.8rem;
}

.title-actions {
  display: flex;
  gap: 10px;
}

.top-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) 320px;
  gap: 18px;
}

.video-panel,
.catalog-card,
.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.video-panel {
  overflow: hidden;
}

.video-stage {
  min-height: 420px;
  background: radial-gradient(circle at 30% 30%, #183d8c 0%, #09204b 45%, #07162f 100%);
  position: relative;
}

.video-overlay {
  position: absolute;
  inset: 40px;
  color: #fff;
}

.video-overlay h2 {
  font-size: 2rem;
}

.video-overlay ul {
  margin-top: 20px;
  padding-left: 18px;
  line-height: 2;
}

.video-controls {
  padding: 14px 18px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: center;
}

.control-left,
.control-right {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #475569;
  font-size: 0.78rem;
}

.progress-bar {
  height: 6px;
  border-radius: 999px;
  background: #dbe5f7;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2b6cff, #76a2ff);
}

.catalog-card,
.surface-card {
  padding: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.section-head h2 {
  color: #1e293b;
  font-size: 1rem;
}

.muted {
  color: #94a3b8;
  font-size: 0.74rem;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.catalog-section {
  padding-bottom: 12px;
  border-bottom: 1px solid #edf2f8;
}

.catalog-section:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.catalog-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #475569;
  font-size: 0.8rem;
}

.catalog-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border-radius: 12px;
  color: #64748b;
  font-size: 0.78rem;
}

.catalog-item.active {
  background: #edf3ff;
  color: #2b6cff;
}

.catalog-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
}

.catalog-name {
  min-width: 0;
}

.catalog-time {
  font-size: 0.72rem;
}

.bottom-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 300px;
  gap: 18px;
}

.progress-summary {
  display: flex;
  align-items: center;
  gap: 18px;
}

.ring {
  --progress: 65%;
  width: 112px;
  height: 112px;
  border-radius: 50%;
  background: conic-gradient(#2b6cff 0 var(--progress), #e5edfb var(--progress) 100%);
  display: grid;
  place-items: center;
}

.ring-inner {
  width: 82px;
  height: 82px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-inner strong {
  color: #2b6cff;
  font-size: 1.3rem;
}

.ring-inner span {
  color: #94a3b8;
  font-size: 0.68rem;
}

.progress-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.progress-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #64748b;
  font-size: 0.8rem;
}

.progress-row strong {
  color: #1e293b;
}

.more-link {
  margin-top: 16px;
  border: 0;
  background: transparent;
  color: #2b6cff;
  font: inherit;
  cursor: pointer;
}

.trend-chart {
  width: 100%;
  height: 180px;
}

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-item {
  border: 1px solid #edf2f8;
  border-radius: 14px;
  background: #fbfcff;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font: inherit;
}

.tool-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.tool-copy {
  display: flex;
  flex-direction: column;
  text-align: left;
}

.tool-copy strong {
  color: #1e293b;
  font-size: 0.84rem;
}

.tool-copy small {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 0.72rem;
}

@media (max-width: 1260px) {
  .top-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .title-row,
  .title-actions,
  .progress-summary {
    flex-direction: column;
    align-items: flex-start;
  }

  .video-controls {
    grid-template-columns: 1fr;
  }
}
</style>
