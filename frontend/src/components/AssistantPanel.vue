<template>
  <div class="assistant-panel" :class="{ collapsed: !assistantStore.isOpen }">
    <!-- Toggle button -->
    <button v-if="!assistantStore.isOpen" class="assistant-toggle" @click="assistantStore.open()">
      <div class="toggle-robot">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="13" fill="#2563eb" opacity="0.15"/>
          <rect x="7" y="10" width="14" height="10" rx="3" fill="#2563eb"/>
          <circle cx="11" cy="15" r="1.5" fill="white"/>
          <circle cx="17" cy="15" r="1.5" fill="white"/>
          <rect x="12" y="18" width="4" height="1.5" rx="0.75" fill="white"/>
          <circle cx="14" cy="7" r="2" fill="#2563eb"/>
        </svg>
      </div>
      <span class="toggle-text">AI 助教</span>
    </button>

    <!-- Panel -->
    <div v-else class="panel-wrap">
      <div class="panel-header">
        <div class="panel-title">
          <svg width="20" height="20" viewBox="0 0 28 28" fill="none">
            <rect x="7" y="10" width="14" height="10" rx="3" fill="#2563eb"/>
            <circle cx="11" cy="15" r="1.5" fill="white"/>
            <circle cx="17" cy="15" r="1.5" fill="white"/>
            <rect x="12" y="18" width="4" height="1.5" rx="0.75" fill="white"/>
          </svg>
          <span>AI助教</span>
        </div>
        <button class="panel-close" @click="assistantStore.close()"><el-icon><Close /></el-icon></button>
      </div>

      <!-- Tabs -->
      <div class="panel-tabs">
        <button v-for="tab in tabs" :key="tab.key" :class="['tab-btn', { active: activeTab === tab.key }]" @click="activeTab = tab.key">{{ tab.label }}</button>
      </div>

      <!-- Chat -->
      <div v-if="activeTab === 'chat'" class="panel-body">
        <!-- Context items -->
        <div v-if="assistantStore.contextItems.length" class="context-bar">
          <div class="context-label">已加载上下文</div>
          <div class="context-chip" v-for="item in assistantStore.contextItems" :key="item.id">
            <el-icon v-if="item.type === 'text'"><Document /></el-icon>
            <el-icon v-else><Picture /></el-icon>
            <span class="chip-text">{{ item.content?.slice(0, 30) }}{{ item.content?.length > 30 ? '...' : '' }}</span>
            <el-icon class="chip-close" @click="assistantStore.removeContext(item.id)"><Close /></el-icon>
          </div>
        </div>

        <!-- Messages -->
        <div class="messages" ref="msgRef">
          <div v-for="msg in assistantStore.messages" :key="msg.id" :class="['msg', msg.role]">
            <div class="msg-avatar" v-if="msg.role === 'assistant'">
              <svg width="16" height="16" viewBox="0 0 28 28" fill="none"><rect x="7" y="10" width="14" height="10" rx="3" fill="#2563eb"/><circle cx="11" cy="15" r="1.5" fill="white"/><circle cx="17" cy="15" r="1.5" fill="white"/></svg>
            </div>
            <div class="msg-avatar" v-else>我</div>
            <div class="msg-bubble">{{ msg.content }}</div>
          </div>
          <div v-if="assistantStore.isThinking" class="msg assistant">
            <div class="msg-avatar">
              <svg width="16" height="16" viewBox="0 0 28 28" fill="none"><rect x="7" y="10" width="14" height="10" rx="3" fill="#2563eb"/><circle cx="11" cy="15" r="1.5" fill="white"/><circle cx="17" cy="15" r="1.5" fill="white"/></svg>
            </div>
            <div class="thinking-dots"><span></span><span></span><span></span></div>
          </div>
        </div>

        <!-- Quick replies -->
        <div class="quick-replies">
          <button v-for="q in quickReplies" :key="q" class="quick-reply" @click="quickSend(q)">{{ q }}</button>
          <button class="quick-reply refresh" @click="refreshReplies">🔄 换一换</button>
        </div>

        <!-- Input -->
        <div class="panel-input">
          <div class="input-actions">
            <button class="input-action-btn" title="截图" @click="onScreenshot"><el-icon><Camera /></el-icon></button>
            <button class="input-action-btn" title="上传图片" @click="onUpload"><el-icon><Upload /></el-icon></button>
          </div>
          <div class="input-row">
            <el-input
              v-model="inputText"
              placeholder="输入你的问题..."
              :disabled="assistantStore.isThinking"
              @keyup.enter="send"
            />
            <el-button type="primary" :disabled="assistantStore.isThinking || !inputText.trim()" @click="send" :loading="assistantStore.isThinking">
              <el-icon><Promotion /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <!-- Notes tab -->
      <div v-if="activeTab === 'notes'" class="panel-body">
        <div class="notes-list">
          <div class="note-empty"><el-icon :size="24"><EditPen /></el-icon><p>暂无笔记</p></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { Close, Document, Picture, Camera, Upload, Promotion, EditPen } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAssistantStore } from '@/store/assistantStore'

const assistantStore = useAssistantStore()
const activeTab = ref('chat')
const inputText = ref('')
const msgRef = ref(null)

const tabs = [
  { key: 'chat', label: '问答' },
  { key: 'notes', label: '笔记' },
]

const quickRepliesPool = [
  '生成思维导图', '出一道题', '继续追问', '举一个生活中的例子',
  '总结本节知识', '有哪些常见错误？', '推荐相关学习资源', '画个流程图说明',
  '解释这段内容', '举反例说明', '这段代码什么意思？', '帮我整理笔记',
]

const quickReplies = ref(quickRepliesPool.slice(0, 4))

function refreshReplies() {
  const shuffled = [...quickRepliesPool].sort(() => Math.random() - 0.5)
  quickReplies.value = shuffled.slice(0, 4)
}

watch(() => assistantStore.messages.length, () => scrollToBottom())
watch(() => assistantStore.isThinking, () => scrollToBottom())

function scrollToBottom() {
  nextTick(() => {
    if (msgRef.value) msgRef.value.scrollTop = msgRef.value.scrollHeight
  })
}

async function send() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await assistantStore.sendMessage(text)
}

function quickSend(text) {
  inputText.value = text
  send()
}

function onScreenshot() {
  ElMessage.info('截图功能即将上线')
}

function onUpload() {
  ElMessage.info('图片上传功能即将上线')
}
</script>

<style scoped>
.assistant-panel { position: fixed; right: 0; top: 0; height: 100vh; z-index: 300; display: flex; }
.assistant-toggle {
  position: fixed; right: 20px; bottom: 100px; width: 52px; height: 52px; border: none; border-radius: 50%;
  background: white; box-shadow: 0 4px 16px rgba(37,99,235,0.2); cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
  transition: box-shadow 0.2s, transform 0.2s; z-index: 300;
}
.assistant-toggle:hover { box-shadow: 0 6px 20px rgba(37,99,235,0.3); transform: scale(1.05); }
.toggle-text { font-size: 0.6rem; color: var(--brand-primary); font-weight: 500; }

.panel-wrap {
  width: 360px; height: 100vh; background: white; border-left: 1px solid var(--border);
  display: flex; flex-direction: column; box-shadow: -4px 0 20px rgba(0,0,0,0.06);
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 16px 12px; border-bottom: 1px solid var(--border-light);
}
.panel-title { display: flex; align-items: center; gap: 8px; font-size: 1rem; font-weight: 600; color: var(--text-primary); }
.panel-close { border: none; background: transparent; cursor: pointer; color: var(--text-muted); padding: 4px; border-radius: 4px; display: flex; }
.panel-close:hover { background: var(--bg-hover); }

.panel-tabs { display: flex; border-bottom: 1px solid var(--border-light); padding: 0 16px; }
.tab-btn {
  padding: 10px 16px; border: none; background: transparent; font-size: 0.85rem; color: var(--text-muted);
  cursor: pointer; border-bottom: 2px solid transparent; transition: color 0.2s, border-color 0.2s; font-family: inherit;
}
.tab-btn.active { color: var(--brand-primary); border-bottom-color: var(--brand-primary); font-weight: 500; }

.panel-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* Context bar */
.context-bar {
  padding: 8px 12px; border-bottom: 1px solid var(--border-light);
  display: flex; flex-direction: column; gap: 4px;
}
.context-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.context-chip {
  display: flex; align-items: center; gap: 4px; padding: 4px 8px;
  background: var(--bg-selected); border-radius: 4px; font-size: 0.75rem; color: var(--brand-primary);
}
.chip-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-close { cursor: pointer; font-size: 12px; }
.chip-close:hover { color: var(--text-primary); }

/* Messages */
.messages { flex: 1; overflow-y: auto; padding: 12px 16px; display: flex; flex-direction: column; gap: 12px; }
.msg { display: flex; gap: 8px; max-width: 100%; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar {
  width: 28px; height: 28px; border-radius: 50%; background: var(--brand-primary-light);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  font-size: 0.7rem; font-weight: 600; color: var(--brand-primary);
}
.msg.user .msg-avatar { background: var(--brand-primary); color: white; }
.msg-bubble {
  padding: 10px 14px; border-radius: 12px; font-size: 0.82rem; line-height: 1.6; max-width: 85%;
}
.msg.assistant .msg-bubble { background: var(--bg-page); color: var(--text-primary); border-bottom-left-radius: 4px; }
.msg.user .msg-bubble { background: var(--brand-primary); color: white; border-bottom-right-radius: 4px; }

.thinking-dots { display: flex; gap: 4px; padding: 12px 16px; background: var(--bg-page); border-radius: 12px; border-bottom-left-radius: 4px; }
.thinking-dots span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); animation: dotPulse 1.4s infinite ease-in-out both; }
.thinking-dots span:nth-child(1) { animation-delay: 0s; }
.thinking-dots span:nth-child(2) { animation-delay: 0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.32s; }
@keyframes dotPulse { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }

/* Quick replies */
.quick-replies { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 16px 4px; border-top: 1px solid var(--border-light); }
.quick-reply {
  padding: 6px 12px; border: 1px solid var(--border); border-radius: 16px; background: white;
  font-size: 0.75rem; color: var(--text-secondary); cursor: pointer; transition: border-color 0.2s; font-family: inherit;
}
.quick-reply:hover { border-color: var(--brand-primary); color: var(--brand-primary); }

/* Input */
.panel-input { padding: 8px 12px; border-top: 1px solid var(--border); }
.input-actions { display: flex; gap: 4px; margin-bottom: 6px; }
.input-action-btn {
  width: 32px; height: 32px; border: none; background: transparent; border-radius: 6px;
  cursor: pointer; color: var(--text-muted); display: flex; align-items: center; justify-content: center;
}
.input-action-btn:hover { background: var(--bg-hover); color: var(--text-secondary); }
.input-row { display: flex; gap: 6px; }

.notes-list { padding: 20px; }
.note-empty { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 40px 0; color: var(--text-muted); }
.note-empty p { font-size: 0.85rem; }
</style>
