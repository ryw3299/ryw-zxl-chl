<script setup>
import { ref, nextTick } from 'vue'

const messages = ref([
  { role: 'assistant', content: '你好！我是图片生成助手，告诉我你想要什么样的图片，我来帮你生成~' },
])
const inputText = ref('')
const isTyping = ref(false)
const chatContainer = ref(null)

const replies = [
  '好的，我正在为你生成图片，请稍等片刻...',
  '图片已生成！这是一张基于你描述的教学示意图，你可以下载或保存到课程资料中。',
  '我为你生成了3个不同风格的版本，你可以在下方预览并选择最合适的一个。',
  '根据你的需求，我建议使用更简洁的示意图风格，这样学生更容易理解。让我重新生成一下。',
]

const sendMessage = async () => {
  if (!inputText.value.trim()) return
  messages.value.push({ role: 'user', content: inputText.value })
  inputText.value = ''
  isTyping.value = true
  await nextTick()
  scrollToBottom()
  setTimeout(() => {
    const reply = replies[Math.floor(Math.random() * replies.length)]
    messages.value.push({ role: 'assistant', content: reply })
    isTyping.value = false
    nextTick(() => scrollToBottom())
  }, 800 + Math.random() * 1200)
}

const scrollToBottom = () => {
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}
</script>

<template>
  <div class="chat-view">
    <div class="chat-header">
      <el-text size="large" style="font-weight: bold; font-size: 20px">图片生成</el-text>
    </div>
    <div class="chat-body" ref="chatContainer">
      <div v-for="(msg, idx) in messages" :key="idx"
           :class="['chat-message', msg.role === 'user' ? 'message-user' : 'message-assistant']">
        <div class="message-avatar">
          <div v-if="msg.role === 'assistant'" class="avatar-assistant">小微</div>
          <div v-else class="avatar-user">我</div>
        </div>
        <div :class="['message-bubble', msg.role === 'user' ? 'bubble-user' : 'bubble-assistant']">
          <el-text>{{ msg.content }}</el-text>
        </div>
      </div>
      <div v-if="isTyping" class="chat-message message-assistant">
        <div class="message-avatar"><div class="avatar-assistant">小微</div></div>
        <div class="message-bubble bubble-assistant">
          <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
      </div>
    </div>
    <div class="chat-input-area">
      <el-input v-model="inputText" placeholder="描述你想要生成的图片..." @keyup.enter="sendMessage" size="large" clearable>
        <template #append>
          <el-button :icon="'Promotion'" @click="sendMessage" :disabled="!inputText.trim() || isTyping" />
        </template>
      </el-input>
    </div>
  </div>
</template>

<style scoped>
.chat-view { height: 100%; display: flex; flex-direction: column; }
.chat-header { padding: 16px 24px; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.chat-body { flex: 1; overflow-y: auto; padding: 20px 24px; }
.chat-message { display: flex; margin-bottom: 20px; gap: 12px; }
.message-user { flex-direction: row-reverse; }
.message-avatar { flex-shrink: 0; }
.avatar-assistant { width: 40px; height: 40px; border-radius: 8px; background: #8080ff; color: #fff; font-size: 13px; font-weight: bold; display: flex; align-items: center; justify-content: center; }
.avatar-user { width: 40px; height: 40px; border-radius: 8px; background: #67c23a; color: #fff; font-size: 13px; font-weight: bold; display: flex; align-items: center; justify-content: center; }
.message-bubble { max-width: 70%; padding: 12px 16px; border-radius: 12px; line-height: 1.6; }
.bubble-assistant { background: #f4f4f5; border-radius: 12px 12px 12px 4px; }
.bubble-user { background: #8080ff; color: #fff; border-radius: 12px 12px 4px 12px; }
.bubble-user .el-text { color: #fff; }
.chat-input-area { padding: 16px 24px; border-top: 1px solid #e4e7ed; flex-shrink: 0; }
.typing-indicator { display: flex; gap: 4px; padding: 4px 0; }
.typing-indicator span { width: 8px; height: 8px; border-radius: 50%; background: #8080ff; animation: typing 1.4s infinite; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%, 60%, 100% { opacity: 0.3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-4px); } }
</style>