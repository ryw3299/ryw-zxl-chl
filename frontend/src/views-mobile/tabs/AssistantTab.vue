<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { showToast } from 'vant'
import { interactQA } from '@/api/qa'
import { useLessonStore } from '@/store/lessonStore'

const lessonStore = useLessonStore()

const messageInput = ref('')
const isTyping = ref(false)
const chatListRef = ref(null)
const chatHistory = ref([])

const messages = ref([
  { id: 'sys-1', type: 'system', text: '已接入课程 AI 助手' },
  {
    id: 'ai-1',
    role: 'ai',
    text: '同学你好！我是你的专属 AI 课代表。\n\n你可以问我本章知识点、例题解法，或者说"总结本节"让我帮你梳理重点。',
    time: '',
    status: 'success',
  },
])

const quickPrompts = [
  '帮我总结本节重点',
  '这道例题有其他解法吗？',
  '我没听懂这个推导',
  '考试重点是什么？',
]

const canSend = computed(() => messageInput.value.trim().length > 0 && !isTyping.value)

const now = () =>
  new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })

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
    const ctx = lessonStore.platformContext
    const res = await interactQA({
      userId: ctx.userId,
      courseId: ctx.courseId || lessonStore.courseInfo.courseId,
      lessonId: ctx.lessonId || lessonStore.lessonInfo.lessonId,
      schoolId: ctx.schoolId,
      question: content,
      currentPage: lessonStore.lessonInfo.currentPage,
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
    showToast('AI 助手暂时不可用，请稍后重试')
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
</script>

<template>
  <div class="chat-root">
    <!-- 消息列表 -->
    <div class="chat-messages" ref="chatListRef">
      <template v-for="msg in messages" :key="msg.id">

        <!-- 系统提示 -->
        <div v-if="msg.type === 'system'" class="sys-msg">
          <span>{{ msg.text }}</span>
        </div>

        <!-- 对话气泡 -->
        <div v-else class="bubble-row" :class="`is-${msg.role}`">
          <div v-if="msg.role === 'ai'" class="bubble-avatar bubble-avatar--ai">
            <van-icon name="gem-o" size="16" color="#fff" />
          </div>

          <div class="bubble-content">
            <div class="bubble-box" :class="{ 'bubble-box--error': msg.status === 'error' }">
              <span v-for="(line, i) in msg.text.split('\n')" :key="i">
                {{ line }}<br v-if="i < msg.text.split('\n').length - 1" />
              </span>
            </div>
            <div class="bubble-meta" v-if="msg.time">
              <span>{{ msg.time }}</span>
              <van-loading v-if="msg.status === 'sending'" size="10px" color="#9aa3b2" />
              <van-icon v-if="msg.status === 'error'" name="warning-o" size="12" color="#f53f3f" />
            </div>
          </div>

          <div v-if="msg.role === 'user'" class="bubble-avatar bubble-avatar--user">
            我
          </div>
        </div>

      </template>

      <!-- 打字中 -->
      <div v-if="isTyping" class="bubble-row is-ai">
        <div class="bubble-avatar bubble-avatar--ai">
          <van-icon name="gem-o" size="16" color="#fff" />
        </div>
        <div class="bubble-box typing-box">
          <span class="dot" /><span class="dot" /><span class="dot" />
        </div>
      </div>
    </div>

    <!-- 底部交互区 -->
    <div class="chat-bottom">
      <!-- 快捷提问 -->
      <div class="quick-row">
        <button
          v-for="p in quickPrompts"
          :key="p"
          class="quick-chip"
          @click="sendMessage(p)"
        >{{ p }}</button>
      </div>

      <!-- 输入框 -->
      <div class="input-row">
        <van-field
          v-model="messageInput"
          type="textarea"
          rows="1"
          autosize
          :maxlength="300"
          placeholder="向 AI 提问..."
          class="chat-field"
          :border="false"
          @keydown="handleKeydown"
        />
        <button
          class="send-btn"
          :class="{ 'send-btn--active': canSend }"
          :disabled="!canSend"
          @click="sendMessage()"
        >
          <van-icon name="guide-o" size="19" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-root {
  display: flex;
  flex-direction: column;
  height: clamp(400px, calc(100dvh - 300px), 600px);
  background: #f5f7fa;
  border-radius: inherit;
  overflow: hidden;
}



/* ── 消息列表 ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-messages::-webkit-scrollbar {
  width: 0;
}

/* 系统消息 */
.sys-msg {
  text-align: center;
}

.sys-msg span {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 999px;
  background: #e8ecf2;
  font-size: 11px;
  color: #9aa3b2;
}

/* 气泡行 */
.bubble-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 88%;
}

.bubble-row.is-user {
  align-self: flex-end;
}

.bubble-row.is-ai {
  align-self: flex-start;
}

/* 头像 */
.bubble-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 800;
}

.bubble-avatar--ai {
  background: linear-gradient(135deg, #1677ff, #46aaff);
  box-shadow: 0 4px 10px rgba(22, 119, 255, 0.25);
}

.bubble-avatar--user {
  background: #1a2035;
  color: #fff;
}

/* 气泡内容 */
.bubble-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.is-user .bubble-content {
  align-items: flex-end;
}

.bubble-box {
  padding: 11px 14px;
  border-radius: 4px 16px 16px 16px;
  background: #fff;
  font-size: 14px;
  line-height: 1.75;
  color: #1a2035;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  word-break: break-word;
  white-space: pre-wrap;
}

.is-user .bubble-box {
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 4px 14px rgba(22, 119, 255, 0.28);
}

.bubble-box--error {
  border: 1px solid #f53f3f;
}

.bubble-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #b0b9c8;
}

/* 打字中 */
.typing-box {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 14px 18px;
  min-width: 60px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c5cdd8;
  animation: blink 1.3s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.3s; }
.dot:nth-child(2) { animation-delay: -0.15s; }

@keyframes blink {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* ── 底部 ── */
.chat-bottom {
  background: #fff;
  border-top: 1px solid #eef0f4;
  padding: 10px 14px 16px;
  flex-shrink: 0;
}

.quick-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.quick-row::-webkit-scrollbar { display: none; }

.quick-chip {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #d4e4ff;
  background: #f0f6ff;
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: #f5f7fa;
  border-radius: 16px;
  padding: 4px 6px 4px 14px;
}

.chat-field {
  flex: 1;
  background: transparent;
  padding: 0;
  font-size: 14px;
}

.chat-field :deep(.van-field__control) {
  max-height: 80px;
  font-size: 14px;
  line-height: 1.6;
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: #e4e8ef;
  color: #b0b9c8;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s;
  cursor: pointer;
  margin-bottom: 2px;
}

.send-btn--active {
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.32);
}
</style>
