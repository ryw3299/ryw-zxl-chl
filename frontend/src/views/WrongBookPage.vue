<template>
  <div class="tool-page">
    <section class="hero-card">
      <div>
        <p class="hero-label">学习计划工具</p>
        <h1>错题本</h1>
        <p class="hero-desc">集中查看高频错题、薄弱知识点和复习建议，帮助你把易错点快速转成稳固能力。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="goQuiz">继续练习</el-button>
        <el-button @click="goLearningPath">返回个性化路径</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <article class="summary-card" v-for="item in summaryCards" :key="item.label">
        <span class="summary-value">{{ item.value }}</span>
        <span class="summary-label">{{ item.label }}</span>
      </article>
    </section>

    <section class="content-grid">
      <article class="surface-card">
        <div class="section-head">
          <h2>错题列表</h2>
          <span class="section-tip">优先复习最近一周重复出错内容</span>
        </div>

        <StateBlock v-if="loading" loading loading-text="加载错题中..." />
        <div v-else class="wrong-list">
          <div v-for="item in displayItems" :key="item.id" class="wrong-item">
            <div class="wrong-main">
              <div class="wrong-title-row">
                <h3>{{ item.title }}</h3>
                <el-tag size="small" :type="item.tagType" effect="plain">{{ item.level }}</el-tag>
              </div>
              <p class="wrong-desc">{{ item.desc }}</p>
              <div class="wrong-meta">
                <span>{{ item.topic }}</span>
                <span>错误次数 {{ item.errorCount }}</span>
                <span>最近复习 {{ item.lastReview }}</span>
              </div>
            </div>
            <div class="wrong-side">
              <strong>{{ item.accuracy }}</strong>
              <span>订正完成率</span>
              <el-button size="small" type="primary" @click="goQuiz">去巩固</el-button>
            </div>
          </div>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>复习建议</h2>
        </div>
        <div class="advice-list">
          <div v-for="item in advices" :key="item.title" class="advice-item">
            <span class="advice-dot"></span>
            <div>
              <div class="advice-title">{{ item.title }}</div>
              <div class="advice-desc">{{ item.desc }}</div>
            </div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getWrongQuiz } from '@/api/quiz'
import StateBlock from '@/components/StateBlock.vue'

const router = useRouter()
const loading = ref(false)
const wrongItems = ref([])

const advices = [
  { title: '优先回顾重复错误题', desc: '连续两次以上出错的知识点，建议今天安排 20 分钟专项练习。' },
  { title: '先复盘再重做', desc: '先看解题思路和错因，再做同类题，效果比直接刷题更稳定。' },
  { title: '串联路径阶段内容', desc: '可回到个性化路径中的当前阶段，补齐相关课程和练习。' },
]

const summaryCards = computed(() => [
  { label: '累计错题', value: `${displayItems.value.length} 题` },
  { label: '高频错题', value: `${displayItems.value.filter((item) => item.errorCount >= 3).length} 题` },
  { label: '平均订正率', value: `${Math.round(displayItems.value.reduce((sum, item) => sum + parseInt(item.accuracy, 10), 0) / (displayItems.value.length || 1))}%` },
])

const displayItems = computed(() => {
  if (wrongItems.value.length) {
    return wrongItems.value.map((item, index) => ({
      id: item.id || `wrong-${index}`,
      title: item.question || item.title || `错题 ${index + 1}`,
      desc: item.analysis || '建议回顾相关知识点，并重新完成一次同类题练习。',
      topic: item.knowledge_point || 'Python 基础',
      errorCount: item.error_count || (index % 3) + 2,
      lastReview: item.last_review_at || `2024-06-0${(index % 5) + 4}`,
      accuracy: `${72 + (index % 4) * 6}%`,
      level: index % 2 === 0 ? '重点复习' : '常规复习',
      tagType: index % 2 === 0 ? 'warning' : 'primary',
    }))
  }

  return [
    { id: '1', title: 'Python 函数参数传递', desc: '容易混淆位置参数和关键字参数，建议先做 5 题专项练习。', topic: 'Python 基础', errorCount: 3, lastReview: '2024-06-08', accuracy: '78%', level: '重点复习', tagType: 'warning' },
    { id: '2', title: 'Pandas 缺失值处理', desc: '对 fillna 和 dropna 的适用场景掌握还不稳定。', topic: '数据分析', errorCount: 2, lastReview: '2024-06-07', accuracy: '84%', level: '常规复习', tagType: 'primary' },
    { id: '3', title: '线性回归损失函数', desc: '公式理解已具备，建议增加 1 次推导复盘。', topic: '机器学习', errorCount: 4, lastReview: '2024-06-06', accuracy: '70%', level: '重点复习', tagType: 'warning' },
  ]
})

async function loadWrongQuiz() {
  loading.value = true
  try {
    const response = await getWrongQuiz()
    wrongItems.value = Array.isArray(response) ? response : response?.items || []
  } catch {
    wrongItems.value = []
  } finally {
    loading.value = false
  }
}

function goQuiz() {
  router.push('/resources?resource_type=quiz')
}

function goLearningPath() {
  router.push('/learning-path')
}

onMounted(loadWrongQuiz)
</script>

<style scoped>
.tool-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.summary-card,
.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.hero-card {
  padding: 22px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.hero-label {
  color: #2b6cff;
  font-size: 0.78rem;
}

.hero-card h1 {
  margin-top: 8px;
  color: #1e293b;
  font-size: 1.8rem;
}

.hero-desc {
  margin-top: 8px;
  max-width: 640px;
  color: #64748b;
  font-size: 0.9rem;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  gap: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
}

.summary-value {
  color: #1e293b;
  font-size: 1.5rem;
  font-weight: 700;
}

.summary-label {
  margin-top: 6px;
  color: #64748b;
  font-size: 0.82rem;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.9fr);
  gap: 18px;
}

.surface-card {
  padding: 18px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head h2 {
  color: #1e293b;
  font-size: 1rem;
}

.section-tip {
  color: #94a3b8;
  font-size: 0.76rem;
}

.wrong-list,
.advice-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.wrong-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 110px;
  gap: 16px;
  padding: 16px;
  border: 1px solid #edf2f8;
  border-radius: 14px;
  background: #fbfcff;
}

.wrong-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.wrong-title-row h3 {
  color: #27364f;
  font-size: 0.92rem;
}

.wrong-desc {
  margin-top: 8px;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.65;
}

.wrong-meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #94a3b8;
  font-size: 0.74rem;
}

.wrong-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  text-align: right;
}

.wrong-side strong {
  color: #2b6cff;
  font-size: 1.25rem;
}

.wrong-side span {
  color: #94a3b8;
  font-size: 0.74rem;
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 0;
  border-bottom: 1px solid #edf2f8;
}

.advice-item:last-child {
  border-bottom: 0;
}

.advice-dot {
  width: 8px;
  height: 8px;
  margin-top: 8px;
  border-radius: 50%;
  background: #2b6cff;
  flex: none;
}

.advice-title {
  color: #27364f;
  font-size: 0.86rem;
}

.advice-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.7;
}

@media (max-width: 1080px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero-card,
  .summary-grid,
  .wrong-item {
    grid-template-columns: 1fr;
  }

  .hero-card,
  .hero-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    display: grid;
  }

  .wrong-item {
    display: flex;
    flex-direction: column;
  }

  .wrong-side {
    align-items: flex-start;
    text-align: left;
  }
}
</style>
