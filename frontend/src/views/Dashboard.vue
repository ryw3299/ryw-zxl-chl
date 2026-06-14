<template>
  <div class="dashboard-page">
    <section class="top-grid">
      <article class="hero-card">
        <div class="hero-copy">
          <h1>Hi，{{ userStore.username || '同学' }}</h1>
          <p class="hero-date">今天是 {{ formattedDate }}</p>
          <p class="hero-desc">坚持学习的每一天，都是向目标靠近的一小步！</p>
        </div>

        <div class="hero-note-card">
          <span class="hero-note-title">今日一句</span>
          <span class="hero-note-text">学如逆水行舟，不进则退。</span>
        </div>

        <div class="hero-robot" aria-hidden="true">
          <div class="robot-halo"></div>
          <div class="robot-head">
            <span></span>
            <span></span>
          </div>
          <div class="robot-body"></div>
        </div>
      </article>

      <article class="surface-card calendar-card">
        <div class="section-head">
          <h2>学习日历</h2>
          <div class="calendar-switcher">
            <button type="button" @click="changeMonth(-1)">
              <el-icon><ArrowLeft /></el-icon>
            </button>
            <span>{{ calendarLabel }}</span>
            <button type="button" @click="changeMonth(1)">
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </div>

        <div class="calendar-grid">
          <span v-for="weekday in weekdays" :key="weekday" class="calendar-weekday">{{ weekday }}</span>
          <button
            v-for="(day, index) in calendarCells"
            :key="`${index}-${day.dateKey}`"
            type="button"
            class="calendar-day"
            :class="{
              muted: !day.inCurrentMonth,
              today: day.isToday,
              planned: day.status === 'planned',
              done: day.status === 'done',
            }"
            @click="goLearningPath"
          >
            {{ day.label }}
          </button>
        </div>

        <div class="calendar-legend">
          <span><i class="legend-dot planned"></i>有学习计划</span>
          <span><i class="legend-dot done"></i>已完成</span>
          <span><i class="legend-dot default"></i>未完成</span>
        </div>
      </article>
    </section>

    <section class="surface-card quick-card">
      <div class="section-head">
        <h2>快捷入口</h2>
      </div>

      <div class="quick-grid">
        <button
          v-for="action in quickActions"
          :key="action.label"
          type="button"
          class="quick-item"
          @click="action.action"
        >
          <span class="quick-icon" :style="{ background: action.bg, color: action.color }">
            <el-icon><component :is="action.icon" /></el-icon>
          </span>
          <span class="quick-label">{{ action.label }}</span>
        </button>
      </div>
    </section>

    <section class="metrics-grid">
      <article class="surface-card tasks-card">
        <div class="section-head">
          <h2>今日任务</h2>
          <button type="button" class="text-link" @click="goLearningPath">更多</button>
        </div>

        <div class="task-list">
          <div v-for="task in tasks" :key="task.id" class="task-item">
            <div :class="['task-check', { done: task.is_done }]" @click="toggleTask(task.id)" style="cursor:pointer">
              <el-icon v-if="task.is_done"><Check /></el-icon>
            </div>
            <div class="task-info">
              <div class="task-title-row">
                <span class="task-title" :class="{ done: task.is_done }">{{ task.title }}</span>
                <el-tag :type="task.is_done ? 'success' : 'primary'" effect="plain" size="small">
                  {{ task.is_done ? '已完成' : '进行中' }}
                </el-tag>
              </div>
              <div class="task-meta">
                <span>预计 {{ task.time }}</span>
                <span>{{ task.progress }}</span>
              </div>
            </div>
          </div>
        </div>

        <button type="button" class="add-task-button" @click="goLearningPath">
          <el-icon><Plus /></el-icon>
          <span>添加任务</span>
        </button>
      </article>

      <article class="surface-card progress-card">
        <div class="section-head">
          <h2>学习进度</h2>
        </div>

        <div class="progress-summary">
          <div class="progress-main">
            <div class="progress-caption">本周学习时长</div>
            <div class="progress-hours">8.6 <span>小时</span></div>
            <div class="progress-compare">较上周 +12%</div>
          </div>

          <div class="progress-ring" :style="{ '--progress': `${studyHours > 0 ? Math.min(studyHours / studyTargetHours * 100, 100) : 0}%` }">
            <div class="progress-ring-inner">
              <strong>{{ studyHours > 0 ? Math.round(studyHours / studyTargetHours * 100) : 0 }}%</strong>
              <span>学习达成度</span>
            </div>
          </div>
        </div>

        <div class="progress-breakdown">
          <div v-for="item in studyBreakdown" :key="item.label" class="progress-item">
            <span class="progress-item-dot" :style="{ background: item.color }"></span>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>

        <div class="target-block">
          <div class="target-head">
            <span>本周目标</span>
            <strong>{{ studyTargetHours }} 小时</strong>
          </div>
          <div class="target-bar">
            <div class="target-fill" :style="{ width: `${studyHours > 0 ? Math.min(studyHours / studyTargetHours * 100, 100) : 0}%` }"></div>
          </div>
        </div>
      </article>

      <article class="surface-card radar-card">
        <div class="section-head">
          <h2>知识掌握雷达图</h2>
        </div>
        <div ref="radarRef" class="radar-chart"></div>
      </article>

      <article class="surface-card weak-card">
        <div class="section-head">
          <h2>薄弱知识点 TOP5</h2>
          <button type="button" class="text-link" @click="goResources">更多</button>
        </div>

        <div class="weak-list">
          <div v-for="(item, index) in weakPoints" :key="item.name" class="weak-item">
            <span class="weak-rank">{{ index + 1 }}</span>
            <div class="weak-main">
              <div class="weak-name">{{ item.name }}</div>
              <div class="weak-desc">{{ item.desc }}</div>
            </div>
            <span class="weak-score">{{ item.score }}%</span>
          </div>
        </div>

        <button type="button" class="weak-action" @click="goResources">去强化学习</button>
      </article>
    </section>

    <section class="surface-card notice-card">
      <div class="section-head">
        <h2>最新公告</h2>
        <button type="button" class="text-link" @click="goResources">更多公告</button>
      </div>

      <div class="notice-list">
        <div v-for="notice in announcements" :key="notice.title" class="notice-item">
          <div class="notice-main">
            <el-tag :type="notice.tag" effect="plain" size="small">{{ notice.type }}</el-tag>
            <div class="notice-copy">
              <div class="notice-title">{{ notice.title }}</div>
              <div class="notice-desc">{{ notice.description }}</div>
            </div>
          </div>
          <span class="notice-date">{{ notice.date }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'
import * as echarts from 'echarts'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Collection,
  Compass,
  DataAnalysis,
  EditPen,
  Files,
  FolderOpened,
  Management,
  Plus,
  Reading,
  VideoCamera,
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const radarRef = ref(null)

const weekdays = ['一', '二', '三', '四', '五', '六', '日']
const today = new Date()
const calendarYear = ref(today.getFullYear())
const calendarMonth = ref(today.getMonth() + 1)
let radarChart = null

const quickActions = [
  { label: '课程学习', icon: VideoCamera, bg: 'rgba(43, 108, 255, 0.10)', color: '#2b6cff', action: () => router.push('/resources?resource_type=course') },
  { label: '智能题库', icon: EditPen, bg: 'rgba(16, 185, 129, 0.12)', color: '#10b981', action: () => router.push('/resources?resource_type=quiz') },
  { label: '学习计划', icon: Compass, bg: 'rgba(139, 92, 246, 0.12)', color: '#8b5cf6', action: () => router.push('/learning-path') },
  { label: '错题本', icon: Files, bg: 'rgba(245, 158, 11, 0.14)', color: '#f59e0b', action: () => router.push('/resources?resource_type=quiz') },
  { label: '学习报告', icon: DataAnalysis, bg: 'rgba(59, 130, 246, 0.10)', color: '#3b82f6', action: () => router.push('/profile') },
  { label: '资源中心', icon: FolderOpened, bg: 'rgba(16, 185, 129, 0.10)', color: '#14b8a6', action: () => router.push('/resources') },
]

const tasks = ref([])
const studyBreakdown = ref([
  { label: '视频学习', value: '0 小时', color: '#2b6cff' },
  { label: '练习测验', value: '0 小时', color: '#f59e0b' },
  { label: '资料阅读', value: '0 小时', color: '#10b981' },
])
const studyHours = ref(0)
const studyTargetHours = ref(12)
const weakPoints = ref([])
const announcements = ref([])
const studyRecords = ref([])
const streakDays = ref(0)
const totalHours = ref(0)

async function loadDashboardData() {
  try {
    const [taskRes, statsRes, recordRes, announceRes, masteryRes] = await Promise.allSettled([
      import('@/api/task').then(m => m.getTasks()),
      import('@/api/studyRecord').then(m => m.getStudyStats()),
      import('@/api/studyRecord').then(m => m.getStudyRecords()),
      import('@/api/announcement').then(m => m.getAnnouncements()),
      import('@/api/event').then(m => m.getMastery()),
    ])

    if (taskRes.status === 'fulfilled') tasks.value = taskRes.value.map(t => ({ ...t, time: `${t.duration_minutes || 30}分钟` }))

    if (statsRes.status === 'fulfilled') {
      studyHours.value = statsRes.value.total_hours || 0
      streakDays.value = statsRes.value.streak_days || 0
      totalHours.value = statsRes.value.total_hours || 0
      // Generate breakdown from records
      if (recordRes.status === 'fulfilled') {
        const records = recordRes.value || []
        const video = records.filter(r => r.record_type === 'video').reduce((s, r) => s + (r.duration_minutes || 0), 0)
        const quiz = records.filter(r => r.record_type === 'quiz').reduce((s, r) => s + (r.duration_minutes || 0), 0)
        const reading = records.filter(r => r.record_type === 'reading').reduce((s, r) => s + (r.duration_minutes || 0), 0)
        studyBreakdown.value = [
          { label: '视频学习', value: `${(video/60).toFixed(1)} 小时`, color: '#2b6cff' },
          { label: '练习测验', value: `${(quiz/60).toFixed(1)} 小时`, color: '#f59e0b' },
          { label: '资料阅读', value: `${(reading/60).toFixed(1)} 小时`, color: '#10b981' },
        ]
      }
    }
    if (announceRes.status === 'fulfilled') announcements.value = announceRes.value || []
    if (masteryRes.status === 'fulfilled') {
      weakPoints.value = (masteryRes.value || [])
        .sort((a, b) => a.mastery_score - b.mastery_score)
        .slice(0, 5)
        .map(m => ({ name: m.knowledge_point, desc: `掌握度 ${m.mastery_score}%`, score: m.mastery_score }))
    }
    if (recordRes.status === 'fulfilled') studyRecords.value = (recordRes.value || []).slice(0, 4)
  } catch {}
}

function toggleTask(id) {
  import('@/api/task').then(m => m.toggleTask(id))
  const t = tasks.value.find(t => t.id === id)
  if (t) t.is_done = !t.is_done
}

const planDays = new Set([6, 12, 19, 22, 26])
const doneDays = new Set([5, 7, 14, 21])

const formattedDate = computed(() => {
  const weekdaysMap = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  return `${today.getFullYear()}年${today.getMonth() + 1}月${today.getDate()}日 ${weekdaysMap[today.getDay()]}`
})

const calendarLabel = computed(() => `${calendarYear.value}年${calendarMonth.value}月`)

const calendarCells = computed(() => {
  const firstDay = new Date(calendarYear.value, calendarMonth.value - 1, 1)
  const lastDate = new Date(calendarYear.value, calendarMonth.value, 0)
  const leading = (firstDay.getDay() + 6) % 7
  const total = lastDate.getDate()
  const cells = []

  const prevLastDate = new Date(calendarYear.value, calendarMonth.value - 1, 0).getDate()
  for (let i = leading - 1; i >= 0; i -= 1) {
    const day = prevLastDate - i
    cells.push({
      label: day,
      inCurrentMonth: false,
      isToday: false,
      status: 'default',
      dateKey: `prev-${day}`,
    })
  }

  for (let day = 1; day <= total; day += 1) {
    cells.push({
      label: day,
      inCurrentMonth: true,
      isToday:
        calendarYear.value === today.getFullYear() &&
        calendarMonth.value === today.getMonth() + 1 &&
        day === today.getDate(),
      status: doneDays.has(day) ? 'done' : planDays.has(day) ? 'planned' : 'default',
      dateKey: `current-${day}`,
    })
  }

  const trailing = cells.length <= 35 ? 35 - cells.length : 42 - cells.length
  for (let day = 1; day <= trailing; day += 1) {
    cells.push({
      label: day,
      inCurrentMonth: false,
      isToday: false,
      status: 'default',
      dateKey: `next-${day}`,
    })
  }

  return cells
})

function changeMonth(step) {
  const next = new Date(calendarYear.value, calendarMonth.value - 1 + step, 1)
  calendarYear.value = next.getFullYear()
  calendarMonth.value = next.getMonth() + 1
}

function goLearningPath() {
  router.push('/learning-path')
}

function goResources() {
  router.push('/resources')
}

function renderRadar() {
  if (!radarRef.value) return

  if (!radarChart) {
    radarChart = echarts.init(radarRef.value)
  }

  radarChart.setOption({
    radar: {
      center: ['50%', '52%'],
      radius: '66%',
      splitNumber: 4,
      axisName: {
        color: '#64748b',
        fontSize: 10,
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.25)',
        },
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(148, 163, 184, 0.18)',
        },
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(43,108,255,0.02)', 'rgba(43,108,255,0.04)'],
        },
      },
      indicator: [
        { name: 'Python基础', max: 100 },
        { name: '数据结构', max: 100 },
        { name: '算法设计', max: 100 },
        { name: '机器学习', max: 100 },
        { name: '数据库', max: 100 },
        { name: '数据分析', max: 100 },
      ],
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 5,
        data: [
          {
            value: [85, 72, 68, 60, 75, 80],
            areaStyle: {
              color: 'rgba(43, 108, 255, 0.22)',
            },
            lineStyle: {
              color: '#2b6cff',
              width: 2,
            },
            itemStyle: {
              color: '#2b6cff',
            },
          },
        ],
      },
    ],
  })
}

function handleResize() {
  radarChart?.resize()
}

onMounted(async () => {
  await loadDashboardData()
  nextTick(() => {
    renderRadar()
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
  radarChart = null
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.top-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 1fr);
  gap: 18px;
}

.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
  padding: 18px;
}

.hero-card {
  position: relative;
  min-height: 168px;
  border: 1px solid #dbe6fb;
  border-radius: 18px;
  background: linear-gradient(135deg, #edf3ff 0%, #eef5ff 55%, #f7faff 100%);
  padding: 24px 26px;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 180px;
  align-items: center;
  gap: 18px;
}

.hero-copy h1 {
  font-size: 2rem;
  line-height: 1.1;
  color: #2b6cff;
}

.hero-date {
  margin-top: 18px;
  font-size: 0.92rem;
  color: #4f5f79;
}

.hero-desc {
  margin-top: 8px;
  max-width: 320px;
  line-height: 1.8;
  color: #6d7b92;
  font-size: 0.9rem;
}

.hero-note-card {
  width: 132px;
  padding: 14px;
  border: 1px solid rgba(207, 220, 245, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(6px);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hero-note-title {
  color: #7a8cb3;
  font-size: 0.76rem;
}

.hero-note-text {
  color: #42526b;
  font-size: 0.88rem;
  line-height: 1.7;
}

.hero-robot {
  position: relative;
  width: 160px;
  height: 150px;
}

.robot-halo {
  position: absolute;
  inset: 4px 10px 8px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.75) 0, rgba(223,235,255,0.95) 65%, rgba(207,223,255,0.5) 100%);
}

.robot-head,
.robot-body {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  border: 1px solid rgba(186, 205, 242, 0.92);
  background: linear-gradient(180deg, #ffffff, #eef4ff);
  box-shadow: 0 16px 32px rgba(82, 118, 195, 0.14);
}

.robot-head {
  top: 16px;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
}

.robot-head span {
  width: 14px;
  height: 22px;
  border-radius: 999px;
  background: radial-gradient(circle at 50% 50%, #77deff 0, #77deff 30%, #275bff 80%, #275bff 100%);
  box-shadow: 0 0 14px rgba(72, 195, 255, 0.45);
}

.robot-body {
  top: 108px;
  width: 106px;
  height: 34px;
  border-radius: 16px;
}

.calendar-card {
  min-height: 168px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h2 {
  font-size: 1rem;
  color: #1e293b;
}

.calendar-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #4f5f79;
  font-size: 0.86rem;
}

.calendar-switcher button {
  width: 24px;
  height: 24px;
  border: 1px solid #e1e8f2;
  border-radius: 50%;
  background: #fff;
  color: #6b7b94;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px 6px;
}

.calendar-weekday {
  text-align: center;
  font-size: 0.72rem;
  color: #98a2b3;
}

.calendar-day {
  width: 30px;
  height: 30px;
  margin: 0 auto;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #4f5f79;
  font: inherit;
  cursor: pointer;
  position: relative;
}

.calendar-day.muted {
  color: #c0cada;
}

.calendar-day.today {
  background: #2b6cff;
  color: #fff;
  font-weight: 600;
}

.calendar-day.planned::after,
.calendar-day.done::after {
  content: '';
  position: absolute;
  bottom: 3px;
  left: 50%;
  transform: translateX(-50%);
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.calendar-day.planned::after {
  background: #2b6cff;
}

.calendar-day.done::after {
  background: #22c55e;
}

.calendar-day.today.planned::after,
.calendar-day.today.done::after {
  background: #fff;
}

.calendar-legend {
  display: flex;
  gap: 14px;
  margin-top: 14px;
  font-size: 0.74rem;
  color: #7b8798;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 5px;
}

.legend-dot.planned {
  background: #2b6cff;
}

.legend-dot.done {
  background: #22c55e;
}

.legend-dot.default {
  background: #cbd5e1;
}

.quick-card {
  padding-bottom: 12px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.quick-item {
  border: 1px solid #edf2f8;
  border-radius: 14px;
  background: #fff;
  padding: 14px 10px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font: inherit;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.quick-item:hover {
  border-color: #d4e0f6;
  box-shadow: 0 10px 22px rgba(45, 68, 110, 0.05);
}

.quick-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.quick-label {
  font-size: 0.82rem;
  color: #4f5f79;
}

.metrics-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.tasks-card,
.progress-card,
.radar-card,
.weak-card {
  min-height: 312px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 12px;
}

.task-check {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1.5px solid #d5deeb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: transparent;
}

.task-check.done {
  border-color: #22c55e;
  background: #22c55e;
  color: #fff;
}

.task-info {
  min-width: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #edf2f8;
}

.task-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.task-title {
  color: #27364f;
  font-size: 0.87rem;
}

.task-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.74rem;
  color: #8b98ab;
}

.add-task-button {
  margin-top: 14px;
  width: 100%;
  height: 38px;
  border: 1px dashed #cdd9ee;
  border-radius: 12px;
  background: #f8fbff;
  color: #2b6cff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font: inherit;
  cursor: pointer;
}

.progress-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.progress-caption,
.progress-compare {
  font-size: 0.78rem;
  color: #8b98ab;
}

.progress-hours {
  margin: 8px 0 4px;
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
}

.progress-hours span {
  font-size: 0.92rem;
  font-weight: 500;
  color: #64748b;
}

.progress-ring {
  --progress: 68%;
  width: 112px;
  height: 112px;
  border-radius: 50%;
  background: conic-gradient(#2b6cff 0 var(--progress), #e5edfb var(--progress) 100%);
  display: grid;
  place-items: center;
  flex: none;
}

.progress-ring-inner {
  width: 82px;
  height: 82px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.progress-ring-inner strong {
  font-size: 1.3rem;
  color: #2b6cff;
}

.progress-ring-inner span {
  margin-top: 2px;
  font-size: 0.68rem;
  color: #8b98ab;
}

.progress-breakdown {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: #4f5f79;
}

.progress-item-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.progress-item strong {
  margin-left: auto;
  color: #27364f;
}

.target-block {
  margin-top: 16px;
}

.target-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.78rem;
  color: #64748b;
}

.target-head strong {
  color: #2b6cff;
}

.target-bar {
  height: 6px;
  border-radius: 999px;
  background: #e9eff8;
  overflow: hidden;
}

.target-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2b6cff, #6f96ff);
}

.radar-chart {
  width: 100%;
  height: 250px;
}

.weak-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.weak-item {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}

.weak-rank {
  color: #f59e0b;
  font-size: 0.78rem;
  font-weight: 600;
}

.weak-main {
  min-width: 0;
}

.weak-name {
  font-size: 0.84rem;
  color: #27364f;
}

.weak-desc {
  margin-top: 4px;
  font-size: 0.72rem;
  color: #94a3b8;
}

.weak-score {
  font-size: 0.76rem;
  color: #64748b;
}

.weak-action {
  width: 100%;
  margin-top: 16px;
  height: 38px;
  border: 1px solid #d7e3fb;
  border-radius: 12px;
  background: #f8fbff;
  color: #2b6cff;
  font: inherit;
  cursor: pointer;
}

.notice-list {
  display: flex;
  flex-direction: column;
}

.notice-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 0;
  border-bottom: 1px solid #edf2f8;
}

.notice-item:last-child {
  border-bottom: 0;
}

.notice-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.notice-copy {
  min-width: 0;
}

.notice-title {
  color: #27364f;
  font-size: 0.88rem;
}

.notice-desc {
  margin-top: 4px;
  color: #98a2b3;
  font-size: 0.74rem;
}

.notice-date,
.text-link {
  color: #7b8798;
  font-size: 0.76rem;
}

.text-link {
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.text-link:hover {
  color: #2b6cff;
}

@media (max-width: 1320px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .quick-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1080px) {
  .top-grid {
    grid-template-columns: 1fr;
  }

  .hero-card {
    grid-template-columns: 1fr;
  }

  .hero-note-card,
  .hero-robot {
    display: none;
  }
}

@media (max-width: 720px) {
  .metrics-grid,
  .quick-grid {
    grid-template-columns: 1fr;
  }

  .progress-summary,
  .notice-item,
  .notice-main {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
