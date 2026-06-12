<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  progressPercent: { type: Number, default: 45 },
  sectionTitle: { type: String, default: '' },
  understandingLabel: { type: String, default: '稳步推进' },
  sections: { type: Array, default: () => [] },
})

const emit = defineEmits(['select-section'])

// ── 双星问题 mock 数据 ─────────────────────────────────────────────────
const mockChapters = [
  { id: 'c1', title: '双星系统概述', page: 1, duration: '8 min', done: true },
  { id: 'c2', title: '万有引力与向心力分析', page: 3, duration: '12 min', done: true },
  { id: 'c3', title: '共同质心与轨道半径', page: 6, duration: '10 min', done: false, active: true },
  { id: 'c4', title: '周期与角速度推导', page: 9, duration: '11 min', done: false },
  { id: 'c5', title: '双星能量与稳定性', page: 12, duration: '9 min', done: false },
  { id: 'c6', title: '典型例题精讲', page: 15, duration: '15 min', done: false },
]

const displayChapters = computed(() =>
  props.sections.length
    ? props.sections
    : mockChapters,
)

const activeChapter = computed(() =>
  props.sections.length
    ? displayChapters.value.find(s => s.title === props.sectionTitle) || displayChapters.value[0]
    : mockChapters.find(c => c.active) || mockChapters[0],
)

const knowledgeTags = ['万有引力', '向心力', '共同质心', '角速度', '开普勒第三定律', '轨道半径']

const formulas = [
  {
    id: 'f1',
    label: '引力提供向心力',
    formula: 'Gm₁m₂ / r² = mᵢω²rᵢ',
    note: '两星受同一引力，角速度相同',
  },
  {
    id: 'f2',
    label: '质心条件',
    formula: 'm₁r₁ = m₂r₂',
    note: '两星到质心距离之比等于质量反比',
  },
  {
    id: 'f3',
    label: '轨道间距',
    formula: 'r = r₁ + r₂',
    note: 'r 为两星中心距离',
  },
  {
    id: 'f4',
    label: '周期与角速度',
    formula: 'T = 2π / ω',
    note: '两星公转周期完全相同',
  },
]

const keyPoints = [
  '双星系统中两颗恒星绕共同质心旋转，角速度和周期始终相等。',
  '两星间万有引力就是各自做圆周运动的向心力，方向指向对方。',
  '质量越大的星，轨道半径越小；质量越小的星，轨道半径越大。',
  '利用 m₁r₁ = m₂r₂ 可由轨道半径之比直接得到质量之比。',
]

const expandedFormula = ref(null)
const toggleFormula = (id) => {
  expandedFormula.value = expandedFormula.value === id ? null : id
}

const progressColor = computed(() => {
  if (props.progressPercent >= 80) return '#12b76a'
  if (props.progressPercent >= 40) return '#1677ff'
  return '#f79009'
})
const progressBg = computed(() => progressColor.value + '18')
</script>

<template>
  <div class="learn-root">

    <!-- ── 进度卡 ── -->
    <div class="main-card">
      <div class="main-card__top">
        <div class="main-card__info">
          <p class="main-card__label">当前章节</p>
          <h3 class="main-card__title">{{ activeChapter?.title || '双星系统概述' }}</h3>
        </div>
        <div class="pct-ring" :style="{ background: progressBg, color: progressColor }">
          <span class="pct-num">{{ progressPercent }}</span>
          <span class="pct-sym">%</span>
        </div>
      </div>

      <van-progress
        :percentage="progressPercent"
        :color="progressColor"
        stroke-width="5"
        :show-pivot="false"
        class="main-progress"
      />

      <div class="main-card__row">
        <span class="understanding-badge" :style="{ background: progressBg, color: progressColor }">
          <van-icon name="award-o" size="12" />
          {{ understandingLabel }}
        </span>
        <span class="chapter-progress-text">
          {{ mockChapters.filter(c => c.done).length }} / {{ mockChapters.length }} 章节完成
        </span>
      </div>

      <div class="divider" />

      <p class="section-label">本节知识点</p>
      <div class="tag-wrap">
        <span v-for="tag in knowledgeTags" :key="tag" class="knowledge-tag">{{ tag }}</span>
      </div>
    </div>

    <!-- ── 核心概念 ── -->
    <div class="content-card">
      <div class="content-card__head">
        <div class="content-card__icon" style="background: linear-gradient(135deg,#e8f0ff,#dbeafe)">
          <van-icon name="bulb-o" size="16" color="#1677ff" />
        </div>
        <span class="content-card__title">核心概念</span>
      </div>

      <!-- 简介 -->
      <p class="concept-intro">
        双星问题是万有引力定律的经典应用场景。两颗恒星在相互引力作用下，围绕它们共同的质心做圆周运动，轨道形状为圆形（近似）。
      </p>

      <div class="key-points">
        <div v-for="(pt, i) in keyPoints" :key="i" class="key-point-item">
          <span class="kp-bullet">{{ i + 1 }}</span>
          <p class="kp-text">{{ pt }}</p>
        </div>
      </div>
    </div>

    <!-- ── 关键公式 ── -->
    <div class="content-card">
      <div class="content-card__head">
        <div class="content-card__icon" style="background: linear-gradient(135deg,#fef3c7,#fde68a)">
          <van-icon name="records-o" size="16" color="#d97706" />
        </div>
        <span class="content-card__title">关键公式</span>
      </div>

      <div class="formula-list">
        <div
          v-for="f in formulas"
          :key="f.id"
          class="formula-item"
          :class="{ 'is-expanded': expandedFormula === f.id }"
          @click="toggleFormula(f.id)"
        >
          <div class="formula-item__top">
            <span class="formula-label">{{ f.label }}</span>
            <van-icon
              :name="expandedFormula === f.id ? 'arrow-up' : 'arrow-down'"
              size="12"
              color="#9aa3b2"
            />
          </div>
          <div class="formula-expr">{{ f.formula }}</div>
          <transition name="expand">
            <p v-if="expandedFormula === f.id" class="formula-note">{{ f.note }}</p>
          </transition>
        </div>
      </div>
    </div>

    <!-- ── 课程目录 ── -->
    <div class="content-card">
      <div class="content-card__head">
        <div class="content-card__icon" style="background: linear-gradient(135deg,#ecfdf5,#d1fae5)">
          <van-icon name="list-switch" size="16" color="#059669" />
        </div>
        <span class="content-card__title">课程目录</span>
        <span class="dir-count">{{ displayChapters.length }} 章节</span>
      </div>

      <div class="chapter-list">
        <button
          v-for="(item, idx) in displayChapters"
          :key="item.id || idx"
          class="chapter-item"
          :class="{
            'is-active': item.active || item.title === sectionTitle,
            'is-done': item.done,
          }"
          @click="emit('select-section', item)"
        >
          <div class="chapter-item__status">
            <van-icon v-if="item.done" name="checked" size="16" color="#12b76a" />
            <span v-else-if="item.active || item.title === sectionTitle" class="status-dot status-dot--active" />
            <span v-else class="status-dot" />
          </div>
          <div class="chapter-item__body">
            <span class="chapter-item__title">{{ item.title }}</span>
            <span class="chapter-item__meta">
              第 {{ item.page || idx + 1 }} 页
              <template v-if="item.duration"> · {{ item.duration }}</template>
            </span>
          </div>
          <span v-if="item.active || item.title === sectionTitle" class="chapter-item__badge">进行中</span>
          <van-icon v-else name="arrow" size="13" color="#d4d8e0" />
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.learn-root {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 0 28px;
  background: #f5f7fa;
}

/* ── 进度卡 ── */
.main-card {
  background: #fff;
  border-radius: 20px;
  padding: 18px 18px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.main-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.main-card__info { flex: 1; min-width: 0; }

.main-card__label {
  margin: 0 0 4px;
  font-size: 11px;
  color: #9aa3b2;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.main-card__title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #1a2035;
  line-height: 1.3;
}

.pct-ring {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 1px;
  padding-top: 2px;
}

.pct-num { font-size: 20px; font-weight: 900; line-height: 1; }
.pct-sym { font-size: 11px; font-weight: 700; }

.main-progress { margin-bottom: 10px; }

.main-card__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.understanding-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.chapter-progress-text {
  font-size: 11px;
  color: #9aa3b2;
  font-weight: 600;
}

.divider {
  height: 1px;
  background: #f0f2f5;
  margin: 14px 0 12px;
}

.section-label {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 700;
  color: #9aa3b2;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.tag-wrap { display: flex; flex-wrap: wrap; gap: 8px; }

.knowledge-tag {
  padding: 5px 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, #f0f5ff, #e8eeff);
  color: #3b5bdb;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid rgba(59, 91, 219, 0.1);
}

/* ── 通用内容卡 ── */
.content-card {
  background: #fff;
  border-radius: 20px;
  padding: 16px 16px 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.content-card__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.content-card__icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.content-card__title {
  font-size: 15px;
  font-weight: 800;
  color: #1a2035;
  flex: 1;
}

.dir-count {
  font-size: 12px;
  color: #9aa3b2;
  font-weight: 600;
}

/* ── 核心概念 ── */
.concept-intro {
  margin: 0 0 14px;
  font-size: 13.5px;
  line-height: 1.8;
  color: #4b5563;
}

.key-points {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.key-point-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.kp-bullet {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}

.kp-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.75;
  color: #374151;
}

/* ── 公式 ── */
.formula-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.formula-item {
  border: 1px solid #f0f2f5;
  border-radius: 14px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s;
  background: #fafbfc;
}

.formula-item.is-expanded {
  border-color: #bfdbfe;
  background: #f0f7ff;
}

.formula-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.formula-label {
  font-size: 12px;
  font-weight: 700;
  color: #6b7a90;
}

.formula-expr {
  font-size: 16px;
  font-weight: 800;
  color: #1a2035;
  letter-spacing: 0.04em;
  font-family: 'Courier New', monospace;
}

.formula-note {
  margin: 8px 0 0;
  font-size: 12px;
  color: #6b7a90;
  line-height: 1.6;
}

.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── 课程目录 ── */
.chapter-list {
  display: flex;
  flex-direction: column;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  border-top: 1px solid #f3f4f6;
  transition: opacity 0.15s;
}

.chapter-item:first-child { border-top: none; padding-top: 4px; }
.chapter-item:last-child { padding-bottom: 4px; }
.chapter-item:active { opacity: 0.6; }

.chapter-item__status {
  flex-shrink: 0;
  width: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e4e7ec;
  display: block;
}

.status-dot--active {
  background: #1677ff;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.18);
  animation: pulse 1.8s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.18); }
  50% { box-shadow: 0 0 0 6px rgba(22, 119, 255, 0.08); }
}

.chapter-item__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chapter-item__title {
  font-size: 14px;
  font-weight: 600;
  color: #1a2035;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chapter-item.is-active .chapter-item__title,
.chapter-item.is-done .chapter-item__title {
  color: #1677ff;
}

.chapter-item.is-done .chapter-item__title {
  color: #374151;
}

.chapter-item__meta {
  font-size: 11px;
  color: #9aa3b2;
}

.chapter-item__badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  color: #1677ff;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 999px;
}
</style>
