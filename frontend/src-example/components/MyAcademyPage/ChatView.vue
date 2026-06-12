<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  title: { type: String, default: '智能问答' },
  placeholder: { type: String, default: '请输入你的问题...' },
})

const messages = ref([
  { role: 'assistant', content: '你好！我是小微，你的智能学习助手。有什么问题都可以问我哦~' },
])
const inputText = ref('')
const isTyping = ref(false)
const chatContainer = ref(null)

const mockReplies = {
  '智能问答': [
    '这是一个很好的问题！让我从课程内容的角度来分析一下...',
    '根据你的学习进度，我建议先掌握基础概念，再深入理解这个知识点。',
    '这个概念在人工智能导论第三章有详细讲解，建议你回顾一下相关内容。',
    '我注意到这个问题涉及多个知识点的交叉，让我帮你梳理一下它们之间的联系。',
  ],
  '资源推荐': [
    '根据你当前的学习进度，我推荐以下资源：\n1. 《人工智能：一种现代方法》第三章\n2. MIT OpenCourseWare 的相关视频\n3. 课程配套实验手册',
    '你最近在数据结构方面花的时间较多，这里有一些补充练习资源可以帮你巩固。',
    '我找到了几篇和你当前学习主题相关的优质论文，建议阅读以加深理解。',
  ],
  '图片生成': [
    '我已经为你生成了一张概念关系图，展示了这个知识点与其他概念的关联。',
    '根据你的描述，我生成了一张思维导图，帮助你理清这个章节的知识结构。',
    '这里是一张可视化图表，展示了算法的执行流程，希望对你有帮助。',
  ],
}

const sendMessage = async () => {
  if (!inputText.value.trim()) return

  messages.value.push({ role: 'user', content: inputText.value })
  const userInput = inputText.value
  inputText.value = ''
  isTyping.value = true

  await nextTick()
  scrollToBottom()

  // Mock reply with delay
  setTimeout(() => {
    const replies = mockReplies[props.title] || mockReplies['智能问答']
    const reply = replies[Math.floor(Math.random() * replies.length)]
    messages.value.push({ role: 'assistant', content: reply })
    isTyping.value = false
    nextTick(() => scrollToBottom())
  }, 800 + Math.random() * 1200)
}

const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}
</script>

<template>
  <div class="chat-view">
    <div class="chat-header">
      <el-text size="large" style="font-weight: bold; font-size: 20px">{{ title }}</el-text>
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
        <div class="message-avatar">
          <div class="avatar-assistant">小微</div>
        </div>
        <div class="message-bubble bubble-assistant">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <el-input
        v-model="inputText"
        :placeholder="placeholder"
        @keyup.enter="sendMessage"
        size="large"
        clearable
      >
        <template #append>
          <el-button :icon="'Promotion'" @click="sendMessage" :disabled="!inputText.trim() || isTyping" />
        </template>
      </el-input>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.chat-message {
  display: flex;
  margin-bottom: 20px;
  gap: 12px;
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar-assistant {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #8080ff;
  color: #fff;
  font-size: 13px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-user {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #67c23a;
  color: #fff;
  font-size: 13px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
}

.bubble-assistant {
  background: #f4f4f5;
  border-radius: 12px 12px 12px 4px;
}

.bubble-user {
  background: #8080ff;
  color: #fff;
  border-radius: 12px 12px 4px 12px;
}

.bubble-user .el-text {
  color: #fff;
}

.chat-input-area {
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8080ff;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}
</style>