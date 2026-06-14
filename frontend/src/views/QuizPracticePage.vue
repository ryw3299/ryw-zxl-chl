<template>
  <div class="quiz-page">
    <div class="breadcrumb">练习题 > 机器学习习题 > 线性回归习题</div>

    <div class="title-row">
      <div>
        <h1>线性回归基础练习</h1>
        <div class="meta-tags">
          <span>难度：中等</span>
          <span>知识点：线性回归模型</span>
          <span>最小二乘法</span>
          <span>模型评估</span>
        </div>
      </div>
    </div>

    <section class="summary-card">
      <div class="summary-item" v-for="item in summaryItems" :key="item.label">
        <div class="summary-label">{{ item.label }}</div>
        <strong class="summary-value">{{ item.value }}</strong>
        <small class="summary-desc">{{ item.desc }}</small>
      </div>
    </section>

    <section class="question-card">
      <div class="question-head">
        <div class="question-meta">
          <el-tag size="small" type="primary" effect="plain">单选题</el-tag>
          <span>第 13 题（共 20 题）</span>
        </div>
        <div class="question-actions">
          <button type="button" class="text-action"><el-icon><Star /></el-icon> 收藏</button>
          <button type="button" class="text-action"><el-icon><EditPen /></el-icon> 标记</button>
        </div>
      </div>

      <div class="question-title">
        给定如下数据集，使用最小二乘法拟合线性回归模型 `y = wx + b`，下列哪个选项是关于模型参数 `w` 和 `b` 的正确表达式？
      </div>

      <div class="question-body">
        <div class="question-figure">
          <div class="figure-box">
            <div class="scatter-line"></div>
            <span class="axis axis-x">x</span>
            <span class="axis axis-y">y</span>
          </div>
        </div>

        <div class="option-list">
          <label
            v-for="option in options"
            :key="option.key"
            :class="['option-item', { active: selectedOption === option.key }]"
          >
            <input v-model="selectedOption" type="radio" :value="option.key" />
            <span class="option-key">{{ option.key }}</span>
            <span class="option-text">{{ option.text }}</span>
          </label>
        </div>
      </div>

      <div class="question-footer">
        <el-button @click="prevQuestion">上一题</el-button>
        <div class="footer-actions">
          <el-button @click="nextQuestion">下一题</el-button>
          <el-button type="primary" @click="submitAnswer">提交答案</el-button>
        </div>
      </div>
    </section>

    <section class="bottom-grid">
      <article class="surface-card">
        <div class="section-head">
          <h2>错题记录</h2>
          <button type="button" class="section-link" @click="goWrongBook">查看全部</button>
        </div>
        <div class="record-list">
          <div v-for="item in records" :key="item.title" class="record-item">
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.subtitle }}</p>
            </div>
            <el-tag size="small" type="danger" effect="plain">{{ item.tag }}</el-tag>
          </div>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>答案解析</h2>
        </div>
        <div class="analysis-card">
          <el-tag size="small" type="success" effect="plain">正确答案：B</el-tag>
          <p>在线性回归中，斜率 `w` 的最优解为：`w = Σ((xi - x̄)(yi - ȳ)) / Σ((xi - x̄)^2)`，截距为 `b = ȳ - wx̄`。这正是线性回归的标准解。</p>
          <button type="button" class="more-link" @click="goResources">知识点：线性回归参数的最小二乘解</button>
        </div>
      </article>

      <article class="surface-card">
        <div class="section-head">
          <h2>掌握度趋势</h2>
        </div>
        <div ref="trendRef" class="trend-chart"></div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { EditPen, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const trendRef = ref(null)
const currentQ = ref(1)
const selectedOption = ref('B')
let trendChart = null

const summaryItems = [
  { label: '本次练习得分', value: '82 分', desc: '满分 100' },
  { label: '答题进度', value: '12 / 20', desc: '已完成 60%' },
  { label: '正确率', value: '80%', desc: '正确 12 题，错误 3 题' },
  { label: '预计用时', value: '18 分钟', desc: '已用时 12:36' },
  { label: '掌握度提升', value: '12%', desc: '较上次练习' },
]

const options = [
  { key: 'A', text: 'w = Σxiyi / Σxi², b = ȳ - wx̄' },
  { key: 'B', text: 'w = Σ((xi - x̄)(yi - ȳ)) / Σ((xi - x̄)²), b = ȳ - wx̄' },
  { key: 'C', text: 'w = Σyi² / Σxiyi, b = x̄ - wȳ' },
  { key: 'D', text: 'w = (nΣxiyi - ΣxiΣyi) / (nΣxi² - (Σxi)²), b = (Σyi - wΣxi) / n' },
]

const records = [
  { title: '第 6 题', subtitle: '特征归一化在求解中的作用细节', tag: '错误' },
  { title: '第 9 题', subtitle: '决定系数 R² 的计算与意义', tag: '错误' },
  { title: '第 11 题', subtitle: '岭回归与 Lasso 的区别', tag: '错误' },
]

function renderTrend() {
  if (!trendRef.value) return
  if (!trendChart) trendChart = echarts.init(trendRef.value)
  trendChart.setOption({
    grid: { top: 14, right: 10, bottom: 20, left: 24 },
    xAxis: {
      type: 'category',
      data: ['05-15', '05-17', '05-19', '05-21', '05-23', '05-25', '05-27'],
      axisLabel: { color: '#98a2b3', fontSize: 10 },
      axisLine: { lineStyle: { color: '#edf2f8' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#98a2b3', fontSize: 10 },
      splitLine: { lineStyle: { color: '#edf2f8' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: [36, 44, 39, 61, 55, 67, 82],
        lineStyle: { color: '#2b6cff', width: 2 },
        itemStyle: { color: '#2b6cff' },
      },
    ],
  })
}

function submitAnswer() {
  ElMessage.success(`已提交答案：${selectedOption.value}`)
}

function prevQuestion() {
  if (currentQ.value > 1) { currentQ.value--; ElMessage.info(`第 ${currentQ.value} 题`) }
}
function nextQuestion() {
  if (currentQ.value < 20) { currentQ.value++; ElMessage.info(`第 ${currentQ.value} 题`) }
}

function goWrongBook() {
  router.push('/learning-path/wrong-book')
}

function goResources() {
  router.push('/resources')
}

function handleResize() {
  trendChart?.resize()
}

onMounted(() => {
  nextTick(() => {
    renderTrend()
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  trendChart = null
})
</script>

<style scoped>
.quiz-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.breadcrumb {
  color: #94a3b8;
  font-size: 0.78rem;
}

.title-row h1 {
  color: #1e293b;
  font-size: 1.8rem;
}

.meta-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #94a3b8;
  font-size: 0.76rem;
}

.summary-card,
.question-card,
.surface-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.summary-card {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
}

.summary-item {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
}

.summary-item + .summary-item {
  border-left: 1px solid #edf2f8;
}

.summary-label {
  color: #94a3b8;
  font-size: 0.74rem;
}

.summary-value {
  margin-top: 6px;
  color: #1e293b;
  font-size: 1.5rem;
}

.summary-desc {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 0.72rem;
}

.question-card,
.surface-card {
  padding: 18px;
}

.question-head,
.section-head,
.question-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.question-meta,
.question-actions,
.footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.question-meta span,
.text-action {
  color: #64748b;
  font-size: 0.8rem;
}

.text-action {
  border: 0;
  background: transparent;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.question-title {
  margin-top: 16px;
  color: #1e293b;
  font-size: 0.92rem;
  line-height: 1.7;
}

.question-body {
  margin-top: 18px;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
}

.figure-box {
  height: 250px;
  border: 1px solid #dbe5f7;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  position: relative;
  overflow: hidden;
}

.figure-box::before,
.figure-box::after {
  content: '';
  position: absolute;
  inset: 18px;
  border-left: 1px solid #cbd5e1;
  border-bottom: 1px solid #cbd5e1;
}

.scatter-line {
  position: absolute;
  left: 32px;
  right: 28px;
  top: 168px;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, #ef4444 22%, #ef4444 80%, transparent 100%);
  transform: rotate(-28deg);
}

.axis {
  position: absolute;
  color: #94a3b8;
  font-size: 0.72rem;
}

.axis-x {
  right: 18px;
  bottom: 14px;
}

.axis-y {
  left: 12px;
  top: 14px;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-item {
  border: 1px solid #dfe7f5;
  border-radius: 14px;
  background: #fff;
  padding: 16px;
  display: grid;
  grid-template-columns: 18px 22px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  cursor: pointer;
}

.option-item input {
  margin-top: 2px;
}

.option-item.active {
  border-color: #2b6cff;
  background: #f7faff;
  box-shadow: 0 0 0 2px rgba(43, 108, 255, 0.08);
}

.option-key {
  color: #64748b;
  font-weight: 600;
}

.option-text {
  color: #1e293b;
  line-height: 1.7;
  font-size: 0.86rem;
}

.question-footer {
  margin-top: 18px;
}

.section-head {
  margin-bottom: 14px;
}

.section-head h2 {
  color: #1e293b;
  font-size: 1rem;
}

.section-link,
.more-link {
  border: 0;
  background: transparent;
  color: #2b6cff;
  font: inherit;
  cursor: pointer;
}

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #edf2f8;
}

.record-item:last-child {
  border-bottom: 0;
}

.record-item strong,
.analysis-card p {
  color: #1e293b;
}

.record-item p {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 0.74rem;
}

.analysis-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-card p {
  line-height: 1.75;
  color: #64748b;
  font-size: 0.82rem;
}

.trend-chart {
  width: 100%;
  height: 180px;
}

@media (max-width: 1180px) {
  .summary-card,
  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .summary-item + .summary-item {
    border-left: 0;
    border-top: 1px solid #edf2f8;
  }
}

@media (max-width: 860px) {
  .question-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .question-head,
  .question-footer,
  .question-meta,
  .question-actions,
  .footer-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
