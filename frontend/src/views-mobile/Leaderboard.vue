<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const boardTabs = [
  { key: 'overall',     label: '综合' },
  { key: 'weekly',      label: '本周' },
  { key: 'interactive', label: '互动' },
  { key: 'growth',      label: '进步' },
]

const courseFilters = [
  { key: 'all',   label: '全部课程' },
  { key: 'ai',    label: '人工智能导论' },
  { key: 'ml',    label: '机器学习基础' },
  { key: 'ds',    label: '数据结构与算法' },
  { key: 'py',    label: 'Python 程序设计' },
]

const rankingEntries = [
  { id: 'u-1',  name: '林知夏', courseKey: 'ds', courseName: '数据结构与算法',  score: 98, progress: 96, interactions: 18, qaAccuracy: 97, rankDelta:  2, badge: '进步最快', avatar: '林', weeklyActive: 7, weakPoints: '动态规划' },
  { id: 'u-2',  name: '陈屿',   courseKey: 'ai', courseName: '人工智能导论',    score: 94, progress: 91, interactions: 15, qaAccuracy: 95, rankDelta:  1, badge: '稳定输出', avatar: '陈', weeklyActive: 6, weakPoints: '反向传播' },
  { id: 'u-3',  name: '宋嘉宁', courseKey: 'ml', courseName: '机器学习基础',    score: 92, progress: 89, interactions: 17, qaAccuracy: 92, rankDelta: -1, badge: '互动积极', avatar: '宋', weeklyActive: 5, weakPoints: '正则化' },
  { id: 'u-4',  name: '周予安', courseKey: 'py', courseName: 'Python 程序设计', score: 89, progress: 87, interactions: 12, qaAccuracy: 90, rankDelta:  3, badge: '答疑高效', avatar: '周', weeklyActive: 7, weakPoints: '装饰器' },
  { id: 'u-5',  name: '沈星遥', courseKey: 'ds', courseName: '数据结构与算法',  score: 86, progress: 83, interactions: 11, qaAccuracy: 88, rankDelta:  0, badge: '稳步提升', avatar: '沈', weeklyActive: 4, weakPoints: '图算法' },
  { id: 'u-6',  name: '顾言',   courseKey: 'ai', courseName: '人工智能导论',    score: 84, progress: 82, interactions: 10, qaAccuracy: 86, rankDelta:  1, badge: '课堂专注', avatar: '顾', weeklyActive: 5, weakPoints: '注意力机制' },
  { id: 'u-7',  name: '何清越', courseKey: 'ml', courseName: '机器学习基础',    score: 82, progress: 79, interactions:  9, qaAccuracy: 85, rankDelta: -2, badge: '潜力选手', avatar: '何', weeklyActive: 3, weakPoints: 'SVM 核函数' },
  { id: 'u-8',  name: '许澈',   courseKey: 'ds', courseName: '数据结构与算法',  score: 80, progress: 77, interactions:  8, qaAccuracy: 84, rankDelta:  2, badge: '状态回升', avatar: '许', weeklyActive: 5, weakPoints: '红黑树' },
  { id: 'u-9',  name: '程知微', courseKey: 'py', courseName: 'Python 程序设计', score: 78, progress: 76, interactions:  7, qaAccuracy: 82, rankDelta:  0, badge: '持续打卡', avatar: '程', weeklyActive: 4, weakPoints: '异步编程' },
  { id: 'u-10', name: '姜望舒', courseKey: 'ai', courseName: '人工智能导论',    score: 76, progress: 73, interactions:  6, qaAccuracy: 80, rankDelta: -1, badge: '保持节奏', avatar: '姜', weeklyActive: 3, weakPoints: 'CNN 结构' },
]

const activeBoard = ref('overall')
const activeCourse = ref('all')
const expandedId = ref(null)

const getBoardScore = (entry, boardKey) => {
  if (boardKey === 'weekly')      return entry.score + entry.rankDelta * 2 + entry.interactions
  if (boardKey === 'interactive') return entry.interactions * 5 + entry.qaAccuracy * 0.3
  if (boardKey === 'growth')      return entry.progress * 0.65 + Math.max(entry.rankDelta, 0) * 8 + entry.qaAccuracy * 0.15
  return entry.score
}

const filteredEntries = computed(() => {
  const list = activeCourse.value === 'all'
    ? rankingEntries
    : rankingEntries.filter((e) => e.courseKey === activeCourse.value)
  return list
    .map((e) => ({ ...e, boardScore: Math.round(getBoardScore(e, activeBoard.value) * 10) / 10 }))
    .sort((a, b) => b.boardScore - a.boardScore)
    .map((e, i) => ({ ...e, rank: i + 1 }))
})

const top3 = computed(() => {
  const r = filteredEntries.value.slice(0, 3)
  return [r[1], r[0], r[2]].filter(Boolean)
})

const classStats = computed(() => {
  const list = filteredEntries.value
  if (!list.length) return { avg: 0, active: 0, total: 0, top: 0 }
  const avg = Math.round(list.reduce((s, e) => s + e.boardScore, 0) / list.length)
  const active = list.filter((e) => e.weeklyActive >= 5).length
  return { avg, active, total: list.length, top: list[0]?.boardScore ?? 0 }
})

const boardIntroMap = {
  overall:     { title: '综合学习总榜',   subtitle: '综合进度、互动与答题准确率' },
  weekly:      { title: '本周冲榜动态',   subtitle: '最近一周各学生积分变化趋势' },
  interactive: { title: '互动活跃榜',     subtitle: '课堂参与度与提问活跃排名' },
  growth:      { title: '学习进步榜',     subtitle: '强调成长幅度，发现潜力学生' },
}

const heroContent = computed(() => boardIntroMap[activeBoard.value])
const formatDelta = (v) => v > 0 ? `↑${v}` : v < 0 ? `↓${Math.abs(v)}` : '—'
const deltaClass = (v) => v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
const podiumHeights = { 1: 88, 2: 64, 3: 52 }

const toggleExpand = (id) => {
  expandedId.value = expandedId.value === id ? null : id
}
</script>

<template>
  <div class="lb-page">

    <!-- 顶栏 -->
    <div class="lb-topbar">
      <button class="lb-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <span class="lb-topbar-title">学生排行榜</span>
      <div style="width:36px" />
    </div>

    <!-- Tab 切换 -->
    <div class="lb-tabs">
      <button
        v-for="tab in boardTabs"
        :key="tab.key"
        class="lb-tab"
        :class="{ active: activeBoard === tab.key }"
        @click="activeBoard = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Hero 卡 -->
    <div class="lb-hero">
      <div class="lb-hero-icon">
        <van-icon name="chart-trending-o" size="28" color="#fbbf24" />
      </div>
      <div class="lb-hero-copy">
        <p class="lb-hero-eyebrow">TEACHER OVERVIEW</p>
        <h2 class="lb-hero-title">{{ heroContent.title }}</h2>
        <p class="lb-hero-sub">{{ heroContent.subtitle }}</p>
        <div class="lb-hero-metrics">
          <div class="lb-metric">
            <span class="lb-metric-val">{{ classStats.total }}</span>
            <span class="lb-metric-lbl">参与学生</span>
          </div>
          <div class="lb-metric-div" />
          <div class="lb-metric">
            <span class="lb-metric-val">{{ classStats.avg }}</span>
            <span class="lb-metric-lbl">班级均分</span>
          </div>
          <div class="lb-metric-div" />
          <div class="lb-metric">
            <span class="lb-metric-val">{{ classStats.active }}</span>
            <span class="lb-metric-lbl">本周活跃</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 课程筛选 -->
    <div class="lb-course-filter">
      <button
        v-for="c in courseFilters"
        :key="c.key"
        class="lb-course-chip"
        :class="{ active: activeCourse === c.key }"
        @click="activeCourse = c.key"
      >
        {{ c.label }}
      </button>
    </div>

    <!-- TOP 3 领奖台 -->
    <div class="lb-section-head">
      <span class="lb-section-eyebrow">TOP 3</span>
      <h3 class="lb-section-title">领跑席位</h3>
    </div>
    <div class="lb-podium">
      <div
        v-for="entry in top3"
        :key="entry.id"
        class="lb-podium-card"
        :class="`rank-${entry.rank}`"
      >
        <div class="lb-pod-rank">No.{{ entry.rank }}</div>
        <div class="lb-pod-avatar">{{ entry.avatar }}</div>
        <div class="lb-pod-name">{{ entry.name }}</div>
        <div class="lb-pod-score">{{ entry.boardScore }}</div>
        <div class="lb-pod-badge">{{ entry.badge }}</div>
        <div class="lb-pod-bar" :style="{ height: `${podiumHeights[entry.rank] || 52}px` }" />
      </div>
    </div>

    <!-- 完整榜单 -->
    <div class="lb-section-head" style="margin-top:6px">
      <span class="lb-section-eyebrow">RANKING LIST</span>
      <h3 class="lb-section-title">完整榜单</h3>
    </div>
    <div class="lb-list">
      <div
        v-for="entry in filteredEntries"
        :key="entry.id"
        class="lb-row-wrap"
      >
        <div class="lb-row" @click="toggleExpand(entry.id)">
          <div class="lb-row-rank" :class="{ 'top': entry.rank <= 3 }">{{ entry.rank }}</div>
          <div class="lb-row-avatar">{{ entry.avatar }}</div>
          <div class="lb-row-body">
            <div class="lb-row-name-line">
              <span class="lb-row-name">{{ entry.name }}</span>
              <span class="lb-row-badge">{{ entry.badge }}</span>
            </div>
            <div class="lb-row-sub">{{ entry.courseName }}</div>
          </div>
          <div class="lb-row-right">
            <span class="lb-row-score">{{ entry.boardScore }}</span>
            <span class="lb-row-delta" :class="deltaClass(entry.rankDelta)">{{ formatDelta(entry.rankDelta) }}</span>
          </div>
          <van-icon
            :name="expandedId === entry.id ? 'arrow-up' : 'arrow-down'"
            size="12"
            color="#c5cdd8"
            style="flex-shrink:0;margin-left:4px"
          />
        </div>

        <!-- 展开详情（教师视角） -->
        <transition name="expand">
          <div v-if="expandedId === entry.id" class="lb-detail">
            <div class="lb-detail-stats">
              <div class="lb-ds-item">
                <span class="lb-ds-val">{{ entry.progress }}%</span>
                <span class="lb-ds-lbl">完成度</span>
              </div>
              <div class="lb-ds-item">
                <span class="lb-ds-val">{{ entry.interactions }}</span>
                <span class="lb-ds-lbl">互动次数</span>
              </div>
              <div class="lb-ds-item">
                <span class="lb-ds-val">{{ entry.qaAccuracy }}%</span>
                <span class="lb-ds-lbl">答题准确率</span>
              </div>
              <div class="lb-ds-item">
                <span class="lb-ds-val">{{ entry.weeklyActive }}天</span>
                <span class="lb-ds-lbl">本周活跃</span>
              </div>
            </div>
            <div class="lb-detail-weak">
              <van-icon name="warning-o" size="12" color="#f59e0b" />
              <span>薄弱点：{{ entry.weakPoints }}</span>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- 班级分析卡 -->
    <div class="lb-section-head" style="margin-top:6px">
      <span class="lb-section-eyebrow">CLASS INSIGHT</span>
      <h3 class="lb-section-title">班级洞察</h3>
    </div>
    <div class="lb-insight">
      <div class="lb-insight-row">
        <van-icon name="friends-o" size="16" color="#1677ff" />
        <span>共 <strong>{{ classStats.total }}</strong> 名学生参与，本周活跃 <strong>{{ classStats.active }}</strong> 人，活跃率 <strong>{{ classStats.total ? Math.round(classStats.active / classStats.total * 100) : 0 }}%</strong></span>
      </div>
      <div class="lb-insight-row">
        <van-icon name="chart-trending-o" size="16" color="#7c3aed" />
        <span>班级均分 <strong>{{ classStats.avg }}</strong>，最高分 <strong>{{ classStats.top }}</strong>，建议关注末位 3 名同学</span>
      </div>
      <div class="lb-insight-row">
        <van-icon name="warning-o" size="16" color="#f59e0b" />
        <span>多名同学在 <strong>动态规划</strong>、<strong>反向传播</strong> 上得分偏低，建议重点补充讲解</span>
      </div>
    </div>

    <div style="height:28px" />
  </div>
</template>

<style scoped>
.lb-page {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, 'Sora', sans-serif;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

/* 顶栏 */
.lb-topbar {
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

.lb-back {
  width: 36px; height: 36px;
  border: none; background: #f5f7fa;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #1a2035; cursor: pointer;
}

.lb-topbar-title {
  font-size: 17px; font-weight: 800; color: #1a2035;
}

/* Tab */
.lb-tabs {
  display: flex;
  padding: 12px 16px 0;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
}

.lb-tab {
  flex: 1;
  border: none; background: transparent;
  padding: 8px 0 10px;
  font-size: 14px; font-weight: 600;
  color: #9aa3b2; cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.18s;
}

.lb-tab.active {
  color: #1677ff;
  border-bottom-color: #1677ff;
}

/* Hero */
.lb-hero {
  margin: 14px 14px 0;
  border-radius: 20px;
  background: linear-gradient(135deg, #0d1f3c 0%, #1a3a6b 40%, #1e5fa8 75%, #2196f3 100%);
  padding: 20px 18px 18px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
  overflow: hidden;
  position: relative;
}

.lb-hero::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(circle at 20% 20%, rgba(255,255,255,0.12), transparent 36%);
  pointer-events: none;
}

.lb-hero-icon {
  flex-shrink: 0;
  width: 56px; height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1d4ed8, #2563eb80);
  border: 1.5px solid rgba(255,255,255,0.18);
  display: flex; align-items: center; justify-content: center;
  position: relative; z-index: 1;
}

.lb-hero-copy { flex: 1; min-width: 0; position: relative; z-index: 1; }

.lb-hero-eyebrow {
  margin: 0 0 4px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.16em;
  color: rgba(255,255,255,0.5); text-transform: uppercase;
}

.lb-hero-title {
  margin: 0;
  font-size: 18px; font-weight: 800; color: #fff;
  line-height: 1.25;
}

.lb-hero-sub {
  margin: 4px 0 12px;
  font-size: 11px; color: rgba(255,255,255,0.65); line-height: 1.6;
}

.lb-hero-metrics {
  display: flex; align-items: center; gap: 10px;
}

.lb-metric {
  display: flex; flex-direction: column; gap: 2px;
}

.lb-metric-val {
  font-size: 15px; font-weight: 800; color: #fff;
}

.lb-metric-lbl {
  font-size: 10px; color: rgba(255,255,255,0.55);
}

.lb-metric-div {
  width: 1px; height: 28px;
  background: rgba(255,255,255,0.2);
}

/* 课程筛选 */
.lb-course-filter {
  display: flex;
  gap: 8px;
  padding: 12px 14px 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.lb-course-filter::-webkit-scrollbar { display: none; }

.lb-course-chip {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1.5px solid #e4e8ef;
  background: #fff;
  color: #6b7a90;
  font-size: 12px; font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.lb-course-chip.active {
  background: #1677ff;
  border-color: #1677ff;
  color: #fff;
}

/* Section head */
.lb-section-head {
  padding: 16px 16px 8px;
  display: flex; flex-direction: column; gap: 2px;
}

.lb-section-eyebrow {
  font-size: 10px; font-weight: 700; letter-spacing: 0.12em;
  color: #9aa3b2; text-transform: uppercase;
}

.lb-section-title {
  margin: 0;
  font-size: 18px; font-weight: 800; color: #1a2035;
}

/* Podium */
.lb-podium {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 10px;
  padding: 0 16px 14px;
}

.lb-podium-card {
  flex: 1;
  max-width: 120px;
  display: flex; flex-direction: column; align-items: center;
  background: #fff;
  border-radius: 16px;
  padding: 12px 8px 0;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  border: 1px solid #eef1f6;
  overflow: hidden;
}

.lb-podium-card.rank-1 {
  border-color: rgba(245,158,11,0.35);
  box-shadow: 0 6px 20px rgba(245,158,11,0.15);
}

.lb-pod-rank {
  font-size: 10px; font-weight: 800; color: #9aa3b2; letter-spacing: 0.06em;
}

.lb-pod-avatar {
  width: 44px; height: 44px;
  margin: 8px auto 6px;
  border-radius: 14px;
  background: linear-gradient(135deg, #2563eb, #0891b2);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 800; color: #fff;
  box-shadow: 0 6px 14px rgba(37,99,235,0.22);
}

.lb-pod-name {
  font-size: 14px; font-weight: 800; color: #1a2035;
}

.lb-pod-score {
  font-size: 22px; font-weight: 800; color: #1652a8;
  margin-top: 2px;
}

.lb-pod-badge {
  margin: 6px 0 8px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 10px; font-weight: 700;
  color: #2563eb; background: #eef4ff;
}

.lb-pod-bar {
  width: 100%;
  background: linear-gradient(180deg, #e8f0fe, #dce6fd);
  border-radius: 0 0 10px 10px;
  flex-shrink: 0;
}

.lb-podium-card.rank-1 .lb-pod-bar {
  background: linear-gradient(180deg, #fef3c7, #fde68a);
}

.lb-podium-card.rank-3 .lb-pod-bar {
  background: linear-gradient(180deg, #fce7d6, #fbd5bb);
}

/* Full list */
.lb-list {
  display: flex; flex-direction: column; gap: 8px;
  padding: 0 14px;
}

.lb-row-wrap {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #eef1f6;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  overflow: hidden;
}

.lb-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.lb-row:active { background: #f8f9fc; }

.lb-row-rank {
  font-size: 18px; font-weight: 800; color: #c5cdd8;
  min-width: 28px; text-align: center;
}

.lb-row-rank.top { color: #2563eb; }

.lb-row-avatar {
  width: 38px; height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1d4ed8, #0ea5e9);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 800;
  flex-shrink: 0;
}

.lb-row-body { flex: 1; min-width: 0; }

.lb-row-name-line {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}

.lb-row-name {
  font-size: 14px; font-weight: 700; color: #1a2035;
}

.lb-row-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px; font-weight: 700;
  color: #2563eb; background: rgba(37,99,235,0.08);
}

.lb-row-sub {
  margin-top: 2px;
  font-size: 11px; color: #9aa3b2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.lb-row-right {
  display: flex; flex-direction: column; align-items: flex-end; gap: 3px;
  flex-shrink: 0;
}

.lb-row-score {
  font-size: 20px; font-weight: 800; color: #163a63;
}

.lb-row-delta { font-size: 12px; font-weight: 700; }
.lb-row-delta.up   { color: #059669; }
.lb-row-delta.down { color: #dc2626; }
.lb-row-delta.flat { color: #94a3b8; }

/* 展开详情 */
.lb-detail {
  padding: 0 14px 12px;
  border-top: 1px solid #f0f2f5;
}

.lb-detail-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 12px 0 8px;
}

.lb-ds-item {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: #f8f9fc;
  border-radius: 10px;
  padding: 8px 4px;
}

.lb-ds-val { font-size: 14px; font-weight: 800; color: #1677ff; }
.lb-ds-lbl { font-size: 10px; color: #9aa3b2; }

.lb-detail-weak {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  background: #fffbeb;
  border-radius: 8px;
  border: 1px solid #fde68a;
  font-size: 12px;
  color: #92400e;
}

/* 班级洞察 */
.lb-insight {
  margin: 0 14px;
  padding: 16px;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lb-insight-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #4b5563;
  line-height: 1.65;
}

.lb-insight-row strong { color: #1a2035; font-weight: 700; }

/* 展开动画 */
.expand-enter-active,
.expand-leave-active {
  transition: max-height 0.22s ease, opacity 0.18s ease;
  overflow: hidden;
  max-height: 200px;
}
.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
