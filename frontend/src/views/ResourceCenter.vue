<template>
  <div class="resource-center-page">
    <div class="rc-header">
      <h1>资源中心</h1>
      <p>海量优质学习资源，覆盖多学科多场景，助你高效学习与成长</p>
    </div>

    <section class="filter-header">
      <div class="filter-search">
        <el-input v-model="keyword" placeholder="搜索资源名称、知识点..." clearable @keyup.enter="applyFilters" @clear="applyFilters">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
      <button type="button" class="filter-toggle" @click="filterVisible = !filterVisible">
        <el-icon><Filter /></el-icon>
        <span>筛选</span>
        <el-icon :class="{ rotated: filterVisible }"><ArrowDown /></el-icon>
      </button>
      <button type="button" class="filter-toggle text-action" @click="clearFilters">
        <el-icon><RefreshRight /></el-icon>
        <span>清空</span>
      </button>
    </section>

    <section class="filter-panel" v-show="filterVisible">
      <div class="top-type-tabs">
        <button
          v-for="type in resourceTypes"
          :key="type.key"
          type="button"
          :class="['top-type-tab', { active: activeType === type.key }]"
          @click="selectType(type.key)"
        >
          {{ type.label }}
        </button>
      </div>

      <div class="filter-rows">
        <div class="filter-row">
          <span class="filter-row-label">学科:</span>
          <div class="filter-chip-list">
            <button
              v-for="subject in subjects"
              :key="subject"
              type="button"
              :class="['filter-chip', { active: selectedSubject === subject }]"
              @click="selectedSubject = subject"
            >
              {{ subject }}
            </button>
          </div>
        </div>

        <div class="filter-row">
          <span class="filter-row-label">难度:</span>
          <div class="filter-chip-list">
            <button
              v-for="difficulty in difficulties"
              :key="difficulty"
              type="button"
              :class="['filter-chip', { active: selectedDifficulty === difficulty }]"
              @click="selectedDifficulty = difficulty"
            >
              {{ difficulty }}
            </button>
          </div>
        </div>

        <div class="filter-row">
          <span class="filter-row-label">类型:</span>
          <div class="filter-chip-list">
            <button
              v-for="kind in kinds"
              :key="kind"
              type="button"
              :class="['filter-chip', { active: selectedKind === kind }]"
              @click="selectedKind = kind"
            >
              {{ kind }}
            </button>
          </div>
        </div>

        <div class="filter-row">
          <span class="filter-row-label">排序:</span>
          <div class="filter-chip-list">
            <button
              v-for="sort in sorts"
              :key="sort"
              type="button"
              :class="['filter-chip', { active: selectedSort === sort }]"
              @click="selectedSort = sort"
            >
              {{ sort }}
            </button>
          </div>
        </div>
      </div>

      <div class="panel-actions">
        <button type="button" class="text-action" @click="clearFilters">
          <el-icon><RefreshRight /></el-icon>
          <span>清空筛选</span>
        </button>
        <button type="button" class="primary-action" @click="applyFilters">
          <el-icon><Filter /></el-icon>
          <span>筛选</span>
        </button>
      </div>
    </section>

    <section class="result-toolbar">
      <span class="result-count">共找到 {{ filteredResources.length.toLocaleString() }} 个资源</span>
      <div class="pager-indicator" v-if="pageCount > 0">
        <button type="button" class="pager-button" :disabled="currentPage === 1" @click="currentPage -= 1">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <span>{{ currentPage }} / {{ pageCount }}</span>
        <button type="button" class="pager-button" :disabled="currentPage === pageCount" @click="currentPage += 1">
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
    </section>

    <StateBlock v-if="loading" loading loading-text="加载资源中..." />

    <template v-else-if="pagedResources.length">
      <div class="resource-grid">
        <article
          v-for="resource in pagedResources"
          :key="resource.id"
          class="resource-card"
          @click="openDetail(resource.id)"
        >
          <div class="resource-cover" :style="{ background: getCoverBg(resource.resource_type) }">
            <div class="resource-cover-top">
              <span class="resource-type-badge">{{ resource.typeLabel }}</span>
            </div>
            <div class="resource-cover-bottom">
              <div class="resource-cover-text">
                <strong>{{ resource.coverTitle }}</strong>
                <span>{{ resource.coverSubtitle }}</span>
              </div>
              <div class="resource-cover-icon">{{ getCoverIcon(resource.resource_type) }}</div>
            </div>
          </div>

          <div class="resource-body">
            <h3 class="resource-title">{{ resource.title }}</h3>

            <div class="resource-tags">
              <span class="resource-chip">{{ resource.subject }}</span>
              <span class="resource-chip">{{ resource.levelLabel }}</span>
              <span class="resource-chip" v-if="resource.knowledge_points?.[0]">{{ resource.knowledge_points[0] }}</span>
            </div>

            <div class="resource-meta-row">
              <span>⭐ {{ resource.rating }}</span>
              <span>👥 {{ resource.learners }}</span>
              <span>{{ resource.date }}</span>
            </div>
          </div>
        </article>
      </div>

      <div class="pagination-wrap" v-if="pageCount > 1">
        <el-pagination
          v-model:current-page="currentPage"
          background
          layout="prev, pager, next"
          :page-size="pageSize"
          :total="filteredResources.length"
        />
      </div>
    </template>

    <StateBlock v-else empty-text="没有找到匹配的资源" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowDown, ArrowRight, Filter, RefreshRight, Search } from '@element-plus/icons-vue'
import { getResources } from '@/api/resource'
import StateBlock from '@/components/StateBlock.vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const currentPage = ref(1)
const pageSize = 8
const resourceItems = ref([])
const filterVisible = ref(true)

const activeType = ref('all')
const selectedSubject = ref('全部')
const selectedDifficulty = ref('全部')
const selectedKind = ref('全部')
const selectedSort = ref('综合推荐')
const keyword = ref('')

const resourceTypes = [
  { key: 'all', label: '全部资源' },
  { key: 'course', label: '课程' },
  { key: 'document', label: '文档' },
  { key: 'video', label: '视频' },
  { key: 'quiz', label: '题库' },
  { key: 'ppt', label: 'PPT' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'project', label: '项目案例' },
]

const subjects = ['全部', 'Python', '数据分析', '机器学习', '深度学习', '前端开发', '大数据', 'AI应用']
const difficulties = ['全部', '入门', '初级', '中级', '高级']
const kinds = ['全部', '课程', '文档', '视频', '题库', 'PPT', '思维导图', '项目案例']
const sorts = ['综合推荐', '最新发布', '最多使用', '最高评分']

const typeMap = {
  course: '课程',
  document: '文档',
  video: '视频',
  quiz: '题库',
  project: '项目案例',
  ppt: 'PPT',
  mindmap: '思维导图',
}

const diffMap = {
  beginner: '入门',
  junior: '初级',
  intermediate: '中级',
  advanced: '高级',
}

const subjectMap = {
  course: 'Python',
  document: '数据分析',
  video: '机器学习',
  quiz: 'AI应用',
  ppt: '深度学习',
  mindmap: '数据分析',
  project: '前端开发',
}

const coverThemes = {
  course: {
    bg: 'linear-gradient(135deg, #6f4bff 0%, #2b6cff 100%)',
    icon: 'P',
    title: 'Python 基础入门',
    subtitle: '全套课程',
  },
  document: {
    bg: 'linear-gradient(135deg, #0f9d7a 0%, #0a6f59 100%)',
    icon: 'X',
    title: 'Excel 数据透视表',
    subtitle: '实战案例精讲',
  },
  video: {
    bg: 'linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)',
    icon: '▶',
    title: '机器学习算法',
    subtitle: '进阶与实战',
  },
  quiz: {
    bg: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
    icon: '题',
    title: '刷题专区',
    subtitle: '专项训练',
  },
  ppt: {
    bg: 'linear-gradient(135deg, #dbeafe 0%, #eef4ff 100%)',
    icon: 'P',
    title: '深度学习发展史',
    subtitle: '与未来趋势',
  },
  mindmap: {
    bg: 'linear-gradient(135deg, #eef2ff 0%, #c7d2fe 100%)',
    icon: '图',
    title: '数据分析思维导图',
    subtitle: '知识脉络',
  },
  project: {
    bg: 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%)',
    icon: '项',
    title: '前端开发项目',
    subtitle: 'HTML/CSS/JS',
  },
}

function normalizeDifficulty(value) {
  if (!value) return 'beginner'
  if (value === '入门') return 'beginner'
  if (value === '初级') return 'junior'
  if (value === '中级') return 'intermediate'
  if (value === '高级') return 'advanced'
  return value
}

function buildDisplayResource(item, index) {
  const theme = coverThemes[item.resource_type] || coverThemes.course
  const numericIndex = index + 1
  const normalizedDifficulty = normalizeDifficulty(item.difficulty)
  const levelLabel = diffMap[normalizedDifficulty] || '入门'

  return {
    ...item,
    typeLabel: typeMap[item.resource_type] || '课程',
    levelLabel,
    subject: subjectMap[item.resource_type] || 'Python',
    rating: (4.6 + (numericIndex % 4) * 0.1).toFixed(1),
    learners: `${(4.9 + numericIndex * 0.38).toFixed(1)}万`,
    date: `2024-05-${String(26 - (numericIndex % 20)).padStart(2, '0')}`,
    coverTitle: theme.title,
    coverSubtitle: theme.subtitle,
  }
}

function getCoverBg(resourceType) {
  return (coverThemes[resourceType] || coverThemes.course).bg
}

function getCoverIcon(resourceType) {
  return (coverThemes[resourceType] || coverThemes.course).icon
}

const filteredResources = computed(() => {
  let list = [...resourceItems.value]

  if (activeType.value !== 'all') {
    list = list.filter((item) => item.resource_type === activeType.value)
  }

  if (selectedKind.value !== '全部') {
    list = list.filter((item) => item.typeLabel === selectedKind.value)
  }

  if (selectedSubject.value !== '全部') {
    list = list.filter((item) => item.subject === selectedSubject.value)
  }

  if (selectedDifficulty.value !== '全部') {
    list = list.filter((item) => item.levelLabel === selectedDifficulty.value)
  }

  const keywordValue = keyword.value.trim().toLowerCase()
  if (keywordValue) {
    list = list.filter((item) => {
      const kpText = Array.isArray(item.knowledge_points) ? item.knowledge_points.join(' ') : ''
      return `${item.title} ${kpText} ${item.subject}`.toLowerCase().includes(keywordValue)
    })
  }

  if (selectedSort.value === '最新发布') {
    list.sort((a, b) => b.date.localeCompare(a.date))
  } else if (selectedSort.value === '最多使用') {
    list.sort((a, b) => parseFloat(b.learners) - parseFloat(a.learners))
  } else if (selectedSort.value === '最高评分') {
    list.sort((a, b) => parseFloat(b.rating) - parseFloat(a.rating))
  }

  return list
})

const pageCount = computed(() => Math.ceil(filteredResources.value.length / pageSize))

const pagedResources = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredResources.value.slice(start, start + pageSize)
})

function syncFromRoute() {
  activeType.value = typeof route.query.resource_type === 'string' ? route.query.resource_type : 'all'
  keyword.value = typeof route.query.keyword === 'string' ? route.query.keyword : ''
  currentPage.value = 1
}

function updateRouteQuery() {
  const query = { ...route.query }

  if (activeType.value !== 'all') query.resource_type = activeType.value
  else delete query.resource_type

  if (keyword.value.trim()) query.keyword = keyword.value.trim()
  else delete query.keyword

  router.replace({ query })
}

function selectType(type) {
  activeType.value = type
  currentPage.value = 1
  updateRouteQuery()
}

function applyFilters() {
  currentPage.value = 1
}

function clearFilters() {
  activeType.value = 'all'
  selectedSubject.value = '全部'
  selectedDifficulty.value = '全部'
  selectedKind.value = '全部'
  selectedSort.value = '综合推荐'
  keyword.value = ''
  currentPage.value = 1
  updateRouteQuery()
}

function openDetail(id) {
  router.push(`/resources/${id}`)
}

async function fetchResources() {
  loading.value = true
  try {
    const params = { page: 1, page_size: 60 }
    if (activeType.value !== 'all') params.resource_type = activeType.value
    const response = await getResources(params)
    resourceItems.value = (response.items || []).map(buildDisplayResource)
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query,
  () => {
    syncFromRoute()
    fetchResources()
  },
  { deep: true }
)

watch(filteredResources, () => {
  if (currentPage.value > pageCount.value && pageCount.value > 0) {
    currentPage.value = pageCount.value
  }
})

onMounted(() => {
  syncFromRoute()
  fetchResources()
})
</script>

<style scoped>
.resource-center-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rc-header h1 {
  font-size: 1.95rem;
  line-height: 1.15;
  color: #1e293b;
}

.rc-header p {
  margin-top: 6px;
  color: #64748b;
  font-size: 0.9rem;
}

.filter-panel {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
  padding: 14px 18px 16px;
}

.top-type-tabs {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #edf2f8;
  overflow-x: auto;
}

.top-type-tab {
  border: 0;
  background: transparent;
  color: #64748b;
  font: inherit;
  font-size: 0.86rem;
  cursor: pointer;
  padding: 0 0 8px;
  position: relative;
  white-space: nowrap;
}

.top-type-tab.active {
  color: #2b6cff;
  font-weight: 600;
}

.top-type-tab.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -13px;
  height: 2px;
  border-radius: 999px;
  background: #2b6cff;
}

.filter-rows {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 14px;
}

.filter-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.filter-row-label {
  width: 40px;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 28px;
  flex: none;
}

.filter-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.filter-chip {
  min-height: 28px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: #5f7190;
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}

.filter-chip:hover {
  color: #2b6cff;
}

.filter-chip.active {
  background: #edf3ff;
  border-color: #d5e3ff;
  color: #2b6cff;
}

.panel-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.filter-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.filter-search { flex: 1; max-width: 400px; }
.filter-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 14px;
  border: 1px solid #e7edf6; border-radius: 10px;
  background: #fff; color: #4f5f79; font: inherit; font-size: 0.85rem;
  cursor: pointer; white-space: nowrap;
}
.filter-toggle:hover { border-color: #2b6cff; color: #2b6cff; }
.filter-toggle .el-icon.rotated { transform: rotate(180deg); transition: transform 0.2s; }
.filter-toggle.text-action { color: #94a3b8; }
.filter-toggle.text-action:hover { color: #ef4444; border-color: #fecaca; }

.text-action,
.primary-action {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font: inherit;
  cursor: pointer;
}

.text-action {
  border: 0;
  background: transparent;
  color: #7b8798;
}

.primary-action {
  border: 1px solid #d8e5ff;
  background: #f7faff;
  color: #2b6cff;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.result-count {
  color: #64748b;
  font-size: 0.84rem;
}

.pager-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 0.82rem;
}

.pager-button {
  width: 24px;
  height: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 50%;
  background: #fff;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.pager-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.resource-card {
  background: #fff;
  border: 1px solid #e7edf6;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 28px rgba(52, 72, 108, 0.04);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.resource-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(52, 72, 108, 0.08);
}

.resource-cover {
  min-height: 132px;
  padding: 12px;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.resource-cover-top {
  display: flex;
  justify-content: flex-end;
}

.resource-type-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  color: inherit;
  font-size: 0.7rem;
}

.resource-cover-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}

.resource-cover-text strong {
  display: block;
  font-size: 0.98rem;
  line-height: 1.4;
}

.resource-cover-text span {
  display: block;
  margin-top: 4px;
  font-size: 0.76rem;
  opacity: 0.9;
}

.resource-cover-icon {
  font-size: 2rem;
  line-height: 1;
  font-weight: 700;
}

.resource-body {
  padding: 14px 14px 16px;
}

.resource-title {
  color: #1e293b;
  font-size: 0.9rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.resource-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.resource-chip {
  padding: 3px 8px;
  border-radius: 999px;
  background: #f5f7fb;
  color: #64748b;
  font-size: 0.72rem;
}

.resource-meta-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: #94a3b8;
  font-size: 0.72rem;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  padding-top: 8px;
}

@media (max-width: 1320px) {
  .resource-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .resource-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .result-toolbar,
  .filter-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-row-label {
    width: auto;
    line-height: 1;
  }

  .resource-grid {
    grid-template-columns: 1fr;
  }
}
</style>
