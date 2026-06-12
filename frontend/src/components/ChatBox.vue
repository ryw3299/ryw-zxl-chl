<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { interactQA } from '@/api/qa'
import { useLessonStore } from '@/store/lessonStore'

const props = defineProps({
  lessonId: {
    type: String,
    default: '',
  },
  courseId: {
    type: String,
    default: '',
  },
  userId: {
    type: String,
    default: '',
  },
  currentSectionId: {
    type: String,
    default: '',
  },
  currentPage: {
    type: Number,
    default: 1,
  },
  sessionId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['after-answer'])
const lessonStore = useLessonStore()

const inputText = ref('')
const sending = ref(false)
const recognizing = ref(false)
const voicePressing = ref(false)
const scrollRef = ref(null)
const speechTranscript = ref('')

let speechRecognition = null
let shouldSubmitAfterRecognitionEnd = false
let textBeforeVoiceInput = ''
let activeVoicePointerId = null

const localMessages = ref(
  lessonStore.chatHistory.length
    ? [...lessonStore.chatHistory]
    : [
      {
        id: `msg-${Date.now()}`,
        role: 'ai',
        text: '欢迎来到智悉云擎问答区，请输入你的问题。',
        createdAt: new Date().toISOString(),
      },
    ],
)

const browserSpeechRecognitionSupported = computed(() => {
  if (typeof window === 'undefined') {
    return false
  }
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
})

const voiceButtonText = computed(() => {
  if (!browserSpeechRecognitionSupported.value) {
    return '浏览器不支持语音'
  }
  if (sending.value) {
    return '发送中...'
  }
  if (voicePressing.value) {
    return '松开发送'
  }
  if (recognizing.value) {
    return '识别中...'
  }
  return '按住说话'
})

const voiceHintText = computed(() => {
  if (!browserSpeechRecognitionSupported.value) {
    return '当前浏览器不支持原生语音识别。'
  }
  if (voicePressing.value) {
    return '正在录音，松开后会自动识别并发送。'
  }
  if (recognizing.value) {
    return '正在识别语音，请稍候。'
  }
  return '按住按钮说话，松开后自动发送。'
})

const scrollToBottom = () => {
  nextTick(() => {
    const target = scrollRef.value
    if (target) {
      target.scrollTop = target.scrollHeight
    }
  })
}

watch(
  () => localMessages.value.length,
  () => {
    scrollToBottom()
    lessonStore.clearChatHistory()
    localMessages.value.forEach((item) => lessonStore.appendChatMessage(item))
  },
)

watch(
  () => props.currentSectionId,
  (newValue, oldValue) => {
    if (newValue && oldValue && newValue !== oldValue) {
      localMessages.value.push({
        id: `msg-${Date.now()}`,
        role: 'system',
        text: `已切换到章节 ${newValue}，提问将结合当前章节回答。`,
        createdAt: new Date().toISOString(),
      })
    }
  },
)

const formatMessageTime = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

const messageAuthor = (role) => {
  if (role === 'ai') {
    return 'AI 助教'
  }
  if (role === 'student') {
    return '我'
  }
  return '系统'
}

const displayAuthor = (role) => {
  if (role === 'ai') return 'AI 助教'
  if (role === 'student') return '我'
  return '系统'
}

const understandingLabel = (level) => {
  const value = String(level || '').trim()
  const map = {
    full: '掌握较好',
    partial: '部分理解',
    low: '需要巩固',
    medium: '基本理解',
    high: '掌握较好',
  }
  return map[value] || ''
}

const narrationLabel = (level) => {
  const value = String(level || '').trim().toUpperCase()
  const map = {
    A: '拓展版讲稿',
    B: '标准版讲稿',
    C: '细化版讲稿',
    D: '基础版讲稿',
  }
  return map[value] || value
}

const appendSystemMessage = (text) => {
  localMessages.value.push({
    id: `msg-${Date.now()}-system`,
    role: 'system',
    text,
    createdAt: new Date().toISOString(),
  })
}

const resetVoiceDraft = ({ restoreText = false } = {}) => {
  speechTranscript.value = ''
  if (restoreText) {
    inputText.value = textBeforeVoiceInput
  }
  textBeforeVoiceInput = ''
}

const sendMessage = async ({ questionOverride = '', questionType = 'text' } = {}) => {
  const question = String(questionOverride || inputText.value).trim()
  if (!question || sending.value) {
    return
  }

  localMessages.value.push({
    id: `msg-${Date.now()}-student`,
    role: 'student',
    text: question,
    createdAt: new Date().toISOString(),
  })
  inputText.value = ''
  speechTranscript.value = ''
  sending.value = true

  try {
    const result = await interactQA({
      userId: props.userId,
      lessonId: props.lessonId,
      courseId: props.courseId,
      currentSectionId: props.currentSectionId,
      currentPage: props.currentPage,
      sessionId: props.sessionId,
      questionType,
      question,
    })

    localMessages.value.push({
      id: `msg-${Date.now()}-ai`,
      role: 'ai',
      text: result.answer,
      relatedKnowledge: result.relatedKnowledge || [],
      understandingLevel: result.understandingLevel || '',
      suggestions: result.suggestions || [],
      nextAction: result.nextAction || '',
      recommendedNarrationLevel: result.recommendedNarrationLevel || '',
      reason: result.reason || '',
      createdAt: new Date().toISOString(),
    })

    emit('after-answer', {
      shouldResume: true,
      answerId: result.answerId,
      understandingLevel: result.understandingLevel,
      suggestions: result.suggestions || [],
      recommendedNarrationLevel: result.recommendedNarrationLevel || '',
      nextAction: result.nextAction || '',
      reason: result.reason || '',
      matchedSectionId: result.matchedSectionId || '',
      matchedPage: result.matchedPage,
      targetSectionId: result.targetSectionId || '',
      targetPage: result.targetPage,
    })
  } catch {
    localMessages.value.push({
      id: `msg-${Date.now()}-error`,
      role: 'ai',
      text: '当前问答服务不可用，请稍后再试。',
      createdAt: new Date().toISOString(),
    })
  } finally {
    sending.value = false
  }
}

const submitRecognizedSpeech = async (fallbackTranscript = '') => {
  const question = String(speechTranscript.value || fallbackTranscript || '').trim()
  if (!question) {
    resetVoiceDraft({ restoreText: true })
    appendSystemMessage('未识别到有效语音，请重试。')
    return
  }

  textBeforeVoiceInput = ''
  speechTranscript.value = question
  inputText.value = question
  await sendMessage({ questionOverride: question, questionType: 'voice' })
}

const clearSession = () => {
  localMessages.value = [
    {
      id: `msg-${Date.now()}-reset`,
      role: 'ai',
      text: '会话已清空。你可以继续提问。',
      createdAt: new Date().toISOString(),
    },
  ]
}

const useSuggestion = (suggestion) => {
  inputText.value = suggestion
  speechTranscript.value = ''
}

const resolveSpeechErrorMessage = (errorCode) => {
  switch (errorCode) {
    case 'not-allowed':
    case 'service-not-allowed':
      return '未获得麦克风或语音识别权限，请检查浏览器设置。'
    case 'audio-capture':
      return '未检测到可用麦克风，请检查设备。'
    case 'network':
      return '浏览器语音识别服务不可用，请稍后重试。'
    case 'no-speech':
      return '未识别到语音，请重试。'
    case 'aborted':
      return ''
    default:
      return '语音识别失败，请重试。'
  }
}

const hardStopSpeechRecognition = ({ restoreText = false, preservePressState = false } = {}) => {
  shouldSubmitAfterRecognitionEnd = false

  if (!speechRecognition) {
    if (restoreText) {
      resetVoiceDraft({ restoreText: true })
    }
    recognizing.value = false
    if (!preservePressState) {
      voicePressing.value = false
      activeVoicePointerId = null
    }
    return
  }

  const recognition = speechRecognition
  speechRecognition = null
  recognition.onstart = null
  recognition.onresult = null
  recognition.onerror = null
  recognition.onend = null

  try {
    recognition.abort()
  } catch {
    // Ignore abort failures during teardown.
  }

  recognizing.value = false
  if (!preservePressState) {
    voicePressing.value = false
    activeVoicePointerId = null
  }

  if (restoreText) {
    resetVoiceDraft({ restoreText: true })
  }
}

const startSpeechRecognition = () => {
  const RecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!RecognitionCtor) {
    appendSystemMessage('当前浏览器不支持原生语音识别。')
    return false
  }

  hardStopSpeechRecognition({ preservePressState: true })

  const recognition = new RecognitionCtor()
  let finalTranscript = ''
  let recognitionFailed = false

  textBeforeVoiceInput = inputText.value
  speechTranscript.value = ''
  shouldSubmitAfterRecognitionEnd = false

  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = true
  recognition.maxAlternatives = 1

  recognition.onstart = () => {
    recognizing.value = true
  }

  recognition.onresult = (event) => {
    let interimTranscript = ''
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index]
      const transcript = String(result?.[0]?.transcript || '')
      if (result.isFinal) {
        finalTranscript += transcript
      } else {
        interimTranscript += transcript
      }
    }

    const mergedTranscript = `${finalTranscript}${interimTranscript}`.trim()
    speechTranscript.value = mergedTranscript
    inputText.value = mergedTranscript
  }

  recognition.onerror = (event) => {
    recognitionFailed = true
    const message = resolveSpeechErrorMessage(event?.error)
    if (message) {
      appendSystemMessage(message)
    }
  }

  recognition.onend = async () => {
    if (speechRecognition === recognition) {
      speechRecognition = null
    }
    recognizing.value = false

    if (recognitionFailed) {
      shouldSubmitAfterRecognitionEnd = false
      resetVoiceDraft({ restoreText: true })
      return
    }

    if (!shouldSubmitAfterRecognitionEnd) {
      return
    }

    shouldSubmitAfterRecognitionEnd = false
    await submitRecognizedSpeech(finalTranscript)
  }

  speechRecognition = recognition

  try {
    recognition.start()
    return true
  } catch {
    speechRecognition = null
    recognizing.value = false
    resetVoiceDraft({ restoreText: true })
    appendSystemMessage('无法启动语音识别，请重试。')
    return false
  }
}

const startVoicePress = (event) => {
  if (sending.value || recognizing.value || voicePressing.value) {
    return
  }

  if (!browserSpeechRecognitionSupported.value) {
    appendSystemMessage('当前浏览器不支持原生语音识别。')
    return
  }

  if (event?.pointerType === 'mouse' && event.button !== 0) {
    return
  }

  voicePressing.value = true
  activeVoicePointerId = event?.pointerId ?? null
  event?.preventDefault?.()
  event?.currentTarget?.setPointerCapture?.(event.pointerId)

  if (!startSpeechRecognition()) {
    voicePressing.value = false
    activeVoicePointerId = null
  }
}

const finishVoicePress = async (event) => {
  if (!voicePressing.value) {
    return
  }

  if (
    activeVoicePointerId !== null
    && event?.pointerId != null
    && event.pointerId !== activeVoicePointerId
  ) {
    return
  }

  voicePressing.value = false
  activeVoicePointerId = null
  event?.preventDefault?.()

  if (speechRecognition) {
    shouldSubmitAfterRecognitionEnd = true
    try {
      speechRecognition.stop()
    } catch {
      hardStopSpeechRecognition({ restoreText: true })
      appendSystemMessage('无法结束语音识别，请重试。')
    }
    return
  }

  await submitRecognizedSpeech()
}

const cancelVoicePress = (event) => {
  if (!voicePressing.value) {
    return
  }

  if (
    activeVoicePointerId !== null
    && event?.pointerId != null
    && event.pointerId !== activeVoicePointerId
  ) {
    return
  }

  voicePressing.value = false
  activeVoicePointerId = null
  event?.preventDefault?.()
  hardStopSpeechRecognition({ restoreText: true })
}

onBeforeUnmount(() => {
  hardStopSpeechRecognition({ restoreText: false })
})
</script>

<template>
  <el-card class="chat-card" shadow="never" :body-style="{ padding: '0', display: 'flex', flexDirection: 'column' }">
    <!-- header -->
    <template #header>
      <div class="chat-header">
        <div>
          <div class="header-title">AI 助手</div>
          <div class="header-subtitle">可随时提问当前课程内容</div>
        </div>
        <el-button text type="danger" size="small" @click="clearSession">
          清空
        </el-button>
      </div>
    </template>

    <!-- 消息区 -->
    <div ref="scrollRef" class="chat-list">
      <div v-for="item in localMessages" :key="item.id" class="chat-item" :class="[`chat-item-${item.role}`]">
        <!-- system -->
        <template v-if="item.role === 'system'">
          <div class="system-msg">{{ item.text }}</div>
        </template>

        <!-- ai / user -->
        <template v-else>
          <div class="message-avatar" :class="`avatar-${item.role}`">
            {{ item.role === 'ai' ? 'AI' : '我' }}
          </div>
          <div class="message-panel">
            <div class="message-meta">
              <span>{{ displayAuthor(item.role) }}</span>
              <span>{{ formatMessageTime(item.createdAt) }}</span>
            </div>
            <div class="bubble">
              <div class="message-text">{{ item.text }}</div>

              <!-- 关联知识 -->
              <div v-if="item.role === 'ai' && item.relatedKnowledge?.length" class="meta-block">
                <div class="meta-label">关联知识</div>
                <div class="meta-tags">
                  <span v-for="tag in item.relatedKnowledge" :key="tag" class="tag">
                    {{ tag }}
                  </span>
                </div>
              </div>

              <!-- 理解程度 -->
              <div v-if="item.role === 'ai' && item.understandingLevel && item.understandingLevel !== 'none'" class="meta-block">
                <div class="meta-label">理解程度</div>
                <span class="level-tag">
                  {{ understandingLabel(item.understandingLevel) }}
                </span>
              </div>

              <div v-if="item.role === 'ai' && item.recommendedNarrationLevel" class="meta-block">
                <div class="meta-label">讲解策略</div>
                <span class="level-tag strategy-tag">
                  {{ narrationLabel(item.recommendedNarrationLevel) }}
                </span>
              </div>

              <!-- 推荐追问 -->
              <div v-if="item.role === 'ai' && item.suggestions?.length" class="meta-block">
                <div class="meta-label">推荐追问</div>
                <div class="meta-actions">
                  <div v-for="s in item.suggestions" :key="s" class="suggestion-item" @click="useSuggestion(s)">
                    {{ s }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input-wrapper">
      <div class="input-box">
        <el-input v-model="inputText" type="textarea" :rows="2" resize="none" class="gpt-input"
          placeholder="输入你的问题..." />

        <div class="input-actions">
          <!-- 🎤 -->
          <el-button circle class="icon-btn voice-btn" :class="{ active: voicePressing || recognizing }"
            :disabled="sending" @pointerdown="startVoicePress" @pointerup="finishVoicePress"
            @pointercancel="cancelVoicePress">
            🎤
          </el-button>

          <!-- ➤ -->
          <el-button circle type="primary" class="icon-btn send-btn" :loading="sending" @click="sendMessage">
            ➤
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.chat-card {
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-weight: 700;
  font-size: 16px;
}

.header-subtitle {
  font-size: 12px;
  color: #888;
}

/* 消息区 */
.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f7f9fb;
}

/* item */
.chat-item {
  display: flex;
  margin-bottom: 14px;
}

.chat-item-ai {
  justify-content: flex-start;
}

.chat-item-student {
  justify-content: flex-end;
}

/* system */
.system-msg {
  margin: 0 auto;
  font-size: 12px;
  color: #888;
}

/* 气泡 */
.message-panel {
  max-width: 80%;
}

.bubble {
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;

  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
}

/* AI */
.chat-item-ai .bubble {
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

/* 用户 */
.chat-item-student .bubble {
  background: #1677ff;
  color: #fff;
}

/* ========================= */
/* meta */
/* ========================= */

.meta-block {
  margin-top: 12px;
}

.meta-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}

/* 关联知识 */
.meta-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  background: #eef2ff;
  color: #3b5ccc;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;

  white-space: normal;
  word-break: break-word;
}

/* 理解程度 */
.level-tag {
  background: #dcfce7;
  color: #16a34a;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
}

/* 推荐追问 */
.meta-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-item {
  width: fit-content;
  max-width: 100%;

  padding: 8px 12px;
  border-radius: 12px;

  background: #f1f5f9;
  border: 1px solid #e2e8f0;

  font-size: 13px;
  line-height: 1.6;
  color: #334155;

  cursor: pointer;

  white-space: normal;
  word-break: break-word;
  overflow-wrap: break-word;

  transition: all 0.2s ease;
}

.suggestion-item:hover {
  background: #e2e8f0;
}

/* ========================= */
/* 输入区 */
/* ========================= */

.chat-input-wrapper {
  padding: 12px;
  border-top: 1px solid #eee;
  background: #fff;
}

.input-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 输入框 */
.gpt-input :deep(.el-textarea__inner) {
  border-radius: 20px;
  padding: 10px 14px;
  background: #f5f5f5;
  border: none;
}

/* 按钮 */
.input-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 40px;
  height: 40px;
  font-size: 16px;
}

/* 语音 */
.voice-btn.active {
  background: #ff4d4f;
  color: white;
}

/* 滚动条 */
.chat-list::-webkit-scrollbar {
  width: 6px;
}

.chat-list::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 10px;
}

/* Modern assistant panel overrides */
.chat-card {
  border: none;
  border-radius: 0;
  background: transparent;
}

.chat-header {
  padding: 2px 0;
}

.header-title {
  color: #0f172a;
  font-size: 14px;
  letter-spacing: 0;
}

.header-subtitle {
  margin-top: 2px;
  color: #64748b;
  font-size: 11.5px;
}

.clear-session {
  color: #64748b;
}

.chat-list {
  padding: 14px 12px 12px;
  background:
    radial-gradient(circle at 18% 0%, rgba(20, 184, 166, 0.08), transparent 34%),
    linear-gradient(180deg, #f8fafc 0%, #f6fbfb 100%);
}

.chat-item {
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 14px;
}

.chat-item-student {
  justify-content: flex-end;
  flex-direction: row;
}

.message-avatar {
  display: none;
}

.avatar-ai {
  color: #ffffff;
  border-color: rgba(20, 184, 166, 0.22);
  background: linear-gradient(135deg, #0f766e, #14b8a6);
}

.avatar-student {
  color: #2563eb;
  background: #ffffff;
}

.message-panel {
  max-width: 88%;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 2px 5px;
  color: #94a3b8;
  font-size: 10.5px;
  font-weight: 600;
}

.chat-item-student .message-meta {
  justify-content: flex-end;
}

.chat-item-student .message-panel {
  margin-left: auto;
}

.bubble,
.chat-item-ai .bubble,
.chat-item-student .bubble {
  color: #1e293b;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 14px;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.chat-item-ai .bubble {
  border-top-left-radius: 6px;
}

.chat-item-student .bubble {
  border-top-right-radius: 6px;
}

.message-text {
  color: #1f2937;
  font-size: 13px;
  line-height: 1.75;
}

.system-msg {
  padding: 5px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #64748b;
}

.meta-block {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eef2f7;
}

.meta-label {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.tag,
.level-tag {
  border: 1px solid rgba(153, 246, 228, 0.72);
  background: #f0fdfa;
  color: #0f766e;
  font-weight: 700;
}

.strategy-tag {
  border-color: rgba(191, 219, 254, 0.9);
  background: #eff6ff;
  color: #2563eb;
}

.meta-actions {
  flex-direction: row;
  flex-wrap: wrap;
}

.suggestion-item {
  all: unset;
  box-sizing: border-box;
  cursor: pointer;
  max-width: 100%;
  padding: 7px 10px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #ffffff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.06);
}

.suggestion-item:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
  transform: translateY(-1px);
}

.chat-input-wrapper {
  padding: 12px 12px 32px;
  border-top: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.94);
}

.input-box {
  align-items: flex-end;
  gap: 8px;
}

.gpt-input {
  flex: 1;
  min-width: 0;
}

.gpt-input :deep(.el-textarea__inner) {
  min-height: 52px !important;
  border: 1px solid #dbe7f3;
  border-radius: 16px;
  background: #f8fafc;
  color: #0f172a;
  box-shadow: none;
}

.gpt-input :deep(.el-textarea__inner:focus) {
  border-color: #99f6e4;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.12);
}

.input-actions {
  gap: 7px;
}

.icon-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #dbe7f3;
}

.voice-btn {
  color: #64748b;
  background: #ffffff;
}

.voice-btn.active {
  color: #0f766e;
  background: #ccfbf1;
}

.send-btn {
  border: 1px solid rgba(94, 234, 212, 0.85);
  background: linear-gradient(135deg, #99f6e4, #5eead4);
  color: #0f766e;
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.16);
}
</style>
