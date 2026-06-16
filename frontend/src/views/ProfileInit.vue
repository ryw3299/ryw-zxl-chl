<template>
  <div class="init-page">
    <div class="init-chat">
      <div class="chat-header">
        <h2>初始化个人信息</h2>
        <p>让小智更了解你，为你量身定制专属学习方案</p>
      </div>
      <div class="chat-messages" ref="msgRef">
        <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
          <div class="msg-avatar" v-if="msg.role === 'assistant'">
            <svg width="18" height="18" viewBox="0 0 28 28" fill="none"><rect x="7" y="10" width="14" height="10" rx="3" fill="#2563eb"/><circle cx="11" cy="15" r="1.5" fill="white"/><circle cx="17" cy="15" r="1.5" fill="white"/></svg>
          </div>
          <div class="msg-avatar" v-else>我</div>
          <div class="msg-content" v-html="msg.content"></div>
        </div>
        <div v-if="isThinking && !profileDone" class="msg assistant">
          <div class="msg-avatar">
            <svg width="18" height="18" viewBox="0 0 28 28" fill="none"><rect x="7" y="10" width="14" height="10" rx="3" fill="#2563eb"/><circle cx="11" cy="15" r="1.5" fill="white"/><circle cx="17" cy="15" r="1.5" fill="white"/></svg>
          </div>
          <div class="thinking-card">
            <div class="thinking-dots"><span></span><span></span><span></span></div>
            <p class="thinking-text">正在为你记录信息并整理追问，可能需要一分钟左右，复杂情况会更久一点。</p>
          </div>
        </div>
      </div>
      <div class="chat-input-area" v-if="!profileDone">
        <div v-if="isGenerating" class="chat-status">
          <el-icon class="chat-status-icon is-loading"><Loading /></el-icon>
          <span>{{ generatingText }}</span>
        </div>
        <div class="chat-input">
          <el-input v-model="userInput" placeholder="输入你的回答..." :disabled="isThinking" @keyup.enter="sendMessage" />
          <el-button type="primary" :disabled="isThinking || !userInput.trim()" @click="sendMessage"><el-icon><Promotion /></el-icon></el-button>
        </div>
      </div>
    </div>
    <aside class="intro-guide">
      <div class="guide-card">
        <div class="guide-header">
          <div class="guide-icon">
            <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
              <rect x="2" y="2" width="24" height="24" rx="6" fill="#2563eb" />
              <path d="M9 11.5H19" stroke="white" stroke-width="2.2" stroke-linecap="round" />
              <path d="M9 16H16" stroke="white" stroke-width="2.2" stroke-linecap="round" />
            </svg>
          </div>
          <div>
            <h3>可以自我介绍的方向</h3>
            <p>不需要一次说全，先从你最想说的部分开始就可以。</p>
          </div>
        </div>
        <div class="guide-section" v-for="section in introDirections" :key="section.title">
          <div class="guide-section-title">{{ section.title }}</div>
          <div class="guide-tags">
            <span v-for="item in section.items" :key="item" class="guide-tag">{{ item }}</span>
          </div>
        </div>
        <div v-if="isGenerating" class="guide-footer">
          <p class="gen-hint"><el-icon><Loading /></el-icon>{{ generatingText }}</p>
        </div>
      </div>
    </aside>
    <div v-if="showSuccessOverlay" class="success-overlay">
      <div class="success-card">
        <el-result icon="success" title="学习画像已生成">
          <template #extra>
            <p class="success-summary">{{ profileSummary }}</p>
            <div class="success-actions">
              <el-button type="primary" @click="$router.push('/profile')">查看画像</el-button>
              <el-button @click="$router.push('/learning-path')">生成学习路径</el-button>
              <el-button @click="$router.push('/dashboard')">稍后再说</el-button>
            </div>
          </template>
        </el-result>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Promotion, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useProfileStore } from '@/store/profileStore'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const profileStore = useProfileStore()
const userStore = useUserStore()

const DEFAULT_MESSAGES = [
  {
    role: 'assistant',
    content:
      '你好，我是小智。为了更好地为你制定专属于你自己的学习路径，请问你可以先简单做个自我介绍吗？<br><br>比如你的姓名、年级、专业，现在在学什么，想往什么方向发展，或者最近觉得哪些地方比较吃力。',
  },
]

const userInput = ref('')
const isThinking = ref(false)
const isGenerating = ref(false)
const profileDone = ref(false)
const showSuccessOverlay = ref(false)
const profileSummary = ref('')
const generatingText = ref('正在为你记录信息并整理追问，请稍等。')
const msgRef = ref(null)
const conversationId = ref('')
const draftRestored = ref(false)

const introDirections = [
  {
    title: '基础信息',
    items: ['姓名', '年级', '专业', '当前课程'],
  },
  {
    title: '学习目标',
    items: ['想往哪个方向发展', '近期想达成什么结果', '希望做出什么作品'],
  },
  {
    title: '当前情况',
    items: ['学到哪里了', '哪些内容掌握得还不错', '哪些地方最吃力'],
  },
  {
    title: '学习方式',
    items: ['每天能投入多久', '喜欢看文档还是视频', '更偏好练习还是项目'],
  },
]

const messages = ref([...DEFAULT_MESSAGES])

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || isThinking.value) return
  userInput.value = ''
  messages.value.push({ role: 'user', content: text })
  saveDraftState()
  scrollToBottom()
  isThinking.value = true
  isGenerating.value = true
  generatingText.value = '正在为你记录信息并整理追问，请稍等。'
  try {
    const chatData = messages.value.map(m => ({
      role: m.role,
      content: m.content.replace(/<[^>]*>/g, ''),
    }))
    const result = await profileStore.init(chatData, conversationId.value)
    conversationId.value = result?.conversation_id || conversationId.value

    if (result?.profile_ready) {
      const completionMessage =
        result?.frontend_message || '你的个性化学习画像已生成，接下来可以查看画像或继续生成学习路径。'
      messages.value.push({ role: 'assistant', content: formatAssistantMessage(completionMessage) })
      profileSummary.value =
        result?.profile_summary || result?.summary || completionMessage
      scrollToBottom()
      profileDone.value = true
      clearDraftState()
      await wait(900)
      showSuccessOverlay.value = true
      return
    }

    const reply =
      result?.frontend_message ||
      '我已经记录了这些信息。接下来请继续补充你的学习目标、当前基础、薄弱点和时间安排。'
    isThinking.value = false
    messages.value.push({ role: 'assistant', content: formatAssistantMessage(reply) })
    saveDraftState()
    scrollToBottom()
  } catch (error) {
    ElMessage.error(error?.message || '画像生成失败，请稍后重试')
    isThinking.value = false
    saveDraftState()
  } finally {
    isThinking.value = false
    isGenerating.value = false
  }
}

function formatAssistantMessage(text) {
  return escapeHtml(String(text || ''))
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function scrollToBottom() {
  nextTick(() => { if (msgRef.value) msgRef.value.scrollTop = msgRef.value.scrollHeight })
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function getDraftStorageKey() {
  const userId = userStore.user?.id || userStore.username || 'anonymous'
  return `profile-init-draft:${userId}`
}

function getLocalDraftTimestamp(draft) {
  const value = draft?.updatedAt
  if (typeof value === 'number') return value
  return value ? Date.parse(value) || 0 : 0
}

function normalizeMessageForDisplay(message, fromServer = false) {
  if (!message || !message.role || !message.content) return null
  if (message.role === 'assistant' && fromServer) {
    return { role: 'assistant', content: formatAssistantMessage(message.content) }
  }
  return {
    role: message.role,
    content: String(message.content),
  }
}

function saveDraftState() {
  if (profileDone.value) return
  localStorage.setItem(
    getDraftStorageKey(),
    JSON.stringify({
      messages: messages.value,
      conversationId: conversationId.value,
      userInput: userInput.value,
      updatedAt: Date.now(),
    }),
  )
}

function clearDraftState() {
  localStorage.removeItem(getDraftStorageKey())
}

function loadLocalDraft() {
  try {
    return JSON.parse(localStorage.getItem(getDraftStorageKey()) || 'null')
  } catch {
    return null
  }
}

function applyDraftState(draft, fromServer = false) {
  const restoredMessages = Array.isArray(draft?.messages)
    ? draft.messages
        .map(item => normalizeMessageForDisplay(item, fromServer))
        .filter(Boolean)
    : []
  if (restoredMessages.length) {
    messages.value = restoredMessages
  }
  conversationId.value = draft?.conversationId || draft?.conversation_id || ''
  userInput.value = draft?.userInput || ''
}

async function restoreDraftState() {
  const localDraft = loadLocalDraft()
  let serverDraft = null
  try {
    serverDraft = await profileStore.fetchInitState()
  } catch {
    serverDraft = null
  }

  const localTs = getLocalDraftTimestamp(localDraft)
  const serverTs = getLocalDraftTimestamp({ updatedAt: serverDraft?.updated_at })
  const hasLocalDraft = Array.isArray(localDraft?.messages) && localDraft.messages.length > 1
  const hasServerDraft = Boolean(serverDraft?.has_draft && serverDraft?.messages?.length)

  if (!hasLocalDraft && !hasServerDraft) return

  if (hasServerDraft && (!hasLocalDraft || serverTs > localTs)) {
    applyDraftState(serverDraft, true)
    saveDraftState()
  } else if (hasLocalDraft) {
    applyDraftState(localDraft, false)
  }

  draftRestored.value = true
  scrollToBottom()
  ElMessage.success('已恢复你上次未完成的画像初始化会话')
}

watch(userInput, () => {
  if (draftRestored.value || userInput.value) {
    saveDraftState()
  }
})

onMounted(async () => {
  await restoreDraftState()
})
</script>

<style scoped>
.init-page { display: flex; gap: 24px; min-height: calc(100vh - 100px); }
.init-chat { flex: 1; display: flex; flex-direction: column; background: white; border-radius: 14px; border: 1px solid var(--border); overflow: hidden; }
.chat-header { padding: 20px 24px; border-bottom: 1px solid var(--border-light); }
.chat-header h2 { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.chat-header p { font-size: 0.85rem; color: var(--text-secondary); }
.chat-messages { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.msg { display: flex; gap: 10px; max-width: 85%; }
.msg.user { align-self: flex-end; flex-direction: row-reverse; }
.msg-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--brand-primary-light); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 0.75rem; font-weight: 600; color: var(--brand-primary); }
.msg.user .msg-avatar { background: var(--brand-primary); color: white; }
.msg-content { padding: 12px 16px; border-radius: 12px; font-size: 0.88rem; line-height: 1.7; }
.msg.assistant .msg-content { background: var(--bg-page); color: var(--text-primary); border-bottom-left-radius: 4px; }
.msg.user .msg-content { background: var(--brand-primary); color: white; border-bottom-right-radius: 4px; }
.msg-content :deep(strong) { font-weight: 600; }
.thinking-card { display: flex; flex-direction: column; align-items: flex-start; gap: 10px; padding: 14px 18px; background: var(--bg-page); border-radius: 12px; }
.thinking-dots { display: flex; gap: 4px; }
.thinking-dots span { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); animation: dotPulse 1.4s infinite ease-in-out both; }
.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.32s; }
.thinking-text { font-size: 0.82rem; line-height: 1.6; color: var(--text-secondary); }
@keyframes dotPulse { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
.chat-input-area { padding: 16px 24px; border-top: 1px solid var(--border); }
.chat-status { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding: 10px 12px; border-radius: 12px; background: rgba(37, 99, 235, 0.06); color: #1d4ed8; font-size: 0.82rem; }
.chat-status-icon { font-size: 0.95rem; }
.chat-input { display: flex; gap: 8px; }
.intro-guide { width: 300px; flex-shrink: 0; }
.guide-card { background: white; border-radius: 18px; border: 1px solid var(--border); overflow: hidden; position: sticky; top: 84px; box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05); }
.guide-header { display: flex; gap: 12px; padding: 18px 20px 16px; border-bottom: 1px solid var(--border-light); background: linear-gradient(180deg, rgba(37, 99, 235, 0.06) 0%, rgba(37, 99, 235, 0) 100%); }
.guide-icon { width: 40px; height: 40px; border-radius: 12px; background: rgba(37, 99, 235, 0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.guide-header h3 { font-size: 0.98rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.guide-header p { font-size: 0.8rem; line-height: 1.6; color: var(--text-secondary); }
.guide-section { padding: 14px 20px; border-bottom: 1px solid var(--border-light); }
.guide-section-title { font-size: 0.79rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.guide-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.guide-tag { display: inline-flex; align-items: center; min-height: 32px; padding: 0 12px; border-radius: 999px; background: var(--bg-page); color: var(--text-primary); font-size: 0.8rem; line-height: 1.2; }
.guide-footer { padding: 16px 20px; display: flex; align-items: center; justify-content: center; }
.success-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; z-index: 500; }
.success-card { background: white; border-radius: 18px; padding: 40px; max-width: 480px; width: 90%; box-shadow: var(--shadow-lg); }
.success-summary { font-size: 0.88rem; color: var(--text-secondary); line-height: 1.7; margin: 16px 0; }
.success-actions { display: flex; flex-direction: column; gap: 8px; }
@media (max-width: 1080px) {
  .init-page { flex-direction: column; }
  .intro-guide { width: 100%; }
  .guide-card { position: static; }
}
</style>
