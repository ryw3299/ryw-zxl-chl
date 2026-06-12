<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const messageInput = ref('')
const isTyping = ref(false)
const chatListRef = ref(null)

// ── 预设回复库（关键词匹配） ──────────────────────────────────────────
const replyMap = [
  {
    keys: ['星轨探微', '学习情况', '课程分析'],
    reply: `📊 **《星轨探微》课程学习情况分析**\n\n本课程当前共 38 名学生参与学习，整体完成率 72%，以下是详细情况：\n\n**总体概览**\n• 平均得分：81.4 分（满分 100）\n• 活跃学习天数：平均每人 8.3 天\n• 课堂互动次数：总计 312 次\n\n**掌握较好的模块**\n• 双星系统概述（通过率 91%）\n• 万有引力基本公式（通过率 88%）\n\n**薄弱知识点（重点关注）**\n• 质心位置推导：通过率仅 48%，学生普遍混淆 r₁ + r₂ = L 与 m₁r₁ = m₂r₂ 的联立方式\n• 周期公式推导：通过率 55%，主要错误在轨道半径取 L/2 还是 rᵢ\n• 总质量与单星质量的区分：通过率 61%，部分学生误以为已知 T 和 L 可求单个星质量\n\n**建议**\n1. 下节课前 5 分钟专项复习质心条件，强调两个方程必须联立\n2. 针对周期推导设计一道对比练习题（等质量 vs 不等质量双星）\n3. 可在课后任务中加入"判断题：已知 T 和 L 能否求 m₁？"帮助纠偏\n\n是否需要我为薄弱点生成专项补充讲义？`,
  },
  {
    keys: ['练习题', '习题', '出题', '题目', '测验'],
    reply: `好的，以下是为《人工智能导论》第3章生成的 5 道练习题：\n\n1. 简述监督学习与无监督学习的核心区别。\n2. 什么是过拟合？列举两种防止过拟合的方法。\n3. 反向传播算法的核心思想是什么？\n4. 以下哪个激活函数会导致梯度消失问题？\n   A. ReLU   B. Sigmoid   C. Tanh   D. Leaky ReLU\n5. 描述卷积神经网络中池化层的作用。\n\n可以告诉我题目难度偏好，我可以重新调整。`,
  },
  {
    keys: ['学情', '分析', '掌握', '薄弱', '问题', '了解', '数据'],
    reply: `📊 **学情分析报告（本周）**\n\n当前班级共 42 名学生，学习情况如下：\n\n• **掌握良好**：梯度下降、线性回归（85% 以上通过率）\n• **需要关注**：反向传播推导（通过率仅 54%）\n• **严重薄弱**：正则化方法（通过率 38%）\n\n建议下节课重点讲解正则化，可结合 L1/L2 对比案例加深理解。\n\n是否需要为薄弱知识点生成补充讲义？`,
  },
  {
    keys: ['教学方案', '课程设计', '备课', '教案', '优化', '改进'],
    reply: `基于当前学生学情，建议对后续教学方案做以下调整：\n\n**第4章 神经网络优化**\n1. 课程开头增加 5 分钟快速复习（反向传播核心步骤）\n2. 将"动量优化器"章节前移，学生对比学习更直观\n3. 增加一个实操环节：用 PyTorch 训练简单分类器\n\n预计调整后，学生对优化器的理解度提升约 20%。\n\n需要我生成调整后的完整教案吗？`,
  },
  {
    keys: ['总结', '重点', '知识点', '梳理', '本节', '本章'],
    reply: `以下是本章核心知识点总结：\n\n**一、感知机模型**\n- 单层感知机只能解决线性可分问题\n- 权重更新规则：Δw = η(y - ŷ)x\n\n**二、多层神经网络**\n- 隐藏层引入非线性变换能力\n- 常用激活函数：ReLU、Sigmoid、Tanh\n\n**三、训练策略**\n- 批梯度下降 vs 随机梯度下降 vs 小批量\n- 正则化：L1（稀疏化）/ L2（权重衰减）\n- Dropout：随机失活防止过拟合\n\n是否需要我生成学生版思维导图？`,
  },
  {
    keys: ['讲义', '资料', '材料', '补充', '文档'],
    reply: `已为您生成《正则化方法》补充讲义草稿：\n\n**一、为什么需要正则化？**\n过拟合是指模型在训练集表现很好，但泛化能力差。\n\n**二、L2 正则化（Ridge）**\n损失函数加入权重平方项：L' = L + λΣw²\n效果：权重趋于均匀小值，模型更平滑。\n\n**三、L1 正则化（Lasso）**\n损失函数加入权重绝对值：L' = L + λΣ|w|\n效果：产生稀疏解，部分权重变为 0（特征选择）。\n\n**四、Dropout**\n训练时随机将部分神经元输出置零（p=0.5 常见）。\n\n需要添加例题或可视化图示说明吗？`,
  },
]

const getReply = (text) => {
  const matched = replyMap.find(({ keys }) => keys.some((k) => text.includes(k)))
  return matched?.reply || '收到你的问题，正在分析课程数据…\n\n根据当前智课内容，我建议可以从以下角度切入：结合学生最近的作答记录，找出高错误率的知识节点，优先安排强化讲解。\n\n如果你能告诉我具体想优化哪个章节，我可以给出更精准的建议。'
}

const messages = ref([
  {
    id: 'ai-welcome',
    role: 'ai',
    text: '老师好！我是你的 AI 助教。\n\n我可以帮你：出练习题、分析学情数据、优化教学方案、生成补充讲义等。\n\n请问有什么需要我协助的？',
    time: '',
    status: 'success',
  },
])

const quickPrompts = [
  { label: '分析下课程《星轨探微》的学习情况', icon: 'chart-trending-o', gradient: ['#667eea', '#764ba2'] },
  { label: '生成课后练习题', icon: 'edit',          gradient: ['#f093fb', '#f5576c'] },
  { label: '优化教学方案',   icon: 'orders-o',       gradient: ['#4facfe', '#00f2fe'] },
  { label: '生成补充讲义',   icon: 'description',    gradient: ['#43e97b', '#38f9d7'] },
]

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
  messages.value.push({ id: msgId, role: 'user', text: content, time: now(), status: 'success' })
  messageInput.value = ''
  await scrollToBottom()
  isTyping.value = true

  await new Promise((r) => setTimeout(r, 5000))

  messages.value.push({
    id: `ai-${Date.now()}`,
    role: 'ai',
    text: getReply(content),
    time: now(),
    status: 'success',
  })
  isTyping.value = false
  scrollToBottom()
}

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
}

watch(messages, scrollToBottom, { deep: true })
onMounted(scrollToBottom)
</script>

<template>
  <div class="page-root">

    <!-- 顶部导航 -->
    <header class="page-nav">
      <button class="nav-back" @click="router.back()">
        <van-icon name="arrow-left" size="18" />
      </button>
      <div class="nav-center">
        <div class="nav-avatar">
          <van-icon name="gem-o" size="16" color="#fff" />
        </div>
        <div class="nav-texts">
          <span class="nav-title">AI 助教</span>
          <span class="nav-sub">· 在线</span>
        </div>
      </div>
      <div class="nav-placeholder" />
    </header>

    <!-- 消息区 -->
    <div class="chat-messages" ref="chatListRef">

      <!-- 装饰背景 -->
      <div class="bg-decor" aria-hidden="true">
        <div class="bg-blob bg-blob--1" />
        <div class="bg-blob bg-blob--2" />
      </div>

      <template v-for="msg in messages" :key="msg.id">
        <div class="bubble-row" :class="`is-${msg.role}`">
          <div v-if="msg.role === 'ai'" class="bubble-avatar bubble-avatar--ai">
            <van-icon name="gem-o" size="14" color="#fff" />
          </div>
          <div class="bubble-content">
            <div class="bubble-box">{{ msg.text }}</div>
            <div v-if="msg.time" class="bubble-meta">{{ msg.time }}</div>
          </div>
          <div v-if="msg.role === 'user'" class="bubble-avatar bubble-avatar--user">师</div>
        </div>
      </template>

      <!-- 打字动画 -->
      <div v-if="isTyping" class="bubble-row is-ai">
        <div class="bubble-avatar bubble-avatar--ai">
          <van-icon name="gem-o" size="14" color="#fff" />
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
      <div class="input-wrap" :class="{ 'is-focus': canSend }">
        <van-field
          v-model="messageInput"
          type="textarea"
          rows="1"
          autosize
          :maxlength="300"
          placeholder="向 AI 助教提问…"
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
          <van-icon name="guide-o" size="18" />
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.page-root {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  background: linear-gradient(180deg, #f7f9ff 0%, #eef3fb 100%);
  overflow: hidden;
}

/* ── 导航栏 ── */
.page-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(124,58,237,0.08);
  flex-shrink: 0;
  z-index: 10;
}

.nav-back {
  width: 36px; height: 36px;
  border: none; background: #f5f0ff;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #7c3aed;
  transition: opacity 0.15s;
}
.nav-back:active { opacity: 0.6; }

.nav-center {
  display: flex;
  align-items: center;
  gap: 9px;
}

.nav-avatar {
  width: 34px; height: 34px;
  border-radius: 11px;
  background: linear-gradient(135deg, #7c3aed 0%, #9f67ff 60%, #b794f4 100%);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(124,58,237,0.3);
}

.nav-texts { display: flex; align-items: baseline; gap: 4px; }
.nav-title { font-size: 16px; font-weight: 800; color: #1a2035; }
.nav-sub { font-size: 11px; color: #12b76a; font-weight: 600; }

.nav-placeholder { width: 36px; }

/* ── 消息区 ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
}
.chat-messages::-webkit-scrollbar { width: 0; }

/* 装饰背景 */
.bg-decor { position: absolute; inset: 0; pointer-events: none; overflow: hidden; z-index: 0; }
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.3;
}
.bg-blob--1 {
  width: 220px; height: 220px;
  background: radial-gradient(circle, #c5b8ff 0%, transparent 70%);
  top: -40px; right: -50px;
  animation: float-1 14s ease-in-out infinite;
}
.bg-blob--2 {
  width: 180px; height: 180px;
  background: radial-gradient(circle, #ffd1e0 0%, transparent 70%);
  bottom: 80px; left: -40px;
  animation: float-2 18s ease-in-out infinite;
}
@keyframes float-1 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(-15px,25px); } }
@keyframes float-2 { 0%,100% { transform: translate(0,0); } 50% { transform: translate(25px,-15px); } }

/* ── 气泡 ── */
.bubble-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 88%;
  position: relative;
  z-index: 1;
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
  background: linear-gradient(135deg, #7c3aed 0%, #9f67ff 60%, #b794f4 100%);
  box-shadow: 0 3px 12px rgba(124,58,237,0.32);
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
  box-shadow: 0 2px 12px rgba(124,58,237,0.08);
  border: 1px solid rgba(124,58,237,0.06);
  word-break: break-word;
  white-space: pre-wrap;
}
.is-user .bubble-box {
  background: linear-gradient(135deg, #7c3aed, #9f67ff);
  color: #fff;
  border: none;
  border-radius: 18px 4px 18px 18px;
  box-shadow: 0 4px 18px rgba(124,58,237,0.32);
}

.bubble-meta { font-size: 11px; color: #b0b9c8; }

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
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  border-top: 1px solid rgba(124,58,237,0.08);
  padding: 10px 14px calc(env(safe-area-inset-bottom, 0px) + 14px);
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
  color: var(--g1, #7c3aed);
  font-size: 12px; font-weight: 600;
  cursor: pointer; white-space: nowrap;
  transition: all 0.15s;
  position: relative;
  box-shadow: 0 2px 8px rgba(124,58,237,0.07);
}
.quick-chip::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1.5px;
  background: linear-gradient(135deg, var(--g1, #7c3aed), var(--g2, #b794f4));
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
  background: #f5f0ff;
  border-radius: 18px;
  border: 1.5px solid #e9d8fd;
  padding: 6px 6px 6px 14px;
  transition: all 0.2s;
}
.input-wrap.is-focus {
  border-color: #b794f4;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(183,148,244,0.15);
}

.chat-field { flex: 1; background: transparent; padding: 0; font-size: 14px; }
.chat-field :deep(.van-field__control) { max-height: 80px; font-size: 14px; line-height: 1.6; background: transparent; }

.send-btn {
  width: 38px; height: 38px;
  border-radius: 12px; border: none;
  background: #e9d8fd; color: #b794f4;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s;
  cursor: pointer;
}
.send-btn--active {
  background: linear-gradient(135deg, #7c3aed, #9f67ff);
  color: #fff;
  box-shadow: 0 4px 16px rgba(124,58,237,0.38);
  transform: scale(1.04);
}
</style>
