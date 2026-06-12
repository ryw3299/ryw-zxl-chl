<script setup>
import { computed, ref } from 'vue'
import { useUserStore } from '@/store/userStore'
import goldMedalNo1 from '@/assets/leaderboard/no1-medal-transparent.png'

const userStore = useUserStore()

const boardTabs = [
  { key: 'overall', label: '总榜' },
  { key: 'weekly', label: '本周榜' },
  { key: 'interactive', label: '互动榜' },
  { key: 'growth', label: '课程进步榜' },
]

const courseOptions = [
  { value: 'all', label: '全部课程' },
  { value: '数据结构与算法', label: '数据结构与算法' },
  { value: '人工智能导论', label: '人工智能导论' },
  { value: '机器学习基础', label: '机器学习基础' },
  { value: 'Python 程序设计', label: 'Python 程序设计' },
]

const rankingEntries = [
  { id: 'u-1', name: '林知夏', courseName: '数据结构与算法', score: 98, progress: 96, interactions: 18, qaAccuracy: 97, rankDelta: 2, badge: '进步最快', avatar: '林' },
  { id: 'u-2', name: '陈屿', courseName: '人工智能导论', score: 94, progress: 91, interactions: 15, qaAccuracy: 95, rankDelta: 1, badge: '稳定输出', avatar: '陈' },
  { id: 'u-3', name: '宋嘉宁', courseName: '机器学习基础', score: 92, progress: 89, interactions: 17, qaAccuracy: 92, rankDelta: -1, badge: '互动积极', avatar: '宋' },
  { id: 'u-4', name: '周予安', courseName: 'Python 程序设计', score: 89, progress: 87, interactions: 12, qaAccuracy: 90, rankDelta: 3, badge: '答疑高效', avatar: '周' },
  { id: 'u-5', name: '沈星遥', courseName: '数据结构与算法', score: 86, progress: 83, interactions: 11, qaAccuracy: 88, rankDelta: 0, badge: '稳步提升', avatar: '沈' },
  { id: 'u-6', name: '顾言', courseName: '人工智能导论', score: 84, progress: 82, interactions: 10, qaAccuracy: 86, rankDelta: 1, badge: '课堂专注', avatar: '顾' },
  { id: 'u-7', name: '何清越', courseName: '机器学习基础', score: 82, progress: 79, interactions: 9, qaAccuracy: 85, rankDelta: -2, badge: '潜力选手', avatar: '何' },
  { id: 'u-8', name: '许澈', courseName: '数据结构与算法', score: 80, progress: 77, interactions: 8, qaAccuracy: 84, rankDelta: 2, badge: '状态回升', avatar: '许' },
  { id: 'u-9', name: '程知微', courseName: 'Python 程序设计', score: 78, progress: 76, interactions: 7, qaAccuracy: 82, rankDelta: 0, badge: '持续打卡', avatar: '程' },
  { id: 'u-10', name: '姜望舒', courseName: '人工智能导论', score: 76, progress: 73, interactions: 6, qaAccuracy: 80, rankDelta: -1, badge: '保持节奏', avatar: '姜' },
]

const currentUserName = computed(() => userStore.userInfo.userId || '我')
const isTeacher = computed(() => userStore.isTeacher)
const activeBoard = ref('overall')
const activeCourse = ref('all')

const boardIntroMap = {
  overall: {
    teacherTitle: '班级活跃总榜',
    teacherDesc: '综合学习活跃度、互动表现与任务完成度生成班级排行榜。',
    studentTitle: '课堂综合总榜',
    studentDesc: '综合学习进度、课堂互动和答疑表现形成你的课堂位置。',
  },
  weekly: {
    teacherTitle: '本周课堂热度榜',
    teacherDesc: '聚焦最近一周课堂表现，便于快速发现状态上升的学生。',
    studentTitle: '本周冲榜动态',
    studentDesc: '查看最近一周谁在持续上分，也看看自己离前一名还有多远。',
  },
  interactive: {
    teacherTitle: '互动表现榜',
    teacherDesc: '按提问、答疑参与和课堂响应次数统计互动活跃度。',
    studentTitle: '互动活跃榜',
    studentDesc: '更适合展示课堂参与度和表达积极性。',
  },
  growth: {
    teacherTitle: '课程进步榜',
    teacherDesc: '关注学习进步曲线，帮助你快速识别提升最快的学生。',
    studentTitle: '课程进步榜',
    studentDesc: '更强调成长幅度，而不是单纯看当前绝对分数。',
  },
}

const getBoardScore = (entry, boardKey) => {
  if (boardKey === 'weekly') return entry.score + entry.rankDelta * 2 + entry.interactions
  if (boardKey === 'interactive') return entry.interactions * 5 + entry.qaAccuracy * 0.3
  if (boardKey === 'growth') return entry.progress * 0.65 + Math.max(entry.rankDelta, 0) * 8 + entry.qaAccuracy * 0.15
  return entry.score
}

const rankedEntries = computed(() => {
  const filtered = rankingEntries.filter((entry) => activeCourse.value === 'all' || entry.courseName === activeCourse.value)
  return filtered
    .map((entry) => ({ ...entry, boardScore: Math.round(getBoardScore(entry, activeBoard.value) * 10) / 10 }))
    .sort((a, b) => b.boardScore - a.boardScore)
    .map((entry, index) => ({ ...entry, rank: index + 1 }))
})

const podiumEntries = computed(() => {
  const ranking = rankedEntries.value
  return [ranking[1], ranking[0], ranking[2]].filter(Boolean)
})

const heroContent = computed(() => {
  const boardIntro = boardIntroMap[activeBoard.value]
  if (isTeacher.value) {
    return {
      eyebrow: 'CLASS PERFORMANCE RANKING',
      title: boardIntro.teacherTitle,
      subtitle: boardIntro.teacherDesc,
      metrics: [
        { value: 'TOP 10', label: '当前榜单范围', sub: '课堂排名区间' },
        { value: '8', label: '与上一名差距', sub: '分' },
        { value: '3', label: '最近上升名次', sub: '名' },
        { value: '32', label: '班级人数', sub: '人' },
      ],
    }
  }

  return {
    eyebrow: 'LEARNING LEADERBOARD',
    title: boardIntro.studentTitle,
    subtitle: boardIntro.studentDesc,
    metrics: [
      { value: 'TOP 10', label: '当前榜单范围', sub: '课堂排名区间' },
      { value: '8', label: '与上一名差距', sub: '分' },
      { value: '3', label: '最近上升名次', sub: '名' },
      { value: '32', label: '班级人数', sub: '人' },
    ],
  }
})

const currentStudentEntry = computed(() => {
  const ranking = rankedEntries.value
  const matched = ranking.find((entry) => entry.name === currentUserName.value)
  if (matched) return matched
  return {
    ...(ranking[5] || ranking[ranking.length - 1] || rankingEntries[0]),
    name: currentUserName.value,
    avatar: String(currentUserName.value).slice(0, 1) || '我',
    rank: Math.min(6, ranking.length || 1),
    boardScore: 84,
    score: 84,
    progress: 81,
    interactions: 9,
    qaAccuracy: 87,
    rankDelta: 2,
    badge: '状态稳定',
  }
})

const previousStudentEntry = computed(() => {
  const myRank = currentStudentEntry.value.rank
  return rankedEntries.value.find((entry) => entry.rank === myRank - 1) || null
})

const studentGap = computed(() => {
  if (!previousStudentEntry.value) return 0
  return Math.max(0, Math.round((previousStudentEntry.value.boardScore - currentStudentEntry.value.boardScore) * 10) / 10)
})

const teacherInsightCards = computed(() => ([
  { title: '进步之星', value: '林知夏', desc: '本周上升 2 名，数据结构与算法完成度达到 96%' },
  { title: '互动最强', value: '宋嘉宁', desc: '课堂互动 17 次，追问与答疑参与度最高' },
  { title: '值得关注', value: '姜望舒', desc: '完成度与互动频次连续两周略有下降' },
]))

const formatDelta = (value) => {
  if (value > 0) return `↑ ${value}`
  if (value < 0) return `↓ ${Math.abs(value)}`
  return '—'
}

const deltaClass = (value) => {
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return 'flat'
}

const isCurrentStudent = (entry) => !isTeacher.value && entry.name === currentStudentEntry.value.name
</script>

<template>
  <div class="leaderboard-page">
    <div class="page-inner">
    <section class="hero-panel">
      <div class="hero-copy">
        <p class="hero-eyebrow">{{ heroContent.eyebrow }}</p>
        <h1 class="hero-title">{{ heroContent.title }}</h1>
        <p class="hero-subtitle">{{ heroContent.subtitle }}</p>
      </div>
      <div class="hero-metrics" aria-label="排行榜概览">
        <div v-for="metric in heroContent.metrics" :key="metric.label" class="hero-metric">
          <span class="hero-metric-icon" aria-hidden="true"></span>
          <span class="hero-metric-label">{{ metric.label }}</span>
          <span class="hero-metric-value">{{ metric.value }}</span>
          <span class="hero-metric-sub">{{ metric.sub }}</span>
        </div>
      </div>
    </section>

    <section class="toolbar">
      <div class="toolbar-left">
        <button v-for="tab in boardTabs" :key="tab.key" type="button" class="filter-pill"
          :class="{ active: activeBoard === tab.key }" @click="activeBoard = tab.key">
          {{ tab.label }}
        </button>
      </div>
      <div class="toolbar-right">
        <label class="select-label" for="course-filter">课程范围</label>
        <select id="course-filter" v-model="activeCourse" class="course-select">
          <option v-for="option in courseOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>
    </section>

    <section class="podium-section">
      <div class="section-head">
        <div>
          <p class="section-eyebrow">TOP 3</p>
          <h2 class="section-title">领跑席位</h2>
        </div>
        <div class="section-note">榜单分值会随筛选条件动态更新</div>
      </div>

      <div class="podium-grid">
        <article v-for="entry in podiumEntries" :key="entry.id" class="podium-card" :class="`rank-${entry.rank}`">
          <div class="podium-rank">No.{{ entry.rank }}</div>
          <img v-if="entry.rank === 1" class="winner-medal" :src="goldMedalNo1" alt="" aria-hidden="true" />
          <div class="podium-avatar">{{ entry.avatar }}</div>
          <h3 class="podium-name">{{ entry.name }}</h3>
          <div class="podium-score">{{ entry.boardScore }}</div>
          <div class="podium-badge">{{ entry.badge }}</div>
          <div class="podium-course">{{ entry.courseName }}</div>
        </article>
      </div>
    </section>

    <section class="main-grid">
      <div class="rank-panel">
        <div class="section-head compact">
          <div>
            <p class="section-eyebrow">RANKING LIST</p>
            <h2 class="section-title">完整榜单</h2>
          </div>
          <div class="section-note">{{ activeCourse === 'all' ? '全部课程' : activeCourse }}</div>
        </div>

        <div class="rank-list">
          <div class="rank-table-head" aria-hidden="true">
            <span>排名</span>
            <span>学生</span>
            <span>课程</span>
            <span>完成度</span>
            <span>互动</span>
            <span>答题率</span>
            <span>总得分</span>
          </div>
          <article v-for="entry in rankedEntries" :key="entry.id" class="rank-row"
            :class="{ highlight: isCurrentStudent(entry) }">
            <div class="rank-index">{{ entry.rank }}</div>
            <div class="rank-user">
              <div class="rank-avatar">{{ entry.avatar }}</div>
              <div class="rank-user-meta">
                <div class="rank-name-line">
                  <span class="rank-name">{{ entry.name }}</span>
                  <span class="rank-badge">{{ entry.badge }}</span>
                </div>
              </div>
            </div>
            <div class="rank-sub">{{ entry.courseName }}</div>
            <div class="rank-metrics">
              <div class="rank-metric-item">
                <span class="metric-label">完成度</span>
                <strong>{{ entry.progress }}%</strong>
                <i class="metric-track"><b :style="{ width: `${entry.progress}%` }" /></i>
              </div>
              <div class="rank-metric-item">
                <span class="metric-label">互动</span>
                <strong>{{ entry.interactions }}</strong>
                <i class="metric-track"><b :style="{ width: `${Math.min(entry.interactions * 5, 100)}%` }" /></i>
              </div>
              <div class="rank-metric-item">
                <span class="metric-label">答疑</span>
                <strong>{{ entry.qaAccuracy }}%</strong>
                <i class="metric-track"><b :style="{ width: `${entry.qaAccuracy}%` }" /></i>
              </div>
            </div>
            <div class="rank-score">
              <span class="score-label">成长分</span>
              <span class="score-value">{{ entry.boardScore }}</span>
              <span class="score-delta" :class="deltaClass(entry.rankDelta)">{{ formatDelta(entry.rankDelta) }}</span>
            </div>
          </article>
        </div>
      </div>

      <aside class="side-panel">
        <template v-if="isTeacher">
          <div class="spotlight-card">
            <p class="section-eyebrow">TEACHER INSIGHT</p>
            <h3 class="spotlight-title">课堂观察</h3>
            <div class="insight-list">
              <article v-for="item in teacherInsightCards" :key="item.title" class="insight-item">
                <div class="insight-title">{{ item.title }}</div>
                <div class="insight-value">{{ item.value }}</div>
                <div class="insight-desc">{{ item.desc }}</div>
              </article>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="spotlight-card">
            <p class="section-eyebrow">MY RANK</p>
            <h3 class="spotlight-title">我的位置</h3>
            <div class="my-rank-card">
              <div class="my-rank-top">
                <div>
                  <div class="my-rank-value">No.{{ currentStudentEntry.rank }}</div>
                  <div class="my-rank-course">{{ currentStudentEntry.courseName }}</div>
                </div>
                <div class="my-rank-avatar">{{ currentStudentEntry.avatar }}</div>
              </div>
              <p class="my-rank-desc">距离上一名还差 <strong>{{ studentGap }}</strong> 分，继续保持互动和任务完成度就能继续上升。</p>
              <div class="my-rank-stats">
                <span>完成度 {{ currentStudentEntry.progress }}%</span>
                <span>互动 {{ currentStudentEntry.interactions }}</span>
                <span>答疑 {{ currentStudentEntry.qaAccuracy }}%</span>
              </div>
            </div>
          </div>
        </template>
      </aside>
    </section>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Noto+Serif+SC:wght@600;700&display=swap');

*,
*::before,
*::after {
  box-sizing: border-box;
}

.leaderboard-page {
  position: relative;
  min-height: 100vh;
  padding: 0;
  background: #f8fafc;
  font-family: 'Sora', sans-serif;
  color: #0f172a;
}

.page-inner {
  padding: 0 0 40px;
}

.leaderboard-page::before {
  display: none;
}

.hero-panel,
.toolbar,
.podium-section,
.main-grid {
  position: relative;
  z-index: 1;
}

.hero-panel {
  position: relative;
  padding: 38px 44px;
  border-radius: 14px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 28px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(29, 78, 216, 0.94) 55%, rgba(34, 211, 238, 0.88) 100%);
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.10);
}

.hero-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 22% 18%, rgba(255, 255, 255, 0.14), transparent 24%),
    linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.06) 50%, transparent 100%);
  pointer-events: none;
}

.hero-panel::after {
  content: '';
  position: absolute;
  right: -44px;
  top: -54px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  filter: blur(10px);
  pointer-events: none;
}

.hero-copy,
.hero-visual {
  position: relative;
  z-index: 1;
}

.hero-eyebrow {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #7dd3fc;
  text-transform: uppercase;
}

.hero-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 42px;
  line-height: 1.2;
  color: #f8fbff;
}

.hero-subtitle {
  max-width: 720px;
  margin: 16px 0 28px;
  font-size: 14px;
  line-height: 1.85;
  color: #c5defb;
}

.hero-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.hero-metric {
  min-width: 140px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.hero-metric-value {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
}

.hero-metric-label {
  font-size: 12px;
  color: #b8d4f7;
}

.hero-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.ring-lg {
  width: 200px;
  height: 200px;
}

.ring-md {
  width: 148px;
  height: 148px;
  border-style: dashed;
  border-color: rgba(125, 211, 252, 0.35);
}

.ring-sm {
  width: 98px;
  height: 98px;
  border-color: rgba(103, 232, 249, 0.32);
}

.crown-core {
  width: 76px;
  height: 76px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #f59e0b, #fbbf24 48%, #fde68a 100%);
  box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.06), 0 18px 36px rgba(15, 23, 42, 0.28);
}

.toolbar,
.podium-section,
.main-grid {
  max-width: 1400px;
  margin: 22px auto 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #dde8f5;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(12px);
}

.toolbar-left {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-pill {
  all: unset;
  cursor: pointer;
  padding: 8px 15px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #69809c;
  background: rgba(240, 245, 252, 0.92);
  transition: all 0.18s ease;
}

.filter-pill.active,
.filter-pill:hover {
  color: #1d4ed8;
  background: #e0ecff;
  transform: translateY(-1px);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-label {
  font-size: 12px;
  font-weight: 700;
  color: #6f86a3;
}

.course-select {
  height: 40px;
  min-width: 170px;
  padding: 0 14px;
  border: 1px solid #d6e4f3;
  border-radius: 12px;
  background: #f9fbfe;
  color: #1f3d63;
  font: 600 12px 'Sora', sans-serif;
  outline: none;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-head.compact {
  margin-bottom: 14px;
}

.section-eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #88a0bd;
  text-transform: uppercase;
}

.section-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 24px;
  color: #13253f;
}

.section-note {
  font-size: 12px;
  color: #7d90a8;
}

.podium-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  align-items: end;
}

.podium-card {
  padding: 26px 20px 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dce8f6;
  text-align: center;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.06);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(12px);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.podium-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 24px 44px rgba(15, 23, 42, 0.08);
}

.podium-card::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.9;
  pointer-events: none;
}

.podium-card.rank-1 {
  padding-top: 34px;
  transform: translateY(-10px);
}

.podium-card.rank-1::before {
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.18), transparent 48%);
}

.podium-card.rank-2::before {
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.16), transparent 48%);
}

.podium-card.rank-3::before {
  background: linear-gradient(180deg, rgba(251, 146, 60, 0.14), transparent 48%);
}

.podium-rank {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #7388a4;
  text-transform: uppercase;
}

.podium-avatar {
  width: 64px;
  height: 64px;
  margin: 14px auto 12px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #0891b2);
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.22);
}

.podium-name {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #13253f;
}

.podium-course {
  margin: 6px 0 0;
  font-size: 12px;
  color: #7b90aa;
}

.podium-score {
  margin-top: 14px;
  font-size: 30px;
  font-weight: 800;
  color: #173f79;
}

.podium-badge {
  display: inline-flex;
  margin-top: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #2459a9;
  background: #e6f0ff;
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.9fr);
  gap: 20px;
}

.rank-panel,
.spotlight-card {
  border-radius: 24px;
  border: 1px solid #dce7f4;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(12px);
}

.rank-panel {
  padding: 24px;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rank-row {
  display: grid;
  grid-template-columns: 54px minmax(0, 1.2fr) minmax(260px, 0.95fr) 110px;
  align-items: center;
  gap: 14px;
  padding: 15px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #fbfdff, #f6faff);
  border: 1px solid #e5eef8;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.rank-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.06);
  border-color: #cdddf2;
}

.rank-row.highlight {
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.72), rgba(240, 249, 255, 0.95));
  border-color: #93c5fd;
}

.rank-index {
  font-size: 24px;
  font-weight: 800;
  color: #9bb0c9;
  text-align: center;
}

.rank-user {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.rank-avatar {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1d4ed8, #0ea5e9);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  flex-shrink: 0;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.16);
}

.rank-user-meta,
.rank-name-line {
  min-width: 0;
}

.rank-name-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rank-name {
  font-size: 15px;
  font-weight: 800;
  color: #153354;
}

.rank-badge {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
}

.rank-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #7d92ab;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rank-metrics span,
.my-rank-stats span {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: #597391;
  background: #eef4fb;
}

.rank-score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.score-value {
  font-size: 24px;
  font-weight: 800;
  color: #163a63;
}

.score-delta {
  font-size: 12px;
  font-weight: 800;
}

.score-delta.up {
  color: #059669;
}

.score-delta.down {
  color: #dc2626;
}

.score-delta.flat {
  color: #94a3b8;
}

.side-panel {
  display: flex;
  flex-direction: column;
}

.spotlight-card {
  padding: 24px;
  height: fit-content;
}

.spotlight-title {
  margin: 0;
  font-size: 24px;
  font-family: 'Noto Serif SC', serif;
  color: #153354;
}

.insight-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}

.insight-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #f7fbff, #f1f7ff);
  border: 1px solid #e0ebf8;
}

.insight-title {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #7b90aa;
  text-transform: uppercase;
}

.insight-value {
  margin-top: 8px;
  font-size: 20px;
  font-weight: 800;
  color: #13335b;
}

.insight-desc {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.75;
  color: #6d84a0;
}

.my-rank-card {
  margin-top: 18px;
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.78), rgba(240, 249, 255, 0.96));
  border: 1px solid #bfdbfe;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.my-rank-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.my-rank-value {
  font-size: 34px;
  font-weight: 800;
  color: #1d4ed8;
}

.my-rank-course {
  font-size: 12px;
  color: #6f88a4;
}

.my-rank-avatar {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #0891b2);
}

.my-rank-desc {
  margin: 16px 0 0;
  font-size: 13px;
  line-height: 1.8;
  color: #4f6886;
}

.my-rank-desc strong {
  color: #1d4ed8;
}

.my-rank-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

@media (max-width: 1100px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .podium-grid {
    grid-template-columns: 1fr;
  }

  .podium-card.rank-1 {
    transform: none;
  }

  .rank-row {
    grid-template-columns: 44px 1fr;
  }

  .rank-metrics,
  .rank-score {
    grid-column: 2;
  }

  .rank-score {
    align-items: flex-start;
  }
}

@media (max-width: 820px) {
  .leaderboard-page .page-inner {
    padding: 0 0 34px;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    flex-wrap: wrap;
  }

  .hero-panel {
    grid-template-columns: 1fr;
    padding: 32px 24px;
  }

  .hero-title {
    font-size: 34px;
  }

  .hero-visual {
    min-height: 180px;
  }

  .rank-row {
    padding: 14px;
  }
}

/* Portal theme sync */
.leaderboard-page {
  --rank-bg: #f8fafc;
  --rank-surface: #ffffff;
  --rank-border: #e2e8f0;
  --rank-border-soft: #edf2f7;
  --rank-text: #0f172a;
  --rank-muted: #64748b;
  --rank-subtle: #94a3b8;
  --rank-primary: #14b8a6;
  --rank-primary-strong: #0f766e;
  --rank-primary-soft: #f0fdfa;
  padding: 0;
  background: var(--rank-bg) !important;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif !important;
  overflow-x: hidden;
}

.leaderboard-page .page-inner {
  padding: 0 0 40px;
}

.leaderboard-page::before {
  display: none;
}

.leaderboard-page .hero-panel {
  display: grid !important;
  min-height: 210px !important;
  padding: 22px 24px !important;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 330px) !important;
  gap: 20px !important;
  border-radius: 8px !important;
  border: 1px solid rgba(20, 184, 166, 0.16) !important;
  color: var(--rank-text) !important;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(255, 255, 255, 0.92) 46%, rgba(14, 165, 233, 0.16)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px) !important;
  background-size: auto, 22px 22px, 22px 22px !important;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07) !important;
}

.leaderboard-page .hero-panel::before {
  background:
    radial-gradient(circle at 72% 22%, rgba(20, 184, 166, 0.14), transparent 24%),
    radial-gradient(circle at 95% 72%, rgba(59, 130, 246, 0.12), transparent 22%) !important;
  opacity: 1 !important;
}

.leaderboard-page .hero-title {
  color: var(--rank-text) !important;
  font-family: inherit !important;
  font-size: 30px !important;
  font-weight: 800 !important;
}

.leaderboard-page .hero-eyebrow,
.leaderboard-page .section-eyebrow {
  color: var(--rank-primary) !important;
  font-size: 12px !important;
  letter-spacing: 0 !important;
}

.leaderboard-page .hero-subtitle {
  color: var(--rank-muted) !important;
  max-width: 640px !important;
  font-size: 15px !important;
}

.leaderboard-page .hero-metrics,
.leaderboard-page .hero-visual,
.leaderboard-page .ring,
.leaderboard-page .crown-core {
  display: flex !important;
}

.leaderboard-page .ring {
  display: block !important;
  border-color: rgba(20, 184, 166, 0.22) !important;
}

.leaderboard-page .ring-md {
  border-color: rgba(20, 184, 166, 0.32) !important;
}

.leaderboard-page .hero-metric {
  background: rgba(255, 255, 255, 0.72) !important;
  border: 1px solid rgba(15, 118, 110, 0.12) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}

.leaderboard-page .hero-metric-value,
.leaderboard-page .section-title,
.leaderboard-page .spotlight-title {
  color: var(--rank-text) !important;
  font-family: inherit !important;
}

.leaderboard-page .hero-metric-label {
  color: #134e4a !important;
}

.leaderboard-page .crown-core {
  color: var(--rank-primary-strong) !important;
  background: rgba(255, 255, 255, 0.78) !important;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.07) !important;
}

.leaderboard-page .toolbar,
.leaderboard-page .podium-section,
.leaderboard-page .rank-panel,
.leaderboard-page .spotlight-card {
  max-width: 1480px !important;
  border-radius: 8px !important;
  border: 1px solid var(--rank-border) !important;
  background: var(--rank-surface) !important;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.055) !important;
  backdrop-filter: none !important;
}

.leaderboard-page .toolbar {
  padding: 12px 14px !important;
}

.leaderboard-page .toolbar,
.leaderboard-page .podium-section,
.leaderboard-page .main-grid {
  margin-left: auto !important;
  margin-right: auto !important;
  max-width: 1480px !important;
  width: calc(100% - 192px) !important;
}

.leaderboard-page .filter-pill {
  color: var(--rank-muted) !important;
  background: #f8fafc !important;
  border: 1px solid transparent !important;
}

.leaderboard-page .filter-pill.active,
.leaderboard-page .filter-pill:hover {
  color: var(--rank-primary-strong) !important;
  background: var(--rank-primary-soft) !important;
  border-color: #99f6e4 !important;
}

.leaderboard-page .course-select {
  border-radius: 8px !important;
  border-color: var(--rank-border) !important;
  background: #ffffff !important;
}

.leaderboard-page .podium-card,
.leaderboard-page .rank-row,
.leaderboard-page .insight-item,
.leaderboard-page .my-rank-card {
  border-radius: 8px !important;
  border-color: var(--rank-border) !important;
  background:
    radial-gradient(circle at 96% 10%, rgba(20, 184, 166, 0.08), transparent 34%),
    linear-gradient(180deg, #ffffff, #fbfdff) !important;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.045) !important;
  backdrop-filter: none !important;
}

.leaderboard-page .podium-avatar,
.leaderboard-page .rank-avatar,
.leaderboard-page .my-rank-avatar {
  border-radius: 8px !important;
  background: linear-gradient(135deg, var(--rank-primary), var(--rank-primary-strong)) !important;
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.16) !important;
}

.leaderboard-page .podium-score,
.leaderboard-page .score-value,
.leaderboard-page .my-rank-value,
.leaderboard-page .my-rank-desc strong {
  color: var(--rank-primary-strong) !important;
}

.leaderboard-page .podium-badge,
.leaderboard-page .rank-badge,
.leaderboard-page .rank-metrics span,
.leaderboard-page .my-rank-stats span {
  color: var(--rank-primary-strong) !important;
  background: var(--rank-primary-soft) !important;
}

.leaderboard-page .rank-row.highlight {
  background:
    linear-gradient(135deg, rgba(204, 251, 241, 0.7), rgba(255, 255, 255, 0.96)) !important;
  border-color: #99f6e4 !important;
}

@media (max-width: 820px) {
  .leaderboard-page .toolbar,
  .leaderboard-page .podium-section,
  .leaderboard-page .main-grid {
    width: 100% !important;
  }

  .leaderboard-page .page-inner {
    padding: 0 0 32px;
  }

  .leaderboard-page .hero-panel {
    grid-template-columns: 1fr !important;
    min-height: auto !important;
  }

  .leaderboard-page .hero-title {
    font-size: 28px !important;
  }
}

/* Growth ranking layout refinement */
.leaderboard-page .podium-grid {
  gap: 14px !important;
}

.leaderboard-page .podium-card {
  display: grid !important;
  grid-template-columns: auto minmax(0, 1fr) auto !important;
  grid-template-areas:
    "avatar name rank"
    "avatar course rank"
    "badge badge score" !important;
  align-items: center !important;
  column-gap: 14px !important;
  row-gap: 8px !important;
  padding: 18px !important;
  text-align: left !important;
}

.leaderboard-page .podium-card.rank-1 {
  transform: none !important;
}

.leaderboard-page .podium-rank {
  grid-area: rank;
  justify-self: end;
  padding: 6px 10px;
  border-radius: 999px;
  background: #fffbeb;
  color: #b45309 !important;
}

.leaderboard-page .podium-avatar {
  grid-area: avatar;
  margin: 0 !important;
}

.leaderboard-page .podium-name {
  grid-area: name;
}

.leaderboard-page .podium-course {
  grid-area: course;
}

.leaderboard-page .podium-badge {
  grid-area: badge;
  width: max-content;
  margin-top: 2px !important;
}

.leaderboard-page .podium-score {
  grid-area: score;
  justify-self: end;
  margin-top: 0 !important;
  font-size: 26px !important;
}

.leaderboard-page .rank-list {
  gap: 10px !important;
}

.leaderboard-page .rank-row {
  position: relative;
  grid-template-columns: 44px minmax(190px, 0.92fr) minmax(280px, 1.45fr) 116px !important;
  gap: 16px !important;
  align-items: center !important;
  padding: 14px 16px !important;
  border-radius: 10px !important;
  overflow: hidden;
}

.leaderboard-page .rank-row::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 999px;
  background: #14b8a6;
}

.leaderboard-page .rank-index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #f8fafc;
  color: #64748b !important;
  font-size: 16px !important;
}

.leaderboard-page .rank-row:nth-child(1) .rank-index {
  color: #b45309 !important;
  background: #fffbeb;
}

.leaderboard-page .rank-row:nth-child(2) .rank-index {
  color: #475569 !important;
  background: #f1f5f9;
}

.leaderboard-page .rank-row:nth-child(3) .rank-index {
  color: #c2410c !important;
  background: #fff7ed;
}

.leaderboard-page .rank-avatar,
.leaderboard-page .podium-avatar,
.leaderboard-page .my-rank-avatar {
  border: 1px solid rgba(15, 23, 42, 0.06) !important;
  color: #0f766e !important;
  background:
    linear-gradient(135deg, rgba(204, 251, 241, 0.96), rgba(240, 253, 250, 0.78)) !important;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06) !important;
}

.leaderboard-page .rank-row:nth-child(4n + 1) .rank-avatar,
.leaderboard-page .podium-card.rank-1 .podium-avatar {
  color: #1d4ed8 !important;
  background: linear-gradient(135deg, #dbeafe, #eff6ff) !important;
}

.leaderboard-page .rank-row:nth-child(4n + 2) .rank-avatar,
.leaderboard-page .podium-card.rank-2 .podium-avatar {
  color: #7c3aed !important;
  background: linear-gradient(135deg, #ede9fe, #faf5ff) !important;
}

.leaderboard-page .rank-row:nth-child(4n + 3) .rank-avatar,
.leaderboard-page .podium-card.rank-3 .podium-avatar {
  color: #d97706 !important;
  background: linear-gradient(135deg, #fef3c7, #fffbeb) !important;
}

.leaderboard-page .rank-avatar {
  width: 44px !important;
  height: 44px !important;
  border-radius: 12px !important;
  font-size: 18px !important;
}

.leaderboard-page .rank-name-line {
  flex-wrap: wrap;
}

.leaderboard-page .rank-name {
  color: #0f172a !important;
}

.leaderboard-page .rank-sub {
  color: #64748b !important;
}

.leaderboard-page .rank-metrics {
  display: grid !important;
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 10px !important;
}

.leaderboard-page .rank-metric-item {
  min-width: 0;
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #ffffff;
}

.leaderboard-page .rank-metric-item strong {
  color: #0f172a;
  font-size: 14px;
  line-height: 1;
}

.leaderboard-page .metric-label {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.leaderboard-page .metric-track {
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: #ecfdf5;
}

.leaderboard-page .metric-track b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2dd4bf, #14b8a6);
}

.leaderboard-page .rank-score {
  min-height: 84px;
  align-items: center !important;
  justify-content: center;
  padding: 10px;
  border: 1px solid #ccfbf1;
  border-radius: 10px;
  background: linear-gradient(180deg, #f0fdfa, #ffffff);
}

.leaderboard-page .score-label {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.leaderboard-page .score-value {
  font-size: 28px !important;
  line-height: 1;
}

.leaderboard-page .score-delta {
  padding: 3px 8px;
  border-radius: 999px;
  background: #ffffff;
}

@media (max-width: 1180px) {
  .leaderboard-page .rank-row {
    grid-template-columns: 40px minmax(0, 1fr) 110px !important;
  }

  .leaderboard-page .rank-metrics {
    grid-column: 2 / -1;
  }
}

@media (max-width: 760px) {
  .leaderboard-page .podium-card {
    grid-template-columns: auto minmax(0, 1fr) !important;
    grid-template-areas:
      "avatar name"
      "avatar course"
      "badge badge"
      "score rank" !important;
  }

  .leaderboard-page .rank-row {
    grid-template-columns: 36px minmax(0, 1fr) !important;
  }

  .leaderboard-page .rank-metrics,
  .leaderboard-page .rank-score {
    grid-column: 1 / -1 !important;
  }

  .leaderboard-page .rank-metrics {
    grid-template-columns: 1fr !important;
  }
}

/* Screenshot-matched leaderboard surface */
.leaderboard-page {
  --leader-content-gutter: 96px;
  --leader-content-width: calc(100% - (var(--leader-content-gutter) * 2));
  --rank-bg: #f7fafc;
  --rank-surface: #ffffff;
  --rank-border: #dfe7ef;
  --rank-border-soft: #edf3f8;
  --rank-text: #111827;
  --rank-muted: #5d728a;
  --rank-primary: #14b8a6;
  --rank-primary-strong: #0f766e;
  background: var(--rank-bg) !important;
}

.leaderboard-page .hero-panel {
  min-height: 190px !important;
  padding: 34px 46px 26px !important;
  grid-template-columns: minmax(340px, 0.9fr) minmax(560px, 1.2fr) !important;
  align-items: start !important;
  gap: 42px !important;
  border-radius: 0 !important;
  border: 0 !important;
  background:
    linear-gradient(90deg, rgba(246, 249, 253, 0.98), rgba(249, 252, 255, 0.98)),
    radial-gradient(circle at 92% 16%, rgba(51, 112, 255, 0.08), transparent 24%) !important;
  box-shadow: none !important;
}

.leaderboard-page .hero-copy {
  align-self: start;
}

.leaderboard-page .hero-eyebrow,
.leaderboard-page .section-eyebrow {
  margin-bottom: 8px !important;
  color: var(--rank-primary) !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
}

.leaderboard-page .hero-title {
  font-size: 30px !important;
  font-weight: 700 !important;
  line-height: 1.22 !important;
  color: var(--rank-text) !important;
}

.leaderboard-page .hero-subtitle {
  margin: 14px 0 0 !important;
  color: var(--rank-muted) !important;
  font-size: 14px !important;
  line-height: 1.7 !important;
}

.leaderboard-page .hero-metrics {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 16px !important;
  align-items: stretch;
}

.leaderboard-page .hero-metric {
  width: auto !important;
  min-width: 0 !important;
  height: 110px !important;
  padding: 16px 18px 14px 64px !important;
  position: relative;
  justify-content: center !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  border: 1px solid #dfe7ef !important;
  box-shadow: none !important;
}

.leaderboard-page .hero-metric-icon {
  position: absolute;
  left: 18px;
  top: 42px;
  width: 26px;
  height: 26px;
  color: #3370ff;
}

.leaderboard-page .hero-metric-icon::before,
.leaderboard-page .hero-metric-icon::after {
  content: "";
  position: absolute;
  border-radius: 3px;
}

.leaderboard-page .hero-metric-icon::before {
  left: 2px;
  bottom: 2px;
  width: 5px;
  height: 12px;
  background: currentColor;
  box-shadow: 8px -5px 0 currentColor, 16px -10px 0 currentColor;
}

.leaderboard-page .hero-metric-icon::after {
  right: 0;
  top: 2px;
  width: 10px;
  height: 10px;
  border-top: 3px solid currentColor;
  border-right: 3px solid currentColor;
  transform: rotate(45deg);
  opacity: 0.85;
}

.leaderboard-page .hero-metric:nth-child(2) .hero-metric-icon {
  color: #7c3aed;
}

.leaderboard-page .hero-metric:nth-child(3) .hero-metric-icon {
  color: #059669;
}

.leaderboard-page .hero-metric:nth-child(4) .hero-metric-icon {
  color: #f97316;
}

.leaderboard-page .hero-metric-label {
  order: 1;
  color: #52657d !important;
  font-size: 12px !important;
  font-weight: 500 !important;
}

.leaderboard-page .hero-metric-value {
  order: 2;
  color: var(--rank-text) !important;
  margin-top: 4px;
  font-size: 24px !important;
  font-weight: 700 !important;
  line-height: 1.1 !important;
}

.leaderboard-page .hero-metric-sub {
  order: 3;
  margin-top: 5px;
  color: #52657d;
  font-size: 12px !important;
}

.leaderboard-page .toolbar,
.leaderboard-page .podium-section,
.leaderboard-page .main-grid {
  width: var(--leader-content-width) !important;
  max-width: 1480px !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

.leaderboard-page .toolbar {
  min-height: 60px;
  margin-top: 18px !important;
  padding: 12px 14px !important;
  border-radius: 8px !important;
  border: 1px solid var(--rank-border) !important;
  background: var(--rank-surface) !important;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.055) !important;
}

.leaderboard-page .filter-pill {
  min-width: 72px;
  height: 36px;
  display: inline-flex;
  position: relative;
  align-items: center;
  justify-content: center;
  padding: 0 14px !important;
  border-radius: 6px !important;
  color: #24344d !important;
  font-weight: 600 !important;
  background: transparent !important;
}

.leaderboard-page .filter-pill.active,
.leaderboard-page .filter-pill:hover {
  color: #1d64d8 !important;
  background: transparent !important;
  border-color: transparent !important;
  transform: none !important;
}

.leaderboard-page .filter-pill.active::after {
  content: "";
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: -13px;
  height: 3px;
  border-radius: 999px;
  background: #1d64d8;
}

.leaderboard-page .course-select {
  height: 40px !important;
  min-width: 170px !important;
  border-radius: 8px !important;
  color: #20344d !important;
  font-weight: 600 !important;
}

.leaderboard-page .podium-section,
.leaderboard-page .rank-panel,
.leaderboard-page .spotlight-card {
  border-radius: 8px !important;
  border: 1px solid var(--rank-border) !important;
  background: var(--rank-surface) !important;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.055) !important;
}

.leaderboard-page .podium-section {
  margin-top: 20px !important;
  padding: 22px 22px 24px !important;
}

.leaderboard-page .section-head {
  margin-bottom: 20px !important;
}

.leaderboard-page .section-title,
.leaderboard-page .spotlight-title {
  color: var(--rank-text) !important;
  font-size: 22px !important;
  font-weight: 700 !important;
}

.leaderboard-page .section-note {
  color: var(--rank-muted) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  background: transparent !important;
  border: 0 !important;
}

.leaderboard-page .podium-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 14px !important;
}

.leaderboard-page .podium-card {
  min-height: 144px;
  padding: 18px !important;
  border-radius: 8px !important;
  background:
    radial-gradient(circle at 94% 12%, rgba(20, 184, 166, 0.08), transparent 32%),
    linear-gradient(180deg, #ffffff, #fbfdff) !important;
  border: 1px solid var(--rank-border) !important;
  box-shadow: none !important;
}

.leaderboard-page .podium-card.rank-1 {
  position: relative;
  overflow: visible !important;
  border-color: #9bc6ff !important;
  background:
    radial-gradient(circle at 94% 10%, rgba(51, 112, 255, 0.12), transparent 34%),
    linear-gradient(180deg, #f3f8ff, #ffffff) !important;
}

.leaderboard-page .podium-card.rank-2 {
  background:
    radial-gradient(circle at 94% 10%, rgba(20, 184, 166, 0.12), transparent 34%),
    linear-gradient(180deg, #f8fafc, #ffffff) !important;
}

.leaderboard-page .podium-card.rank-3 {
  background:
    radial-gradient(circle at 94% 10%, rgba(245, 158, 11, 0.12), transparent 34%),
    linear-gradient(180deg, #fff7ed, #ffffff) !important;
}

.leaderboard-page .winner-medal {
  position: absolute;
  left: 50%;
  top: -18px;
  width: 58px;
  height: 58px;
  object-fit: contain;
  object-position: center;
  filter: drop-shadow(0 7px 12px rgba(180, 83, 9, 0.16));
  transform: translateX(-50%);
  z-index: 2;
}

.leaderboard-page .podium-rank {
  min-width: 52px;
  justify-self: end;
  text-align: center;
  font-size: 12px !important;
  letter-spacing: 0 !important;
}

.leaderboard-page .podium-avatar,
.leaderboard-page .rank-avatar,
.leaderboard-page .my-rank-avatar {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.leaderboard-page .podium-name {
  color: var(--rank-text) !important;
  font-size: 20px !important;
  font-weight: 700 !important;
}

.leaderboard-page .podium-score {
  color: var(--rank-primary-strong) !important;
  font-size: 28px !important;
  font-weight: 700 !important;
}

.leaderboard-page .podium-badge,
.leaderboard-page .rank-badge,
.leaderboard-page .my-rank-stats span {
  color: var(--rank-primary-strong) !important;
  background: #f0fdfa !important;
  border-radius: 999px !important;
}

.leaderboard-page .main-grid {
  margin-top: 18px !important;
  grid-template-columns: minmax(0, 1.72fr) minmax(360px, 0.86fr) !important;
  gap: 18px !important;
}

.leaderboard-page .rank-panel,
.leaderboard-page .spotlight-card {
  padding: 24px !important;
}

.leaderboard-page .rank-list {
  gap: 10px !important;
}

.leaderboard-page .rank-table-head {
  display: grid;
  grid-template-columns: 48px minmax(130px, 0.75fr) minmax(150px, 0.9fr) repeat(3, minmax(76px, 0.65fr)) 78px;
  gap: 10px;
  padding: 0 14px 10px;
  color: #5f7087;
  font-size: 12px;
  font-weight: 600;
  border-bottom: 1px solid var(--rank-border-soft);
}

.leaderboard-page .rank-row {
  min-height: 48px;
  grid-template-columns: 48px minmax(130px, 0.75fr) minmax(150px, 0.9fr) repeat(3, minmax(76px, 0.65fr)) 78px !important;
  gap: 10px !important;
  padding: 8px 14px !important;
  border-radius: 0 !important;
  border: 0 !important;
  border-top: 1px solid var(--rank-border-soft) !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.leaderboard-page .rank-row::before {
  display: none !important;
}

.leaderboard-page .rank-row:hover {
  transform: none !important;
  background: #f8fbff !important;
  box-shadow: none !important;
}

.leaderboard-page .rank-index {
  width: 24px !important;
  height: 24px !important;
  border-radius: 999px !important;
  font-size: 12px !important;
  font-weight: 700 !important;
}

.leaderboard-page .rank-user {
  gap: 10px !important;
}

.leaderboard-page .rank-avatar {
  width: 30px !important;
  height: 30px !important;
  border-radius: 6px !important;
  font-size: 14px !important;
}

.leaderboard-page .rank-name {
  font-size: 13px !important;
  font-weight: 600 !important;
}

.leaderboard-page .rank-badge {
  display: none !important;
}

.leaderboard-page .rank-sub {
  margin-top: 0 !important;
  font-size: 12px !important;
}

.leaderboard-page .rank-metrics {
  display: contents !important;
}

.leaderboard-page .rank-metric-item {
  display: grid !important;
  gap: 4px;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

.leaderboard-page .metric-label,
.leaderboard-page .score-label {
  color: var(--rank-muted) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
}

.leaderboard-page .metric-track {
  height: 4px !important;
  background: #e8eef7 !important;
}

.leaderboard-page .metric-track b {
  background: #1d64d8 !important;
}

.leaderboard-page .score-value,
.leaderboard-page .my-rank-value {
  color: var(--rank-primary-strong) !important;
  font-weight: 700 !important;
}

.leaderboard-page .rank-score {
  min-height: 0;
  padding: 0 !important;
  align-items: flex-end !important;
  border: 0 !important;
  background: transparent !important;
}

.leaderboard-page .score-label {
  display: none;
}

.leaderboard-page .my-rank-card {
  margin-top: 18px !important;
  padding: 26px 20px !important;
  border-radius: 8px !important;
  border: 1px solid #ccfbf1 !important;
  background:
    radial-gradient(circle at 92% 14%, rgba(20, 184, 166, 0.14), transparent 28%),
    linear-gradient(180deg, #ffffff, #fbfdff) !important;
}

.leaderboard-page .my-rank-desc {
  color: #415771 !important;
  font-size: 13px !important;
}

@media (max-width: 1180px) {
  .leaderboard-page {
    --leader-content-gutter: 32px;
  }
}

@media (max-width: 820px) {
  .leaderboard-page {
    --leader-content-gutter: 14px;
  }

  .leaderboard-page .hero-panel {
    border-radius: 0 0 8px 8px !important;
  }

  .leaderboard-page .hero-metric {
    width: auto !important;
    min-width: 120px !important;
    flex: 1 1 120px;
  }

  .leaderboard-page .toolbar,
  .leaderboard-page .podium-section,
  .leaderboard-page .main-grid {
    width: var(--leader-content-width) !important;
  }
}
</style>
