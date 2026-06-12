<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { showToast } from 'vant'
import { interactQA, transcribeVoice } from '@/api/qa'
import { useUserStore } from '@/store/userStore'

const userStore = useUserStore()

const messageInput = ref('')
const isTyping = ref(false)
const chatListRef = ref(null)
const chatHistory = ref([])
const sessionId = `mob-chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

// ── voice input state ──────────────────────────────────────────────
const isRecording = ref(false)
const isTranscribing = ref(false)
const voiceMode = ref('idle') // idle | speech-api | recorder

let speechRecognition = null
let mediaRecorder = null
let mediaStream = null
let recordedChunks = []
let textBeforeVoice = ''
let shouldSubmitOnEnd = false

const speechApiSupported = typeof window !== 'undefined'
  && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)

const voiceButtonHint = computed(() => {
  if (isTranscribing.value) return '识别中…'
  if (isRecording.value) return '松开发送'
  return '按住说话'
})

// ── Strategy 1: Web Speech API (native, low latency) ──────────────
const startSpeechApi = () => {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Ctor) return false

  const rec = new Ctor()
  rec.lang = 'zh-CN'
  rec.continuous = false
  rec.interimResults = true
  rec.maxAlternatives = 1

  let finalText = ''
  textBeforeVoice = messageInput.value

  rec.onresult = (event) => {
    let interim = ''
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const r = event.results[i]
      const t = String(r?.[0]?.transcript || '')
      if (r.isFinal) finalText += t
      else interim += t
    }
    messageInput.value = `${finalText}${interim}`.trim()
  }

  rec.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      showToast('麦克风权限被拒绝')
    } else if (e.error !== 'no-speech' && e.error !== 'aborted') {
      showToast('语音识别失败')
    }
    stopVoiceInput({ submit: false })
  }

  rec.onend = () => {
    speechRecognition = null
    if (shouldSubmitOnEnd && finalText.trim()) {
      messageInput.value = finalText.trim()
      shouldSubmitOnEnd = false
      sendMessage()
    } else if (!finalText.trim()) {
      messageInput.value = textBeforeVoice
    }
    shouldSubmitOnEnd = false
  }

  try {
    rec.start()
    speechRecognition = rec
    voiceMode.value = 'speech-api'
    return true
  } catch {
    return false
  }
}

// ── Strategy 2: MediaRecorder → backend Whisper ────────────────────
const pickMimeType = () => {
  if (typeof MediaRecorder === 'undefined') return ''
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ]
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || ''
}

const startRecorder = async () => {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    showToast('无法访问麦克风')
    return false
  }

  const mimeType = pickMimeType()
  try {
    mediaRecorder = mimeType
      ? new MediaRecorder(mediaStream, { mimeType })
      : new MediaRecorder(mediaStream)
  } catch {
    showToast('浏览器不支持录音')
    mediaStream.getTracks().forEach((t) => t.stop())
    mediaStream = null
    return false
  }

  recordedChunks = []
  mediaRecorder.ondataavailable = (e) => {
    if (e.data && e.data.size > 0) recordedChunks.push(e.data)
  }
  mediaRecorder.onstop = async () => {
    const tracks = mediaStream?.getTracks() || []
    tracks.forEach((t) => t.stop())
    mediaStream = null

    if (!recordedChunks.length) {
      isTranscribing.value = false
      return
    }
    const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
    recordedChunks = []
    mediaRecorder = null

    isTranscribing.value = true
    try {
      const { text } = await transcribeVoice(blob, 'zh-CN')
      if (text) {
        messageInput.value = text
        await nextTick()
        sendMessage()
      } else {
        showToast('未识别到语音内容')
      }
    } catch {
      showToast('语音识别服务异常')
    } finally {
      isTranscribing.value = false
    }
  }

  mediaRecorder.start()
  voiceMode.value = 'recorder'
  return true
}

const startVoiceInput = async () => {
  if (isRecording.value || isTranscribing.value) return
  if (isTyping.value) return

  isRecording.value = true
  const ok = speechApiSupported ? startSpeechApi() : await startRecorder()
  if (!ok) {
    const fallback = await startRecorder()
    if (!fallback) {
      isRecording.value = false
      voiceMode.value = 'idle'
    }
  }
}

const stopVoiceInput = ({ submit = true } = {}) => {
  if (!isRecording.value) return
  isRecording.value = false

  shouldSubmitOnEnd = submit

  if (voiceMode.value === 'speech-api' && speechRecognition) {
    try {
      if (submit) speechRecognition.stop()
      else speechRecognition.abort()
    } catch { /* no-op */ }
  } else if (voiceMode.value === 'recorder' && mediaRecorder) {
    try {
      if (submit) mediaRecorder.stop()
      else {
        mediaRecorder.ondataavailable = null
        mediaRecorder.onstop = null
        mediaRecorder.stop()
        mediaStream?.getTracks().forEach((t) => t.stop())
        mediaStream = null
        mediaRecorder = null
      }
    } catch { /* no-op */ }
  }
  voiceMode.value = 'idle'
}

// Pointer handlers for press-and-hold
const onVoicePressStart = (e) => {
  e?.preventDefault?.()
  startVoiceInput()
}
const onVoicePressEnd = (e) => {
  e?.preventDefault?.()
  stopVoiceInput({ submit: true })
}
const onVoicePressCancel = () => stopVoiceInput({ submit: false })

const MOCK_REPLY_BINARY_STAR = '学习双星问题有以下几个关键注意点：\n\n1. 【向心力来源要明确】两星之间的万有引力就是各自做圆周运动的向心力，不要额外再引入"向心力"作为第三个力。\n\n2. 【角速度（周期）相同，线速度不同】两星绕公共质心转动，周期完全相同；但由于轨道半径不同，线速度 v = ωr，质量大的星轨道半径小、线速度反而小。\n\n3. 【质心条件是关键等式】m₁r₁ = m₂r₂，且 r₁ + r₂ = L（两星间距）。这两个方程联立才能分别求出各自的轨道半径，不能只用其中一个。\n\n4. 【只能求总质量，不能求单个质量】由 G(m₁+m₂)/L² = (2π/T)²·L 可以求出 m₁+m₂，但如果题目只给了 T 和 L，无法单独求出 m₁ 或 m₂，除非再给质量比或各自轨道半径。\n\n5. 【向心加速度不同】a = F/m，两星受到的引力大小相等，但质量不同，所以加速度不同——质量大的星加速度反而小。\n\n建议先画出示意图标注质心位置，再逐步列方程，避免把两星的轨道半径混淆。'

const messages = ref([
  {
    id: 'ai-welcome',
    role: 'ai',
    text: '你好！我是你的 AI 学习伙伴。\n\n可以问我任意课程的知识问题，或者说"帮我制定学习计划"，让我为你提供个性化建议。',
    time: '',
    status: 'success',
  },
  {
    id: 'mock-user-1',
    role: 'user',
    text: '解释下学习双星问题需要注意的点',
    time: '09:00',
    status: 'success',
  },
  {
    id: 'mock-ai-1',
    role: 'ai',
    text: MOCK_REPLY_BINARY_STAR,
    time: '09:00',
    status: 'success',
  },
])

const quickPrompts = [
  { label: '制定学习计划', icon: 'calendar-o', gradient: ['#667eea', '#764ba2'] },
  { label: '核心公式梳理', icon: 'orders-o',  gradient: ['#f093fb', '#f5576c'] },
  { label: '推荐学习顺序', icon: 'guide-o',   gradient: ['#4facfe', '#00f2fe'] },
  { label: '概念理解答疑', icon: 'question-o', gradient: ['#43e97b', '#38f9d7'] },
]

const showWelcome = computed(() => false)

const canSend = computed(() => messageInput.value.trim().length > 0 && !isTyping.value)

const now = () => new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })

const scrollToBottom = async () => {
  await nextTick()
  if (chatListRef.value) chatListRef.value.scrollTop = chatListRef.value.scrollHeight
}

const sendMessage = async (text = '') => {
  const content = (text || messageInput.value).trim()
  if (!content || isTyping.value) return

  const msgId = `user-${Date.now()}`
  messages.value.push({ id: msgId, role: 'user', text: content, time: now(), status: 'sending' })
  messageInput.value = ''
  await scrollToBottom()
  isTyping.value = true

  try {
    const res = await interactQA({
      userId: userStore.userInfo.userId,
      sessionId,
      question: content,
      historyQa: chatHistory.value.slice(-6),
    })

    const userMsg = messages.value.find((m) => m.id === msgId)
    if (userMsg) userMsg.status = 'success'

    chatHistory.value.push({ role: 'user', text: content })
    chatHistory.value.push({ role: 'ai', text: res.answer })

    messages.value.push({ id: `ai-${Date.now()}`, role: 'ai', text: res.answer, time: now(), status: 'success' })
  } catch {
    const userMsg = messages.value.find((m) => m.id === msgId)
    if (userMsg) userMsg.status = 'error'
    messages.value.push({ id: `ai-${Date.now()}`, role: 'ai', text: 'AI 助手暂时不可用，请稍后重试', time: now(), status: 'error' })
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
}

watch(messages, scrollToBottom, { deep: true })
onMounted(scrollToBottom)
onBeforeUnmount(() => {
  stopVoiceInput({ submit: false })
})
</script>

<template>
  <div class="chat-root">

    <!-- 装饰背景 -->
    <div class="bg-decor">
      <div class="bg-blob bg-blob--1" />
      <div class="bg-blob bg-blob--2" />
      <div class="bg-blob bg-blob--3" />
    </div>

    <!-- 消息区 -->
    <div class="chat-messages" ref="chatListRef">

      <!-- 欢迎卡（仅初始态展示） -->
      <transition name="welcome-fade">
        <div v-if="showWelcome" class="welcome-card">
          <div class="welcome-glow" />
          <div class="welcome-icon">
            <van-icon name="gem-o" size="30" color="#fff" />
            <span class="welcome-pulse" />
          </div>
          <p class="welcome-badge">AI 学习伙伴 · 在线</p>
          <p class="welcome-title">你好，我能帮到你什么？</p>
          <p class="welcome-desc">{{ messages[0].text.replace('你好！我是你的 AI 学习伙伴。\n\n', '') }}</p>

          <div class="welcome-features">
            <div class="feature-item">
              <div class="feature-dot" style="background: linear-gradient(135deg, #667eea, #764ba2)" />
              <span>智能答疑</span>
            </div>
            <div class="feature-item">
              <div class="feature-dot" style="background: linear-gradient(135deg, #4facfe, #00f2fe)" />
              <span>个性规划</span>
            </div>
            <div class="feature-item">
              <div class="feature-dot" style="background: linear-gradient(135deg, #43e97b, #38f9d7)" />
              <span>随问随答</span>
            </div>
          </div>
        </div>
      </transition>

      <!-- 消息气泡 -->
      <template v-for="msg in messages" :key="msg.id">
        <div v-if="msg.id !== 'ai-welcome'" class="bubble-row" :class="`is-${msg.role}`">
          <div v-if="msg.role === 'ai'" class="bubble-avatar bubble-avatar--ai">
            <van-icon name="gem-o" size="14" color="#fff" />
          </div>
          <div class="bubble-content">
            <div class="bubble-box" :class="{ 'bubble-box--error': msg.status === 'error' && msg.role === 'ai' }">{{ msg.text }}</div>
            <div v-if="msg.time" class="bubble-meta">
              <span>{{ msg.time }}</span>
              <van-loading v-if="msg.status === 'sending'" size="10px" color="#9aa3b2" />
            </div>
          </div>
          <div v-if="msg.role === 'user'" class="bubble-avatar bubble-avatar--user">我</div>
        </div>
      </template>

      <!-- 打字动画 -->
      <div v-if="isTyping" class="bubble-row is-ai">
        <div class="bubble-avatar bubble-avatar--ai"><van-icon name="gem-o" size="14" color="#fff" /></div>
        <div class="bubble-box typing-box">
          <span class="dot" /><span class="dot" /><span class="dot" />
        </div>
      </div>

    </div>

    <!-- 底部操作区 -->
    <div class="chat-bottom">

      <!-- 快捷提问 -->
      <div class="quick-row">
        <button
          v-for="p in quickPrompts"
          :key="p.label"
          class="quick-chip"
          :style="{ '--g1': p.gradient[0], '--g2': p.gradient[1] }"
          @click="sendMessage(p.label)"
        >
          <van-icon :name="p.icon" size="13" />
          {{ p.label }}
        </button>
      </div>

      <!-- 输入框 -->
      <div class="input-wrap" :class="{ 'is-focus': canSend, 'is-recording': isRecording }">
        <van-field
          v-model="messageInput"
          type="textarea"
          rows="1"
          autosize
          :maxlength="300"
          :placeholder="isRecording ? '正在录音，松开发送…' : (isTranscribing ? '识别中…' : '向 AI 提问…')"
          class="chat-field"
          :border="false"
          :disabled="isRecording || isTranscribing"
          @keydown="handleKeydown"
        />
        <button
          class="voice-btn"
          :class="{ 'voice-btn--active': isRecording, 'voice-btn--loading': isTranscribing }"
          :disabled="isTranscribing || isTyping"
          @pointerdown="onVoicePressStart"
          @pointerup="onVoicePressEnd"
          @pointerleave="onVoicePressCancel"
          @pointercancel="onVoicePressCancel"
          @contextmenu.prevent
        >
          <van-loading v-if="isTranscribing" size="16" color="#fff" />
          <van-icon v-else name="volume-o" size="18" />
        </button>
        <button
          class="send-btn"
          :class="{ 'send-btn--active': canSend }"
          :disabled="!canSend"
          @click="sendMessage()"
        >
          <van-icon name="guide-o" size="18" />
        </button>
      </div>

      <!-- 录音提示 -->
      <transition name="voice-tip-fade">
        <div v-if="isRecording || isTranscribing" class="voice-tip">
          <span class="voice-tip__pulse" />
          {{ voiceButtonHint }}
        </div>
      </transition>

    </div>
  </div>
</template>

<style scoped>
.chat-root {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: linear-gradient(180deg, #f7f9ff 0%, #eef3fb 100%);
  overflow: hidden;
}

/* ── 装饰背景 blob ── */
.bg-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.35;
}
.bg-blob--1 {
  width: 240px; height: 240px;
  background: radial-gradient(circle, #a5c8ff 0%, transparent 70%);
  top: -60px; right: -60px;
  animation: float-1 12s ease-in-out infinite;
}
.bg-blob--2 {
  width: 200px; height: 200px;
  background: radial-gradient(circle, #c5b8ff 0%, transparent 70%);
  top: 40%; left: -80px;
  animation: float-2 15s ease-in-out infinite;
}
.bg-blob--3 {
  width: 180px; height: 180px;
  background: radial-gradient(circle, #ffd1e0 0%, transparent 70%);
  bottom: 100px; right: -40px;
  animation: float-3 18s ease-in-out infinite;
}
@keyframes float-1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-20px, 30px) scale(1.1); } }
@keyframes float-2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(30px, -20px) scale(1.15); } }
@keyframes float-3 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-15px, -25px) scale(1.08); } }

/* ── 消息区 ── */
.chat-messages {
  position: relative;
  z-index: 1;
  flex: 1;
  overflow-y: auto;
  padding: 20px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.chat-messages::-webkit-scrollbar { width: 0; }

/* ── 欢迎卡 ── */
.welcome-card {
  position: relative;
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.8);
  border-radius: 24px;
  padding: 28px 22px 24px;
  box-shadow: 0 8px 32px rgba(22,119,255,0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  margin: 8px 2px 6px;
  overflow: hidden;
}

.welcome-glow {
  position: absolute;
  top: -40px;
  left: 50%;
  transform: translateX(-50%);
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(22,119,255,0.2) 0%, transparent 70%);
  pointer-events: none;
}

.welcome-icon {
  position: relative;
  width: 62px; height: 62px;
  border-radius: 20px;
  background: linear-gradient(135deg, #1677ff 0%, #46aaff 50%, #6c5ce7 100%);
  display: flex; align-items: center; justify-content: center;
  box-shadow:
    0 8px 26px rgba(22,119,255,0.35),
    inset 0 1px 0 rgba(255,255,255,0.3);
  margin-bottom: 6px;
  z-index: 1;
}

.welcome-pulse {
  position: absolute;
  inset: -6px;
  border-radius: 26px;
  border: 1.5px solid rgba(22,119,255,0.4);
  animation: pulse-ring 2.4s ease-out infinite;
}
@keyframes pulse-ring {
  0%   { opacity: 0.7; transform: scale(1); }
  100% { opacity: 0; transform: scale(1.25); }
}

.welcome-badge {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  color: #1677ff;
  background: linear-gradient(135deg, rgba(22,119,255,0.12), rgba(100,92,231,0.12));
  padding: 3px 10px;
  border-radius: 10px;
  letter-spacing: 0.04em;
  border: 1px solid rgba(22,119,255,0.15);
}

.welcome-title {
  margin: 4px 0 2px;
  font-size: 19px;
  font-weight: 800;
  color: #1a2035;
  letter-spacing: -0.01em;
  background: linear-gradient(135deg, #1a2035 0%, #3a4a70 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7a90;
  line-height: 1.7;
  white-space: pre-wrap;
  max-width: 280px;
}

.welcome-features {
  display: flex;
  gap: 18px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(107,122,144,0.18);
  width: 100%;
  justify-content: center;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4a5878;
  font-weight: 600;
}
.feature-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.welcome-fade-enter-active { transition: all 0.35s ease; }
.welcome-fade-leave-active { transition: all 0.22s ease; }
.welcome-fade-enter-from, .welcome-fade-leave-to { opacity: 0; transform: translateY(12px); }

/* ── 气泡 ── */
.bubble-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 88%;
}
.bubble-row.is-user { align-self: flex-end; }
.bubble-row.is-ai  { align-self: flex-start; }

.bubble-avatar {
  width: 30px; height: 30px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  font-size: 11px; font-weight: 800;
}
.bubble-avatar--ai {
  background: linear-gradient(135deg, #1677ff 0%, #46aaff 50%, #6c5ce7 100%);
  box-shadow: 0 3px 12px rgba(22,119,255,0.32);
}
.bubble-avatar--user {
  background: linear-gradient(135deg, #1a2035, #2d3a5b);
  color: #fff;
  box-shadow: 0 3px 10px rgba(26,32,53,0.22);
}

.bubble-content { display: flex; flex-direction: column; gap: 4px; }
.is-user .bubble-content { align-items: flex-end; }

.bubble-box {
  padding: 12px 15px;
  border-radius: 4px 18px 18px 18px;
  background: #fff;
  font-size: 14px;
  line-height: 1.75;
  color: #1a2035;
  box-shadow: 0 2px 12px rgba(22,119,255,0.08);
  border: 1px solid rgba(22,119,255,0.06);
  word-break: break-word;
  white-space: pre-wrap;
}
.is-user .bubble-box {
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff;
  border: none;
  border-radius: 18px 4px 18px 18px;
  box-shadow: 0 4px 18px rgba(22,119,255,0.32);
}
.bubble-box--error {
  background: #fff5f5;
  color: #c53030;
  border-color: rgba(197,48,48,0.15);
}

.bubble-meta { display: flex; align-items: center; gap: 5px; font-size: 11px; color: #b0b9c8; }

/* 打字动画 */
.typing-box { display: flex; gap: 5px; align-items: center; padding: 13px 16px; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #b0b9c8; animation: blink 1.3s infinite ease-in-out both; }
.dot:nth-child(1) { animation-delay: -0.3s; }
.dot:nth-child(2) { animation-delay: -0.15s; }
@keyframes blink {
  0%,80%,100% { transform: scale(0.7); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* ── 底部 ── */
.chat-bottom {
  position: relative;
  z-index: 1;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(22,119,255,0.08);
  padding: 10px 14px calc(60px + env(safe-area-inset-bottom, 0px) + 10px);
  flex-shrink: 0;
}

.quick-row {
  display: flex;
  gap: 7px;
  overflow-x: auto;
  padding-bottom: 10px;
  scrollbar-width: none;
}
.quick-row::-webkit-scrollbar { display: none; }

.quick-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 13px;
  border-radius: 999px;
  border: 1.5px solid transparent;
  background: #fff;
  background-clip: padding-box;
  color: var(--g1, #1677ff);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  position: relative;
  box-shadow: 0 2px 8px rgba(22,119,255,0.06);
}
.quick-chip::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1.5px;
  background: linear-gradient(135deg, var(--g1, #1677ff), var(--g2, #46aaff));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
.quick-chip:active {
  transform: scale(0.95);
  background: linear-gradient(135deg, var(--g1), var(--g2));
  color: #fff;
}
.quick-chip:active::before { opacity: 0; }

.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f5f7fa;
  border-radius: 18px;
  border: 1.5px solid #e8ecf4;
  padding: 6px 6px 6px 14px;
  transition: all 0.2s;
}
.input-wrap:focus-within,
.input-wrap.is-focus {
  border-color: #93c5fd;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(147,197,253,0.15);
}

.chat-field { flex: 1; background: transparent; padding: 0; font-size: 14px; }
.chat-field :deep(.van-field__control) { max-height: 80px; font-size: 14px; line-height: 1.6; background: transparent; }

.send-btn {
  width: 38px; height: 38px;
  border-radius: 12px; border: none;
  background: #e4e8ef; color: #b0b9c8;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s;
  cursor: pointer;
}
.send-btn--active {
  background: linear-gradient(135deg, #1677ff, #46aaff);
  color: #fff;
  box-shadow: 0 4px 16px rgba(22,119,255,0.38);
  transform: scale(1.04);
}

/* ── 语音按钮 ── */
.voice-btn {
  width: 38px; height: 38px;
  border-radius: 12px; border: none;
  background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.18s;
  box-shadow: 0 3px 12px rgba(245,87,108,0.3);
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: none;
}
.voice-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.voice-btn--active {
  background: linear-gradient(135deg, #ff4757 0%, #ff6b7a 100%);
  transform: scale(1.12);
  box-shadow:
    0 0 0 4px rgba(255,71,87,0.18),
    0 6px 22px rgba(255,71,87,0.5);
  animation: voice-pulse 1s ease-in-out infinite;
}
.voice-btn--loading {
  background: linear-gradient(135deg, #667eea, #764ba2);
  box-shadow: 0 3px 12px rgba(102,126,234,0.4);
}
@keyframes voice-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(255,71,87,0.18), 0 6px 22px rgba(255,71,87,0.5); }
  50%      { box-shadow: 0 0 0 8px rgba(255,71,87,0.08), 0 6px 22px rgba(255,71,87,0.5); }
}

.input-wrap.is-recording {
  border-color: rgba(255,71,87,0.35);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(255,71,87,0.1);
}

.voice-tip {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  transform: translateX(-50%);
  background: rgba(26,32,53,0.92);
  color: #fff;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.2);
  white-space: nowrap;
  pointer-events: none;
}
.voice-tip__pulse {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #ff4757;
  animation: voice-dot-blink 0.8s ease-in-out infinite;
}
@keyframes voice-dot-blink {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.4; transform: scale(0.7); }
}
.voice-tip-fade-enter-active,
.voice-tip-fade-leave-active { transition: all 0.2s ease; }
.voice-tip-fade-enter-from,
.voice-tip-fade-leave-to { opacity: 0; transform: translateX(-50%) translateY(6px); }

</style>
