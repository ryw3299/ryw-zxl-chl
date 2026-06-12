<template>
  <div class="section">
    <h2>实时问答</h2>

    <!-- ── Session config panel ── -->
    <div class="api-card">
      <div class="api-header" @click="configOpen = !configOpen">
        <div class="api-title-row">
          <span class="method-badge post">CONFIG</span>
          <span class="api-desc">会话配置</span>
          <span v-if="sessionId" class="session-tag">Session: {{ sessionId }}</span>
        </div>
        <span class="expand-icon">{{ configOpen ? '▾' : '▸' }}</span>
      </div>
      <div v-show="configOpen" class="api-body">
        <div class="form-grid">
          <div class="form-group">
            <label>学校ID</label>
            <input v-model="config.schoolId" placeholder="sch10001" />
          </div>
          <div class="form-group">
            <label>用户ID(学生)</label>
            <input v-model="config.userId" placeholder="stu20001" />
          </div>
          <div class="form-group">
            <label>课程ID</label>
            <input v-model="config.courseId" placeholder="cou30001" />
          </div>
          <div class="form-group">
            <label>智课ID</label>
            <input v-model="config.lessonId" placeholder="lesson20240520001" />
          </div>
          <div class="form-group">
            <label>会话ID</label>
            <div class="input-with-btn">
              <input v-model="config.sessionId" placeholder="ses20240520001" />
              <button class="mini-btn" @click="newSession">新建会话</button>
            </div>
          </div>
          <div class="form-group">
            <label>当前章节ID(可选)</label>
            <input v-model="config.currentSectionId" placeholder="sec_1" />
          </div>
          <div class="form-group">
            <label>当前页码(可选)</label>
            <input v-model.number="config.currentPage" type="number" placeholder="1" />
          </div>
          <div class="form-group">
            <label>当前讲稿块ID(可选)</label>
            <input v-model="config.currentScriptBlockId" placeholder="script_2" />
          </div>
        </div>
      </div>
    </div>

    <!-- ── Chat panel ── -->
    <div class="chat-panel">
      <div class="chat-header">
        <span>多轮对话测试</span>
        <div class="chat-actions">
          <span class="turn-count">{{ messages.length / 2 }} 轮</span>
          <button class="mini-btn danger" @click="clearChat">清空对话</button>
        </div>
      </div>

      <div class="chat-messages" ref="chatContainer">
        <div v-if="messages.length === 0" class="chat-empty">
          输入问题开始多轮对话测试。同一个 Session ID 的对话历史会自动持久化。
        </div>
        <div v-for="(msg, i) in messages" :key="i" class="chat-msg" :class="msg.role">
          <div class="msg-avatar">{{ msg.role === 'user' ? '🧑‍🎓' : '🤖' }}</div>
          <div class="msg-body">
            <div class="msg-text">{{ msg.text }}</div>
            <div v-if="msg.meta" class="msg-meta">
              <div class="meta-grid">
                <div v-if="msg.meta.questionType" class="meta-item">
                  <span class="meta-label">问题类型</span>
                  <span class="meta-value tag">{{ msg.meta.questionType }}</span>
                </div>
                <div v-if="msg.meta.understandingLevel" class="meta-item">
                  <span class="meta-label">理解程度</span>
                  <span class="meta-value tag" :class="'ul-' + msg.meta.understandingLevel">{{ msg.meta.understandingLevel }}</span>
                </div>
                <div v-if="msg.meta.nextAction" class="meta-item">
                  <span class="meta-label">下一步</span>
                  <span class="meta-value tag action">{{ msg.meta.nextAction }}</span>
                </div>
                <div v-if="msg.meta.reason" class="meta-item wide">
                  <span class="meta-label">原因</span>
                  <span class="meta-value">{{ msg.meta.reason }}</span>
                </div>
                <div v-if="msg.meta.matchedSectionId" class="meta-item">
                  <span class="meta-label">命中章节</span>
                  <span class="meta-value mono">{{ msg.meta.matchedSectionId }}</span>
                </div>
                <div v-if="msg.meta.matchedPage != null" class="meta-item">
                  <span class="meta-label">命中页码</span>
                  <span class="meta-value mono">P{{ msg.meta.matchedPage }}</span>
                </div>
                <div v-if="msg.meta.targetSectionId" class="meta-item">
                  <span class="meta-label">目标章节</span>
                  <span class="meta-value mono">{{ msg.meta.targetSectionId }}</span>
                </div>
                <div v-if="msg.meta.targetPage != null" class="meta-item">
                  <span class="meta-label">目标页码</span>
                  <span class="meta-value mono">P{{ msg.meta.targetPage }}</span>
                </div>
                <div v-if="msg.meta.answerId" class="meta-item">
                  <span class="meta-label">Answer ID</span>
                  <span class="meta-value mono small">{{ msg.meta.answerId }}</span>
                </div>
              </div>
              <details v-if="msg.meta.suggestions && msg.meta.suggestions.length" class="suggestions">
                <summary>追问建议 ({{ msg.meta.suggestions.length }})</summary>
                <div class="suggestion-list">
                  <button v-for="s in msg.meta.suggestions" :key="s" class="suggestion-btn" @click="askQuestion(s)">
                    {{ s }}
                  </button>
                </div>
              </details>
              <details v-if="msg.meta.relatedKnowledge" class="suggestions">
                <summary>关联知识点</summary>
                <pre class="mini-json">{{ JSON.stringify(msg.meta.relatedKnowledge, null, 2) }}</pre>
              </details>
              <details class="suggestions">
                <summary>原始响应 JSON</summary>
                <pre class="mini-json">{{ JSON.stringify(msg.meta, null, 2) }}</pre>
              </details>
            </div>
            <div class="msg-time">{{ msg.time }}<span v-if="msg.elapsed" class="msg-elapsed"> · {{ msg.elapsed }}ms</span></div>
          </div>
        </div>
        <div v-if="loading" class="chat-msg assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-body">
            <div class="msg-text typing">思考中<span class="dots"><span>.</span><span>.</span><span>.</span></span></div>
          </div>
        </div>
      </div>

      <form class="chat-input" @submit.prevent="sendMessage">
        <input
          v-model="question"
          :disabled="loading"
          placeholder="输入学生问题..."
          autofocus
        />
        <button type="submit" :disabled="loading || !question.trim()" class="send-btn">
          {{ loading ? '...' : '发送' }}
        </button>
      </form>
    </div>

    <!-- ── Raw API tester (kept for direct testing) ── -->
    <details class="raw-tester-toggle">
      <summary>原始 API 测试器</summary>
      <ApiTester
        title="问答交互 (原始)"
        path="/api/v1/qa/interact"
        :fields="rawFields"
      />
      <ApiTester
        title="语音转文字"
        path="/api/v1/qa/voiceToText"
        :fields="[
          { name: 'voiceUrl', label: '语音文件URL', placeholder: 'http://xxx.com/question/voice/123.wav' },
          { name: 'voiceDuration', label: '语音时长(秒)', type: 'number', placeholder: '10' },
          { name: 'language', label: '语言', options: ['zh-CN', 'en-US'], default: 'zh-CN' },
          { name: 'enc', label: '签名', placeholder: 'DEBUG模式可留空' },
          { name: 'time', label: '时间戳', placeholder: 'DEBUG模式可留空' },
        ]"
      />
    </details>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import http from '../api/request.js'
import ApiTester from './ApiTester.vue'

const config = reactive({
  schoolId: 'sch10001',
  userId: 'stu20001',
  courseId: 'cou30001',
  lessonId: 'lesson20240520001',
  sessionId: 'ses20240520001',
  currentSectionId: '',
  currentPage: null,
  currentScriptBlockId: '',
})

const configOpen = ref(true)
const sessionId = ref(config.sessionId)
const question = ref('')
const loading = ref(false)
const messages = ref([])
const chatContainer = ref(null)

const rawFields = [
  { name: 'schoolId', label: '学校ID', placeholder: 'sch10001', default: 'sch10001' },
  { name: 'userId', label: '用户ID(学生)', placeholder: 'stu20001', default: 'stu20001' },
  { name: 'courseId', label: '课程ID', placeholder: 'cou30001', default: 'cou30001' },
  { name: 'lessonId', label: '智课ID', placeholder: 'lesson20240520001' },
  { name: 'sessionId', label: '会话ID', placeholder: 'ses20240520001', default: 'ses20240520001' },
  { name: 'questionType', label: '提问类型', options: ['text', 'voice'], default: 'text' },
  { name: 'questionContent', label: '提问内容', placeholder: '平面假设为什么能简化梁弯曲问题？' },
  { name: 'currentSectionId', label: '当前章节ID(可选)', placeholder: 'sec002' },
  { name: 'currentPage', label: '当前页码(可选)', type: 'number', placeholder: '3' },
  { name: 'currentScriptBlockId', label: '当前讲稿块ID(可选)', placeholder: 'script_2' },
  { name: 'historyQa', label: '历史问答(JSON)', type: 'json', placeholder: '[]' },
  { name: 'enc', label: '签名', placeholder: 'DEBUG模式可留空' },
  { name: 'time', label: '时间戳', placeholder: 'DEBUG模式可留空' },
]

function newSession() {
  config.sessionId = 'ses_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6)
  sessionId.value = config.sessionId
  messages.value = []
}

function clearChat() {
  messages.value = []
}

function askQuestion(q) {
  question.value = q
  sendMessage()
}

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function sendMessage() {
  const q = question.value.trim()
  if (!q || loading.value) return

  sessionId.value = config.sessionId
  configOpen.value = false

  messages.value.push({ role: 'user', text: q, time: now() })
  question.value = ''
  loading.value = true
  await scrollToBottom()

  const body = {
    schoolId: config.schoolId,
    userId: config.userId,
    courseId: config.courseId,
    lessonId: config.lessonId,
    sessionId: config.sessionId,
    questionType: 'text',
    questionContent: q,
  }
  if (config.currentSectionId) body.currentSectionId = config.currentSectionId
  if (config.currentPage) body.currentPage = config.currentPage
  if (config.currentScriptBlockId) body.currentScriptBlockId = config.currentScriptBlockId

  const start = Date.now()
  try {
    const res = await http.post('/api/v1/qa/interact', body)
    const elapsed = Date.now() - start
    const data = res.data?.data || res.data || {}

    messages.value.push({
      role: 'assistant',
      text: data.answerContent || '(无回答内容)',
      time: now(),
      elapsed,
      meta: data,
    })

    if (data.targetSectionId) config.currentSectionId = data.targetSectionId
    if (data.targetPage != null) config.currentPage = data.targetPage
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      text: `请求失败: ${e.message}`,
      time: now(),
      elapsed: Date.now() - start,
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}
</script>

<style scoped>
.session-tag {
  font-size: 11px;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 2px 8px;
  border-radius: 10px;
  font-family: "SF Mono", "Fira Code", monospace;
}

.input-with-btn {
  display: flex;
  gap: 6px;
}

.input-with-btn input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  background: #fafbfc;
}

.mini-btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.mini-btn:hover { background: #f1f5f9; border-color: var(--primary); }
.mini-btn.danger { color: var(--error); border-color: #fca5a5; }
.mini-btn.danger:hover { background: #fef2f2; }

/* Chat panel */
.chat-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  margin-top: 12px;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  font-size: 14px;
}

.chat-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.turn-count {
  font-size: 12px;
  color: var(--text-secondary);
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 10px;
}

.chat-messages {
  min-height: 200px;
  max-height: 520px;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8fafc;
}

.chat-empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 60px 20px;
  font-size: 14px;
}

.chat-msg {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.chat-msg.user { align-self: flex-end; flex-direction: row-reverse; }
.chat-msg.assistant { align-self: flex-start; }

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: #e2e8f0;
}

.msg-body { flex: 1; min-width: 0; }

.msg-text {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.user .msg-text {
  background: var(--primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant .msg-text {
  background: var(--surface);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}

.msg-time {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
  padding: 0 4px;
}

.user .msg-time { text-align: right; }

.msg-elapsed {
  color: #94a3b8;
}

/* Typing animation */
.typing .dots span {
  animation: blink 1.4s infinite;
  animation-fill-mode: both;
}
.typing .dots span:nth-child(2) { animation-delay: 0.2s; }
.typing .dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0% { opacity: 0.2; } 20% { opacity: 1; } 100% { opacity: 0.2; } }

/* Meta grid (agent decision info) */
.msg-meta {
  margin-top: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
}

.meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item.wide { flex-basis: 100%; }

.meta-label {
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.meta-value {
  color: var(--text);
}

.meta-value.tag {
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
}

.meta-value.tag { background: #e2e8f0; }
.meta-value.tag.action { background: #dbeafe; color: #1d4ed8; }
.meta-value.ul-full { background: #dcfce7; color: #15803d; }
.meta-value.ul-partial { background: #fef3c7; color: #92400e; }
.meta-value.ul-none { background: #fecdd3; color: #be123c; }
.meta-value.mono { font-family: "SF Mono", "Fira Code", monospace; }
.meta-value.small { font-size: 10px; }

.suggestions {
  margin-top: 8px;
}

.suggestions summary {
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  color: var(--primary);
}

.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.suggestion-btn {
  padding: 4px 10px;
  border: 1px solid var(--primary);
  border-radius: 14px;
  background: #eff6ff;
  color: var(--primary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-btn:hover { background: var(--primary); color: #fff; }

.mini-json {
  margin-top: 6px;
  padding: 8px;
  background: #fafbfc;
  border-radius: 6px;
  font-size: 11px;
  font-family: "SF Mono", "Fira Code", monospace;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Chat input */
.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface);
}

.chat-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: #fafbfc;
  transition: border-color 0.2s;
}

.chat-input input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.chat-input .send-btn {
  padding: 10px 20px;
  margin-top: 0;
}

/* Raw tester toggle */
.raw-tester-toggle {
  margin-top: 20px;
}

.raw-tester-toggle summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 8px 0;
}
</style>
