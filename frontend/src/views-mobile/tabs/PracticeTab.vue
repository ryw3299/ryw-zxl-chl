<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { buildGameLevels } from '@/utils/mockGameQuiz'

const props = defineProps({
  sectionTitle: { type: String, default: '双星问题' },
})

const levels = computed(() => buildGameLevels({ sectionTitle: props.sectionTitle }))

const TIMER_SECONDS = 30

const phase = ref('map')         // map | playing | feedback | level-clear | gameover
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
let timerInterval = null

const level = computed(() => levels.value[currentLevel.value])
const question = computed(() => level.value?.questions?.[currentQuestion.value])
const answeredCount = computed(() => answeredQuestions.value.length)
const accuracy = computed(() => {
  if (!answeredCount.value) return 0
  return Math.round((answeredQuestions.value.filter(a => a.correct).length / answeredCount.value) * 100)
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

const startLevel = (idx) => {
  currentLevel.value = idx
  currentQuestion.value = 0
  selectedOption.value = -1
  showHint.value = false
  phase.value = 'playing'
  startTimer()
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
      stars: correct === total ? 3 : correct >= Math.ceil(total * 0.66) ? 2 : correct >= 1 ? 1 : 0,
    })
    phase.value = currentLevel.value < levels.value.length - 1 ? 'level-clear' : 'gameover'
  }
}

const continueToNextLevel = () => startLevel(currentLevel.value + 1)
const restartGame = () => {
  score.value = 0; combo.value = 0; maxCombo.value = 0; hearts.value = 3
  answeredQuestions.value = []; levelResults.value = []; phase.value = 'map'
}

const timerPct = computed(() => (timer.value / TIMER_SECONDS) * 100)
const timerColor = computed(() => timer.value > 20 ? '#10b981' : timer.value > 10 ? '#f59e0b' : '#ef4444')
const isLevelUnlocked = (idx) => idx === 0 || levelResults.value.some(r => r.levelIdx === idx - 1)
const getLevelStars = (idx) => levelResults.value.find(r => r.levelIdx === idx)?.stars ?? -1

onBeforeUnmount(() => stopTimer())
</script>

<template>
  <div class="gm-root">

    <!-- ══ 顶部状态栏 ══ -->
    <div v-if="phase !== 'map'" class="gm-topbar">
      <button class="gm-back" @click="phase = 'map'; stopTimer()">
        <van-icon name="arrow-left" size="15" />
      </button>
      <div class="gm-hearts">
        <span v-for="i in 3" :key="i" class="heart-icon" :class="{ lost: i > hearts }">
          <svg width="14" height="14" viewBox="0 0 24 24" :fill="i <= hearts ? '#f43f5e' : '#e2e8f0'" stroke="none">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
        </span>
      </div>
      <div class="gm-score-area">
        <span class="gm-score">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="#f59e0b" stroke="none">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
          {{ score }}
        </span>
        <transition name="combo-pop">
          <span v-if="combo > 1" class="gm-combo">{{ combo }}x</span>
        </transition>
      </div>
    </div>

    <!-- ══ MAP 关卡地图 ══ -->
    <div v-if="phase === 'map'" class="phase-map">
      <div class="map-hero">
        <div class="map-hero-icon">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
            <path d="M12 3l7 4v5c0 5-3.5 8.5-7 9-3.5-.5-7-4-7-9V7l7-4z" />
            <path d="M9.5 12.5l1.7 1.7 3.3-4.2" />
          </svg>
        </div>
        <div>
          <h1 class="map-title">练习闯关</h1>
          <p class="map-sub">「{{ sectionTitle }}」专项挑战，检验掌握程度</p>
        </div>
      </div>

      <div class="level-list">
        <button
          v-for="(lv, idx) in levels"
          :key="lv.id"
          class="level-card"
          :class="{ locked: !isLevelUnlocked(idx), cleared: getLevelStars(idx) >= 0, current: isLevelUnlocked(idx) && getLevelStars(idx) < 0 }"
          :disabled="!isLevelUnlocked(idx)"
          @click="startLevel(idx)"
        >
          <div class="lc-left">
            <div class="lc-badge">第{{ idx + 1 }}关</div>
            <span class="lc-icon">{{ lv.icon }}</span>
          </div>
          <div class="lc-body">
            <div class="lc-name">{{ lv.name }}</div>
            <div class="lc-desc">{{ lv.desc }}</div>
            <div v-if="getLevelStars(idx) >= 0" class="lc-stars">
              <span v-for="s in 3" :key="s" :class="['lc-star', { filled: s <= getLevelStars(idx) }]">★</span>
            </div>
          </div>
          <div class="lc-right">
            <van-icon v-if="!isLevelUnlocked(idx)" name="lock" size="18" color="#c5cdd8" />
            <span v-else-if="getLevelStars(idx) >= 0" class="lc-check">✓</span>
            <span v-else class="lc-cta">开始</span>
          </div>
        </button>
      </div>
    </div>

    <!-- ══ PLAYING / FEEDBACK ══ -->
    <div v-else-if="phase === 'playing' || phase === 'feedback'" class="phase-play">

      <!-- 进度段 -->
      <div class="pb-wrap">
        <span class="pb-level-name">{{ level.icon }} {{ level.name }}</span>
        <div class="pb-track">
          <div
            v-for="(q, qi) in level.questions"
            :key="q.id"
            :class="['pb-seg', {
              current: qi === currentQuestion && phase === 'playing',
              correct: answeredQuestions.some(a => a.levelIdx === currentLevel && a.qIdx === qi && a.correct),
              wrong: answeredQuestions.some(a => a.levelIdx === currentLevel && a.qIdx === qi && !a.correct),
            }]"
          >{{ qi + 1 }}</div>
        </div>
      </div>

      <!-- 计时条 -->
      <div v-if="phase === 'playing'" class="timer-bar">
        <div class="timer-fill" :style="{ width: timerPct + '%', background: timerColor }" />
        <span class="timer-num" :style="{ color: timerColor }">{{ timer }}s</span>
      </div>

      <!-- 题目卡 -->
      <div class="q-card">
        <span class="q-kp">{{ question.knowledgePoint }}</span>
        <p class="q-text">{{ question.question }}</p>

        <div class="opts-list">
          <button
            v-for="(opt, oi) in question.options"
            :key="oi"
            class="opt-btn"
            :class="{
              selected: selectedOption === oi && phase === 'playing',
              correct: phase === 'feedback' && oi === question.correctIndex,
              wrong: phase === 'feedback' && selectedOption === oi && oi !== question.correctIndex,
              dimmed: phase === 'feedback' && oi !== question.correctIndex && oi !== selectedOption,
            }"
            :disabled="phase === 'feedback'"
            @click="selectAnswer(oi)"
          >
            <span class="opt-key">{{ ['A','B','C','D'][oi] }}</span>
            <span class="opt-label">{{ opt }}</span>
            <svg v-if="phase === 'feedback' && oi === question.correctIndex" class="opt-icon opt-icon--ok" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <svg v-if="phase === 'feedback' && selectedOption === oi && oi !== question.correctIndex" class="opt-icon opt-icon--ng" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <button v-if="phase === 'playing' && !showHint" class="hint-toggle" @click="showHint = true">
          <van-icon name="question-o" size="13" />
          查看提示
        </button>
        <div v-if="showHint" class="hint-box">💡 {{ question.hint }}</div>
      </div>

      <!-- 反馈条 -->
      <div v-if="phase === 'feedback'" class="feedback-bar" :class="selectedOption === question.correctIndex ? 'fb-correct' : 'fb-wrong'">
        <div class="fb-left">
          <span class="fb-emoji">{{ selectedOption === question.correctIndex ? '🎉' : (selectedOption === -2 ? '⏰' : '💡') }}</span>
          <div>
            <div class="fb-title">{{ selectedOption === question.correctIndex ? '回答正确！' : (selectedOption === -2 ? '时间到！' : '答错了，没关系') }}</div>
            <div v-if="selectedOption === question.correctIndex && combo > 1" class="fb-detail">连续答对 {{ combo }} 题，加分！</div>
            <div v-if="selectedOption !== question.correctIndex" class="fb-detail">正确答案：{{ question.options[question.correctIndex] }}</div>
          </div>
        </div>
        <button class="fb-next" @click="nextStep">
          {{ currentQuestion < level.questions.length - 1 ? '下一题' : '查看结果' }}
          <van-icon name="arrow" size="13" />
        </button>
      </div>
    </div>

    <!-- ══ LEVEL CLEAR ══ -->
    <div v-else-if="phase === 'level-clear'" class="phase-result">
      <div class="result-card">
        <div class="rc-icon">{{ level.icon }}</div>
        <h2 class="rc-title">{{ level.name }} 通关！</h2>
        <div class="rc-stars">
          <span v-for="s in 3" :key="s" :class="['rc-star', { filled: s <= (levelResults[levelResults.length - 1]?.stars || 0) }]" :style="{ animationDelay: `${s * 0.15}s` }">★</span>
        </div>
        <div class="rc-stats">
          <div class="rcs"><span class="rcs-val">{{ levelResults[levelResults.length - 1]?.correct }}/{{ levelResults[levelResults.length - 1]?.total }}</span><span class="rcs-label">正确</span></div>
          <div class="rcs"><span class="rcs-val">{{ score }}</span><span class="rcs-label">得分</span></div>
          <div class="rcs"><span class="rcs-val">{{ maxCombo }}x</span><span class="rcs-label">最大连击</span></div>
        </div>
        <button class="rc-continue" @click="continueToNextLevel">
          下一关：{{ levels[currentLevel + 1]?.name }}
          <van-icon name="arrow" size="14" />
        </button>
      </div>
    </div>

    <!-- ══ GAME OVER ══ -->
    <div v-else-if="phase === 'gameover'" class="phase-result">
      <div class="result-card">
        <div class="rc-icon">{{ hearts > 0 ? '🏆' : '💪' }}</div>
        <h2 class="rc-title">{{ hearts > 0 ? '闯关完成！' : '挑战结束' }}</h2>
        <p class="rc-sub">{{ hearts > 0 ? '恭喜你完成了所有关卡！' : '复习后再来挑战一次吧' }}</p>

        <div class="final-summary">
          <div class="fs-item"><span class="fs-val">{{ score }}</span><span class="fs-label">总得分</span></div>
          <div class="fs-div" />
          <div class="fs-item"><span class="fs-val">{{ accuracy }}%</span><span class="fs-label">正确率</span></div>
          <div class="fs-div" />
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
            <van-icon name="replay" size="14" />
            重新挑战
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.gm-root {
  padding: 12px 14px 28px;
  min-height: 480px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f5f7fa;
}

/* ── 顶栏 ── */
.gm-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  border-radius: 16px;
  padding: 10px 14px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.gm-back {
  width: 32px; height: 32px; border: none; background: #f5f7fa;
  border-radius: 9px; display: flex; align-items: center; justify-content: center;
  color: #1a2035; cursor: pointer; flex-shrink: 0;
}
.gm-hearts { display: flex; gap: 4px; flex: 1; }
.heart-icon { display: flex; align-items: center; }
.heart-icon.lost { opacity: 0.3; }
.gm-score-area { display: flex; align-items: center; gap: 8px; }
.gm-score { display: flex; align-items: center; gap: 4px; font-size: 15px; font-weight: 800; color: #f59e0b; }
.gm-combo { font-size: 12px; font-weight: 800; color: #fff; background: linear-gradient(135deg, #f59e0b, #ef4444); padding: 2px 8px; border-radius: 999px; }
.combo-pop-enter-active, .combo-pop-leave-active { transition: all 0.2s; }
.combo-pop-enter-from, .combo-pop-leave-to { opacity: 0; transform: scale(0.6); }

/* ── MAP ── */
.phase-map { display: flex; flex-direction: column; gap: 12px; }
.map-hero {
  display: flex; align-items: center; gap: 14px;
  background: linear-gradient(135deg, #1677ff, #2a8aff 60%, #46aaff);
  border-radius: 20px; padding: 18px 20px;
  box-shadow: 0 6px 22px rgba(22,119,255,0.28);
}
.map-hero-icon {
  width: 52px; height: 52px; flex-shrink: 0; border-radius: 16px;
  background: rgba(255,255,255,0.18); display: flex; align-items: center; justify-content: center;
}
.map-title { margin: 0; font-size: 20px; font-weight: 800; color: #fff; }
.map-sub { margin: 4px 0 0; font-size: 12px; color: rgba(255,255,255,0.75); line-height: 1.5; }

.level-list { display: flex; flex-direction: column; gap: 10px; }
.level-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border-radius: 18px; padding: 14px 16px;
  border: 1.5px solid #e4e8ef;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  cursor: pointer; text-align: left; transition: all 0.15s;
}
.level-card:active { transform: scale(0.98); }
.level-card.locked { opacity: 0.5; cursor: not-allowed; }
.level-card.current { border-color: #1677ff; box-shadow: 0 4px 16px rgba(22,119,255,0.14); }
.level-card.cleared { border-color: #10b981; }

.lc-left { display: flex; flex-direction: column; align-items: center; gap: 4px; flex-shrink: 0; }
.lc-badge { font-size: 9px; font-weight: 800; color: #9aa3b2; letter-spacing: 0.05em; }
.lc-icon { font-size: 26px; }
.lc-body { flex: 1; min-width: 0; }
.lc-name { font-size: 15px; font-weight: 800; color: #1a2035; }
.lc-desc { font-size: 12px; color: #9aa3b2; margin-top: 3px; }
.lc-stars { display: flex; gap: 2px; margin-top: 6px; }
.lc-star { font-size: 14px; color: #e2e8f0; }
.lc-star.filled { color: #f59e0b; }
.lc-right { flex-shrink: 0; }
.lc-check { font-size: 18px; font-weight: 800; color: #10b981; }
.lc-cta { font-size: 13px; font-weight: 700; color: #1677ff; background: #eef4ff; padding: 5px 12px; border-radius: 8px; }

/* ── 进度段 ── */
.pb-wrap { display: flex; align-items: center; gap: 10px; }
.pb-level-name { font-size: 13px; font-weight: 700; color: #6b7a90; flex-shrink: 0; }
.pb-track { display: flex; gap: 5px; flex: 1; }
.pb-seg {
  flex: 1; height: 28px; border-radius: 8px;
  background: #e4e8ef; color: #9aa3b2;
  font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.2s;
}
.pb-seg.current { background: #1677ff; color: #fff; }
.pb-seg.correct { background: #10b981; color: #fff; }
.pb-seg.wrong   { background: #f43f5e; color: #fff; }

/* ── 计时条 ── */
.timer-bar {
  position: relative; height: 8px;
  background: #e4e8ef; border-radius: 999px; overflow: visible;
}
.timer-fill { height: 100%; border-radius: 999px; transition: width 0.9s linear, background 0.3s; }
.timer-num {
  position: absolute; right: 0; top: 50%; transform: translate(0, -50%);
  font-size: 11px; font-weight: 800; white-space: nowrap; padding-right: 2px;
  background: #f5f7fa; padding: 0 4px;
}

/* ── 题目卡 ── */
.q-card { background: #fff; border-radius: 18px; padding: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
.q-kp {
  display: inline-block; padding: 2px 10px; border-radius: 6px;
  background: #eef4ff; color: #1677ff;
  font-size: 11px; font-weight: 700; margin-bottom: 10px;
}
.q-text { margin: 0 0 14px; font-size: 15px; font-weight: 700; line-height: 1.65; color: #1a2035; }

.opts-list { display: flex; flex-direction: column; gap: 9px; }
.opt-btn {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 12px 14px; border-radius: 13px;
  border: 1.5px solid #e4e8ef; background: #fff;
  text-align: left; cursor: pointer; transition: all 0.15s;
}
.opt-btn:active { transform: scale(0.98); }
.opt-key {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: 7px;
  background: #f0f4f8; color: #6b7a90;
  font-size: 12px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}
.opt-label { flex: 1; font-size: 13px; line-height: 1.55; color: #3d4a5f; }
.opt-icon { flex-shrink: 0; }
.opt-icon--ok  { color: #10b981; }
.opt-icon--ng  { color: #f43f5e; }

.opt-btn.selected { border-color: #1677ff; background: #f0f6ff; }
.opt-btn.selected .opt-key { background: #1677ff; color: #fff; }
.opt-btn.correct { border-color: #10b981; background: #f0fdf6; }
.opt-btn.correct .opt-key { background: #10b981; color: #fff; }
.opt-btn.correct .opt-label { color: #10b981; font-weight: 600; }
.opt-btn.wrong { border-color: #f43f5e; background: #fff5f5; }
.opt-btn.wrong .opt-key { background: #f43f5e; color: #fff; }
.opt-btn.wrong .opt-label { color: #f43f5e; }
.opt-btn.dimmed { opacity: 0.4; }

.hint-toggle {
  display: flex; align-items: center; gap: 5px;
  margin-top: 12px; border: none; background: none;
  color: #9aa3b2; font-size: 12px; font-weight: 600; cursor: pointer;
}
.hint-box {
  margin-top: 10px; padding: 10px 14px; border-radius: 10px;
  background: #fffbeb; border-left: 3px solid #f59e0b;
  font-size: 13px; color: #78350f; line-height: 1.6;
}

/* ── 反馈条 ── */
.feedback-bar {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 14px 16px; border-radius: 16px;
}
.feedback-bar.fb-correct { background: #f0fdf6; border: 1.5px solid #a7f3d0; }
.feedback-bar.fb-wrong   { background: #fff5f5; border: 1.5px solid #fecdd3; }
.fb-left { display: flex; align-items: flex-start; gap: 10px; flex: 1; min-width: 0; }
.fb-emoji { font-size: 22px; flex-shrink: 0; line-height: 1; }
.fb-title { font-size: 14px; font-weight: 800; color: #1a2035; }
.fb-detail { font-size: 12px; color: #6b7a90; margin-top: 3px; line-height: 1.5; }
.fb-next {
  flex-shrink: 0; display: flex; align-items: center; gap: 5px;
  height: 38px; padding: 0 14px; border-radius: 10px; border: none;
  background: #1677ff; color: #fff;
  font-size: 13px; font-weight: 700; cursor: pointer;
}

/* ── RESULT ── */
.phase-result { display: flex; flex-direction: column; align-items: center; padding: 8px 0 16px; }
.result-card { width: 100%; background: #fff; border-radius: 22px; padding: 28px 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.07); display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center; }
.rc-icon { font-size: 44px; }
.rc-title { margin: 0; font-size: 22px; font-weight: 800; color: #1a2035; }
.rc-sub { margin: 0; font-size: 14px; color: #9aa3b2; }
.rc-stars { display: flex; gap: 6px; }
.rc-star { font-size: 28px; color: #e2e8f0; transition: color 0.3s; }
.rc-star.filled { color: #f59e0b; animation: star-pop 0.4s ease both; }
@keyframes star-pop { 0%,100% { transform: scale(1); } 50% { transform: scale(1.35); } }
.rc-stats { display: flex; gap: 24px; }
.rcs { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.rcs-val { font-size: 22px; font-weight: 800; color: #1a2035; }
.rcs-label { font-size: 11px; color: #9aa3b2; }
.rc-continue {
  width: 100%; height: 48px; border-radius: 14px; border: none;
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff; font-size: 15px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  box-shadow: 0 6px 16px rgba(22,119,255,0.28);
}

/* ── FINAL ── */
.final-summary { display: flex; align-items: center; gap: 16px; background: #f5f7fa; border-radius: 14px; padding: 14px 20px; width: 100%; }
.fs-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.fs-val { font-size: 22px; font-weight: 800; color: #1a2035; }
.fs-label { font-size: 11px; color: #9aa3b2; }
.fs-div { width: 1px; height: 36px; background: #e4e8ef; }

.final-levels { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.fl-row { display: flex; align-items: center; gap: 10px; background: #f5f7fa; border-radius: 12px; padding: 10px 14px; }
.fl-icon { font-size: 18px; }
.fl-name { flex: 1; font-size: 13px; font-weight: 700; color: #1a2035; }
.fl-score { font-size: 13px; font-weight: 700; color: #6b7a90; }
.fl-stars { display: flex; gap: 2px; }
.fl-star { font-size: 13px; color: #e2e8f0; }
.fl-star.filled { color: #f59e0b; }

.final-actions { width: 100%; display: flex; gap: 10px; }
.fa-restart {
  flex: 1; height: 46px; border-radius: 13px; border: 1.5px solid #e4e8ef;
  background: #fff; color: #6b7a90; font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer;
}
</style>
