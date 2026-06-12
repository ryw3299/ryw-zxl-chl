<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Close, Plus } from '@element-plus/icons-vue'
import { buildLessonDownloadUrl, editScript, getScriptStatus, renderLessonPpt } from '@/api/lesson'
import { DEFAULT_SCHOOL_ID } from '@/utils/signature'
import { useLessonStore } from '@/store/lessonStore'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()

const saving = ref(false)
const generatingVoice = ref(false)
const activeSectionId = ref('')
const scriptStructure = ref([])
const keyPointInputRefs = ref([])
const sectionSearch = ref('')
const searchInputRef = ref(null)

const historyStack = ref([])
const historyCursor = ref(-1)
const applyingHistory = ref(false)
const savedSignature = ref('')
const lastSavedAt = ref('')
let historyTimer = null

const defaultQuery = Object.freeze({ schoolId: DEFAULT_SCHOOL_ID, courseId: '101', lessonId: '1', userId: '10001', role: 'teacher', token: 'mock-token', scriptId: '' })
const fallbackScriptStructure = Object.freeze([
  { sectionId: 'sec001', sectionName: '开场导入', content: '欢迎来到本节课程。先建立学习目标，再进入核心内容。', keyPoints: ['学习目标', '课程结构', '课堂节奏'] },
  { sectionId: 'sec002', sectionName: '核心内容讲解', content: '本部分围绕关键概念展开，通过例子建立认知连接。', keyPoints: ['关键概念', '示例讲解', '课堂互动'] },
  { sectionId: 'sec003', sectionName: '总结与延伸', content: '回顾重点并引导学生提出延伸问题。', keyPoints: ['重点回顾', '学习检查', '延伸问题'] },
])

const normalizeQuery = (v, d = '') => (Array.isArray(v) ? v[0] || d : (typeof v === 'string' && v ? v : d))
const platformQuery = computed(() => ({
  schoolId: normalizeQuery(route.query.schoolId, defaultQuery.schoolId),
  courseId: normalizeQuery(route.query.courseId, defaultQuery.courseId),
  lessonId: normalizeQuery(route.query.lessonId, defaultQuery.lessonId),
  userId: normalizeQuery(route.query.userId, defaultQuery.userId),
  role: 'teacher',
  token: normalizeQuery(route.query.token, defaultQuery.token),
  scriptId: normalizeQuery(route.query.scriptId, defaultQuery.scriptId),
}))
const editorSnapshotKey = computed(() => `script-editor:${platformQuery.value.courseId}:${platformQuery.value.lessonId}`)
const courseName = computed(() => lessonStore.courseInfo.courseName || '人工智能导论')
const breadcrumbs = computed(() => [{ label: '首页', to: '/home' }, { label: '教师工作台', to: '/teacher/upload' }, { label: '脚本编辑', current: true }])

const clone = (value) => JSON.parse(JSON.stringify(value))
const getSignature = () => JSON.stringify(scriptStructure.value)

const filteredSections = computed(() => {
  const keyword = sectionSearch.value.trim().toLowerCase()
  if (!keyword) return scriptStructure.value
  return scriptStructure.value.filter((item) => `${item.sectionName} ${item.content}`.toLowerCase().includes(keyword))
})

const currentSection = computed(() => scriptStructure.value.find((item) => item.sectionId === activeSectionId.value) || null)
const canUndo = computed(() => historyCursor.value > 0)
const canRedo = computed(() => historyCursor.value >= 0 && historyCursor.value < historyStack.value.length - 1)
const hasUnsavedChanges = computed(() => getSignature() !== savedSignature.value)
const saveStatusText = computed(() => (hasUnsavedChanges.value ? '未保存' : '已保存'))
const saveStatusType = computed(() => (hasUnsavedChanges.value ? 'warning' : 'success'))

const createScriptStructure = (sections = []) => sections.map((item, index) => ({
  sectionId: item.sectionId || `sec${String(index + 1).padStart(3, '0')}`,
  sectionName: item.sectionName || item.title || `章节 ${index + 1}`,
  content: item.content || item.explainScript || '',
  keyPoints: [...(item.keyPoints || item.keywords || [])],
}))

const buildSectionsPayload = () => {
  const sectionMap = new Map((lessonStore.lessonInfo.sections || []).map((item) => [item.sectionId, item]))
  return scriptStructure.value.map((item) => {
    const original = sectionMap.get(item.sectionId) || {}
    return {
      ...original,
      sectionId: item.sectionId,
      title: item.sectionName.trim() || '未命名章节',
      explainScript: item.content,
      keywords: item.keyPoints.map((point) => point.trim()).filter(Boolean),
    }
  })
}

const pushHistory = () => {
  if (applyingHistory.value) return
  const snapshot = clone(scriptStructure.value)
  const latest = historyStack.value[historyCursor.value]
  if (latest && JSON.stringify(latest) === JSON.stringify(snapshot)) return
  if (historyCursor.value < historyStack.value.length - 1) {
    historyStack.value = historyStack.value.slice(0, historyCursor.value + 1)
  }
  historyStack.value.push(snapshot)
  if (historyStack.value.length > 60) {
    historyStack.value.shift()
  }
  historyCursor.value = historyStack.value.length - 1
}

const applyHistory = async (targetIndex) => {
  if (targetIndex < 0 || targetIndex >= historyStack.value.length) return
  applyingHistory.value = true
  scriptStructure.value = clone(historyStack.value[targetIndex])
  historyCursor.value = targetIndex
  if (!scriptStructure.value.some((item) => item.sectionId === activeSectionId.value)) {
    activeSectionId.value = scriptStructure.value[0]?.sectionId || ''
  }
  await nextTick()
  applyingHistory.value = false
}

const undo = () => applyHistory(historyCursor.value - 1)
const redo = () => applyHistory(historyCursor.value + 1)

const persistEditorSnapshot = () => {
  if (typeof window === 'undefined') return
  const shouldKeep = scriptStructure.value.length > 0
  if (!shouldKeep) {
    localStorage.removeItem(editorSnapshotKey.value)
    return
  }
  localStorage.setItem(editorSnapshotKey.value, JSON.stringify({
    sections: scriptStructure.value,
    activeSectionId: activeSectionId.value,
    savedSignature: savedSignature.value,
    lastSavedAt: lastSavedAt.value,
  }))
}

const buildScriptStructurePayload = () => scriptStructure.value.map((item) => ({
  sectionId: item.sectionId,
  sectionName: item.sectionName.trim() || '未命名章节',
  content: item.content,
  duration: Math.max(15, Math.round((item.content || '').length / 6)),
  relatedChapterId: item.sectionId,
  keyPoints: item.keyPoints.map((point) => point.trim()).filter(Boolean),
}))

const restoreEditorSnapshot = () => {
  if (typeof window === 'undefined') return false
  const raw = localStorage.getItem(editorSnapshotKey.value)
  if (!raw) return false
  try {
    const payload = JSON.parse(raw)
    if (Array.isArray(payload.sections) && payload.sections.length) {
      scriptStructure.value = createScriptStructure(payload.sections)
      activeSectionId.value = payload.activeSectionId || scriptStructure.value[0]?.sectionId || ''
      savedSignature.value = payload.savedSignature || JSON.stringify(scriptStructure.value)
      lastSavedAt.value = payload.lastSavedAt || ''
      pushHistory()
      return true
    }
  } catch {
    localStorage.removeItem(editorSnapshotKey.value)
  }
  return false
}

const initializeData = () => {
  const source = lessonStore.lessonInfo.sections?.length ? createScriptStructure(lessonStore.lessonInfo.sections) : createScriptStructure(fallbackScriptStructure)
  scriptStructure.value = source
  activeSectionId.value = source[0]?.sectionId || ''
  pushHistory()
  savedSignature.value = getSignature()
}

const loadRemoteScript = async () => {
  if (!platformQuery.value.scriptId) {
    return false
  }
  const result = await getScriptStatus(platformQuery.value.scriptId)
  const remoteStructure = createScriptStructure(result.scriptStructure || [])
  if (!remoteStructure.length) {
    return false
  }
  scriptStructure.value = remoteStructure
  activeSectionId.value = remoteStructure[0]?.sectionId || ''
  lessonStore.setLessonInfo({
    lessonId: result.lessonId || platformQuery.value.lessonId,
    scriptId: result.scriptId || platformQuery.value.scriptId,
    sections: buildSectionsPayload(),
  })
  pushHistory()
  savedSignature.value = getSignature()
  return true
}

const selectSection = (sectionId) => { activeSectionId.value = sectionId }
const addKeyPoint = async () => {
  if (!currentSection.value) return
  currentSection.value.keyPoints.push('')
  await nextTick()
  keyPointInputRefs.value[currentSection.value.keyPoints.length - 1]?.focus?.()
}
const removeKeyPoint = (index) => { if (currentSection.value) currentSection.value.keyPoints.splice(index, 1) }
const setKeyPointInputRef = (el, index) => { keyPointInputRefs.value[index] = el }

const handleSave = async () => {
  if (!scriptStructure.value.length) { ElMessage.warning('当前没有可保存内容'); return }
  saving.value = true
  try {
    const nextSections = buildSectionsPayload()
    const scriptId = platformQuery.value.scriptId || lessonStore.lessonInfo.scriptId || ''
    if (scriptId) {
      await editScript({
        scriptId,
        scriptStructure: buildScriptStructurePayload(),
      })
      const lessonId = platformQuery.value.lessonId || lessonStore.lessonInfo.lessonId
      if (lessonId) {
        await renderLessonPpt(lessonId)
      }
    } else {
      await new Promise((resolve) => setTimeout(resolve, 260))
    }
    lessonStore.setLessonInfo({ sections: nextSections })
    savedSignature.value = getSignature()
    lastSavedAt.value = new Date().toISOString()
    ElMessage.success(scriptId ? '脚本已保存，并已触发 PPT 重新渲染' : '脚本已保存')
  } catch (error) {
    console.error('Failed to save script', error)
  } finally {
    saving.value = false
  }
}

const handleGenerateVoice = async () => {
  if (!currentSection.value) { ElMessage.warning('请先选择章节'); return }
  generatingVoice.value = true
  try {
    await new Promise((resolve) => setTimeout(resolve, 650))
    ElMessage.success(`已生成 ${currentSection.value.sectionName} 的语音草案`)
  } finally {
    generatingVoice.value = false
  }
}

const backToTeacher = () => router.push({ path: '/teacher/upload', query: platformQuery.value })
const downloadPpt = () => {
  const lessonId = platformQuery.value.lessonId || lessonStore.lessonInfo.lessonId
  if (!lessonId) {
    ElMessage.warning('当前没有可下载的课件。')
    return
  }
  window.open(buildLessonDownloadUrl(lessonId), '_blank', 'noopener')
}

const handleShortcut = (event) => {
  if (!event.ctrlKey && !event.metaKey) return
  const key = event.key.toLowerCase()
  if (key === 's') { event.preventDefault(); handleSave() }
  if (key === 'z') { event.preventDefault(); undo() }
  if (key === 'y') { event.preventDefault(); redo() }
  if (key === 'f') { event.preventDefault(); searchInputRef.value?.focus?.() }
}

const beforeUnload = (event) => {
  if (!hasUnsavedChanges.value) return
  event.preventDefault()
  event.returnValue = ''
}

onMounted(async () => {
  lessonStore.syncPlatformContext(platformQuery.value)
  if (!restoreEditorSnapshot()) {
    const loaded = await loadRemoteScript().catch(() => false)
    if (!loaded) initializeData()
  }
  window.addEventListener('keydown', handleShortcut)
  window.addEventListener('beforeunload', beforeUnload)
})

watch(() => route.query, () => lessonStore.syncPlatformContext(platformQuery.value), { deep: true })
watch(() => scriptStructure.value, () => {
  if (applyingHistory.value) return
  clearTimeout(historyTimer)
  historyTimer = setTimeout(() => pushHistory(), 180)
}, { deep: true })
watch(() => [scriptStructure.value, activeSectionId.value, savedSignature.value, lastSavedAt.value], persistEditorSnapshot, { deep: true })

onBeforeRouteLeave((to, from, next) => next(!hasUnsavedChanges.value || window.confirm('当前脚本尚未保存，确认离开吗？')))

onBeforeUnmount(() => {
  clearTimeout(historyTimer)
  window.removeEventListener('keydown', handleShortcut)
  window.removeEventListener('beforeunload', beforeUnload)
})
</script>

<template>
  <div class="script-editor-page">
    <div class="editor-toolbar">
      <el-button plain @click="undo" :disabled="!canUndo">撤销</el-button>
      <el-button plain @click="redo" :disabled="!canRedo">重做</el-button>
      <el-button plain :icon="ArrowLeft" @click="backToTeacher">返回</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><strong>章节导航</strong></template>
          <el-input ref="searchInputRef" v-model="sectionSearch" placeholder="搜索章节（Ctrl+F）" clearable />
          <el-menu :default-active="activeSectionId" class="menu" @select="selectSection">
            <el-menu-item v-for="item in filteredSections" :key="item.sectionId" :index="item.sectionId">
              <span>{{ item.sectionName }}</span>
            </el-menu-item>
          </el-menu>
          <small class="hint">快捷键：Ctrl+S 保存，Ctrl+Z 撤销，Ctrl+Y 重做</small>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="editor-head">
              <strong>脚本内容</strong>
              <small v-if="lastSavedAt">上次保存：{{ lastSavedAt }}</small>
            </div>
          </template>
          <template v-if="currentSection">
            <el-input v-model="currentSection.sectionName" placeholder="章节标题" />
            <el-input v-model="currentSection.content" class="content" type="textarea" :rows="10" resize="none" placeholder="章节讲解内容" />

            <div class="keypoint-head">
              <strong>关键点</strong>
              <el-button size="small" :icon="Plus" @click="addKeyPoint">新增关键点</el-button>
            </div>

            <div v-if="currentSection.keyPoints.length" class="chip-wrap">
              <div v-for="(point, index) in currentSection.keyPoints" :key="`${currentSection.sectionId}-${index}`" class="chip">
                <el-input :ref="(el) => setKeyPointInputRef(el, index)" v-model="currentSection.keyPoints[index]" />
                <el-button text type="danger" :icon="Close" @click="removeKeyPoint(index)" />
              </div>
            </div>
            <StateBlock v-else mode="empty" title="暂无关键点" description="点击“新增关键点”开始补充。" />
          </template>
          <StateBlock v-else mode="empty" title="未选择章节" description="请从左侧选择章节。" />
        </el-card>
      </el-col>
    </el-row>

    <div class="actions">
      <el-button type="primary" :loading="saving" @click="handleSave">保存修改</el-button>
      <el-button plain @click="downloadPpt">下载 PPT</el-button>
    </div>
  </div>
</template>

<style scoped>
.script-editor-page { min-height: 100vh; padding: 12px; }
.editor-toolbar { display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 12px; }
.menu { margin-top: 8px; border-right: none; max-height: 460px; overflow: auto; }
.hint { display: block; margin-top: 8px; color: #8597aa; }
.editor-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.content { margin-top: 12px; }
.keypoint-head { margin: 12px 0 8px; display: flex; justify-content: space-between; align-items: center; }
.chip-wrap { display: grid; gap: 8px; }
.chip { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
.actions { margin-top: 14px; display: flex; justify-content: flex-end; gap: 10px; }
</style>
