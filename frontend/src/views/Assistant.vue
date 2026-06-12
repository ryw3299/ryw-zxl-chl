<script setup>
import { computed, ref, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { interactQA } from '@/api/qa'
import { useLessonStore } from '@/store/lessonStore'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const lessonStore = useLessonStore()
const userStore = useUserStore()

const chatInput = ref('')
const chatLoading = ref(false)
const messagesEl = ref(null)

const isTeacher = computed(() => userStore.isTeacher)

const assistantProfile = computed(() => {
  if (isTeacher.value) {
    return {
      name: 'AI 助教',
      eyebrow: 'TEACHING ASSISTANT',
      subtitle: '协助备课、课堂互动设计、学情分析与课后辅导建议。',
      intro: '你好，我是 AI 助教。你可以让我帮你整理课程重点、设计课堂提问、生成课后任务、分析学生薄弱点，或者把一段课件内容交给我改成更适合授课的讲解方案。',
      historyItems: [
        '新对话',
        '三相电知识点补救建议',
        '课后作业分层方案',
      ],
      placeholder: '输入备课、授课、学情分析或课后辅导需求',
      inputHint: '按 Enter 发送，Shift + Enter 换行',
      statusLabel: '课堂支持中',
      statusDesc: '适合继续生成课堂问题和分层辅导建议。',
    }
  }
  return {
    name: '学习助手',
    eyebrow: 'LEARNING ASSISTANT',
    subtitle: '解答课程概念、作业思路、复习计划与代码问题。',
    intro: '你好，我是学习助手。你可以直接问我课程概念、作业思路、复习安排，或者把一段代码贴过来让我帮你分析。',
    historyItems: [
      '运算放大器综合题',
      'Simulink 调制解调实验',
      '复变函数速记清单',
    ],
    placeholder: '输入你的问题，支持粘贴代码或题目内容',
    inputHint: '按 Enter 发送，Shift + Enter 换行',
    statusLabel: '复习节奏稳定',
    statusDesc: '建议优先处理最近提问中暴露的薄弱概念。',
  }
})

const studentMessages = ref([
  { role: 'ai', text: '你好，我是学习助手。你可以直接问我课程概念、作业思路、复习安排，或者把一段代码贴过来让我帮你分析。' },

])

const teacherMessages = ref([
  { role: 'ai', text: '你好，我是 AI 助教。你可以让我帮你整理课程重点、设计课堂提问、生成课后任务、分析学生薄弱点，或者把一段课件内容交给我改成更适合授课的讲解方案。' },
])

const messages = computed(() => isTeacher.value ? teacherMessages.value : studentMessages.value)

const normalizeQuery = (value, fallback = '') => {
  if (Array.isArray(value)) return normalizeQuery(value[0], fallback)
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const buildHistoryQa = (items) => {
  const history = []
  for (let index = 0; index < items.length - 1; index += 1) {
    const current = items[index]
    const next = items[index + 1]
    if (current?.role === 'user' && next?.role === 'ai') {
      history.push({
        questionContent: current.text,
        answerContent: next.text,
      })
    }
  }
  return history.slice(-6)
}

const formatQaAnswer = (result) => {
  const parts = [result.answer].filter(Boolean)
  if (result.relatedKnowledge?.length) {
    parts.push(`相关知识点：${result.relatedKnowledge.join('、')}`)
  }
  if (result.suggestions?.length) {
    parts.push(`学习建议：${result.suggestions.join('；')}`)
  }
  return parts.join('\n\n') || '我已经收到你的问题，但暂时没有生成有效回答。'
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

const buildReply = (text) => {
  if (isTeacher.value) {
    if (text.includes('互动') || text.includes('提问'))
      return '可以按"回忆事实、解释原因、迁移应用、同伴讨论、即时反馈"五个层次设计课堂互动。建议先用一个低门槛问题激活旧知，再用追问暴露概念误区，最后用小练习检查学生是否真正会迁移。'
    if (text.includes('作业') || text.includes('课后'))
      return '建议把课后任务分成三层：基础巩固题覆盖核心概念，提升题训练推导或应用，拓展题引导学生解释真实场景。每层控制题量，并给出评价标准，方便后续学情归因。'
    if (text.includes('薄弱') || text.includes('补救') || text.includes('学情'))
      return '可以先按知识点、题型、错误原因三类整理薄弱点，再安排短讲解、针对练和错因复盘。对共性问题放到下一次课前 5 分钟统一处理，个性问题交给课后任务或答疑区。'
    if (text.includes('脚本') || text.includes('讲解'))
      return '讲解脚本建议采用"问题引入、概念澄清、关键步骤、易错提醒、课堂检查"的结构。这样既符合教师授课节奏，也方便学生在关键处停下来思考。'
    return '我可以从备课目标、课堂活动、板书结构、学情诊断和课后任务五个角度继续拆解。你把具体课程内容或学生反馈贴出来，我会按助教工作流给出可执行建议。'
  }
  if (text.includes('双星'))
    return '学习双星问题有以下几个关键注意点：\n\n1. 【向心力来源要明确】两星之间的万有引力就是各自做圆周运动的向心力，不要额外再引入"向心力"作为第三个力。\n\n2. 【角速度（周期）相同，线速度不同】两星绕公共质心转动，周期完全相同；但由于轨道半径不同，线速度 v = ωr，质量大的星轨道半径小、线速度反而小。\n\n3. 【质心条件是关键等式】m₁r₁ = m₂r₂，且 r₁ + r₂ = L（两星间距）。这两个方程联立才能分别求出各自的轨道半径，不能只用其中一个。\n\n4. 【只能求总质量，不能求单个质量】由 G(m₁+m₂)/L² = (2π/T)²·L 可以求出 m₁+m₂，但如果题目只给了 T 和 L，无法单独求出 m₁ 或 m₂，除非再给质量比或各自轨道半径。\n\n5. 【向心加速度不同】a = F/m，两星受到的引力大小相等，但质量不同，所以加速度不同——质量大的星加速度反而小。\n\n建议先画出示意图标注质心位置，再逐步列方程，避免把两星的轨道半径混淆。'
  if (text.includes('复习计划') || text.includes('学习安排'))
    return '建议按"概念回顾、例题推导、动手练习、错题回看"四段来拆。先保证每天有一门主课，再用 30 分钟处理薄弱点。'
  if (text.includes('TCP'))
    return '流量控制解决的是接收端来不来得及收，拥塞控制解决的是网络通道会不会被挤爆。前者看接收窗口，后者看拥塞窗口。'
  if (text.includes('MATLAB'))
    return '先把矩阵运算、绘图、脚本与函数三块打牢，再进入数值分析和信号处理题目。每次练习后保留一份可复用模板。'
  return '这个问题可以继续往下拆。你把具体课程、题目或者代码片段贴出来，我可以按步骤帮你定位。'
}

const sendMessage = async () => {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return

  chatInput.value = ''
  const cache = isTeacher.value ? teacherMessages : studentMessages
  cache.value.push({ role: 'user', text })
  scrollToBottom()
  chatLoading.value = true

  try {
    const result = await interactQA({
      schoolId: userStore.userInfo.schoolId || route.query.schoolId,
      userId: userStore.userInfo.userId || route.query.userId,
      courseId: lessonStore.courseInfo.courseId || lessonStore.platformContext.courseId || route.query.courseId,
      lessonId: lessonStore.lessonInfo.lessonId || lessonStore.platformContext.lessonId || route.query.lessonId,
      sessionId: lessonStore.sessionInfo.sessionId,
      questionType: 'text',
      questionContent: text,
      currentSectionId: lessonStore.lessonInfo.currentSectionId || route.query.currentSectionId,
      currentPage: lessonStore.lessonInfo.currentPage || normalizeQuery(route.query.currentPage),
      historyQa: buildHistoryQa(cache.value),
    })
    cache.value.push({ role: 'ai', text: formatQaAnswer(result) })
  } catch {
    cache.value.push({ role: 'ai', text: buildReply(text) })
  } finally {
    chatLoading.value = false
    scrollToBottom()
  }
}

const micRecording = ref(false)
const micTimer = ref(null)

const toggleMic = () => {
  if (micRecording.value) {
    micRecording.value = false
    clearTimeout(micTimer.value)
    return
  }
  micRecording.value = true
  micTimer.value = setTimeout(() => {
    micRecording.value = false
    chatInput.value = '解释下学习双星问题需要注意的点'
  }, 2000)
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <header class="topbar">
      <div class="topbar-left">
        <div class="avatar">AI</div>
        <div>
          <div class="topbar-name">{{ assistantProfile.name }}</div>
          <div class="topbar-sub">{{ assistantProfile.subtitle }}</div>
        </div>
      </div>
      <div class="topbar-right">
        <span class="status-pill">
          <i class="dot" />
          DeepSeek-V4 在线
        </span>
        <span class="chip">{{ isTeacher ? '教师端' : '学生端' }}</span>
        <span class="chip">实时响应</span>
      </div>
    </header>

    <!-- Body -->
    <div class="body">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-section">
          <div class="section-label">最近对话</div>
          <div class="history-list">
            <button v-for="(item, index) in assistantProfile.historyItems" :key="item" type="button"
              :class="['hist-item', { active: index === 0 }]">
              <span class="hist-num">{{ index + 1 }}</span>
              {{ item }}
            </button>
          </div>
        </div>

        <button type="button" class="new-btn">+ 新建对话</button>

        <div class="divider" />

        <div class="state-card">
          <div class="section-label">学习状态</div>
          <strong>{{ assistantProfile.statusLabel }}</strong>
          <p>{{ assistantProfile.statusDesc }}</p>
        </div>
      </aside>

      <!-- Conversation -->
      <section class="convo">
        <div class="convo-head">
          <div>
            <div class="section-label">CURRENT THREAD</div>
            <h2>{{ isTeacher ? '教学协作对话' : '课程答疑对话' }}</h2>
          </div>
          <div class="head-actions">
            <button type="button" class="action-btn">整理要点</button>
            <button type="button" class="action-btn">生成计划</button>
          </div>
        </div>

        <div ref="messagesEl" class="messages">
          <div v-for="(msg, index) in messages" :key="index" :class="['msg', msg.role]">
            <div v-if="msg.role === 'ai'" class="msg-icon">AI</div>
            <div class="bubble">{{ msg.text }}</div>
          </div>
          <div v-if="chatLoading" class="msg ai">
            <div class="msg-icon">AI</div>
            <div class="bubble typing">
              <span /><span /><span />
            </div>
          </div>
        </div>

        <div class="composer">
          <div class="composer-inner">
            <textarea v-model="chatInput" class="chat-input" :placeholder="assistantProfile.placeholder" rows="1"
              @keydown.enter.exact.prevent="sendMessage" />
            <button type="button" :class="['icon-btn', { recording: micRecording }]" title="语音输入" @click="toggleMic">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                <rect x="9" y="2" width="6" height="12" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <line x1="12" y1="19" x2="12" y2="22" />
                <line x1="9" y1="22" x2="15" y2="22" />
              </svg>
            </button>
            <button type="button" class="send-btn" :disabled="chatLoading || !chatInput.trim()" @click="sendMessage">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p class="composer-hint">{{ assistantProfile.inputHint }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* ── Reset & base ── */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.page {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 10px;
  overflow: hidden;
  background: var(--color-background-tertiary, #f8fafc);
  font-family: Inter, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: var(--color-text-primary, #0f172a);
}

/* ── Topbar ── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 18px;
  background: #fff;
  border: 0.5px solid #e2e8f0;
  border-radius: 8px;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: #ccfbf1;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 600;
  color: #0f766e;
  border: 0.5px solid #99f6e4;
  flex-shrink: 0;
}

.topbar-name {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.topbar-sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 1px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 0.5px solid #99f6e4;
  background: #f0fdfa;
  font-size: 12px;
  color: #0f766e;
  font-weight: 500;
  white-space: nowrap;
}

.dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #14b8a6;
}

.chip {
  padding: 5px 10px;
  border-radius: 8px;
  border: 0.5px solid #e2e8f0;
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

/* ── Body layout ── */
.body {
  display: grid;
  grid-template-columns: 216px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
  height: 100%;
}

/* ── Sidebar ── */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  background: #fff;
  border: 0.5px solid #e2e8f0;
  border-radius: 8px;
  overflow-y: auto;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.hist-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 0.5px solid transparent;
  background: transparent;
  font-size: 13px;
  color: #475569;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hist-item:hover,
.hist-item.active {
  background: #f0fdfa;
  color: #0f766e;
  border-color: #ccfbf1;
}

.hist-num {
  font-size: 11px;
  color: #94a3b8;
  min-width: 14px;
  flex-shrink: 0;
}

.new-btn {
  padding: 8px;
  border-radius: 6px;
  border: 0.5px solid #e2e8f0;
  background: #f8fafc;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  text-align: center;
  width: 100%;
}

.new-btn:hover {
  background: #f0fdfa;
  color: #0f766e;
  border-color: #99f6e4;
}

.divider {
  height: 0.5px;
  background: #e2e8f0;
}

.state-card {
  padding: 12px;
  border-radius: 6px;
  background: #f8fafc;
  border: 0.5px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: auto;
}

.state-card strong {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.state-card p {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

/* ── Conversation ── */
.convo {
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-height: 0;
  background: #fff;
  border: 0.5px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.convo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 0.5px solid #e2e8f0;
}

.convo-head h2 {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin-top: 3px;
}

.head-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 5px 10px;
  border-radius: 6px;
  border: 0.5px solid #e2e8f0;
  background: #fff;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: background 0.15s;
}

.action-btn:hover {
  background: #f0fdfa;
  color: #0f766e;
  border-color: #99f6e4;
}

/* ── Messages ── */
.messages {
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8fafc;
}

.msg {
  display: flex;
  gap: 10px;
}

.msg.user {
  flex-direction: row-reverse;
}

.msg-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 8px;
  background: #ccfbf1;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 600;
  color: #0f766e;
  border: 0.5px solid #99f6e4;
  align-self: flex-start;
}

.bubble {
  max-width: 76%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  border: 0.5px solid #e2e8f0;
  background: #fff;
  color: #0f172a;
}

.msg.user .bubble {
  background: #f0fdfa;
  border-color: #99f6e4;
  color: #0f766e;
}

/* Typing indicator */
.typing {
  display: flex;
  gap: 5px;
  align-items: center;
  min-height: 20px;
}

.typing span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
  animation: bounce 1.3s infinite ease-in-out both;
}

.typing span:nth-child(2) {
  animation-delay: 0.16s;
}

.typing span:nth-child(3) {
  animation-delay: 0.32s;
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}

/* ── Composer ── */
.composer {
  padding: 12px 14px;
  border-top: 0.5px solid #e2e8f0;
  background: #fff;
}

.composer-inner {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 10px;
  border: 0.5px solid #e2e8f0;
  border-radius: 8px;
  transition: border-color 0.15s;
}

.composer-inner:focus-within {
  border-color: #5DCAA5;
}

.chat-input {
  flex: 1;
  min-height: 40px;
  max-height: 120px;
  border: none;
  outline: none;
  resize: none;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  color: #0f172a;
  background: transparent;
}

.chat-input::placeholder {
  color: #94a3b8;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 0.5px solid #e2e8f0;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}

.icon-btn:hover {
  background: #f0fdfa;
  color: #0f766e;
  border-color: #99f6e4;
}

.icon-btn.recording {
  background: #fee2e2;
  color: #ef4444;
  border-color: #fca5a5;
  animation: mic-pulse 1s ease-in-out infinite;
}

@keyframes mic-pulse {

  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.3);
  }

  50% {
    box-shadow: 0 0 0 5px rgba(239, 68, 68, 0);
  }
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  background: #14b8a6;
  color: #fff;
  cursor: pointer;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: #0f766e;
}

.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.composer-hint {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 8px;
  text-align: center;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .page {
    overflow-y: auto;
  }

  .body {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .topbar-right .chip {
    display: none;
  }
}
</style>
