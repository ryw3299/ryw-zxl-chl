<template>
  <div class="favorites-page">
    <section class="hero-card">
      <div>
        <p class="hero-label">学习计划工具</p>
        <h1>我的收藏</h1>
        <p class="hero-desc">把常用课程、文档和练习集中收纳，方便你在学习路径中快速回看和继续学习。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="$router.push('/resources')">去找资源</el-button>
        <el-button @click="$router.push('/learning-path')">返回路径</el-button>
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
          <h2>收藏资源</h2>
          <span class="section-tip">按最近收藏顺序展示</span>
        </div>
        <StateBlock v-if="loading" loading loading-text="加载收藏中..." />
        <div v-else-if="!favorites.length" class="empty-state">
          <p>暂无收藏资源，去资源中心添加吧</p>
          <el-button type="primary" @click="$router.push('/resources')">去资源中心</el-button>
        </div>
        <div v-else class="favorite-grid">
          <article v-for="item in favorites" :key="item.id" class="favorite-card" @click="$router.push('/resources/' + item.id)">
            <div class="favorite-cover" :style="{ background: getBg(item.resource_type) }">
              <span class="favorite-type">{{ typeLabel(item.resource_type) }}</span>
              <strong>{{ item.title.slice(0, 12) }}</strong>
            </div>
            <div class="favorite-body">
              <h3>{{ item.title }}</h3>
              <p>{{ item.description?.slice(0, 60) || '暂无描述' }}</p>
              <div class="favorite-meta">
                <span>{{ item.direction || '综合' }}</span>
                <span>{{ diffLabel(item.difficulty) }}</span>
              </div>
              <div class="favorite-actions">
                <el-button size="small" type="primary" @click.stop="$router.push('/resources/' + item.id)">继续学习</el-button>
              </div>
            </div>
          </article>
        </div>
      </article>
      <article class="surface-card">
        <div class="section-head"><h2>收藏建议</h2></div>
        <div class="tips-list">
          <div class="tip-item" v-for="item in tips" :key="item.title">
            <div class="tip-title">{{ item.title }}</div>
            <div class="tip-desc">{{ item.desc }}</div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getResources } from '@/api/resource'
import StateBlock from '@/components/StateBlock.vue'

const loading = ref(false)
const allResources = ref([])
const favorites = ref([])
const pages = ref(0)

const tips = [
  { title: '按阶段整理收藏', desc: '可以把当前阶段要学的资源优先加入收藏，减少来回查找的时间。' },
  { title: '收藏不等于完成', desc: '建议每周清理一次，保留真正会在接下来两周使用的内容。' },
  { title: '优先加入学习路径', desc: '遇到关键资源时，可回到个性化路径页把它纳入当前阶段计划。' },
]

const typeMap = { course: '课程', document: '文档', video: '视频', quiz: '题库', project: '项目', ppt: 'PPT', mindmap: '思维导图' }
const diffMap = { beginner: '入门', intermediate: '中级', advanced: '高级' }
function typeLabel(t) { return typeMap[t] || t }
function diffLabel(d) { return diffMap[d] || d }
const coverBgs = { course: 'linear-gradient(135deg, #6f4bff, #2b6cff)', document: 'linear-gradient(135deg, #0f9d7a, #0a6f59)', video: 'linear-gradient(135deg, #b91c1c, #ef4444)', quiz: 'linear-gradient(135deg, #f59e0b, #d97706)', project: 'linear-gradient(135deg, #0f172a, #1d4ed8)', ppt: 'linear-gradient(135deg, #7c3aed, #6366f1)', mindmap: 'linear-gradient(135deg, #0e7490, #14b8a6)' }
function getBg(t) { return coverBgs[t] || coverBgs.course }

const summaryCards = computed(() => [
  { label: '已收藏资源', value: `${favorites.value.length} 个` },
  { label: '总资源数', value: `${allResources.value.length} 个` },
  { label: '学习进度', value: pages.value ? `${Math.round(favorites.value.length / pages.value * 100)}%` : '0%' },
])

onMounted(async () => {
  loading.value = true
  try {
    const res = await getResources({ page_size: 50 })
    allResources.value = res.items || []
    pages.value = res.total || 0
    // Simulate favorites from localStorage
    const saved = JSON.parse(localStorage.getItem('favorites') || '[]')
    if (saved.length > 0) {
      favorites.value = allResources.value.filter(r => saved.includes(r.id))
    } else if (allResources.value.length > 0) {
      // Default: show first 3 as "favorites" for demo
      favorites.value = allResources.value.slice(0, 3)
    }
  } catch {} finally { loading.value = false }
})
</script>

<style scoped>
.favorites-page { display: flex; flex-direction: column; gap: 18px; }
.hero-card, .summary-card, .surface-card, .favorite-card { background: #fff; border: 1px solid #e7edf6; border-radius: 18px; box-shadow: 0 14px 36px rgba(52,72,108,0.05); }
.hero-card { padding: 22px 24px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.hero-label { color: #2b6cff; font-size: 0.78rem; }
.hero-card h1 { margin-top: 8px; color: #1e293b; font-size: 1.8rem; }
.hero-desc { margin-top: 8px; max-width: 640px; color: #64748b; font-size: 0.9rem; line-height: 1.7; }
.hero-actions { display: flex; gap: 10px; }
.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.summary-card { padding: 18px 20px; display: flex; flex-direction: column; }
.summary-value { color: #1e293b; font-size: 1.5rem; font-weight: 700; }
.summary-label { margin-top: 6px; color: #64748b; font-size: 0.82rem; }
.content-grid { display: grid; grid-template-columns: 1.3fr 0.9fr; gap: 18px; }
.surface-card { padding: 18px; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.section-head h2 { color: #1e293b; font-size: 1rem; }
.section-tip { color: #94a3b8; font-size: 0.76rem; }
.empty-state { text-align: center; padding: 40px 0; color: #94a3b8; display: flex; flex-direction: column; gap: 12px; align-items: center; }
.favorite-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.favorite-card { overflow: hidden; cursor: pointer; transition: transform 0.18s; }
.favorite-card:hover { transform: translateY(-2px); }
.favorite-cover { min-height: 90px; padding: 14px; color: #fff; display: flex; flex-direction: column; justify-content: space-between; }
.favorite-type { width: fit-content; padding: 2px 8px; border-radius: 999px; background: rgba(255,255,255,0.2); font-size: 0.72rem; }
.favorite-cover strong { font-size: 0.9rem; }
.favorite-body { padding: 14px; }
.favorite-body h3 { color: #1e293b; font-size: 0.88rem; line-height: 1.5; }
.favorite-body p { margin-top: 6px; color: #64748b; font-size: 0.78rem; }
.favorite-meta { margin-top: 8px; display: flex; gap: 10px; color: #94a3b8; font-size: 0.74rem; }
.favorite-actions { margin-top: 10px; }
.tips-list { display: flex; flex-direction: column; gap: 12px; }
.tip-item { padding: 14px; border: 1px solid #edf2f8; border-radius: 14px; background: #fbfcff; }
.tip-title { color: #27364f; font-size: 0.86rem; }
.tip-desc { margin-top: 6px; color: #64748b; font-size: 0.78rem; }
</style>
