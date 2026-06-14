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
          <div class="thinking-dots"><span></span><span></span><span></span></div>
        </div>
      </div>
      <div class="chat-input-area" v-if="!profileDone">
        <div class="chat-input">
          <el-input v-model="userInput" placeholder="输入你的回答..." :disabled="isThinking" @keyup.enter="sendMessage" />
          <el-button type="primary" :disabled="isThinking || !userInput.trim()" @click="sendMessage"><el-icon><Promotion /></el-icon></el-button>
        </div>
      </div>
    </div>
    <div class="init-preview">
      <div class="preview-card">
        <div class="preview-header">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none"><rect x="2" y="2" width="24" height="24" rx="6" fill="#2563eb"/><path d="M8 14L12 18L20 10" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span>学习画像预览</span>
        </div>
        <div class="preview-section">
          <div class="preview-section-title">基本信息</div>
          <div class="preview-items">
            <div class="preview-item"><span class="pi-label">姓名</span><span class="pi-value" :class="{ empty: !collected.name }">{{ collected.name || '待采集' }}</span></div>
            <div class="preview-item"><span class="pi-label">专业</span><span class="pi-value" :class="{ empty: !collected.major }">{{ collected.major || '待采集' }}</span></div>
          </div>
        </div>
        <div v-if="isGenerating" class="preview-footer">
          <p class="gen-hint"><el-icon><Loading /></el-icon>AI 正在生成你的画像...</p>
        </div>
      </div>
    </div>
    <div v-if="profileDone" class="success-overlay">
      <div class="success-card">
        <el-result icon="success" title="学习方案已生成">
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
import { nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, Promotion, Loading } from '@element-plus/icons-vue'
import { useProfileStore } from '@/store/profileStore'

const router = useRouter()
const profileStore = useProfileStore()

const userInput = ref('')
const isThinking = ref(false)
const isGenerating = ref(false)
const profileDone = ref(false)
const profileSummary = ref('')
const msgRef = ref(null)

const collected = ref({ name: '', major: '' })

const messages = ref([
  { role: 'assistant', content: '你好呀！我是小智，你的专属 AI 学习助手 🎉<br><br>为了给你定制最合适的学习方案，我想先了解一些你的基本情况。<br><br><strong>你叫什么名字？目前读什么专业？</strong>' },
])

function sendMessage() {
  const text = userInput.value.trim()
  if (!text || isThinking.value) return
  userInput.value = ''
  messages.value.push({ role: 'user', content: text })
  scrollToBottom()

  // Extract info
  if (!collected.value.name) {
    collected.value.name = text.slice(0, 30)
    askMajor()
    return
  }
  if (!collected.value.major) {
    collected.value.major = text.slice(0, 30)
    // 收集到姓名和专业后自动生成
    autoGenerate()
    return
  }
}

function askMajor() {
  isThinking.value = true
  setTimeout(() => {
    isThinking.value = false
    messages.value.push({ role: 'assistant', content: `好的 <strong>${collected.value.name}</strong>！那<strong>你读什么专业的呢？</strong>` })
    scrollToBottom()
  }, 600)
}

async function autoGenerate() {
  isThinking.value = true
  setTimeout(async () => {
    isThinking.value = false
    messages.value.push({ role: 'assistant', content: `太棒了！<strong>${collected.value.name}</strong>，我已经了解你的基本情况了。现在让我为你生成专属学习画像吧 🎉` })
    scrollToBottom()

    isGenerating.value = true
    try {
      const chatData = messages.value.map(m => ({
        role: m.role,
        content: m.content.replace(/<[^>]*>/g, ''),
      }))
      const result = await profileStore.init(chatData)
      profileSummary.value = result?.summary || '你的个性化学习画像已生成！'
      profileDone.value = true
    } catch {
      profileDone.value = true
      profileSummary.value = '你的个性化学习画像已生成！'
    } finally {
      isGenerating.value = false
    }
  }, 1000)
}

function scrollToBottom() {
  nextTick(() => { if (msgRef.value) msgRef.value.scrollTop = msgRef.value.scrollHeight })
}
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
.thinking-dots { display: flex; gap: 4px; padding: 14px 18px; background: var(--bg-page); border-radius: 12px; }
.thinking-dots span { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); animation: dotPulse 1.4s infinite ease-in-out both; }
.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.32s; }
@keyframes dotPulse { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
.chat-input-area { padding: 16px 24px; border-top: 1px solid var(--border); }
.chat-input { display: flex; gap: 8px; }
.init-preview { width: 280px; flex-shrink: 0; }
.preview-card { background: white; border-radius: 14px; border: 1px solid var(--border); overflow: hidden; position: sticky; top: 84px; }
.preview-header { display: flex; align-items: center; gap: 8px; padding: 16px 20px; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 0.9rem; }
.preview-section { padding: 12px 20px; border-bottom: 1px solid var(--border-light); }
.preview-section-title { font-size: 0.78rem; font-weight: 500; color: var(--text-muted); margin-bottom: 8px; }
.preview-items { display: flex; flex-direction: column; gap: 6px; }
.preview-item { display: flex; justify-content: space-between; font-size: 0.82rem; }
.pi-label { color: var(--text-secondary); }
.pi-value { color: var(--text-primary); font-weight: 500; }
.pi-value.empty { color: var(--text-muted); font-weight: 400; }
.preview-footer { padding: 16px 20px; display: flex; align-items: center; gap: 6px; justify-content: center; font-size: 0.82rem; color: var(--text-muted); }
.success-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; z-index: 500; }
.success-card { background: white; border-radius: 18px; padding: 40px; max-width: 480px; width: 90%; box-shadow: var(--shadow-lg); }
.success-summary { font-size: 0.88rem; color: var(--text-secondary); line-height: 1.7; margin: 16px 0; }
.success-actions { display: flex; flex-direction: column; gap: 8px; }
</style>
