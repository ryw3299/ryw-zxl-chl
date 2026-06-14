<template>
  <div class="detail-page" v-if="resource">
    <div class="breadcrumb">
      <el-button text @click="$router.push('/resources')"><el-icon><ArrowLeft /></el-icon> 返回资源中心</el-button>
      <span style="color:#94a3b8;margin:0 8px">|</span>
      资源中心 > {{ resource.direction || '机器学习' }} > {{ resource.title }}
    </div>

    <section class="hero-card">
      <div class="hero-cover">
        <div class="cover-art" :style="{ background: coverBg }">
          <span class="cover-badge">{{ typeLabel(resource.resource_type) }}</span>
          <div class="cover-copy">
            <strong>{{ displayTitle }}</strong>
            <small>{{ displaySubtitle }}</small>
          </div>
        </div>
      </div>

      <div class="hero-info">
        <h1 class="detail-title">{{ resource.title }}</h1>
        <div class="detail-tags">
          <el-tag v-for="kp in (resource.knowledge_points || []).slice(0, 5)" :key="kp" size="small" effect="plain">
            {{ kp }}
          </el-tag>
        </div>
        <div class="detail-rating">
          <span class="rating-num">4.8</span>
          <span class="stars">★★★★★</span>
          <span class="rating-count">(1,237人评价)</span>
        </div>
        <div class="detail-meta-grid">
          <div class="dm-item"><span class="dm-icon">🕒</span><span class="dm-label">上传时间</span><span class="dm-val">{{ resource.created_at?.slice(0, 10) || '2024-05-18' }}</span></div>
          <div class="dm-item"><span class="dm-icon">📄</span><span class="dm-label">文件格式</span><span class="dm-val">{{ formatLabel }}</span></div>
          <div class="dm-item"><span class="dm-icon">📦</span><span class="dm-label">大小</span><span class="dm-val">{{ fileSize }}</span></div>
          <div class="dm-item"><span class="dm-icon">📈</span><span class="dm-label">难度</span><span class="dm-val">{{ diffLabel(resource.difficulty) }}</span></div>
          <div class="dm-item"><span class="dm-icon">👥</span><span class="dm-label">学习人数</span><span class="dm-val">{{ studentCount }}</span></div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" size="large" @click="startLearning">开始学习</el-button>
          <el-button size="large" @click="addTask">添加到任务</el-button>
          <el-button size="large" circle @click="handleFavorite"><el-icon><Star /></el-icon></el-button>
        </div>
      </div>
    </section>

    <section class="section-card">
      <h3>资源简介</h3>
      <p class="intro-text">{{ resource.description }}</p>
    </section>

    <section class="section-card">
      <h3>预览内容</h3>
      <div class="preview-grid">
        <div class="preview-thumb" v-for="p in previews" :key="p.title">
          <div class="pt-placeholder">
            <div class="preview-inner" :style="{ background: p.bg }">
              <strong>{{ p.index }}</strong>
            </div>
          </div>
          <span>{{ p.title }}</span>
        </div>
      </div>
    </section>

    <section class="section-card">
      <h3>你可能还需要</h3>
      <div class="related-grid">
        <div class="related-card" v-for="r in related" :key="r.title" @click="router.push('/resources/' + r.id)">
          <div class="rc-cover" :style="{ background: r.bg }">
            <span class="rc-badge">{{ typeLabel(r.type) }}</span>
          </div>
          <div class="rc-body">
            <h4>{{ r.title }}</h4>
            <div class="rc-meta">
              <span>⭐ {{ r.rating }}</span>
              <span>👥 {{ r.students }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Star, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getResourceDetail } from '@/api/resource'

const route = useRoute()
const router = useRouter()
const resource = ref(null)
const id = computed(() => route.params.id)

const coverThemes = {
  document: { bg: 'linear-gradient(135deg, #0f4fbf 0%, #1d6bff 100%)', title: '线性回归算法详解', subtitle: '附实战案例' },
  video: { bg: 'linear-gradient(135deg, #051d49 0%, #113a8c 100%)', title: '3.1 变量的基本概念', subtitle: '视频课程' },
  quiz: { bg: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)', title: '线性回归基础练习', subtitle: '练习题' },
  course: { bg: 'linear-gradient(135deg, #6f4bff 0%, #2b6cff 100%)', title: 'Python 基础入门', subtitle: '全套课程' },
}

const diffMap = { beginner: '入门', intermediate: '中级', advanced: '高级' }
function diffLabel(d) { return diffMap[d] || d }
const typeMap = { course: '课程', document: '文档', video: '视频', quiz: '题库', project: '项目' }
function typeLabel(t) { return typeMap[t] || t }

const coverBg = computed(() => (coverThemes[resource.value?.resource_type] || coverThemes.document).bg)
const displayTitle = computed(() => (coverThemes[resource.value?.resource_type] || coverThemes.document).title)
const displaySubtitle = computed(() => (coverThemes[resource.value?.resource_type] || coverThemes.document).subtitle)

const formatLabel = computed(() => resource.value?.resource_type === 'document' ? 'PDF' : resource.value?.resource_type === 'video' ? 'MP4' : resource.value?.resource_type || 'PDF')
const fileSize = computed(() => resource.value?.resource_type === 'document' ? '8.62 MB' : resource.value?.resource_type === 'video' ? '245 MB' : '1.8 MB')
const studentCount = computed(() => '12,537')
const previewActionText = computed(() => resource.value?.resource_type === 'quiz' ? '题目预览' : '在线预览')
const downloadActionText = computed(() => resource.value?.resource_type === 'video' ? '下载资料' : resource.value?.resource_type === 'quiz' ? '导出题目' : '下载文档')
const startActionText = computed(() => resource.value?.resource_type === 'quiz' ? '开始练习' : '开始学习')

const previews = [
  { index: '1', title: '线性回归概述', bg: 'linear-gradient(135deg, #dbeafe, #eff6ff)' },
  { index: '2', title: '模型建立', bg: 'linear-gradient(135deg, #eef2ff, #f8faff)' },
  { index: '3', title: '参数求解', bg: 'linear-gradient(135deg, #dbeafe, #f3f8ff)' },
  { index: '4', title: '模型评估', bg: 'linear-gradient(135deg, #eef4ff, #f7faff)' },
  { index: '5', title: 'Python实战案例', bg: 'linear-gradient(135deg, #e0ecff, #f5f9ff)' },
]

const related = [
  { title: '梯度下降算法详解', type: 'video', rating: 4.7, students: '8.2k', bg: 'linear-gradient(135deg, #b91c1c, #ef4444)', id: 10 },
  { title: 'Scikit-learn 回归 API 速查', type: 'document', rating: 4.5, students: '3.6k', bg: 'linear-gradient(135deg, #0891b2, #22d3ee)', id: 6 },
  { title: '线性回归常见问题汇总', type: 'quiz', rating: 4.6, students: '5.1k', bg: 'linear-gradient(135deg, #047857, #10b981)', id: 12 },
  { title: '机器学习数学基础', type: 'document', rating: 4.8, students: '6.7k', bg: 'linear-gradient(135deg, #0891b2, #22d3ee)', id: 9 },
]

onMounted(async () => {
  try {
    resource.value = await getResourceDetail(id.value)
  } catch {
    resource.value = {
      id: id.value,
      title: '线性回归算法详解（附实战案例）',
      resource_type: 'document',
      direction: '机器学习',
      difficulty: 'intermediate',
      description: '本资源详细讲解线性回归的原理、建模过程、最小二乘法参数求解、模型评估指标（MSE、R²等），以及使用 Python Scikit-learn 和 Statsmodels 进行实战的完整案例。适合有一定统计学基础和 Python 编程经验的读者。',
      knowledge_points: ['机器学习', '监督学习', '回归算法', 'Python实现', '数据分析', 'Scikit-learn'],
    }
  }
})

function startLearning() { router.push(`/resources/${id.value}/read`) }

function addTask() {
  fetch('/api/v1/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') },
    body: JSON.stringify({ title: resource.value?.title || '', duration_minutes: 30, resource_id: Number(id.value) }),
  }).then(r => r.json()).then(d => {
    if (d.code === 200) ElMessage.success('已添加到今日任务')
    else ElMessage.error('添加失败')
  }).catch(() => ElMessage.error('添加失败'))
}

function handleFavorite() {
  const favs = JSON.parse(localStorage.getItem('favorites') || '[]')
  if (!favs.includes(Number(id.value))) { favs.push(Number(id.value)); localStorage.setItem('favorites', JSON.stringify(favs)); ElMessage.success('已加入收藏') }
  else { ElMessage.info('已在收藏中') }
}

</script>

<style scoped>
.breadcrumb {
  color: #94a3b8;
  font-size: 0.78rem;
  margin-bottom: 18px;
}

.hero-card {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 20px;
  padding: 0;
  margin-bottom: 20px;
}

.hero-cover,
.hero-info,
.section-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}

.hero-cover {
  padding: 16px;
}

.cover-art {
  min-height: 206px;
  border-radius: 16px;
  padding: 14px;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.cover-badge {
  width: fit-content;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  font-size: 0.72rem;
}

.cover-copy strong {
  display: block;
  font-size: 1.6rem;
  line-height: 1.3;
}

.cover-copy small {
  display: block;
  margin-top: 4px;
  font-size: 0.86rem;
  opacity: 0.92;
}

.hero-info {
  padding: 18px 20px;
}

.detail-title {
  font-size: 1.9rem;
  line-height: 1.25;
  color: #1e293b;
}

.detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.detail-rating {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}

.stars {
  color: #f59e0b;
  letter-spacing: 1px;
}

.rating-num {
  color: #1e293b;
  font-size: 1.5rem;
  font-weight: 700;
}

.rating-count {
  color: #94a3b8;
  font-size: 0.8rem;
}

.detail-meta-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.dm-item {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 6px 10px;
  align-items: start;
}

.dm-icon {
  grid-row: span 2;
}

.dm-label {
  color: #94a3b8;
  font-size: 0.72rem;
}

.dm-val {
  color: #1e293b;
  font-size: 0.86rem;
  font-weight: 500;
}

.detail-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 18px;
}

.section-card {
  padding: 18px 20px;
  margin-bottom: 20px;
}

.section-card h3 {
  color: #1e293b;
  font-size: 1rem;
  margin-bottom: 14px;
}

.intro-text {
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.75;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

.preview-thumb {
  text-align: left;
}

.pt-placeholder {
  width: 100%;
  aspect-ratio: 1.1/1;
  border: 1px solid #e3ecfa;
  border-radius: 16px;
  background: #f8fbff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}

.preview-inner {
  width: calc(100% - 20px);
  height: calc(100% - 20px);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-inner strong {
  color: #2b6cff;
  font-size: 1.4rem;
}

.preview-thumb span {
  color: #64748b;
  font-size: 0.76rem;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.related-card {
  border: 1px solid #e7edf6;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
  background: #fff;
}

.related-card:hover {
  box-shadow: 0 16px 36px rgba(52, 72, 108, 0.08);
  transform: translateY(-2px);
}

.rc-cover {
  height: 78px;
  display: flex;
  align-items: flex-start;
  padding: 10px;
  position: relative;
}

.rc-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,0.2);
  color: white;
  font-size: 0.7rem;
  font-weight: 500;
}

.rc-body {
  padding: 10px 12px 12px;
}

.rc-body h4 {
  color: #1e293b;
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.5;
}

.rc-meta {
  margin-top: 6px;
  display: flex;
  gap: 8px;
  color: #94a3b8;
  font-size: 0.72rem;
}

@media (max-width: 1200px) {
  .hero-card,
  .detail-meta-grid,
  .preview-grid,
  .related-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .detail-actions {
    flex-wrap: wrap;
  }
}
</style>
