<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getGamePayload } from '@/api/qa'
import { listLessons } from '@/api/lesson'
import { useLessonStore } from '@/store/lessonStore'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()

const TIMER_SECONDS = 30
const LEVEL_NAMES = ['基础概念', '知识应用', '综合挑战']
const QUESTIONS_PER_LEVEL = 3

const baseCourses = [
  { id: 'course-1', name: '人工智能导论', isDemo: true },
  { id: 'course-2', name: '机器学习基础', isDemo: true },
  { id: 'course-3', name: '数据结构与算法', isDemo: true },
  { id: 'course-4', name: 'Python 程序设计', isDemo: true },
]
const backendCourses = ref([])
const courseOptions = computed(() => [...baseCourses, ...backendCourses.value])
const selectedCourseId = ref(route.query.courseId || baseCourses[0].id)

onMounted(async () => {
  try {
    const res = await listLessons('published')
    const lessons = res?.lessons || []
    backendCourses.value = lessons.map((l) => ({
      id: l.lessonId,
      name: l.lessonName || l.lessonId,
      isDemo: false,
    }))
  } catch { /* 后端不可用时仅显示演示课程 */ }
})

const phase = ref('map')
const currentLevel = ref(0)
const currentQuestion = ref(0)
const selectedOption = ref(-1)
const score = ref(0)
const combo = ref(0)
const maxCombo = ref(0)
const hearts = ref(3)
const timer = ref(TIMER_SECONDS)
const showHint = ref(false)
const answeredQuestions = ref([])
const levelResults = ref([])
const loading = ref(false)
const loadError = ref('')
let timerInterval = null

const levels = ref([
  { id: 'level-1', name: LEVEL_NAMES[0], questions: [] },
  { id: 'level-2', name: LEVEL_NAMES[1], questions: [] },
  { id: 'level-3', name: LEVEL_NAMES[2], questions: [] },
])

const level = computed(() => levels.value[currentLevel.value])
const question = computed(() => level.value?.questions?.[currentQuestion.value])
const answeredCount = computed(() => answeredQuestions.value.length)
const accuracy = computed(() => {
  if (!answeredCount.value) return 0
  return Math.round((answeredQuestions.value.filter(a => a.correct).length / answeredCount.value) * 100)
})

const isLevelUnlocked = (idx) => {
  if (idx === 0) return true
  const prev = levelResults.value.find(r => r.levelIdx === idx - 1)
  return prev && prev.stars >= 1
}
const getLevelStars = (idx) => {
  const r = levelResults.value.find(r => r.levelIdx === idx)
  return r ? r.stars : -1
}

const isRealCourse = computed(() => {
  const found = backendCourses.value.find(c => c.id === selectedCourseId.value)
  return !!found
})

function buildMockQuestions(levelIdx) {
  const banks = [
    [
      { q: '人工智能的核心目标是什么？', opts: ['让机器模拟人类智能', '加快计算速度', '替代所有人类工作', '存储大量数据'], correct: 0, kp: 'AI 定义' },
      { q: '以下哪项属于监督学习？', opts: ['图像分类', '客户聚类', '数据降维', '关联规则挖掘'], correct: 0, kp: '监督学习' },
      { q: '神经网络的灵感来源于？', opts: ['人脑神经元结构', '计算机体系结构', '生物进化论', '量子力学'], correct: 0, kp: '神经网络' },
    ],
    [
      { q: '过拟合现象意味着模型？', opts: ['在训练集表现好但泛化差', '训练集和测试集都差', '完全无法学习', '参数数量太少'], correct: 0, kp: '过拟合' },
      { q: '交叉验证的主要目的是？', opts: ['评估模型泛化能力', '加速模型训练', '增加数据量', '减少模型参数'], correct: 0, kp: '交叉验证' },
      { q: 'L1 正则化会产生什么效果？', opts: ['产生稀疏权重', '权重均匀分布', '增加模型容量', '完全消除过拟合'], correct: 0, kp: '正则化' },
    ],
    [
      { q: '动态规划的核心思想是？', opts: ['分解子问题并复用结果', '随机搜索解空间', '贪心选择局部最优', '穷举所有可能'], correct: 0, kp: '动态规划' },
      { q: '快速排序的平均时间复杂度是？', opts: ['O(n log n)', 'O(n²)', 'O(n)', 'O(log n)'], correct: 0, kp: '排序算法' },
      { q: '哈希表查找的平均时间复杂度是？', opts: ['O(1)', 'O(log n)', 'O(n)', 'O(n²)'], correct: 0, kp: '哈希表' },
    ],
  ]
  const bank = banks[levelIdx] || banks[0]
  return bank.map((item, i) => ({
    id: `l${levelIdx + 1}q${i + 1}`,
    question: item.q,
    knowledgePoint: item.kp,
    hint: '',
    baseScore: 20 + levelIdx * 10,
    correctIndex: item.correct,
    options: item.opts,
    explanation: '',
  }))
}

async function fetchQuestionsForLevel(levelIdx) {
  loading.value = true
  loadError.value = ''

  if (!isRealCourse.value) {
    await new Promise(r => setTimeout(r, 400))
    levels.value[levelIdx].questions = buildMockQuestions(levelIdx)
    loading.value = false
    return
  }

  const questions = []
  for (let i = 0; i < QUESTIONS_PER_LEVEL; i++) {
    try {
      const result = await getGamePayload({
        courseId: selectedCourseId.value,
        lessonId: lessonStore.lessonInfo.lessonId || selectedCourseId.value,
        sessionId: lessonStore.sessionInfo.sessionId,
        userId: lessonStore.platformContext.userId,
        question: `${LEVEL_NAMES[levelIdx]} 第${i + 1}题`,
        currentPage: (levelIdx * QUESTIONS_PER_LEVEL) + i + 1,
      })
      questions.push({
        id: `l${levelIdx + 1}q${i + 1}`,
        question: result.prompt,
        knowledgePoint: '',
        hint: '',
        baseScore: 20 + levelIdx * 10,
        correctIndex: result.correctIndex,
        options: result.choices,
        explanation: result.explanation,
      })
    } catch {
      questions.push(buildMockQuestions(levelIdx)[i] || {
        id: `l${levelIdx + 1}q${i + 1}`,
        question: '题目加载失败',
        knowledgePoint: '', hint: '', baseScore: 0, correctIndex: 0,
        options: ['重试', '跳过'], explanation: '',
      })
    }
  }
  levels.value[levelIdx].questions = questions
  loading.value = false
}

const startLevel = (idx) => {
  currentLevel.value = idx
  currentQuestion.value = 0
  selectedOption.value = -1
  showHint.value = false
  phase.value = 'playing'
  startTimer()
}

async function handleLevelSelect(idx) {
  if (!isLevelUnlocked(idx)) return
  if (levels.value[idx].questions.length === 0) {
    await fetchQuestionsForLevel(idx)
  }
  startLevel(idx)
}

watch(selectedCourseId, () => {
  levels.value.forEach((lv, i) => {
    lv.questions = []
    levelResults.value = []
    answeredQuestions.value = []
    phase.value = 'map'
    currentLevel.value = 0
    currentQuestion.value = 0
    score.value = 0
    combo.value = 0
    maxCombo.value = 0
    hearts.value = 3
  })
})

const startTimer = () => {
  clearInterval(timerInterval)
  timer.value = TIMER_SECONDS
  timerInterval = setInterval(() => {
    timer.value--
    if (timer.value <= 0) { clearInterval(timerInterval); handleTimeout() }
  }, 1000)
}
const stopTimer = () => clearInterval(timerInterval)

const handleTimeout = () => {
  selectedOption.value = -2
  combo.value = 0
  hearts.value = Math.max(0, hearts.value - 1)
  answeredQuestions.value.push({ levelIdx: currentLevel.value, qIdx: currentQuestion.value, correct: false, timeout: true })
  phase.value = 'feedback'
}

const selectAnswer = (idx) => {
  if (phase.value !== 'playing' || selectedOption.value >= 0) return
  stopTimer()
  selectedOption.value = idx
  const isCorrect = idx === question.value.correctIndex
  if (isCorrect) {
    score.value += question.value.baseScore + Math.floor(timer.value * 2) + combo.value * 5
    combo.value++
    if (combo.value > maxCombo.value) maxCombo.value = combo.value
  } else {
    combo.value = 0
    hearts.value = Math.max(0, hearts.value - 1)
  }
  answeredQuestions.value.push({ levelIdx: currentLevel.value, qIdx: currentQuestion.value, correct: isCorrect, timeout: false })
  phase.value = 'feedback'
}

const nextStep = () => {
  if (hearts.value <= 0) { phase.value = 'gameover'; return }
  if (currentQuestion.value < level.value.questions.length - 1) {
    currentQuestion.value++
    selectedOption.value = -1
    showHint.value = false
    phase.value = 'playing'
    startTimer()
  } else {
    const correct = answeredQuestions.value.filter(a => a.levelIdx === currentLevel.value && a.correct).length
    const total = level.value.questions.length
    levelResults.value.push({
      levelIdx: currentLevel.value, correct, total,
      stars: correct === total ? 3 : correct >= total * 0.66 ? 2 : correct >= 1 ? 1 : 0,
    })
    phase.value = currentLevel.value < levels.value.length - 1 ? 'level-clear' : 'gameover'
  }
}

async function continueToNextLevel() {
  const next = currentLevel.value + 1
  if (levels.value[next].questions.length === 0) {
    await fetchQuestionsForLevel(next)
  }
  startLevel(next)
}
const restartGame = () => {
  levels.value.forEach((lv) => { lv.questions = [] })
  score.value = 0; combo.value = 0; maxCombo.value = 0; hearts.value = 3
  answeredQuestions.value = []; levelResults.value = []; phase.value = 'map'
}

onBeforeUnmount(() => stopTimer())

const timerPct = computed(() => (timer.value / TIMER_SECONDS) * 100)
const timerColor = computed(() => timer.value > 20 ? '#10b981' : timer.value > 10 ? '#f59e0b' : '#ef4444')
onBeforeUnmount(() => stopTimer())
</script>

<template>
  <div class="game-page">
    <!-- Hero -->
    <section class="game-hero">
      <div class="hero-copy">
        <p class="hero-eyebrow">PRACTICE CHALLENGE</p>
        <h1 class="hero-title">练习闯关</h1>
        <p class="hero-subtitle">根据课程内容智能生成阶梯式挑战题库，检验知识掌握程度</p>
      </div>
      <div class="hero-right">
        <div class="hero-course-picker">
          <span class="picker-label">选择课程</span>
          <div class="course-select-wrap">
            <svg class="cs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <select v-model="selectedCourseId" class="course-select">
              <optgroup label="演示课程">
                <option v-for="c in baseCourses" :key="c.id" :value="c.id">{{ c.name }}</option>
              </optgroup>
              <optgroup v-if="backendCourses.length" label="我的课程">
                <option v-for="c in backendCourses" :key="c.id" :value="c.id">{{ c.name }}</option>
              </optgroup>
            </select>
            <svg class="cs-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>
        <div class="hero-stats">
          <div class="stat-hearts">
            <span v-for="i in 3" :key="i" :class="['heart', { lost: i > hearts }]">
              <svg width="14" height="14" viewBox="0 0 24 24" :fill="i <= hearts ? '#f43f5e' : '#e2e8f0'" stroke="none">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
            </span>
          </div>
          <div class="stat-score">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="#f59e0b" stroke="none">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            {{ score }}
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ MAP ═══ -->
    <div v-if="phase === 'map'" class="phase-map">
      <div class="level-grid">
        <button v-for="(lv, idx) in levels" :key="lv.id" :class="['level-card', {
          locked: !isLevelUnlocked(idx),
          cleared: getLevelStars(idx) >= 0,
          current: isLevelUnlocked(idx) && getLevelStars(idx) < 0,
        }]" :disabled="!isLevelUnlocked(idx) || loading" @click="handleLevelSelect(idx)">
          <div class="lc-top">
            <span class="lc-icon">{{ lv.icon }}</span>
            <span v-if="!isLevelUnlocked(idx)" class="lc-lock">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </span>
            <span v-else-if="getLevelStars(idx) >= 0" class="lc-check">✓</span>
          </div>
          <div class="lc-name">{{ lv.name }}</div>
          <div class="lc-desc">{{ lv.desc }}</div>
          <div v-if="getLevelStars(idx) >= 0" class="lc-stars">
            <span v-for="s in 3" :key="s" :class="['lc-star', { filled: s <= getLevelStars(idx) }]">★</span>
          </div>
          <div v-else-if="isLevelUnlocked(idx)" class="lc-cta">开始挑战</div>
          <div class="lc-badge">第{{ idx + 1 }}关</div>
        </button>
      </div>
    </div>

    <!-- ═══ PLAYING / FEEDBACK ═══ -->
    <div v-else-if="phase === 'playing' || phase === 'feedback'" class="phase-play">
      <div class="play-container">
        <!-- Progress bar -->
        <div class="progress-bar-wrap">
          <div class="pb-level">{{ level.icon }} {{ level.name }}</div>
          <div class="pb-track">
            <div v-for="(q, qi) in level.questions" :key="q.id" :class="['pb-segment', {
              current: qi === currentQuestion && phase === 'playing',
              correct: answeredQuestions.some(a => a.levelIdx === currentLevel && a.qIdx === qi && a.correct),
              wrong: answeredQuestions.some(a => a.levelIdx === currentLevel && a.qIdx === qi && !a.correct),
            }]">
              <span class="pb-num">{{ qi + 1 }}</span>
            </div>
          </div>
        </div>

        <div class="question-layout">
          <!-- Timer + Question -->
          <div class="q-main">
            <div v-if="phase === 'playing'" class="timer-bar">
              <div class="timer-fill" :style="{ width: timerPct + '%', background: timerColor }" />
              <span class="timer-label" :style="{ color: timerColor }">{{ timer }}s</span>
            </div>

            <div class="q-card">
              <span class="q-kp">{{ question.knowledgePoint }}</span>
              <h2 class="q-text">{{ question.question }}</h2>

              <div class="options-list">
                <button v-for="(opt, oi) in question.options" :key="oi" :class="['opt-btn', {
                  selected: selectedOption === oi && phase === 'playing',
                  correct: phase === 'feedback' && oi === question.correctIndex,
                  wrong: phase === 'feedback' && selectedOption === oi && oi !== question.correctIndex,
                  dimmed: phase === 'feedback' && oi !== question.correctIndex && oi !== selectedOption,
                }]" :disabled="phase === 'feedback'" @click="selectAnswer(oi)">
                  <span class="opt-key">{{ ['A', 'B', 'C', 'D'][oi] }}</span>
                  <span class="opt-label">{{ opt }}</span>
                  <svg v-if="phase === 'feedback' && oi === question.correctIndex" class="opt-result-icon correct"
                    width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <svg v-if="phase === 'feedback' && selectedOption === oi && oi !== question.correctIndex"
                    class="opt-result-icon wrong" width="18" height="18" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" stroke-width="3">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>

              <button v-if="phase === 'playing' && !showHint" class="hint-toggle" @click="showHint = true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                查看提示
              </button>
              <div v-if="showHint" class="hint-box">💡 {{ question.hint }}</div>
            </div>

            <!-- Feedback -->
            <div v-if="phase === 'feedback'" class="feedback-bar">
              <div :class="['fb-content', selectedOption === question.correctIndex ? 'fb-correct' : 'fb-wrong']">
                <div class="fb-left">
                  <span class="fb-emoji">{{ selectedOption === question.correctIndex ? '🎉' : (selectedOption === -2 ?
                    '⏰' : '💡') }}</span>
                  <div>
                    <div class="fb-title">{{ selectedOption === question.correctIndex ? '回答正确！' : (selectedOption === -2
                      ? '时间到！' : '答错了，没关系') }}</div>
                    <div v-if="selectedOption === question.correctIndex && combo > 1" class="fb-detail">连续答对 {{ combo }}
                      题，加分！</div>
                    <div v-if="selectedOption !== question.correctIndex" class="fb-detail">正确答案：{{
                      question.options[question.correctIndex] }}</div>
                  </div>
                </div>
                <button class="fb-next" @click="nextStep">
                  {{ currentQuestion < level.questions.length - 1 ? '下一题' : '查看结果' }} <svg width="14" height="14"
                    viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <path d="M5 12h14M12 5l7 7-7 7" /></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ LEVEL CLEAR ═══ -->
    <div v-else-if="phase === 'level-clear'" class="phase-result">
      <div class="result-card">
        <div class="rc-icon">{{ level.icon }}</div>
        <h2 class="rc-title">{{ level.name }} 通关！</h2>
        <div class="rc-stars">
          <span v-for="s in 3" :key="s"
            :class="['rc-star', { filled: s <= (levelResults[levelResults.length - 1]?.stars || 0) }]"
            :style="{ animationDelay: `${s * 0.15}s` }">★</span>
        </div>
        <div class="rc-stats">
          <div class="rcs"><span class="rcs-val">{{ levelResults[levelResults.length - 1]?.correct }}/{{
            levelResults[levelResults.length - 1]?.total }}</span><span class="rcs-label">正确</span></div>
          <div class="rcs"><span class="rcs-val">{{ score }}</span><span class="rcs-label">得分</span></div>
          <div class="rcs"><span class="rcs-val">{{ maxCombo }}x</span><span class="rcs-label">最大连击</span></div>
        </div>
        <button class="rc-continue" @click="continueToNextLevel">
          下一关：{{ levels[currentLevel + 1]?.name }}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>

    <!-- ═══ GAME OVER ═══ -->
    <div v-else-if="phase === 'gameover'" class="phase-result">
      <div class="result-card result-card-final">
        <div class="rc-icon">{{ hearts > 0 ? '🏆' : '💪' }}</div>
        <h2 class="rc-title">{{ hearts > 0 ? '闯关完成！' : '挑战结束' }}</h2>
        <p class="rc-sub">{{ hearts > 0 ? '恭喜你完成了所有关卡的挑战' : '没关系，复习后再来挑战一次吧' }}</p>

        <div class="final-summary">
          <div class="fs-item"><span class="fs-val">{{ score }}</span><span class="fs-label">总得分</span></div>
          <div class="fs-divider" />
          <div class="fs-item"><span class="fs-val">{{ accuracy }}%</span><span class="fs-label">正确率</span></div>
          <div class="fs-divider" />
          <div class="fs-item"><span class="fs-val">{{ maxCombo }}x</span><span class="fs-label">最大连击</span></div>
        </div>

        <div class="final-levels">
          <div v-for="result in levelResults" :key="result.levelIdx" class="fl-row">
            <span class="fl-icon">{{ levels[result.levelIdx].icon }}</span>
            <span class="fl-name">{{ levels[result.levelIdx].name }}</span>
            <span class="fl-score">{{ result.correct }}/{{ result.total }}</span>
            <span class="fl-stars">
              <span v-for="s in 3" :key="s" :class="['fl-star', { filled: s <= result.stars }]">★</span>
            </span>
          </div>
        </div>

        <div class="final-actions">
          <button class="fa-restart" @click="restartGame">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 .49-3.56" />
            </svg>
            重新挑战
          </button>
          <button class="fa-back" @click="backToLesson">
            返回继续学习
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap');

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.game-page {
  min-height: 100vh;
  font-family: 'Sora', sans-serif;
}

/* ── Hero ── */
.game-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  padding: 32px 36px;
  border-radius: 8px;
  margin-bottom: 24px;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(255, 255, 255, 0.92) 46%, rgba(14, 165, 233, 0.16)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px);
  background-size: auto, 22px 22px, 22px 22px;
  border: 1px solid rgba(20, 184, 166, 0.16);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
}

.hero-eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 800;
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

.hero-right {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}

.hero-course-picker {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.picker-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
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

.cs-icon { color: #14b8a6; flex-shrink: 0; }

.course-select { all: unset; cursor: pointer; font-size: 13px; font-weight: 600; color: #0f172a; min-width: 140px; appearance: none; }
.cs-arrow { color: #14b8a6; flex-shrink: 0; }

.hero-stats { display: flex; align-items: center; gap: 12px; }

.stat-hearts { display: flex; gap: 4px; }
.heart { transition: all 0.3s; display: flex; }
.heart.lost { opacity: 0.25; transform: scale(0.85); }

.stat-score {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 999px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  font-size: 14px;
  font-weight: 700;
  color: #b45309;
}

/* ── MAP ─────────────────────────────────────────────────── */
.phase-map {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}

.level-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.level-card {
  all: unset;
  cursor: pointer;
  position: relative;
  padding: 24px;
  border-radius: 16px;
  background: #fff;
  border: 1.5px solid #e5ecf7;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
  transition: all 0.22s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 6px;
}

.level-card:hover:not(:disabled) {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(37, 99, 235, 0.1);
  border-color: #bfdbfe;
}

.level-card.locked {
  opacity: 0.45;
  cursor: not-allowed;
}

.level-card.cleared {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.level-card.current {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.lc-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.lc-icon {
  font-size: 32px;
}

.lc-lock {
  color: #94a3b8;
}

.lc-check {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #10b981;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lc-name {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.lc-desc {
  font-size: 12px;
  color: #94a3b8;
}

.lc-stars {
  display: flex;
  gap: 2px;
  margin-top: 4px;
}

.lc-star {
  font-size: 18px;
  color: #e2e8f0;
}

.lc-star.filled {
  color: #f59e0b;
}

.lc-cta {
  margin-top: 8px;
  padding: 6px 16px;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.lc-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
}

/* ── PLAYING ─────────────────────────────────────────────── */
.phase-play {
  min-height: calc(100vh - 60px);
  display: flex;
  justify-content: center;
  padding: 24px 24px 80px;
}

.play-container {
  width: 100%;
  max-width: 640px;
}

.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.pb-level {
  font-size: 13px;
  font-weight: 700;
  color: #1e3a5f;
  white-space: nowrap;
}

.pb-track {
  display: flex;
  gap: 6px;
  flex: 1;
}

.pb-segment {
  flex: 1;
  height: 32px;
  border-radius: 8px;
  background: #fff;
  border: 1.5px solid #e5ecf7;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.pb-num {
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
}

.pb-segment.current {
  border-color: #3b82f6;
  background: #eff6ff;
}

.pb-segment.current .pb-num {
  color: #2563eb;
}

.pb-segment.correct {
  border-color: #86efac;
  background: #f0fdf4;
}

.pb-segment.correct .pb-num {
  color: #16a34a;
}

.pb-segment.wrong {
  border-color: #fca5a5;
  background: #fef2f2;
}

.pb-segment.wrong .pb-num {
  color: #dc2626;
}

/* Timer */
.timer-bar {
  position: relative;
  height: 6px;
  border-radius: 999px;
  background: #f1f5f9;
  margin-bottom: 16px;
  overflow: hidden;
}

.timer-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 1s linear, background 0.3s;
}

.timer-label {
  position: absolute;
  right: 0;
  top: -22px;
  font-size: 13px;
  font-weight: 700;
}

/* Question card */
.q-card {
  padding: 32px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid #e5ecf7;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
}

.q-kp {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 16px;
}

.q-text {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.65;
  margin-bottom: 24px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.opt-btn {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1.5px solid #e5ecf7;
  font-size: 14px;
  color: #334155;
  transition: all 0.18s;
}

.opt-btn:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #93c5fd;
  transform: translateX(3px);
}

.opt-btn.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.opt-btn.correct {
  border-color: #10b981;
  background: #f0fdf4;
  color: #065f46;
}

.opt-btn.wrong {
  border-color: #ef4444;
  background: #fef2f2;
  color: #991b1b;
}

.opt-btn.dimmed {
  opacity: 0.4;
}

.opt-key {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: #e5ecf7;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  flex-shrink: 0;
}

.opt-btn.correct .opt-key {
  background: #d1fae5;
  color: #065f46;
}

.opt-btn.wrong .opt-key {
  background: #fee2e2;
  color: #991b1b;
}

.opt-btn:hover:not(:disabled) .opt-key {
  background: #dbeafe;
  color: #1e40af;
}

.opt-label {
  flex: 1;
  line-height: 1.5;
}

.opt-result-icon {
  flex-shrink: 0;
}

.opt-result-icon.correct {
  color: #10b981;
}

.opt-result-icon.wrong {
  color: #ef4444;
}

/* Hint */
.hint-toggle {
  all: unset;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  padding: 7px 14px;
  border-radius: 8px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  color: #b45309;
  font-size: 12px;
  font-weight: 600;
  transition: background 0.15s;
}

.hint-toggle:hover {
  background: #fef3c7;
}

.hint-box {
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: 10px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  color: #92400e;
  font-size: 13px;
  line-height: 1.6;
}

/* Feedback */
.feedback-bar {
  margin-top: 16px;
}

.fb-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-radius: 14px;
  gap: 16px;
}

.fb-correct {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.fb-wrong {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.fb-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fb-emoji {
  font-size: 28px;
  flex-shrink: 0;
}

.fb-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.fb-detail {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.fb-next {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 10px;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  transition: all 0.18s;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.fb-next:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.3);
}

/* ── RESULT SCREENS ──────────────────────────────────────── */
.phase-result {
  min-height: calc(100vh - 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.result-card {
  text-align: center;
  width: 100%;
  max-width: 440px;
  padding: 44px 36px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid #e5ecf7;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.06);
}

.rc-icon {
  font-size: 52px;
  margin-bottom: 12px;
}

.rc-title {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 6px;
}

.rc-sub {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 28px;
}

.rc-stars {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 28px;
}

.rc-star {
  font-size: 36px;
  color: #e2e8f0;
  animation: star-bounce 0.4s ease both;
}

.rc-star.filled {
  color: #f59e0b;
  text-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
}

@keyframes star-bounce {
  0% {
    transform: scale(0) rotate(-20deg);
    opacity: 0;
  }

  60% {
    transform: scale(1.2) rotate(5deg);
  }

  100% {
    transform: scale(1) rotate(0);
    opacity: 1;
  }
}

.rc-stats {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 28px;
  padding: 16px;
  border-radius: 12px;
  background: #f8fafc;
}

.rcs {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rcs-val {
  font-size: 22px;
  font-weight: 800;
  color: #2563eb;
}

.rcs-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
}

.rc-continue {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
  transition: all 0.18s;
}

.rc-continue:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}

/* Final game over card */
.final-summary {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
  padding: 20px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
}

.fs-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fs-val {
  font-size: 26px;
  font-weight: 800;
  color: #2563eb;
}

.fs-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
}

.fs-divider {
  width: 1px;
  height: 36px;
  background: #e5e7eb;
}

.final-levels {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 24px;
  text-align: left;
}

.fl-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f8fafc;
}

.fl-icon {
  font-size: 18px;
}

.fl-name {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.fl-score {
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
}

.fl-stars {
  display: flex;
  gap: 2px;
  font-size: 14px;
}

.fl-star {
  color: #e2e8f0;
}

.fl-star.filled {
  color: #f59e0b;
}

.final-actions {
  display: flex;
  gap: 10px;
}

.fa-restart,
.fa-back {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  padding: 12px;
  border-radius: 12px;
  font-size: 13.5px;
  font-weight: 700;
  transition: all 0.18s;
}

.fa-restart {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e5ecf7;
}

.fa-restart:hover {
  background: #e5ecf7;
  color: #1e293b;
}

.fa-back {
  background: #2563eb;
  color: #fff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.fa-back:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 640px) {
  .game-topbar {
    padding: 0 16px;
  }

  .topbar-info {
    display: none;
  }

  .topbar-divider {
    display: none;
  }

  .level-grid {
    grid-template-columns: 1fr;
  }

  .q-card {
    padding: 24px 20px;
  }

  .q-text {
    font-size: 15px;
  }

  .opt-btn {
    padding: 12px 14px;
    font-size: 13px;
  }

  .fb-content {
    flex-direction: column;
    align-items: stretch;
  }

  .fb-next {
    justify-content: center;
  }

  .final-actions {
    flex-direction: column;
  }
}
</style>
