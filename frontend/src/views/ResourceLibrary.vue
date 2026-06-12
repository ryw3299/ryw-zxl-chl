<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { buildLessonDownloadUrl, listLessons } from '@/api/lesson'
import { useUserStore } from '@/store/userStore'
import { loadResourceLibrary, persistResourceLibrary } from '@/momo/resourceLibraryData'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const courseCatalog = Object.freeze([
  { id: 'course-1', name: '人工智能导论', accent: '#2563eb' },
  { id: 'course-2', name: '机器学习基础', accent: '#0891b2' },
  { id: 'course-3', name: '数据结构与算法', accent: '#7c3aed' },
  { id: 'course-4', name: 'Python 程序设计', accent: '#059669' },
])

const normalizeQuery = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return normalizeQuery(value[0], fallback)
  }
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const formatNow = () => {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
}

const formatFileSize = (size) => {
  const nextSize = Number(size || 0)
  if (!Number.isFinite(nextSize) || nextSize <= 0) {
    return '未知大小'
  }
  if (nextSize < 1024 * 1024) {
    return `${(nextSize / 1024).toFixed(1)} KB`
  }
  return `${(nextSize / (1024 * 1024)).toFixed(1)} MB`
}

const resources = ref(loadResourceLibrary())
const backendLessons = ref([])
const searchKeyword = ref('')
const selectedCourseId = ref(normalizeQuery(route.query.courseId))
const selectedTag = ref('全部')
const editingId = ref('')
const selectedFileMeta = ref(null)

const draft = ref({
  title: '',
  courseId: normalizeQuery(route.query.courseId),
  description: '',
  tags: '',
})

const isTeacher = computed(() => userStore.isTeacher)
const currentUserName = computed(() => userStore.userInfo.userId || (isTeacher.value ? '张老师' : '学习者'))

const normalizeLessonName = (item, fallback = '未命名课程') => normalizeQuery(item?.lessonName || item?.name || item?.title, fallback)

const lessonResources = computed(() => backendLessons.value.map((item, index) => {
  const lessonId = normalizeQuery(item.lessonId || item.id, `lesson-${index + 1}`)
  const name = normalizeLessonName(item)
  const courseId = normalizeQuery(item.courseId, lessonId)
  return {
    id: `lesson-${lessonId}`,
    source: 'lesson',
    lessonId,
    courseId,
    courseName: name,
    title: `${name} 课程包`,
    description: normalizeQuery(item.courseDesc || item.desc || item.description, '来自我的课程接口，可进入课时学习或下载已生成课件。'),
    tags: [normalizeQuery(item.tag, '课程'), normalizeQuery(item.status || item.coursewareStatus, '已发布')].filter(Boolean),
    fileName: `${name}.pptx`,
    fileSize: '课程资源',
    fileType: 'COURSE',
    uploadedAt: normalizeQuery(item.updatedAt || item.createdAt || item.publishTime, '来自我的课程'),
    uploader: normalizeQuery(item.teacherName || item.uploader, '课程教师'),
    downloadCount: Number(item.downloadCount || item.viewCount || 0),
    accent: ['#2563eb', '#0891b2', '#7c3aed', '#059669'][index % 4],
  }
}))

const displayResources = computed(() => {
  const existingIds = new Set(resources.value.map((item) => item.id))
  return [
    ...lessonResources.value.filter((item) => !existingIds.has(item.id)),
    ...resources.value,
  ]
})

const pageTitle = computed(() => (isTeacher.value ? '学习资源库' : '课程资源'))
const pageSubtitle = computed(() => (
  isTeacher.value
    ? '上传课程讲义、实验模板与补充资料，统一管理班级可见资源。'
    : '按课程筛选学习资料，查看重点讲义、实验模板与课堂补充资源。'
))

const allTags = computed(() => {
  const tagSet = new Set(['全部'])
  resources.value.forEach((item) => {
    item.tags.forEach((tag) => tagSet.add(tag))
  })
  return [...tagSet]
})

const availableCourses = computed(() => {
  const courseMap = new Map(courseCatalog.map((item) => [item.id, { ...item }]))
  backendLessons.value.forEach((item, index) => {
    const lessonId = normalizeQuery(item.lessonId || item.id, `lesson-${index + 1}`)
    const courseId = normalizeQuery(item.courseId, lessonId)
    if (!courseMap.has(courseId)) {
      courseMap.set(courseId, {
        id: courseId,
        name: normalizeLessonName(item),
        accent: ['#2563eb', '#0891b2', '#7c3aed', '#059669'][index % 4],
      })
    }
  })
  resources.value.forEach((item) => {
    if (!courseMap.has(item.courseId)) {
      courseMap.set(item.courseId, {
        id: item.courseId,
        name: item.courseName,
        accent: item.accent || '#2563eb',
      })
    }
  })
  return [...courseMap.values()]
})

const filteredResources = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return displayResources.value.filter((item) => {
    const matchKeyword = !keyword || `${item.title} ${item.description} ${item.courseName} ${item.fileName} ${item.tags.join(' ')}`.toLowerCase().includes(keyword)
    const matchCourse = !selectedCourseId.value || item.courseId === selectedCourseId.value
    const matchTag = selectedTag.value === '全部' || item.tags.includes(selectedTag.value)
    return matchKeyword && matchCourse && matchTag
  })
})

const rankedResources = computed(() => [...displayResources.value]
  .sort((left, right) => right.downloadCount - left.downloadCount || left.title.localeCompare(right.title, 'zh-CN'))
  .slice(0, 5))

const summaryCards = computed(() => {
  const totalDownloads = displayResources.value.reduce((sum, item) => sum + Number(item.downloadCount || 0), 0)
  const teacherUploads = resources.value.filter((item) => item.uploader === currentUserName.value).length

  return isTeacher.value
    ? [
      { label: '资源总数', value: String(resources.value.length) },
      { label: '累计下载', value: String(totalDownloads) },
      { label: '我的上传', value: String(teacherUploads) },
    ]
    : [
      { label: '可用资源', value: String(filteredResources.value.length) },
      { label: '最热资料', value: rankedResources.value[0]?.title || '暂无' },
      { label: '覆盖课程', value: String(availableCourses.value.length) },
    ]
})

const sideNotes = computed(() => (
  isTeacher.value
    ? [
      '适合上传导学讲义、实验模板、课堂案例和作业说明。',
      '当前版本仅实现前端演示，文件内容不会真正上传到后端。',
      '后续可把下载统计和课程资源表接入教师学情分析页。',
    ]
    : [
      '优先查看带“重点”“导学”“实验”标签的资料。',
      '下载量较高的资料通常更贴合当前课堂进度。',
      '当前下载为前端演示动作，后续可接入真实资源服务。',
    ]
))

const isEditing = computed(() => Boolean(editingId.value))

const resetDraft = () => {
  draft.value = {
    title: '',
    courseId: selectedCourseId.value || normalizeQuery(route.query.courseId),
    description: '',
    tags: '',
  }
  selectedFileMeta.value = null
  editingId.value = ''
}

const persistResources = () => {
  persistResourceLibrary(resources.value)
}

const handleFileChange = (event) => {
  const file = event.target?.files?.[0]
  if (!file) {
    selectedFileMeta.value = null
    return
  }
  const extension = file.name.includes('.') ? file.name.split('.').pop().toUpperCase() : 'FILE'
  selectedFileMeta.value = {
    fileName: file.name,
    fileSize: formatFileSize(file.size),
    fileType: extension,
  }
}

const handleSubmit = () => {
  if (!isTeacher.value) return

  const course = availableCourses.value.find((item) => item.id === draft.value.courseId)
  const title = draft.value.title.trim()
  const description = draft.value.description.trim()
  const tags = draft.value.tags.split(/[,，]/).map((item) => item.trim()).filter(Boolean)

  if (!title) return ElMessage.warning('请填写资源标题')
  if (!course) return ElMessage.warning('请选择所属课程')
  if (!description) return ElMessage.warning('请填写资源说明')
  if (!selectedFileMeta.value && !isEditing.value) return ElMessage.warning('请选择资源文件')

  const currentFileMeta = selectedFileMeta.value || resources.value.find((item) => item.id === editingId.value)
  const nextItem = {
    id: editingId.value || `res-${Date.now()}`,
    title,
    courseId: course.id,
    courseName: course.name,
    description,
    tags: tags.length ? tags : ['未分类'],
    fileName: currentFileMeta?.fileName || `${title}.file`,
    fileSize: currentFileMeta?.fileSize || '未知大小',
    fileType: currentFileMeta?.fileType || 'FILE',
    uploadedAt: formatNow(),
    uploader: currentUserName.value,
    downloadCount: isEditing.value ? (resources.value.find((item) => item.id === editingId.value)?.downloadCount || 0) : 0,
    accent: course.accent,
  }

  if (isEditing.value) {
    resources.value = resources.value.map((item) => (item.id === editingId.value ? nextItem : item))
    ElMessage.success('资源信息已更新')
  } else {
    resources.value = [nextItem, ...resources.value]
    ElMessage.success('资源已加入资源库')
  }

  persistResources()
  resetDraft()
}

const handleEdit = (item) => {
  if (!isTeacher.value) return
  editingId.value = item.id
  draft.value = {
    title: item.title,
    courseId: item.courseId,
    description: item.description,
    tags: item.tags.join(', '),
  }
  selectedFileMeta.value = {
    fileName: item.fileName,
    fileSize: item.fileSize,
    fileType: item.fileType,
  }
}

const handleDelete = (id) => {
  if (!isTeacher.value) return
  resources.value = resources.value.filter((item) => item.id !== id)
  persistResources()
  if (editingId.value === id) resetDraft()
  ElMessage.success('资源已删除')
}

const handleDownload = (item) => {
  if (item.source === 'lesson') {
    window.open(buildLessonDownloadUrl(item.lessonId), '_blank', 'noopener')
    return
  }
  resources.value = resources.value.map((resource) => (
    resource.id === item.id ? { ...resource, downloadCount: resource.downloadCount + 1 } : resource
  ))
  persistResources()
  ElMessage.success(`已记录下载：${item.title}`)
}

const openLesson = (item) => {
  router.push({
    path: '/pc/lesson/player',
    query: { courseId: item.courseId, lessonId: item.lessonId || '1' },
  })
}

const loadMyCourses = async () => {
  try {
    const result = await listLessons('', { silent: true })
    backendLessons.value = Array.isArray(result?.lessons) ? result.lessons : Array.isArray(result) ? result : []
  } catch {
    backendLessons.value = []
  }
}

const clearFilters = () => {
  searchKeyword.value = ''
  selectedCourseId.value = ''
  selectedTag.value = '全部'
}

onMounted(loadMyCourses)
</script>

<template>
  <div class="resource-page">
    <section class="hero-panel resource-hero-panel" :class="{ 'is-teacher': isTeacher }">
      <div class="hero-copy">
        <p class="view-kicker">{{ isTeacher ? 'Resource Workspace' : 'Learning Materials' }}</p>
        <h1 class="hero-title">{{ pageTitle }}</h1>
        <p class="hero-subtitle">{{ pageSubtitle }}</p>
        <div class="hero-metrics">
          <div v-for="metric in summaryCards" :key="metric.label" class="hero-metric">
            <span class="hero-metric-value">{{ metric.value }}</span>
            <span class="hero-metric-label">{{ metric.label }}</span>
          </div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="ring ring-lg" />
        <div class="ring ring-md" />
        <div class="ring ring-sm" />
        <div class="resource-core">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            <line x1="12" y1="11" x2="12" y2="17"></line>
            <line x1="9" y1="14" x2="15" y2="14"></line>
          </svg>
        </div>
      </div>
    </section>

    <section class="toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input v-model="searchKeyword" class="search-input" type="text" placeholder="搜索资源标题或标签...">
        </div>
        <div class="tag-strip">
          <button v-for="tag in allTags.slice(0, 6)" :key="tag" class="filter-pill"
            :class="{ active: selectedTag === tag }" @click="selectedTag = tag">
            {{ tag }}
          </button>
        </div>
      </div>
      <div class="toolbar-right">
        <label class="select-label" for="course-filter">筛选课程</label>
        <select id="course-filter" v-model="selectedCourseId" class="course-select">
          <option value="">全部课程</option>
          <option v-for="course in availableCourses" :key="course.id" :value="course.id">{{ course.name }}</option>
        </select>
        <button class="icon-btn" title="清空筛选" @click="clearFilters">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </section>

    <section class="main-grid">
      <div class="content-col">
        <div v-if="isTeacher" class="block-panel composer-panel">
          <div class="section-head compact">
            <div>
              <p class="section-eyebrow">UPLOAD</p>
              <h2 class="section-title">{{ isEditing ? '编辑资源信息' : '上传新资源' }}</h2>
            </div>
            <button v-if="isEditing" class="text-btn" @click="resetDraft">取消编辑</button>
          </div>

          <div class="composer-grid">
            <label class="field">
              <span class="field-label">资源标题</span>
              <input v-model="draft.title" class="field-input" type="text" placeholder="例如：机器学习实验模板">
            </label>
            <label class="field compact">
              <span class="field-label">所属课程</span>
              <select v-model="draft.courseId" class="field-input">
                <option value="">请选择课程</option>
                <option v-for="course in availableCourses" :key="course.id" :value="course.id">{{ course.name }}
                </option>
              </select>
            </label>
            <label class="field full">
              <span class="field-label">资源标签</span>
              <input v-model="draft.tags" class="field-input" type="text" placeholder="用逗号分隔，例如：导学, 重点, 实验">
            </label>
            <label class="field full">
              <span class="field-label">资源说明</span>
              <textarea v-model="draft.description" class="field-input field-area" rows="2"
                placeholder="简要说明资源用途、适用章节与使用方式"></textarea>
            </label>
          </div>

          <div class="upload-strip">
            <label class="upload-box">
              <input class="upload-input" type="file" @change="handleFileChange">
              <span class="upload-title">{{ selectedFileMeta ? selectedFileMeta.fileName : '点击选择资源文件' }}</span>
              <span class="upload-desc">{{ selectedFileMeta ? `${selectedFileMeta.fileType} ·
                ${selectedFileMeta.fileSize}` : '支持 PDF, DOCX, ZIP 等格式' }}</span>
            </label>
            <div class="composer-actions">
              <button class="row-btn ghost" type="button" @click="resetDraft">重置</button>
              <button class="row-btn primary" type="button" @click="handleSubmit">{{ isEditing ? '保存修改' : '加入资源库'
              }}</button>
            </div>
          </div>
        </div>

        <div class="block-panel list-panel">
          <div class="section-head compact">
            <div>
              <p class="section-eyebrow">{{ isTeacher ? 'MANAGE' : 'BROWSE' }}</p>
              <h2 class="section-title">{{ isTeacher ? '完整资源列表' : '资源浏览' }}</h2>
            </div>
            <div class="section-note">共匹配到 {{ filteredResources.length }} 项</div>
          </div>

          <div v-if="filteredResources.length" class="resource-list">
            <article v-for="item in filteredResources" :key="item.id" class="resource-row"
              :style="{ '--accent': item.accent }">
              <div class="resource-cover">
                <span class="resource-type">{{ item.fileType }}</span>
                <strong>{{ item.courseName }}</strong>
              </div>
              <div class="resource-body">
                <div class="resource-topline">
                  <h4>{{ item.title }}</h4>
                </div>
                <p class="resource-desc">{{ item.description }}</p>
                <div class="resource-meta">
                  <span class="meta-tag">{{ item.fileName }} ({{ item.fileSize }})</span>
                  <span class="meta-tag">下载 {{ item.downloadCount }}</span>
                  <span class="meta-tag">上传者 {{ item.uploader }}</span>
                  <span class="meta-tag">{{ item.uploadedAt.split(' ')[0] }}</span>
                </div>
                <div class="resource-tags">
                  <span v-for="tag in item.tags" :key="tag" class="resource-tag">{{ tag }}</span>
                </div>
              </div>
              <div class="resource-actions">
                <button class="row-btn ghost" @click="openLesson(item)">{{ isTeacher ? '进入课程' : '查看课时' }}</button>
                <button class="row-btn primary" @click="handleDownload(item)">下载</button>
                <button v-if="isTeacher" class="row-btn ghost" @click="handleEdit(item)">编辑</button>
                <button v-if="isTeacher" class="row-btn danger" @click="handleDelete(item.id)">删除</button>
              </div>
            </article>
          </div>
          <div v-else class="empty-state">
            <strong>{{ isTeacher ? '没有匹配的资源。' : '没有匹配的资源，换个筛选条件试试。' }}</strong>
            <span>{{ isTeacher ? '可以尝试更改上方的筛选条件。' : '可以清空筛选，查看全部课程资源。' }}</span>
          </div>
        </div>
      </div>

      <aside class="side-panel">
        <div class="spotlight-card">
          <p class="section-eyebrow">RANKING</p>
          <h3 class="spotlight-title">资源热度排行</h3>
          <div class="ranking-list">
            <div v-for="(item, index) in rankedResources" :key="item.id" class="ranking-item">
              <span class="ranking-index" :class="`top-${index + 1}`">TOP {{ index + 1 }}</span>
              <div class="ranking-body">
                <strong>{{ item.title }}</strong>
                <span>{{ item.courseName }} · 下载 {{ item.downloadCount }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="spotlight-card">
          <p class="section-eyebrow">COURSES</p>
          <h3 class="spotlight-title">课程分布</h3>
          <div class="course-summary">
            <div v-for="course in availableCourses" :key="course.id" class="course-summary-row">
              <div class="course-summary-label">
                <span class="course-dot" :style="{ background: course.accent }" />
                <span>{{ course.name }}</span>
              </div>
              <strong>{{ displayResources.filter((item) => item.courseId === course.id).length }}</strong>
            </div>
          </div>
        </div>

        <div class="spotlight-card">
          <p class="section-eyebrow">GUIDE</p>
          <h3 class="spotlight-title">{{ isTeacher ? '上传提示' : '使用建议' }}</h3>
          <ul class="notes-list">
            <li v-for="note in sideNotes" :key="note">{{ note }}</li>
          </ul>
        </div>
      </aside>
    </section>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Noto+Serif+SC:wght@600;700&display=swap');

*,
*::before,
*::after {
  box-sizing: border-box;
}

.resource-page {
  position: relative;
  min-height: 100vh;
  padding: 40px 32px 48px;
  background:
    radial-gradient(circle at top left, rgba(96, 165, 250, 0.18), transparent 24%),
    radial-gradient(circle at right 20%, rgba(14, 165, 233, 0.14), transparent 22%),
    radial-gradient(circle at 50% 10%, rgba(255, 255, 255, 0.95), transparent 32%),
    linear-gradient(180deg, #f4f7fc 0%, #eef3fb 100%);
  font-family: 'Sora', sans-serif;
  color: #0f172a;
}

.resource-page::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(148, 163, 184, 0.05) 1px, transparent 1px),
    linear-gradient(rgba(148, 163, 184, 0.05) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.28), transparent 76%);
  opacity: 0.35;
}

/* ================== Layout ================== */
.hero-panel,
.toolbar,
.main-grid {
  position: relative;
  z-index: 1;
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

/* ================== Hero Panel ================== */
.hero-panel {
  padding: 42px 48px;
  border-radius: 28px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 28px;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 58%, #3b82f6 100%);
  overflow: hidden;
  box-shadow: 0 28px 64px rgba(15, 23, 42, 0.14);
}

.hero-panel.is-teacher {
  background: linear-gradient(135deg,
      #0f172a 0%,
      #1e3a8a 58%,
      #3b82f6 100%);
}

.hero-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at 22% 18%, rgba(255, 255, 255, 0.14), transparent 24%),
    linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.06) 50%, transparent 100%);
}

.hero-copy,
.hero-visual {
  position: relative;
  z-index: 1;
}

.hero-eyebrow {
  margin: 0 0 10px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #7dd3fc;
  text-transform: uppercase;
}

.hero-panel.is-teacher .hero-eyebrow {
  color: #5eead4;
}

.hero-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 42px;
  line-height: 1.2;
  color: #f8fbff;
}

.hero-subtitle {
  max-width: 720px;
  margin: 16px 0 28px;
  font-size: 14px;
  line-height: 1.85;
  color: #c5defb;
}

.hero-panel.is-teacher .hero-subtitle {
  color: #ccfbf1;
}

.hero-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.hero-metric {
  min-width: 140px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.hero-metric-value {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
}

.hero-metric-label {
  font-size: 12px;
  color: #b8d4f7;
}

.hero-panel.is-teacher .hero-metric-label {
  color: #99f6e4;
}

.hero-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.ring-lg {
  width: 200px;
  height: 200px;
}

.ring-md {
  width: 148px;
  height: 148px;
  border-style: dashed;
  border-color: rgba(255, 255, 255, 0.35);
}

.ring-sm {
  width: 98px;
  height: 98px;
  border-color: rgba(255, 255, 255, 0.32);
}

.resource-core {
  width: 76px;
  height: 76px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  box-shadow: 0 0 0 10px rgba(255, 255, 255, 0.06), 0 18px 36px rgba(15, 23, 42, 0.28);
}

.hero-panel.is-teacher .resource-core {
  background: linear-gradient(135deg, #14b8a6, #2dd4bf);
}

/* ================== Toolbar ================== */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 22px;
  padding: 14px 22px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #dde8f5;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(12px);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  flex: 1;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  height: 40px;
  background: #f4f7fb;
  border: 1px solid #dce5ef;
  border-radius: 12px;
  color: #6b7f99;
  width: 260px;
}

.search-input {
  all: unset;
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #173354;
}

.search-input::placeholder {
  color: #8ba1ba;
}

.tag-strip {
  display: flex;
  gap: 8px;
}

.filter-pill {
  all: unset;
  cursor: pointer;
  padding: 8px 15px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #69809c;
  background: rgba(240, 245, 252, 0.92);
  transition: all 0.18s ease;
}

.filter-pill.active,
.filter-pill:hover {
  color: #1d4ed8;
  background: #e0ecff;
  transform: translateY(-1px);
}

.select-label {
  font-size: 12px;
  font-weight: 700;
  color: #6f86a3;
}

.course-select {
  height: 40px;
  min-width: 170px;
  padding: 0 14px;
  border: 1px solid #d6e4f3;
  border-radius: 12px;
  background: #f9fbfe;
  color: #1f3d63;
  font: 600 12px 'Sora', sans-serif;
  outline: none;
}

.icon-btn {
  all: unset;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f4f7fb;
  color: #69809c;
  transition: 0.2s;
}

.icon-btn:hover {
  background: #e0ecff;
  color: #1d4ed8;
}

/* ================== Main Grid & Panels ================== */
.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.9fr);
  gap: 20px;
  margin-top: 20px;
}

.content-col {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.block-panel,
.spotlight-card {
  border-radius: 24px;
  border: 1px solid #dce7f4;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(12px);
  padding: 24px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-head.compact {
  margin-bottom: 14px;
}

.section-eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #88a0bd;
  text-transform: uppercase;
}

.section-title {
  margin: 0;
  font-family: 'Noto Serif SC', serif;
  font-size: 24px;
  color: #13253f;
}

.section-note {
  font-size: 12px;
  color: #7d90a8;
  font-weight: 600;
  padding: 4px 10px;
  background: #eef4fc;
  border-radius: 8px;
}

/* Form Fields (Composer) */
.composer-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field.compact {
  flex: 0 0 auto;
}

.field.full {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 12px;
  font-weight: 700;
  color: #6b7f99;
}

.field-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #dce5ef;
  background: #fbfdff;
  font-family: inherit;
  font-size: 13px;
  color: #153354;
  transition: all 0.2s;
}

.field-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.field-area {
  resize: vertical;
  min-height: 80px;
}

.upload-strip {
  display: flex;
  gap: 16px;
  margin-top: 16px;
  align-items: stretch;
}

.upload-box {
  flex: 1;
  position: relative;
  padding: 16px;
  border-radius: 16px;
  border: 2px dashed #bfdbfe;
  background: #eff6ff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: 0.2s;
  text-align: center;
}

.upload-box:hover {
  border-color: #3b82f6;
  background: #e0ecff;
}

.upload-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.upload-title {
  font-size: 13px;
  font-weight: 700;
  color: #1d4ed8;
}

.upload-desc {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}

.composer-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: center;
  width: 120px;
}

/* Resource Row */
.resource-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.resource-row {
  display: grid;
  grid-template-columns: 140px 1fr 100px;
  gap: 18px;
  align-items: center;
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #fbfdff, #f6faff);
  border: 1px solid #e5eef8;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.resource-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.06);
  border-color: #cdddf2;
}

.resource-cover {
  background: linear-gradient(145deg, var(--accent), color-mix(in srgb, var(--accent) 50%, #000));
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #fff;
  min-height: 100px;
}

.resource-type {
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(4px);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 800;
  width: max-content;
}

.resource-cover strong {
  font-size: 14px;
  line-height: 1.3;
  margin-top: 10px;
}

.resource-topline h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #153354;
}

.resource-desc {
  font-size: 13px;
  color: #6d84a0;
  margin: 6px 0 10px;
  line-height: 1.5;
}

.resource-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.meta-tag {
  font-size: 11px;
  font-weight: 600;
  color: #7d92ab;
  background: #eef4fb;
  padding: 4px 8px;
  border-radius: 6px;
}

.resource-tags {
  display: flex;
  gap: 6px;
}

.resource-tag {
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
}

.resource-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Buttons inside forms/lists */
.text-btn {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.text-btn:hover {
  text-decoration: underline;
}

.row-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: 0.2s;
  text-align: center;
}

.primary {
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3);
}

.ghost {
  color: #4b6483;
  background: #eef4fc;
}

.ghost:hover {
  background: #dce9f9;
  color: #163a63;
}

.danger {
  color: #ef4444;
  background: #fef2f2;
}

.danger:hover {
  background: #fee2e2;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  background: #f8fafc;
  border: 2px dashed #e2e8f0;
  border-radius: 16px;
}

.empty-state strong {
  display: block;
  font-size: 14px;
  color: #334155;
  margin-bottom: 4px;
}

.empty-state span {
  font-size: 12px;
  color: #64748b;
}

/* Sidebar Elements */
.spotlight-title {
  margin: 0;
  font-size: 20px;
  font-family: 'Noto Serif SC', serif;
  color: #153354;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 14px;
  background: #fbfdff;
  border: 1px solid #edf3fa;
}

.ranking-index {
  background: #eef4fc;
  color: #6b7f99;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  margin-right: 12px;
}

.ranking-index.top-1 {
  background: #fffbeb;
  color: #d97706;
}

.ranking-index.top-2 {
  background: #f8fafc;
  color: #64748b;
}

.ranking-index.top-3 {
  background: #fff7ed;
  color: #ea580c;
}

.ranking-body strong {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #153354;
  margin-bottom: 2px;
}

.ranking-body span {
  font-size: 11px;
  color: #7d92ab;
}

.course-summary {
  margin-top: 16px;
}

.course-summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px dashed #e2e8f0;
}

.course-summary-row:last-child {
  border-bottom: none;
}

.course-summary-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #153354;
}

.course-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.notes-list {
  margin: 16px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: #6d84a0;
  line-height: 1.6;
}

.notes-list li+li {
  margin-top: 6px;
}

/* Responsive */
@media (max-width: 1100px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .composer-grid {
    grid-template-columns: 1fr;
  }

  .resource-row {
    grid-template-columns: 120px 1fr;
  }

  .resource-actions {
    grid-column: 1 / -1;
    flex-direction: row;
  }

  .row-btn {
    flex: 1;
  }
}

@media (max-width: 820px) {
  .resource-page {
    padding: 18px 14px 34px;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    flex-wrap: wrap;
    width: 100%;
  }

  .search-box {
    width: 100%;
  }

  .hero-panel {
    grid-template-columns: 1fr;
    padding: 32px 24px;
  }

  .hero-title {
    font-size: 34px;
  }

  .hero-visual {
    min-height: 180px;
  }

  .resource-row {
    grid-template-columns: 1fr;
    padding: 14px;
  }

  .resource-cover {
    min-height: 80px;
  }
}

/* ================== Portal Theme Sync ================== */
.resource-page {
  --resource-bg: #f8fafc;
  --resource-surface: #ffffff;
  --resource-surface-soft: #f0fdfa;
  --resource-border: #e2e8f0;
  --resource-border-strong: #ccfbf1;
  --resource-text: #0f172a;
  --resource-muted: #64748b;
  --resource-subtle: #94a3b8;
  --resource-primary: #14b8a6;
  --resource-primary-strong: #0f766e;
  --resource-primary-soft: #ccfbf1;
  padding: 24px 32px 40px;
  background:
    radial-gradient(circle at 18% 0%, rgba(20, 184, 166, 0.12), transparent 28%),
    radial-gradient(circle at 88% 16%, rgba(37, 99, 235, 0.08), transparent 24%),
    var(--resource-bg);
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--resource-text);
  overflow-x: hidden;
}

.resource-page::before {
  background:
    linear-gradient(90deg, rgba(15, 118, 110, 0.045) 1px, transparent 1px),
    linear-gradient(rgba(15, 118, 110, 0.045) 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.52;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.2), transparent 64%);
}

.hero-panel,
.toolbar,
.main-grid {
  max-width: 1480px;
}

.hero-panel,
.hero-panel.is-teacher {
  min-height: 230px;
  padding: 30px 34px;
  grid-template-columns: minmax(0, 1fr) 230px;
  border-radius: 18px;
  border: 1px solid rgba(153, 246, 228, 0.52);
  background:
    radial-gradient(circle at 82% 18%, rgba(209, 250, 229, 0.42), transparent 24%),
    radial-gradient(circle at 18% 0%, rgba(45, 212, 191, 0.3), transparent 28%),
    linear-gradient(128deg, #0f172a 0%, #134e4a 28%, #0f766e 50%, #14b8a6 72%, #99f6e4 100%);
  box-shadow: 0 18px 40px rgba(15, 118, 110, 0.16);
}

.hero-panel::before {
  background:
    linear-gradient(115deg, rgba(255, 255, 255, 0.2), transparent 38%),
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.58;
}

.hero-panel::after {
  content: "";
  position: absolute;
  right: -58px;
  bottom: -76px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  pointer-events: none;
}

.hero-eyebrow,
.section-eyebrow {
  letter-spacing: 0.12em;
}

.hero-eyebrow,
.hero-panel.is-teacher .hero-eyebrow {
  margin-bottom: 8px;
  color: rgba(240, 253, 250, 0.84);
}

.hero-title {
  font-family: inherit;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 0;
  color: #ffffff;
}

.hero-subtitle,
.hero-panel.is-teacher .hero-subtitle {
  max-width: 690px;
  margin: 12px 0 22px;
  color: rgba(240, 253, 250, 0.86);
  font-size: 14px;
  line-height: 1.75;
}

.hero-metrics {
  gap: 10px;
}

.hero-metric {
  min-width: 126px;
  padding: 11px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.hero-metric-value {
  font-size: 22px;
  line-height: 1.15;
}

.hero-metric-label,
.hero-panel.is-teacher .hero-metric-label {
  color: rgba(240, 253, 250, 0.78);
}

.hero-visual {
  min-height: 168px;
}

.ring {
  border-color: rgba(255, 255, 255, 0.26);
}

.ring-lg {
  width: 178px;
  height: 178px;
}

.ring-md {
  width: 128px;
  height: 128px;
}

.ring-sm {
  width: 78px;
  height: 78px;
}

.resource-core,
.hero-panel.is-teacher .resource-core {
  width: 70px;
  height: 70px;
  border-radius: 18px;
  color: #0f766e;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(240, 253, 250, 0.86));
  box-shadow:
    0 0 0 12px rgba(255, 255, 255, 0.1),
    0 18px 34px rgba(15, 23, 42, 0.18);
}

.toolbar {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 14px;
  border-color: var(--resource-border);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.search-box,
.course-select,
.icon-btn {
  height: 38px;
  border-radius: 10px;
  border-color: var(--resource-border);
  background: #ffffff;
  color: var(--resource-muted);
}

.search-box:focus-within,
.course-select:focus {
  border-color: var(--resource-primary);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.12);
}

.search-input {
  color: var(--resource-text);
}

.filter-pill {
  padding: 8px 13px;
  color: var(--resource-muted);
  background: #f8fafc;
  border: 1px solid transparent;
}

.filter-pill.active,
.filter-pill:hover {
  color: var(--resource-primary-strong);
  background: var(--resource-surface-soft);
  border-color: var(--resource-border-strong);
}

.select-label {
  color: var(--resource-muted);
}

.icon-btn:hover {
  background: var(--resource-surface-soft);
  color: var(--resource-primary-strong);
}

.main-grid {
  grid-template-columns: minmax(0, 1.62fr) minmax(300px, 0.72fr);
  gap: 18px;
  margin-top: 18px;
}

.content-col,
.side-panel {
  gap: 18px;
}

.block-panel,
.spotlight-card {
  border-radius: 14px;
  border-color: var(--resource-border);
  background: var(--resource-surface);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.055);
  backdrop-filter: none;
  padding: 20px;
}

.section-eyebrow {
  color: var(--resource-primary-strong);
  font-size: 10px;
}

.section-title,
.spotlight-title {
  font-family: inherit;
  color: var(--resource-text);
  font-weight: 800;
}

.section-title {
  font-size: 21px;
}

.spotlight-title {
  font-size: 18px;
}

.section-note {
  background: var(--resource-surface-soft);
  color: var(--resource-primary-strong);
  border: 1px solid var(--resource-border-strong);
}

.field-label {
  color: var(--resource-muted);
}

.field-input {
  border-radius: 10px;
  border-color: var(--resource-border);
  background: #ffffff;
  color: var(--resource-text);
}

.field-input:focus {
  border-color: var(--resource-primary);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.12);
}

.upload-box {
  border-radius: 12px;
  border-color: #99f6e4;
  background:
    linear-gradient(135deg, rgba(240, 253, 250, 0.94), rgba(255, 255, 255, 0.96));
}

.upload-box:hover {
  border-color: var(--resource-primary);
  background: var(--resource-surface-soft);
}

.upload-title {
  color: var(--resource-primary-strong);
}

.resource-list {
  gap: 10px;
}

.resource-row {
  position: relative;
  grid-template-columns: 118px minmax(0, 1fr) 108px;
  gap: 16px;
  padding: 14px;
  border-radius: 13px;
  background:
    radial-gradient(circle at 96% 10%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 34%),
    linear-gradient(180deg, #ffffff, #fbfdff);
  border-color: var(--resource-border);
  overflow: hidden;
}

.resource-row::before {
  content: "";
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 999px;
  background: var(--accent);
}

.resource-row:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--accent) 26%, var(--resource-border));
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
}

.resource-cover {
  position: relative;
  min-height: 88px;
  border-radius: 12px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent) 88%, #ffffff), color-mix(in srgb, var(--accent) 48%, #0f172a));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
  overflow: hidden;
}

.resource-cover::after {
  content: "";
  width: 42px;
  height: 42px;
  position: absolute;
  right: 10px;
  bottom: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.13);
}

.resource-type {
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.2);
}

.resource-topline h4 {
  color: var(--resource-text);
  font-size: 15px;
}

.resource-desc {
  color: var(--resource-muted);
}

.meta-tag {
  color: var(--resource-muted);
  background: #f8fafc;
  border: 1px solid #edf2f7;
}

.resource-tag {
  color: var(--resource-primary-strong);
  background: var(--resource-surface-soft);
}

.row-btn {
  border-radius: 9px;
}

.primary {
  background: linear-gradient(135deg, var(--resource-primary), var(--resource-primary-strong));
  box-shadow: 0 8px 18px rgba(20, 184, 166, 0.18);
}

.primary:hover {
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.28);
}

.ghost {
  color: var(--resource-muted);
  background: #f8fafc;
  border: 1px solid #edf2f7;
}

.ghost:hover {
  background: var(--resource-surface-soft);
  color: var(--resource-primary-strong);
}

.text-btn {
  color: var(--resource-primary-strong);
}

.empty-state {
  background: #ffffff;
  border-color: var(--resource-border);
}

.ranking-item {
  border-radius: 11px;
  background:
    linear-gradient(135deg, #ffffff, #f8fafc);
  border-color: var(--resource-border);
}

.ranking-index {
  background: var(--resource-surface-soft);
  color: var(--resource-primary-strong);
}

.ranking-body strong,
.course-summary-label {
  color: var(--resource-text);
}

.ranking-body span,
.notes-list {
  color: var(--resource-muted);
}

.course-summary-row {
  border-bottom-color: #edf2f7;
}

@media (max-width: 1100px) {
  .resource-row {
    grid-template-columns: 112px minmax(0, 1fr);
  }
}

@media (max-width: 820px) {
  .resource-page {
    padding: 18px 14px 32px;
  }

  .hero-panel,
  .hero-panel.is-teacher {
    min-height: auto;
    padding: 24px 20px;
    border-radius: 16px;
  }

  .hero-title {
    font-size: 28px;
  }

  .hero-visual {
    min-height: 124px;
  }

  .hero-metric {
    min-width: 0;
    flex: 1 1 120px;
  }
}

.resource-page .resource-hero-panel {
  display: grid !important;
  min-height: 210px !important;
  padding: 22px 24px !important;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 330px) !important;
  align-items: stretch !important;
  gap: 20px !important;
  border-radius: var(--resource-radius, 8px) !important;
  border: 1px solid rgba(20, 184, 166, 0.16) !important;
  color: var(--resource-text) !important;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(255, 255, 255, 0.92) 46%, rgba(14, 165, 233, 0.16)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px) !important;
  background-size: auto, 22px 22px, 22px 22px !important;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07) !important;
}

.resource-page .toolbar,
.resource-page .main-grid {
  margin-left: auto !important;
  margin-right: auto !important;
  width: calc(100% - 192px) !important;
}

.resource-page .resource-hero-panel::before {
  display: block !important;
  background:
    radial-gradient(circle at 72% 22%, rgba(20, 184, 166, 0.14), transparent 24%),
    radial-gradient(circle at 95% 72%, rgba(59, 130, 246, 0.12), transparent 22%) !important;
  background-size: auto !important;
  opacity: 1 !important;
}

.resource-page .resource-hero-panel::after {
  display: block !important;
  right: -46px !important;
  bottom: -70px !important;
  width: 190px !important;
  height: 190px !important;
  background: rgba(20, 184, 166, 0.08) !important;
}

.resource-page .resource-hero-panel .hero-title {
  color: var(--resource-text) !important;
  font-size: 30px !important;
  font-weight: 800 !important;
  line-height: 1.18 !important;
}

.resource-page .resource-hero-panel .hero-eyebrow {
  color: var(--resource-primary) !important;
  font-size: 13px !important;
  letter-spacing: 0 !important;
}

.resource-page .resource-hero-panel .hero-subtitle {
  color: var(--resource-muted) !important;
  max-width: 640px !important;
  font-size: 15px !important;
}

.resource-page .resource-hero-panel .hero-metrics {
  display: flex !important;
}

.resource-page .resource-hero-panel .hero-visual,
.resource-page .resource-hero-panel .ring,
.resource-page .resource-hero-panel .resource-core {
  display: flex !important;
}

.resource-page .resource-hero-panel .ring {
  display: block !important;
}

.resource-page .resource-hero-panel .hero-metric {
  background: rgba(255, 255, 255, 0.72) !important;
  border: 1px solid rgba(15, 118, 110, 0.12) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}

.resource-page .resource-hero-panel .hero-metric-value {
  color: var(--resource-text) !important;
}

.resource-page .resource-hero-panel .hero-metric-label {
  color: #134e4a !important;
}

.resource-page .resource-hero-panel .hero-visual {
  min-height: 150px !important;
}

.resource-page .resource-hero-panel .ring {
  border-color: rgba(20, 184, 166, 0.2) !important;
}

.resource-page .resource-hero-panel .ring-md {
  border-color: rgba(20, 184, 166, 0.32) !important;
}

.resource-page .resource-hero-panel .resource-core {
  color: var(--resource-primary-strong) !important;
  background: rgba(255, 255, 255, 0.78) !important;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.07) !important;
}

@media (max-width: 820px) {
  .resource-page .toolbar,
  .resource-page .main-grid {
    width: 100% !important;
  }

  .resource-page .resource-hero-panel {
    min-height: auto !important;
    padding: 24px 20px !important;
    grid-template-columns: 1fr !important;
  }

  .resource-page .resource-hero-panel .hero-title {
    font-size: 28px !important;
  }
}
</style>
