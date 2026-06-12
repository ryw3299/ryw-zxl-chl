<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { EditPen, Reading, RefreshRight, UploadFilled } from '@element-plus/icons-vue'
import {
  generateCoursewareSlidePlan,
  generateNarrationAudio,
  getCoursewareStatus,
  getNarrationAudioStatus,
  publishLesson,
  renderCoursewarePpt,
  updateCoursewareSlidePlan,
} from '@/api/lesson'
import { TASK_POLL_INTERVAL_MS, TASK_POLL_TIMEOUT_MS } from '@/utils/runtimeConfig'
import { DEFAULT_SCHOOL_ID } from '@/utils/signature'
import { useLessonStore } from '@/store/lessonStore'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()

const uploadRef = ref(null)
const leftColRef = ref(null)
const uploadFile = ref(null)
const restoredFileName = ref('')
const parseResult = ref(null)
const scriptStructure = ref([])
const parseTaskId = ref('')
const scriptTaskId = ref('')
const parsing = ref(false)
const generating = ref(false)
const generatingAudio = ref(false)
const audioGenerated = ref(false)
const audioTaskId = ref('')
const narrationAudioTasks = ref({})
const publishing = ref(false)
const published = ref(false)
const parseSuccess = ref(false)
const scriptGenerated = ref(false)
const slidePlan = ref(null)
const slidePlanText = ref('')
const renderingPpt = ref(false)
const renderMode = ref('flash')
const renderedPptUrl = ref('')
const parseError = ref('')
const generateError = ref('')
const activeResultTab = ref('script')
const activeFlowStep = ref('upload')
const draftDirty = ref(false)
const snapshotAt = ref('')
const hasSnapshot = ref(false)
const courseNameInput = ref('')
const courseDescInput = ref('')
const courseTagInput = ref('')
const coverImageUrl = ref('')

const coverImageFile = ref(null)
const hydratingCourseMeta = ref(true)
const syncedResultPanelHeight = ref(0)
let leftColResizeObserver = null
let narrationAudioPollRun = 0

const defaultQuery = Object.freeze({ schoolId: DEFAULT_SCHOOL_ID, courseId: '101', lessonId: '1', userId: '10001', role: 'teacher', token: 'mock-token' })
const DEFAULT_MOCK_COURSE_NAME = '人工智能导论'
const normalizeQuery = (v, d = '') => (Array.isArray(v) ? v[0] || d : (typeof v === 'string' && v ? v : d))
const normalizeText = (value, fallback = '') => (typeof value === 'string' && value.trim() ? value.trim() : fallback)
const normalizeSavedCourseName = (value) => {
  const name = normalizeText(value)
  return name && name !== DEFAULT_MOCK_COURSE_NAME ? name : ''
}
const platformQuery = computed(() => ({
  schoolId: normalizeQuery(route.query.schoolId, defaultQuery.schoolId),
  courseId: normalizeQuery(route.query.courseId, defaultQuery.courseId),
  lessonId: normalizeQuery(route.query.lessonId, defaultQuery.lessonId),
  userId: normalizeQuery(route.query.userId, defaultQuery.userId),
  role: 'teacher',
  token: normalizeQuery(route.query.token, defaultQuery.token),
}))
const snapshotKey = computed(() => `teacher-workflow:${platformQuery.value.courseId}:${platformQuery.value.lessonId}`)
const fileName = computed(() => uploadFile.value?.name || restoredFileName.value || '')
const resolvedCourseName = computed(() => normalizeText(courseNameInput.value))
const courseName = computed(() => resolvedCourseName.value)
const backendLessonId = computed(() => normalizeText(parseResult.value?.parseId, lessonStore.lessonInfo.lessonId || platformQuery.value.lessonId))
const hasUploadedFile = computed(() => Boolean(fileName.value))
const hasUnsavedWorkflow = computed(() => draftDirty.value && (hasUploadedFile.value || parseSuccess.value || scriptGenerated.value || Boolean(courseNameInput.value.trim()) || Boolean(courseDescInput.value.trim()) || Boolean(courseTagInput.value.trim()) || Boolean(coverImageUrl.value)))
const hasDraftContent = computed(() => (
  hasSnapshot.value ||
  Boolean(snapshotAt.value) ||
  hasUploadedFile.value ||
  parseSuccess.value ||
  scriptGenerated.value ||
  Boolean(courseNameInput.value.trim()) ||
  Boolean(courseDescInput.value.trim()) ||
  Boolean(courseTagInput.value.trim()) ||
  Boolean(coverImageUrl.value)
))
const workflowBusy = computed(() => parsing.value || generating.value || renderingPpt.value || publishing.value)
const statusText = computed(() => (scriptGenerated.value ? 'PPT 已生成' : parseSuccess.value ? '待渲染' : hasUploadedFile.value ? '待生成规划' : '准备中'))
const statusType = computed(() => (scriptGenerated.value ? 'success' : parseSuccess.value ? 'warning' : 'info'))
const resultPanelStyle = computed(() => (
  syncedResultPanelHeight.value
    ? {
      minHeight: `${Math.min(syncedResultPanelHeight.value, 520)}px`,
    }
    : {}
))

const flowSteps = computed(() => {
  const s1 = hasUploadedFile.value ? 'done' : activeFlowStep.value === 'upload' ? 'active' : 'idle'
  const s2 = parseSuccess.value ? 'done' : parsing.value || activeFlowStep.value === 'parse' ? 'active' : hasUploadedFile.value ? 'idle' : 'locked'
  const s3 = scriptGenerated.value ? 'done' : generating.value || renderingPpt.value || activeFlowStep.value === 'script' ? 'active' : parseSuccess.value ? 'idle' : 'locked'
  return [
    { id: 'upload', title: '上传课件', desc: '支持 PPT / PDF 格式', icon: '📁', status: s1 },
    { id: 'parse', title: '生成规划', desc: '选择 Flash / Pro 模式', icon: '🔍', status: s2 },
    { id: 'script', title: '渲染 PPT', desc: '生成 PPT 和四档讲稿', icon: '✨', status: s3 },
  ]
})
const modeLabel = computed(() => (renderMode.value === 'flash' ? 'Flash 快速版' : 'Pro 高质量版'))
const modeDescription = computed(() => (
  renderMode.value === 'flash'
    ? '优先速度，适合先出一版课堂预览。'
    : '优先质量，适合最终发布前生成。'
))
const slideTypeLabelMap = {
  title_slide: '封面页',
  cover: '封面页',
  title: '封面页',
  agenda: '目录页',
  outline: '目录页',
  concept_explanation: '知识讲解页',
  content: '讲授页',
  concept: '概念讲解页',
  knowledge_point: '知识点页',
  lesson_objectives: '学习目标页',
  objective: '学习目标页',
  objectives: '学习目标页',
  chapter_transition: '章节过渡页',
  section_transition: '章节过渡页',
  transition: '过渡页',
  case: '案例页',
  example: '案例页',
  interaction: '互动页',
  quiz: '互动测验页',
  exercise: '练习页',
  comparison: '对比分析页',
  classroom_question: '课堂互动页',
  summary_slide: '总结页',
  summary: '总结页',
  conclusion: '总结页',
}
const rhythmLabelMap = {
  '常规': '常规',
  '引入': '引入',
  '讲解': '讲解',
  '互动': '互动',
  '总结': '总结',
  anchor: '锚定导入',
  dense: '信息讲解',
  breathing: '节奏缓冲',
  normal: '常规讲解',
  lecture: '讲解推进',
  explain: '讲解推进',
  transition: '过渡衔接',
  fast: '快速推进',
  slow: '重点展开',
  discussion: '讨论互动',
}
const slideTypeOptions = [
  { label: '封面页', value: 'title_slide' },
  { label: '章节过渡页', value: 'chapter_transition' },
  { label: '学习目标页', value: 'lesson_objectives' },
  { label: '知识讲解页', value: 'concept_explanation' },
  { label: '对比分析页', value: 'comparison' },
  { label: '课堂互动页', value: 'classroom_question' },
  { label: '总结页', value: 'summary_slide' },
]
const rhythmOptions = [
  { label: '锚定导入', value: 'anchor' },
  { label: '信息讲解', value: 'dense' },
  { label: '节奏缓冲', value: 'breathing' },
]
const textAliasMap = {
  'Learning Objectives': '学习目标',
  'Lesson Objectives': '学习目标',
  Overview: '课程概览',
  Summary: '总结',
  Conclusion: '总结',
}
const getSlideTypeLabel = (value) => slideTypeLabelMap[String(value || '').trim()] || '自定义页面'
const getRhythmLabel = (value) => rhythmLabelMap[String(value || '').trim()] || '自定义节奏'
const hasSlideTypeOption = (value) => slideTypeOptions.some((option) => option.value === value)
const hasRhythmOption = (value) => rhythmOptions.some((option) => option.value === value)
const normalizeSubmitSlideType = (value) => {
  const type = String(value || '').trim()
  if (['title_slide', 'chapter_transition', 'lesson_objectives', 'concept_explanation', 'comparison', 'classroom_question', 'summary_slide'].includes(type)) return type
  if (['cover', 'title'].includes(type)) return 'title_slide'
  if (['agenda', 'outline', 'section_transition', 'transition'].includes(type)) return 'chapter_transition'
  if (['objective', 'objectives'].includes(type)) return 'lesson_objectives'
  if (['interaction', 'quiz'].includes(type)) return 'classroom_question'
  if (['summary', 'conclusion'].includes(type)) return 'summary_slide'
  if (type === 'comparison') return 'comparison'
  return 'concept_explanation'
}
const normalizeSubmitRhythm = (value, slideType = '') => {
  const rhythm = String(value || '').trim()
  if (['anchor', 'dense', 'breathing'].includes(rhythm)) return rhythm
  if (['引入', 'transition'].includes(rhythm)) return 'anchor'
  if (['互动', '总结', 'discussion', 'slow'].includes(rhythm)) return 'breathing'
  const type = normalizeSubmitSlideType(slideType)
  if (['title_slide', 'chapter_transition'].includes(type)) return 'anchor'
  if (['lesson_objectives', 'classroom_question', 'summary_slide'].includes(type)) return 'breathing'
  return 'dense'
}
const objectTextKeys = ['text', 'title', 'content', 'name', 'label', 'summary', 'description', 'point', 'value', 'objective', 'teaching_goal']
const toDisplayText = (value, fallback = '') => {
  if (value === null || value === undefined) return fallback
  if (typeof value === 'string') {
    const text = value.trim()
    if (!text || text === '[object Object]') return fallback
    return textAliasMap[text] || text
  }
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    return value.map((item) => toDisplayText(item)).filter(Boolean).join('、') || fallback
  }
  if (typeof value === 'object') {
    for (const key of objectTextKeys) {
      const text = toDisplayText(value[key])
      if (text) return text
    }
  }
  return fallback
}
const normalizeBulletItems = (value) => {
  const source = Array.isArray(value) ? value : splitPlanLines(value)
  return source.map((item) => toDisplayText(item)).filter(Boolean)
}
const toSubmitBullet = (value) => {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const text = toDisplayText(value.text || value.title || value.content || value.summary || value.point || value.value)
    if (!text) return null
    return {
      text,
      ...(toDisplayText(value.sub || value.detail || value.description) ? { sub: toDisplayText(value.sub || value.detail || value.description) } : {}),
    }
  }
  const text = toDisplayText(value)
  return text ? { text } : null
}
const normalizeSubmitBullets = (value) => {
  const source = Array.isArray(value) ? value : splitPlanLines(value)
  return source.map((item) => toSubmitBullet(item)).filter(Boolean).slice(0, 4)
}
const createSlug = (value, fallback) => {
  const slug = String(value || '').toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '')
  return slug || fallback
}
const normalizeSlidePlanForSubmit = (plan = {}) => {
  const slides = Array.isArray(plan.slides) ? plan.slides : []
  return {
    ...plan,
    deck_title: toDisplayText(plan.deck_title, courseName.value || '课程讲解内容'),
    audience: toDisplayText(plan.audience, '高校课堂学生'),
    language: ['zh', 'en', 'zh-en'].includes(plan.language) ? plan.language : 'zh',
    slide_count: slides.length,
    slides: slides.map((slide, index) => {
      const submitType = normalizeSubmitSlideType(slide.type)
      const slideNumber = index + 1
      const slug = createSlug(slide.slug || submitType, submitType)
      return {
        ...slide,
        slide_id: Number.isFinite(Number(slide.slide_id)) ? Number(slide.slide_id) : slideNumber,
        slug,
        filename: /^\d{2}_[a-z0-9_]+\.svg$/.test(String(slide.filename || ''))
          ? slide.filename
          : `${String(slideNumber).padStart(2, '0')}_${slug}.svg`,
        type: submitType,
        rhythm: normalizeSubmitRhythm(slide.rhythm, submitType),
        title: toDisplayText(slide.title, `页面 ${slideNumber}`),
        subtitle: toDisplayText(slide.subtitle),
        teaching_goal: toDisplayText(slide.teaching_goal || slide.objective, '说明本页的学习目标'),
        bullets: normalizeSubmitBullets(slide.bullets),
      }
    }),
  }
}

const syncStoreContext = () => {
  lessonStore.syncPlatformContext(platformQuery.value)
  if (hydratingCourseMeta.value) {
    courseNameInput.value = ''
    courseDescInput.value = lessonStore.courseInfo.courseDesc || ''
    hydratingCourseMeta.value = false
  }
  lessonStore.setCourseInfo({
    courseId: platformQuery.value.courseId,
    courseName: courseName.value,
    courseDesc: courseDescInput.value,
    teacherName: '张老师',
  })
}

const sleep = (delay) => new Promise((resolve) => setTimeout(resolve, delay))
const readErrorMessage = (error, fallback) => error?.response?.data?.msg || error?.message || fallback

const extractPageNumbers = (value) => {
  const matches = String(value || '').match(/\d+/g) || []
  return [...new Set(matches.map((item) => Number(item)).filter((item) => Number.isFinite(item) && item > 0))]
}

const normalizeStructureTree = (structurePreview = {}) => ({
  chapters: (structurePreview.chapters || []).map((chapter, chapterIndex) => ({
    id: chapter.chapterId || `chapter-${chapterIndex + 1}`,
    label: chapter.chapterName || `章节 ${chapterIndex + 1}`,
    children: (chapter.subChapters || []).map((subChapter, subIndex) => ({
      id: subChapter.subChapterId || `chapter-${chapterIndex + 1}-sub-${subIndex + 1}`,
      label: subChapter.subChapterName || `小节 ${subIndex + 1}`,
    })),
  })),
})

const buildPreviewSections = (structurePreview = {}) => (structurePreview.chapters || []).map((chapter, chapterIndex) => {
  const relatedPages = [...new Set((chapter.subChapters || []).flatMap((item) => extractPageNumbers(item.pageRange)))]
  return {
    sectionId: chapter.chapterId || `chapter-${chapterIndex + 1}`,
    title: chapter.chapterName || `章节 ${chapterIndex + 1}`,
    keywords: (chapter.subChapters || []).map((item) => item.subChapterName).filter(Boolean).slice(0, 3),
    relatedPages: relatedPages.length ? relatedPages : [chapterIndex + 1],
  }
})

const buildPreviewSectionsFromTree = (treePreview = {}) => (treePreview.chapters || []).map((chapter, chapterIndex) => ({
  sectionId: chapter.id || `chapter-${chapterIndex + 1}`,
  title: chapter.label || `章节 ${chapterIndex + 1}`,
  keywords: (chapter.children || []).map((item) => item.label).filter(Boolean).slice(0, 3),
  relatedPages: [chapterIndex + 1],
}))

const normalizeScriptSections = (sections = []) => sections.map((item, index) => ({
  id: item.sectionId || item.id || `sec-${index + 1}`,
  sectionId: item.sectionId || item.id || `sec-${index + 1}`,
  sectionName: item.sectionName || item.title || `章节 ${index + 1}`,
  content: item.content || item.explainScript || '暂无内容',
  keyPoints: Array.isArray(item.keyPoints) ? item.keyPoints : Array.isArray(item.keywords) ? item.keywords : [],
}))

const buildSlidePlanTree = (plan = {}) => ({
  chapters: (plan.slides || []).map((slide, index) => ({
    id: slide.slide_id || slide.filename || `slide-${index + 1}`,
    label: `${index + 1}. ${toDisplayText(slide.title, '未命名页面')}`,
    children: [
      { id: `${slide.slide_id || index}-type`, label: `类型：${slide.type ? getSlideTypeLabel(slide.type) : '未设置'}` },
      { id: `${slide.slide_id || index}-rhythm`, label: `节奏：${slide.rhythm ? getRhythmLabel(slide.rhythm) : '常规'}` },
      { id: `${slide.slide_id || index}-goal`, label: `目标：${toDisplayText(slide.teaching_goal || slide.objective, '未设置')}` },
    ],
  })),
})

const normalizeSlidePlanSections = (plan = {}) => (plan.slides || []).map((slide, index) => ({
  id: slide.slide_id || slide.filename || `slide-${index + 1}`,
  sectionId: slide.slide_id || `slide-${index + 1}`,
  sectionName: toDisplayText(slide.title, `页面 ${index + 1}`),
  content: [
    slide.subtitle,
    slide.teaching_goal,
    slide.objective,
    slide.summary,
  ].map((item) => toDisplayText(item)).filter(Boolean).join('；') || '该页内容将在 PPT 渲染阶段生成。',
  keyPoints: [
    slide.type ? `页面类型：${getSlideTypeLabel(slide.type)}` : '',
    slide.rhythm ? `课堂节奏：${getRhythmLabel(slide.rhythm)}` : '',
    normalizeBulletItems(slide.bullets).length ? `关键要点：${normalizeBulletItems(slide.bullets).join('、')}` : '',
    toDisplayText(slide.notes || slide.teacher_notes),
  ].filter(Boolean),
}))

const splitPlanLines = (value) => String(value || '')
  .split(/\r?\n/)
  .map((item) => item.trim())
  .filter(Boolean)

const getSlideBulletsText = (slide = {}) => (
  normalizeBulletItems(slide.bullets).join('\n')
)

const normalizeEditablePlan = (plan = {}) => ({
  ...plan,
  slides: Array.isArray(plan.slides)
    ? plan.slides.map((slide, index) => ({
      ...slide,
      slide_id: slide.slide_id || `slide-${index + 1}`,
      title: toDisplayText(slide.title, `页面 ${index + 1}`),
      subtitle: toDisplayText(slide.subtitle),
      type: normalizeText(slide.type, 'content'),
      rhythm: normalizeText(slide.rhythm, '常规'),
      teaching_goal: toDisplayText(slide.teaching_goal, toDisplayText(slide.objective)),
      bullets: normalizeBulletItems(slide.bullets),
    }))
    : [],
})

const formatStructureLabel = (label = '') => {
  const text = toDisplayText(label)
  if (text.startsWith('类型：')) return `类型：${getSlideTypeLabel(text.replace('类型：', ''))}`
  if (text.startsWith('节奏：')) return `节奏：${getRhythmLabel(text.replace('节奏：', ''))}`
  if (text.startsWith('目标：')) return `目标：${toDisplayText(text.replace('目标：', ''), '未设置')}`
  return text
}

const normalizeDisplayTree = (treePreview = {}) => ({
  chapters: (treePreview.chapters || []).map((chapter, index) => ({
    ...chapter,
    id: chapter.id || `display-chapter-${index + 1}`,
    label: formatStructureLabel(chapter.label || chapter.chapterName || `页面 ${index + 1}`),
    children: (chapter.children || chapter.subChapters || []).map((child, childIndex) => ({
      ...child,
      id: child.id || child.subChapterId || `display-chapter-${index + 1}-${childIndex + 1}`,
      label: formatStructureLabel(child.label || child.subChapterName || `信息 ${childIndex + 1}`),
    })),
  })),
})

const structureChapters = computed(() => {
  if (slidePlan.value?.slides?.length) {
    return buildSlidePlanTree(slidePlan.value).chapters
  }
  return normalizeDisplayTree(parseResult.value?.structurePreview || {}).chapters
})

const syncPlanPreviewState = () => {
  if (!slidePlan.value) return
  slidePlanText.value = JSON.stringify(slidePlan.value, null, 2)
  scriptStructure.value = normalizeSlidePlanSections(slidePlan.value)
  parseResult.value = {
    ...(parseResult.value || {}),
    rawStructurePreview: buildSlidePlanTree(slidePlan.value),
    structurePreview: buildSlidePlanTree(slidePlan.value),
    fileInfo: {
      ...(parseResult.value?.fileInfo || {}),
      pageCount: Array.isArray(slidePlan.value.slides) ? slidePlan.value.slides.length : 0,
    },
  }
  draftDirty.value = true
}

const updateSlideBullets = (slide, value) => {
  slide.bullets = splitPlanLines(value)
  syncPlanPreviewState()
}

const prepareSlidePlanForSubmit = () => {
  if (slidePlan.value) {
    const editablePlan = normalizeEditablePlan(slidePlan.value)
    const editedPlan = normalizeSlidePlanForSubmit(editablePlan)
    slidePlan.value = editablePlan
    syncPlanPreviewState()
    slidePlanText.value = JSON.stringify(editedPlan, null, 2)
    return editedPlan
  }
  try {
    return normalizeSlidePlanForSubmit(JSON.parse(slidePlanText.value))
  } catch {
    throw new Error('课件规划数据异常，请重新生成规划后再试')
  }
}

const buildLessonSectionsFromScript = (sections = []) => {
  const previewSectionMap = new Map((lessonStore.lessonInfo.sections || []).map((item) => [item.sectionId, item]))
  return sections.map((item, index) => {
    const previewSection = previewSectionMap.get(item.sectionId) || {}
    return {
      ...previewSection,
      sectionId: item.sectionId,
      title: item.sectionName,
      explainScript: item.content,
      keywords: item.keyPoints,
      relatedPages: Array.isArray(previewSection.relatedPages) && previewSection.relatedPages.length
        ? previewSection.relatedPages
        : [index + 1],
    }
  })
}

const applyParseResult = (result) => {
  parseTaskId.value = result.parseId
  parseResult.value = {
    ...result,
    rawStructurePreview: result.structurePreview,
    structurePreview: normalizeStructureTree(result.structurePreview),
  }
  lessonStore.setLessonInfo({
    lessonId: result.parseId || platformQuery.value.lessonId,
    lessonTitle: courseName.value || '课程讲解内容',
    fileName: result.fileInfo?.fileName || uploadFile.value?.name || restoredFileName.value,
    totalPages: result.fileInfo?.pageCount || 1,
    sections: buildPreviewSections(result.structurePreview),
    pageContents: [],
  })
  parseSuccess.value = true
  activeFlowStep.value = 'script'
  activeResultTab.value = 'script'
  draftDirty.value = true
}

const applyCoursewarePlanResult = (result) => {
  const plan = normalizeEditablePlan(result.slidePlan || {})
  parseTaskId.value = result.lessonId
  slidePlan.value = plan
  slidePlanText.value = JSON.stringify(plan, null, 2)
  renderedPptUrl.value = result.renderedPptUrl || ''
  parseResult.value = {
    parseId: result.lessonId,
    fileInfo: {
      fileName: fileName.value,
      fileSize: uploadFile.value?.size || 0,
      pageCount: Array.isArray(plan.slides) ? plan.slides.length : 0,
    },
    rawStructurePreview: buildSlidePlanTree(plan),
    structurePreview: buildSlidePlanTree(plan),
  }
  scriptStructure.value = normalizeSlidePlanSections(plan)
  lessonStore.setLessonInfo({
    lessonId: result.lessonId || platformQuery.value.lessonId,
    lessonTitle: result.lessonName || plan.deck_title || courseName.value || '课程讲解内容',
    fileName: fileName.value || restoredFileName.value,
    totalPages: Array.isArray(plan.slides) ? plan.slides.length : 1,
    sections: buildLessonSectionsFromScript(scriptStructure.value),
    pageContents: [],
  })
  parseSuccess.value = true
  activeFlowStep.value = 'script'
  activeResultTab.value = 'script'
  draftDirty.value = true
}

const tryRecoverParseTask = async (parseId) => {
  const targetParseId = normalizeText(parseId, parseTaskId.value)
  if (!targetParseId) {
    return false
  }

  const latestResult = await getCoursewareStatus(targetParseId)
  if (latestResult?.taskStatus !== 'plan_ready' && latestResult?.taskStatus !== 'completed') {
    return false
  }

  applyCoursewarePlanResult(latestResult)
  return true
}

const pollTaskStatus = async ({
  loadStatus,
  getStatus,
  timeoutMs = TASK_POLL_TIMEOUT_MS,
  intervalMs = TASK_POLL_INTERVAL_MS,
  pendingStates = ['processing', 'pending'],
}) => {
  const deadline = Date.now() + timeoutMs
  let latestResult = null

  while (Date.now() < deadline) {
    latestResult = await loadStatus()
    const status = getStatus(latestResult)
    if (status === 'completed') {
      return latestResult
    }
    if (status === 'failed') {
      throw new Error(normalizeText(latestResult?.errorMessage, '任务执行失败'))
    }
    if (!pendingStates.includes(status)) {
      return latestResult
    }
    await sleep(intervalMs)
  }

  throw new Error('任务执行超时，请稍后刷新状态。')
}

const syncNarrationAudioTasks = (tasks = {}) => {
  narrationAudioTasks.value = tasks && typeof tasks === 'object' ? tasks : {}
  const defaultTask = narrationAudioTasks.value.D || narrationAudioTasks.value.C || narrationAudioTasks.value.B || narrationAudioTasks.value.A
  audioTaskId.value = defaultTask?.audioId || audioTaskId.value || ''
  audioGenerated.value = Object.values(narrationAudioTasks.value).some((task) => task?.taskStatus === 'completed')
}

const pollNarrationAudioStatusInBackground = async (lessonId) => {
  const runId = ++narrationAudioPollRun
  generatingAudio.value = true
  try {
    const result = await pollTaskStatus({
      loadStatus: () => getNarrationAudioStatus(lessonId),
      getStatus: (payload) => {
        const tasks = payload.audioTasks || {}
        syncNarrationAudioTasks(tasks)
        const expected = ['A', 'B', 'C', 'D']
        const values = expected.map((level) => tasks[level]).filter(Boolean)
        if (values.some((task) => task.taskStatus === 'failed')) return 'failed'
        if (values.length === expected.length && values.every((task) => task.taskStatus === 'completed')) return 'completed'
        return 'processing'
      },
      pendingStates: ['processing', 'pending'],
      timeoutMs: 15 * 60 * 1000,
    })
    if (runId !== narrationAudioPollRun) return
    syncNarrationAudioTasks(result.audioTasks || narrationAudioTasks.value)
    lessonStore.setLessonInfo({
      audioId: audioTaskId.value,
      narrationAudioTasks: narrationAudioTasks.value,
    })
    ElMessage.success('讲解音频已生成，默认使用最简单讲稿')
  } catch (error) {
    if (runId === narrationAudioPollRun) {
      ElMessage.warning(readErrorMessage(error, '讲解音频仍在生成中，可稍后刷新状态'))
    }
  } finally {
    if (runId === narrationAudioPollRun) {
      generatingAudio.value = false
    }
  }
}

const generateNarrationAudioForLesson = async (lessonId) => {
  generatingAudio.value = true
  try {
    const submission = await generateNarrationAudio({
      lessonId,
      levels: ['A', 'B', 'C', 'D'],
      voiceType: 'female_standard',
      audioFormat: 'mp3',
    })
    syncNarrationAudioTasks(submission.audioTasks || {})
    pollNarrationAudioStatusInBackground(lessonId)
    return submission
  } catch (error) {
    generatingAudio.value = false
    throw error
  }
}

const clearResultState = () => {
  parseResult.value = null
  scriptStructure.value = []
  slidePlan.value = null
  slidePlanText.value = ''
  renderedPptUrl.value = ''
  parseTaskId.value = ''
  scriptTaskId.value = ''
  parseSuccess.value = false
  scriptGenerated.value = false
  parseError.value = ''
  generateError.value = ''
  activeResultTab.value = 'script'
  narrationAudioTasks.value = {}
}

const persistSnapshot = () => {
  if (typeof window === 'undefined') return
  const shouldKeep =
    hasUploadedFile.value ||
    parseSuccess.value ||
    scriptGenerated.value ||
    scriptStructure.value.length > 0 ||
    Boolean(courseNameInput.value.trim()) ||
    Boolean(courseDescInput.value.trim()) ||
    Boolean(courseTagInput.value.trim()) ||
    Boolean(coverImageUrl.value)
  if (!shouldKeep) { localStorage.removeItem(snapshotKey.value); hasSnapshot.value = false; return }
  localStorage.setItem(snapshotKey.value, JSON.stringify({
    fileName: fileName.value,
    courseNameInput: courseNameInput.value,
    courseDescInput: courseDescInput.value,
    courseTagInput: courseTagInput.value,
    coverImageUrl: coverImageUrl.value,
    parseResult: parseResult.value,
    scriptStructure: scriptStructure.value,
    slidePlan: slidePlan.value,
    slidePlanText: slidePlanText.value,
    renderedPptUrl: renderedPptUrl.value,
    renderMode: renderMode.value,
    parseTaskId: parseTaskId.value,
    scriptTaskId: scriptTaskId.value,
    parseSuccess: parseSuccess.value,
    scriptGenerated: scriptGenerated.value,
    narrationAudioTasks: narrationAudioTasks.value,
    audioTaskId: audioTaskId.value,
    audioGenerated: audioGenerated.value,
    activeResultTab: activeResultTab.value,
    activeFlowStep: activeFlowStep.value,
    updatedAt: new Date().toISOString(),
  }))
  hasSnapshot.value = true
}

const restoreSnapshot = () => {
  if (typeof window === 'undefined') return false
  const raw = localStorage.getItem(snapshotKey.value)
  if (!raw) { hasSnapshot.value = false; return false }
  try {
    const payload = JSON.parse(raw)
    hydratingCourseMeta.value = true
    restoredFileName.value = payload.fileName || ''
    courseNameInput.value = normalizeSavedCourseName(payload.courseNameInput) || normalizeSavedCourseName(courseNameInput.value)
    courseDescInput.value = payload.courseDescInput || courseDescInput.value || lessonStore.courseInfo.courseDesc || ''
    courseTagInput.value = payload.courseTagInput || courseTagInput.value || ''
    coverImageUrl.value = payload.coverImageUrl || coverImageUrl.value || ''
    coverImageFile.value = null
    parseResult.value = payload.parseResult || null
    scriptStructure.value = Array.isArray(payload.scriptStructure) ? payload.scriptStructure : []
    slidePlan.value = payload.slidePlan ? normalizeEditablePlan(payload.slidePlan) : null
    slidePlanText.value = payload.slidePlanText || (slidePlan.value ? JSON.stringify(slidePlan.value, null, 2) : '')
    renderedPptUrl.value = payload.renderedPptUrl || ''
    renderMode.value = payload.renderMode || 'flash'
    parseTaskId.value = payload.parseTaskId || payload.parseResult?.parseId || ''
    scriptTaskId.value = payload.scriptTaskId || ''
    parseSuccess.value = Boolean(payload.parseSuccess)
    scriptGenerated.value = Boolean(payload.scriptGenerated)
    narrationAudioTasks.value = payload.narrationAudioTasks || {}
    audioTaskId.value = payload.audioTaskId || ''
    audioGenerated.value = Boolean(payload.audioGenerated)
    activeResultTab.value = payload.activeResultTab || 'script'
    activeFlowStep.value = payload.activeFlowStep || 'upload'
    snapshotAt.value = payload.updatedAt || ''
    lessonStore.setCourseInfo({
      courseId: platformQuery.value.courseId,
      courseName: courseName.value,
      courseDesc: courseDescInput.value,
      teacherName: '张老师',
    })
    const restoredSections = scriptStructure.value.length
      ? buildLessonSectionsFromScript(scriptStructure.value)
      : buildPreviewSections(payload.parseResult?.rawStructurePreview || payload.parseResult?.structurePreview || {})
    lessonStore.setLessonInfo({
      lessonId: normalizeText(parseTaskId.value, platformQuery.value.lessonId),
      lessonTitle: courseName.value || lessonStore.lessonInfo.lessonTitle || '课程讲解内容',
      fileName: payload.parseResult?.fileInfo?.fileName || restoredFileName.value,
      totalPages: payload.parseResult?.fileInfo?.pageCount || 1,
      sections: restoredSections.length ? restoredSections : buildPreviewSectionsFromTree(payload.parseResult?.structurePreview || {}),
      pageContents: [],
      scriptId: scriptTaskId.value,
    })
    hydratingCourseMeta.value = false
    hasSnapshot.value = true
    draftDirty.value = false
    return true
  } catch {
    hydratingCourseMeta.value = false
    localStorage.removeItem(snapshotKey.value)
    return false
  }
}

const clearSnapshot = ({ confirm = false, silent = false } = {}) => {
  if (workflowBusy.value) {
    if (!silent) ElMessage.warning('任务进行中，暂不能清除')
    return
  }
  if (confirm && !window.confirm('确认清除当前创建页内容和本地自动保存草稿吗？')) {
    return
  }
  localStorage.removeItem(snapshotKey.value)
  hasSnapshot.value = false
  snapshotAt.value = ''
  uploadFile.value = null
  restoredFileName.value = ''
  uploadRef.value?.clearFiles()
  coverImageFile.value = null
  coverImageUrl.value = ''
  courseNameInput.value = ''
  courseDescInput.value = ''
  courseTagInput.value = ''
  renderMode.value = 'flash'
  audioTaskId.value = ''
  audioGenerated.value = false
  generatingAudio.value = false
  narrationAudioTasks.value = {}
  published.value = false
  activeFlowStep.value = 'upload'
  clearResultState()
  lessonStore.setCourseInfo({
    courseId: platformQuery.value.courseId,
    courseName: '',
    courseDesc: '',
    teacherName: '张老师',
  })
  lessonStore.setLessonInfo({
    lessonId: platformQuery.value.lessonId,
    scriptId: '',
    audioId: '',
    totalPages: 0,
    sections: [],
    currentSectionId: '',
    currentPage: 1,
  })
  draftDirty.value = false
  if (!silent) ElMessage.success('已清除当前草稿')
}

const restorePendingTaskState = async () => {
  if (parseSuccess.value || !parseTaskId.value) {
    return
  }

  try {
    const restored = await tryRecoverParseTask(parseTaskId.value)
    if (restored) {
      ElMessage.success('已同步后台解析结果')
    }
  } catch {
    // Ignore restore failures and let the user retry manually.
  }
}

const syncResultPanelHeight = () => {
  if (!leftColRef.value) {
    syncedResultPanelHeight.value = 0
    return
  }

  const nextHeight = Math.round(leftColRef.value.getBoundingClientRect().height)
  syncedResultPanelHeight.value = nextHeight > 0 ? nextHeight : 0
}

const onFileChange = (file) => { uploadFile.value = file.raw; restoredFileName.value = ''; clearResultState(); activeFlowStep.value = 'parse'; draftDirty.value = true }
const reuploadFile = () => { uploadFile.value = null; restoredFileName.value = ''; clearResultState(); uploadRef.value?.clearFiles(); draftDirty.value = true }
const onCoverImageChange = (file) => {
  const raw = file.raw
  if (!raw || !raw.type.startsWith('image/')) { ElMessage.warning('请上传图片文件'); return }
  coverImageFile.value = raw
  const reader = new FileReader()
  reader.onload = (e) => { coverImageUrl.value = e.target.result; draftDirty.value = true }
  reader.readAsDataURL(raw)
}
const removeCoverImage = () => { coverImageUrl.value = ''; coverImageFile.value = null; draftDirty.value = true }

const handleParse = async () => {
  if (!uploadFile.value) { ElMessage.warning('请先上传课件'); return }
  parsing.value = true
  parseError.value = ''
  parseSuccess.value = false
  scriptGenerated.value = false
  scriptStructure.value = []
  slidePlan.value = null
  slidePlanText.value = ''
  const formData = new FormData()
  formData.append('file', uploadFile.value)
  formData.append('schoolId', platformQuery.value.schoolId)
  formData.append('userId', platformQuery.value.userId)
  formData.append('courseId', platformQuery.value.courseId)
  formData.append('fileType', uploadFile.value.name.split('.').pop()?.toLowerCase() || 'pdf')
  formData.append('instruction', courseDescInput.value)
  formData.append('audience', '高校课堂学生')
  let submittedParseId = ''
  try {
    const submission = await generateCoursewareSlidePlan(formData)
    submittedParseId = submission.lessonId
    parseTaskId.value = submission.lessonId
    const result = await pollTaskStatus({
      loadStatus: () => getCoursewareStatus(submission.lessonId),
      getStatus: (payload) => payload.taskStatus === 'plan_ready' ? 'completed' : payload.taskStatus,
      pendingStates: ['processing', 'pending', 'planning'],
    })
    applyCoursewarePlanResult(result)
    ElMessage.success('课件规划已生成')
  } catch (error) {
    try {
      const restored = await tryRecoverParseTask(submittedParseId || parseTaskId.value)
      if (restored) {
        parseError.value = ''
        ElMessage.success('课件规划已完成，已同步最新状态')
        return
      }
    } catch {
      // Ignore recovery errors and fall back to the original error message.
    }
    parseError.value = readErrorMessage(error, '课件规划生成失败，请重试。')
  } finally {
    parsing.value = false
  }
}

const handleGenerateScript = async () => {
  const currentParseId = normalizeText(parseTaskId.value, parseResult.value?.parseId || '')
  if (!parseSuccess.value || !currentParseId) { ElMessage.warning('请先生成课件规划'); return }
  generating.value = true
  renderingPpt.value = true
  generateError.value = ''
  scriptGenerated.value = false
  try {
    const editedPlan = prepareSlidePlanForSubmit()
    const savedPlan = await updateCoursewareSlidePlan({
      lessonId: currentParseId,
      slidePlan: editedPlan,
    })
    applyCoursewarePlanResult({ ...savedPlan, lessonId: currentParseId, lessonName: courseName.value })
    await renderCoursewarePpt({
      lessonId: currentParseId,
      renderMode: renderMode.value,
    })
    const result = await pollTaskStatus({
      loadStatus: () => getCoursewareStatus(currentParseId),
      getStatus: (payload) => payload.taskStatus,
      pendingStates: ['processing', 'pending', 'planning', 'rendering', 'plan_ready'],
    })
    renderedPptUrl.value = result.renderedPptUrl || ''
    syncNarrationAudioTasks(result.narrationAudioTasks || {})
    lessonStore.setLessonInfo({
      lessonId: normalizeText(result.lessonId, backendLessonId.value),
      sections: buildLessonSectionsFromScript(scriptStructure.value),
      renderedPptUrl: renderedPptUrl.value,
      scriptGeneratedAt: new Date().toISOString(),
    })
    scriptGenerated.value = true
    activeResultTab.value = 'script'
    draftDirty.value = true
    try {
      await generateNarrationAudioForLesson(currentParseId)
      lessonStore.setLessonInfo({
        audioId: audioTaskId.value,
        narrationAudioTasks: narrationAudioTasks.value,
      })
      ElMessage.success('PPT 和四档讲稿已生成，讲解音频正在后台生成')
    } catch (audioError) {
      ElMessage.warning(readErrorMessage(audioError, 'PPT 与四档讲稿已生成，但讲解音频生成失败'))
    }
  } catch (error) {
    generateError.value = readErrorMessage(error, 'PPT 渲染失败，请重试。')
  } finally {
    generating.value = false
    renderingPpt.value = false
  }
}

const handlePublish = async () => {
  if (publishing.value || published.value) return
  const publishName = resolvedCourseName.value
  if (!publishName) {
    ElMessage.warning('请输入课程名称')
    return
  }
  publishing.value = true
  try {
    await publishLesson({
      lessonId: backendLessonId.value,
      lessonName: publishName,
      courseDesc: courseDescInput.value,
      tag: courseTagInput.value,
      coverUrl: coverImageUrl.value,
    })
    published.value = true
    clearSnapshot({ silent: true })
    ElMessage.success('智课已发布，正在跳转首页...')
    setTimeout(() => router.push('/pc/home'), 1200)
  } catch (e) {
    ElMessage.error('发布失败，请稍后重试')
  } finally {
    publishing.value = false
  }
}

const goToScriptEditor = () => {
  if (!scriptGenerated.value) return
  draftDirty.value = false
  router.push({
    path: '/teacher/script-editor',
    query: {
      ...platformQuery.value,
      lessonId: backendLessonId.value,
      parseId: parseTaskId.value,
      scriptId: scriptTaskId.value,
    },
  })
}
const enterPreview = async () => {
  if (!scriptGenerated.value) return
  const lessonId = backendLessonId.value
  if (!lessonId) {
    ElMessage.error('未找到课件标识，无法进入预览')
    return
  }

  draftDirty.value = false
  router.push({
    path: '/lesson/player',
    query: {
      courseId: platformQuery.value.courseId,
      userId: platformQuery.value.userId,
      role: 'student',
      lessonId,
      token: platformQuery.value.token,
      schoolId: platformQuery.value.schoolId,
      scriptId: scriptTaskId.value,
      audioId: audioTaskId.value,
    },
  })
}
const beforeUnload = (event) => { if (!hasUnsavedWorkflow.value) return; event.preventDefault(); event.returnValue = '' }

onMounted(async () => {
  syncStoreContext()
  if (restoreSnapshot()) ElMessage.success('已恢复上次流程')
  await restorePendingTaskState()
  await nextTick()
  syncResultPanelHeight()
  if (typeof ResizeObserver !== 'undefined' && leftColRef.value) {
    leftColResizeObserver = new ResizeObserver(() => syncResultPanelHeight())
    leftColResizeObserver.observe(leftColRef.value)
  }
  window.addEventListener('resize', syncResultPanelHeight)
  window.addEventListener('beforeunload', beforeUnload)
})
onBeforeUnmount(() => {
  narrationAudioPollRun += 1
  window.removeEventListener('resize', syncResultPanelHeight)
  window.removeEventListener('beforeunload', beforeUnload)
  leftColResizeObserver?.disconnect()
  leftColResizeObserver = null
})
onBeforeRouteLeave((to, from, next) => next(!hasUnsavedWorkflow.value || window.confirm('有未保存流程，确认离开吗？')))
watch(() => route.query, syncStoreContext, { deep: true })
watch(() => activeFlowStep.value, () => nextTick(syncResultPanelHeight))
watch(
  () => [courseNameInput.value, courseDescInput.value, courseTagInput.value],
  ([nextName, nextDesc, nextTag], [prevName, prevDesc, prevTag]) => {
    if (hydratingCourseMeta.value) return
    lessonStore.setCourseInfo({
      courseId: platformQuery.value.courseId,
      courseName: courseName.value,
      courseDesc: nextDesc,
      teacherName: '张老师',
    })
    if (nextName !== prevName || nextDesc !== prevDesc || nextTag !== prevTag) draftDirty.value = true
  },
)
watch(() => [parseResult.value, scriptStructure.value, slidePlan.value, slidePlanText.value, renderMode.value, renderedPptUrl.value, parseTaskId.value, scriptTaskId.value, parseSuccess.value, scriptGenerated.value, narrationAudioTasks.value, audioTaskId.value, audioGenerated.value, activeResultTab.value, activeFlowStep.value, fileName.value, courseNameInput.value, courseDescInput.value, courseTagInput.value, coverImageUrl.value], persistSnapshot, { deep: true })
watch(() => [parsing.value, generating.value, renderingPpt.value, parseSuccess.value, scriptGenerated.value, fileName.value], () => nextTick(syncResultPanelHeight))

const stepStatusMeta = {
  done: { label: '已完成', color: '#059669', bg: '#ecfdf5', border: '#a7f3d0' },
  active: { label: '进行中', color: '#0f766e', bg: '#f0fdfa', border: '#99f6e4' },
  idle: { label: '待执行', color: '#64748b', bg: '#f8fafc', border: '#e2e8f0' },
  locked: { label: '未解锁', color: '#94a3b8', bg: '#f8fafc', border: '#e2e8f0' },
}
const getStepMeta = (status) => stepStatusMeta[status] || stepStatusMeta.idle
</script>

<template>
  <div class="teacher-page">
    <section class="create-hero">
      <div class="create-hero-copy">
        <span class="view-kicker">课程创建</span>
        <h1>创建智课</h1>
        <p>上传课件，生成可编辑课件规划，并输出 {{ modeLabel }} PPT 与四档讲稿。</p>
        <div class="create-hero-chips">
          <span>{{ modeLabel }}</span>
          <span>{{ statusText }}</span>
          <span>{{ hasDraftContent ? '草稿已保留' : '准备创建' }}</span>
        </div>
      </div>
      <aside class="create-status-card">
        <div class="create-status-head">
          <span>创建状态</span>
          <strong>{{ statusText }}</strong>
        </div>
        <div class="create-status-grid">
          <span>
            <small>当前模式</small>
            <strong>{{ modeLabel.replace('版', '') }}</strong>
          </span>
          <span>
            <small>课程状态</small>
            <strong>{{ statusText }}</strong>
          </span>
        </div>
      </aside>
      <div class="create-hero-decoration" aria-hidden="true">
        <span class="create-deco-folder"><i /></span>
        <span class="create-deco-ring" />
        <span class="create-deco-spark spark-one" />
        <span class="create-deco-spark spark-two" />
      </div>
    </section>

    <!-- draft tip -->
    <p v-if="hasDraftContent" class="draft-tip">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <span>{{ snapshotAt ? `草稿保存于 ${snapshotAt}` : '当前内容会自动保存为本地草稿' }}</span>
      <button class="draft-clear-btn" :disabled="workflowBusy" @click="clearSnapshot({ confirm: true })">
        清除草稿
      </button>
    </p>

    <section class="course-meta-panel">
      <div class="section-card-head course-meta-head">
        <div>
          <span class="section-eyebrow">课程档案</span>
          <h2>课程档案</h2>
          <p>完善封面、名称和描述后，AI 会将这些信息用于生成开场与页面规划。</p>
        </div>
      </div>

      <!-- 封面图上传 -->
      <div class="meta-cover-col">
        <p class="meta-label">课程封面</p>
        <div class="cover-upload-wrap">
          <el-upload v-if="!coverImageUrl" class="cover-uploader" :auto-upload="false" :show-file-list="false"
            accept="image/*" :on-change="onCoverImageChange">
            <div class="cover-placeholder">
              <div class="cover-ph-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <rect x="3" y="3" width="18" height="18" rx="3" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
              <span class="cover-ph-text">点击上传封面</span>
              <span class="cover-ph-sub">JPG / PNG · 建议 16:9</span>
            </div>
          </el-upload>
          <div v-else class="cover-preview">
            <img :src="coverImageUrl" alt="课程封面" class="cover-preview-img" />
            <div class="cover-preview-overlay">
              <button class="cover-remove-btn" @click="removeCoverImage">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
                更换图片
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 文字信息区 -->
      <div class="meta-fields-col">
        <!-- 课程名称 -->
        <div class="meta-field">
          <label class="meta-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
            </svg>
            课程名称
            <span class="meta-required">*</span>
          </label>
          <el-input v-model="courseNameInput" maxlength="40" clearable show-word-limit placeholder="请输入课程名称，例如：人工智能导论"
            class="meta-input-styled" />
        </div>

        <!-- 标签 -->
        <div class="meta-field">
          <label class="meta-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
            课程标签
          </label>
          <el-input v-model="courseTagInput" maxlength="20" clearable placeholder="例如：AI · 入门"
            class="meta-input-styled">
            <template #prefix>
              <span class="tag-prefix">#</span>
            </template>
          </el-input>
        </div>

        <!-- 课程简介 -->
        <div class="meta-field">
          <label class="meta-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="17" y1="10" x2="3" y2="10" />
              <line x1="21" y1="6" x2="3" y2="6" />
              <line x1="21" y1="14" x2="3" y2="14" />
              <line x1="17" y1="18" x2="3" y2="18" />
            </svg>
            课程简介
          </label>
          <el-input v-model="courseDescInput" type="textarea" :rows="3" maxlength="240" resize="none" show-word-limit
            placeholder="简要描述课程目标与内容，将作为 AI 生成脚本的开场引导" class="meta-textarea-styled" />
        </div>

      </div>

      <div class="course-mode-section">
        <div class="mode-section-head">
          <span class="meta-label">生成版本</span>
          <span class="mode-current-pill">{{ modeLabel }}</span>
        </div>
        <div class="workflow-mode-switch" aria-label="选择 PPT 生成版本">
          <button class="workflow-mode-card" :class="{ active: renderMode === 'flash' }" @click="renderMode = 'flash'">
            <span class="mode-card-title">Flash 快速版</span>
            <span class="mode-card-desc">速度优先</span>
          </button>
          <button class="workflow-mode-card" :class="{ active: renderMode === 'pro' }" @click="renderMode = 'pro'">
            <span class="mode-card-title">Pro 高质量版</span>
            <span class="mode-card-desc">质量优先</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ── Main content ────────────────────────────────────── -->
    <div class="main-grid">

      <!-- LEFT: Flow steps ─────────────────────────────────── -->
      <aside ref="leftColRef" class="left-col">

        <!-- Step cards -->
        <div class="steps-list">
          <button v-for="(step, i) in flowSteps" :key="step.id" class="step-card"
            :class="[`is-${step.status}`, { 'is-selected': activeFlowStep === step.id }]"
            :disabled="step.status === 'locked'" @click="step.status !== 'locked' && (activeFlowStep = step.id)">
            <div class="step-left">
              <div class="step-num"
                :style="{ background: getStepMeta(step.status).bg, color: getStepMeta(step.status).color, borderColor: getStepMeta(step.status).border }">
                <svg v-if="step.status === 'done'" width="13" height="13" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span v-else>{{ i + 1 }}</span>
              </div>
              <div class="step-text">
                <span class="step-title">{{ step.title }}</span>
                <span class="step-desc">{{ step.desc }}</span>
              </div>
            </div>
            <span class="step-status-tag"
              :style="{ color: getStepMeta(step.status).color, background: getStepMeta(step.status).bg }">
              {{ getStepMeta(step.status).label }}
            </span>
          </button>
        </div>

        <!-- Active step panel ────────────────────────────── -->
        <div class="action-panel">

          <!-- Upload step -->
          <template v-if="activeFlowStep === 'upload'">
            <div class="action-panel-header">
              <span class="action-title">上传课件文件</span>
              <span class="action-desc">支持 .ppt .pptx .pdf</span>
            </div>
            <el-upload v-if="!hasUploadedFile" ref="uploadRef" class="custom-upload" drag :auto-upload="false"
              :show-file-list="false" accept=".ppt,.pptx,.pdf" :on-change="onFileChange">
              <div class="upload-inner">
                <div class="upload-icon-wrap">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p class="upload-main-text">拖拽文件到此，或 <span class="upload-link">点击上传</span></p>
                <p class="upload-sub-text">PPT / PPTX / PDF · 最大 100MB</p>
              </div>
            </el-upload>
            <div v-else class="file-card">
              <div class="file-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <span class="file-name">{{ fileName }}</span>
              <button class="file-reupload" @click="reuploadFile">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <polyline points="1 4 1 10 7 10" />
                  <path d="M3.51 15a9 9 0 1 0 .49-3.56" />
                </svg>
                重新上传
              </button>
            </div>
          </template>

          <!-- Parse step -->
          <template v-else-if="activeFlowStep === 'parse'">
            <div class="action-panel-header">
              <span class="action-title">生成课件规划</span>
              <span class="action-desc">选择渲染模式后生成 slide_plan.json</span>
            </div>
            <div class="mode-current-line">
              <span>{{ modeLabel }}</span>
              <small>{{ modeDescription }}</small>
            </div>
            <div class="state-row" :class="parseSuccess ? 'state-success' : 'state-info'">
              <svg v-if="parseSuccess" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {{ parseSuccess ? '规划已生成' : '等待生成课件规划' }}
            </div>
            <button class="action-btn primary" :class="{ loading: parsing }" :disabled="!uploadFile || generating"
              @click="handleParse">
              <span v-if="parsing" class="btn-spinner" />
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2.5">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              {{ parsing ? '生成中...' : '生成课件规划' }}
            </button>
          </template>

          <!-- Script step -->
          <template v-else>
            <div class="action-panel-header">
              <span class="action-title">渲染课件 PPT</span>
              <span class="action-desc">确认规划后生成 PPT 和四档讲稿</span>
            </div>
            <div class="mode-current-line">
              <span>{{ modeLabel }}</span>
              <small>{{ modeDescription }}</small>
            </div>
            <div class="state-row" :class="scriptGenerated ? 'state-success' : 'state-info'">
              <svg v-if="scriptGenerated" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
              {{ scriptGenerated ? 'PPT 已生成' : '待渲染 PPT' }}
            </div>
            <button class="action-btn success" :class="{ loading: generating }" :disabled="!parseSuccess || parsing"
              @click="handleGenerateScript">
              <span v-if="generating" class="btn-spinner" />
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2.5">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              {{ generating ? '渲染中...' : '保存规划并渲染 PPT' }}
            </button>
          </template>
        </div>

        <!-- Bottom actions -->
        <div class="bottom-actions">
          <button class="action-btn outline" :disabled="!parseSuccess" @click="activeResultTab = 'plan'">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
            高级编辑
          </button>
          <button class="action-btn primary" :disabled="!scriptGenerated" @click="enterPreview">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            进入预览
          </button>
          <button class="action-btn publish" :class="{ done: published }"
            :disabled="!scriptGenerated || publishing || published" @click="handlePublish">
            <span v-if="publishing" class="btn-spinner" />
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22l-4-9-9-4 20-7z" />
            </svg>
            {{ published ? '已发布' : publishing ? '发布中...' : '发布智课' }}
          </button>
        </div>
      </aside>

      <!-- RIGHT: Result panel ──────────────────────────────── -->
      <section class="right-col">
        <div class="result-panel" :style="resultPanelStyle">
          <!-- Tab header -->
          <div class="result-tabs">
            <button class="result-tab" :class="{ active: activeResultTab === 'script' }"
              @click="activeResultTab = 'script'">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              页面概览
            </button>
            <button class="result-tab" :class="{ active: activeResultTab === 'structure' }"
              @click="activeResultTab = 'structure'">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 3h6v6H3zM15 3h6v6h-6zM3 15h6v6H3zM15 15h6v6h-6z" />
              </svg>
              课件结构
            </button>
            <button class="result-tab" :class="{ active: activeResultTab === 'plan' }"
              @click="activeResultTab = 'plan'">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 3H5a2 2 0 0 0-2 2v4m18 0V5a2 2 0 0 0-2-2h-4" />
                <path d="M9 21H5a2 2 0 0 1-2-2v-4m18 0v4a2 2 0 0 1-2 2h-4" />
                <path d="M8 8h8M8 12h8M8 16h5" />
              </svg>
              高级编辑
            </button>
          </div>

          <!-- Tab content -->
          <div class="result-content">

            <!-- Page overview tab -->
            <template v-if="activeResultTab === 'script'">
              <StateBlock v-if="generating" mode="loading" title="渲染中" description="正在生成 PPT 和四档讲稿" />
              <StateBlock v-else-if="generateError" mode="error" title="渲染失败" :description="generateError"
                action-text="重试" @action="handleGenerateScript" />
              <div v-else-if="scriptStructure.length" class="overview-list">
                <article v-for="(item, index) in scriptStructure" :key="item.id" class="overview-card">
                  <div class="overview-index">{{ String(index + 1).padStart(2, '0') }}</div>
                  <div class="overview-main">
                    <div class="overview-head">
                      <h3>{{ item.sectionName }}</h3>
                    </div>
                    <p class="overview-content">{{ item.content }}</p>
                  </div>
                </article>
              </div>
              <div v-else class="empty-state">
                <div class="empty-icon">📝</div>
                <p class="empty-title">暂无页面概览</p>
                <p class="empty-desc">完成课件规划后，页面摘要将展示在这里</p>
              </div>
            </template>

            <!-- Structure tab -->
            <template v-else-if="activeResultTab === 'structure'">
              <StateBlock v-if="parsing" mode="loading" title="生成中" description="正在生成课件规划" />
              <StateBlock v-else-if="parseError" mode="error" title="生成失败" :description="parseError" action-text="重试"
                @action="handleParse" />
              <el-tree v-else-if="structureChapters.length" class="custom-tree" :data="structureChapters" node-key="id"
                default-expand-all :props="{ label: 'label', children: 'children' }" />
              <div v-else class="empty-state">
                <div class="empty-icon">🗂</div>
                <p class="empty-title">暂无结构数据</p>
                <p class="empty-desc">上传并生成课件规划后，课件结构将展示在这里</p>
              </div>
            </template>

            <!-- Plan tab -->
            <template v-else>
              <StateBlock v-if="parsing" mode="loading" title="生成中" description="正在生成 slide_plan.json" />
              <StateBlock v-else-if="parseError" mode="error" title="规划生成失败" :description="parseError" action-text="重试"
                @action="handleParse" />
              <div v-else-if="slidePlan?.slides?.length" class="plan-editor">
                <div class="plan-editor-header">
                  <div>
                    <p class="plan-title">页面规划编辑</p>
                    <p class="plan-desc">调整课程标题、页面类型、教学目标和关键要点，渲染前会自动保存为课件规划。</p>
                  </div>
                  <span class="plan-count">{{ slidePlan?.slides?.length || 0 }} 页</span>
                </div>
                <div class="plan-deck-field">
                  <label class="plan-field-label">课程标题</label>
                  <el-input v-model="slidePlan.deck_title" placeholder="请输入课程标题" class="plan-input"
                    @input="syncPlanPreviewState" />
                </div>
                <div class="plan-card-list">
                  <article v-for="(slide, index) in slidePlan.slides" :key="slide.slide_id || index" class="plan-card">
                    <div class="plan-card-index">{{ String(index + 1).padStart(2, '0') }}</div>
                    <div class="plan-card-body">
                      <div class="plan-card-top">
                        <el-input v-model="slide.title" placeholder="页面标题" class="plan-title-input"
                          @input="syncPlanPreviewState" />
                        <div class="plan-card-selects">
                          <el-select v-model="slide.type" placeholder="页面类型" class="plan-select"
                            @change="syncPlanPreviewState">
                            <el-option v-if="slide.type && !hasSlideTypeOption(slide.type)"
                              :label="getSlideTypeLabel(slide.type)" :value="slide.type" />
                            <el-option v-for="option in slideTypeOptions" :key="option.value" :label="option.label"
                              :value="option.value" />
                          </el-select>
                          <el-select v-model="slide.rhythm" placeholder="课堂节奏" class="plan-select"
                            @change="syncPlanPreviewState">
                            <el-option v-if="slide.rhythm && !hasRhythmOption(slide.rhythm)"
                              :label="getRhythmLabel(slide.rhythm)" :value="slide.rhythm" />
                            <el-option v-for="option in rhythmOptions" :key="option.value" :label="option.label"
                              :value="option.value" />
                          </el-select>
                        </div>
                      </div>
                      <div class="plan-form-grid">
                        <label class="plan-form-item">
                          <span>副标题</span>
                          <el-input v-model="slide.subtitle" placeholder="可选" class="plan-input"
                            @input="syncPlanPreviewState" />
                        </label>
                        <label class="plan-form-item">
                          <span>教学目标</span>
                          <el-input v-model="slide.teaching_goal" placeholder="本页希望学生掌握什么" class="plan-input"
                            @input="syncPlanPreviewState" />
                        </label>
                      </div>
                      <label class="plan-form-item">
                        <span>关键要点</span>
                        <el-input :model-value="getSlideBulletsText(slide)" type="textarea" :rows="3" resize="none"
                          placeholder="每行一个关键要点" class="plan-textarea-compact"
                          @input="updateSlideBullets(slide, $event)" />
                      </label>
                    </div>
                  </article>
                </div>
              </div>
              <div v-else class="empty-state">
                <div class="empty-icon">{} </div>
                <p class="empty-title">暂无高级编辑内容</p>
                <p class="empty-desc">完成上传后先生成 slide plan</p>
              </div>
            </template>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* ── Base ─────────────────────────────────────────────────── */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.teacher-page {
  min-height: 100%;
  background: #f8fafc;
  font-family: 'Sora', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  overflow: hidden;
}

.create-hero {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);
  gap: 20px;
  margin: 0 0 2px;
  padding: 22px 24px;
  border: 1px solid rgba(20, 184, 166, 0.16);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(255, 255, 255, 0.92) 46%, rgba(14, 165, 233, 0.16)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px);
  background-size: auto, 22px 22px, 22px 22px;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
}

.create-hero-copy,
.create-status-card {
  position: relative;
  z-index: 1;
}

.create-kicker {
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
}

.create-hero h1 {
  margin: 8px 0 0;
  color: #0f172a;
  font-size: 30px;
  line-height: 1.16;
  font-weight: 800;
  letter-spacing: 0;
}

.create-hero p {
  max-width: 650px;
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
}

.create-hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.create-hero-chips span {
  padding: 7px 10px;
  border: 1px solid rgba(15, 118, 110, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
  color: #134e4a;
  font-size: 12px;
  font-weight: 800;
}

.create-status-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(20, 184, 166, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.07);
  backdrop-filter: blur(12px);
}

.create-status-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.create-status-head span {
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
}

.create-status-head strong {
  padding: 6px 9px;
  border-radius: 8px;
  background: #ecfdf5;
  color: #0f766e;
  font-size: 13px;
  font-weight: 800;
}

.create-status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.create-status-grid span {
  display: grid;
  gap: 6px;
  padding: 11px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #ffffff;
}

.create-status-grid small {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.create-status-grid strong {
  overflow: hidden;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.2;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.create-hero-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.create-deco-folder {
  position: absolute;
  left: 45%;
  top: 34px;
  width: 86px;
  height: 58px;
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(20, 184, 166, 0.22), rgba(20, 184, 166, 0.08));
  box-shadow: 0 18px 34px rgba(20, 184, 166, 0.12);
  transform: rotate(-5deg);
}

.create-deco-folder::before {
  content: "";
  position: absolute;
  left: 12px;
  top: -10px;
  width: 32px;
  height: 16px;
  border-radius: 8px 8px 4px 4px;
  background: rgba(20, 184, 166, 0.14);
}

.create-deco-folder i {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 11px;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
}

.create-deco-ring {
  position: absolute;
  right: 31%;
  bottom: 22px;
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: conic-gradient(rgba(59, 130, 246, 0.42) 62%, rgba(219, 234, 254, 0.54) 0);
  opacity: 0.72;
}

.create-deco-ring::before {
  content: "";
  position: absolute;
  inset: 15px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.78);
}

.create-deco-spark {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  color: rgba(20, 184, 166, 0.28);
  background: currentColor;
}

.create-deco-spark::before,
.create-deco-spark::after {
  content: "";
  position: absolute;
  inset: -5px 2px;
  border-radius: 999px;
  background: currentColor;
}

.create-deco-spark::after {
  inset: 2px -5px;
}

.spark-one {
  left: 38%;
  bottom: 48px;
}

.spark-two {
  right: 23%;
  top: 48px;
  transform: scale(0.72);
  color: rgba(59, 130, 246, 0.22);
}

/* ── Draft tip ──────────────────────────────────────────── */
.draft-tip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  margin: 0;
  font-size: 11.5px;
  color: #94a3b8;
  font-weight: 500;
  background: #ffffff;
  border: 1px solid #edf2f7;
  border-radius: 8px;
}

.draft-clear-btn {
  all: unset;
  cursor: pointer;
  margin-left: auto;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #ef4444;
  background: #fef2f2;
  border: 1px solid #fecaca;
  transition: all 0.15s;
}

.draft-clear-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.draft-clear-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.course-meta-panel {
  margin: 0;
  padding: 20px;
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 20px 28px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background:
    linear-gradient(145deg, #ffffff 0%, #ffffff 70%, rgba(240, 253, 250, 0.8) 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  align-items: start;
}

.section-card-head {
  grid-column: 1 / -1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-eyebrow {
  color: #14b8a6;
  font-size: 12px;
  font-weight: 800;
}

.section-card-head h2 {
  margin: 6px 0 0;
  color: #0f172a;
  font-size: 20px;
  line-height: 1.3;
  font-weight: 800;
}

.section-card-head p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

.course-mode-section {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin-top: 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background:
    radial-gradient(circle at 98% 12%, rgba(20, 184, 166, 0.1), transparent 30%),
    linear-gradient(135deg, rgba(248, 250, 252, 0.92), #ffffff);
}

.mode-section-head {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  min-width: 0;
}

.mode-current-pill {
  width: fit-content;
  padding: 4px 8px;
  border-radius: 7px;
  color: #0f766e;
  background: #ccfbf1;
  font-size: 11.5px;
  font-weight: 800;
}

.workflow-mode-switch {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 0;
}

.workflow-mode-card {
  all: unset;
  cursor: pointer;
  min-height: 42px;
  padding: 8px 11px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background:
    linear-gradient(135deg, #ffffff, #f8fafc);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s, transform 0.18s;
}

.workflow-mode-card:hover {
  transform: translateY(-1px);
  border-color: #5eead4;
  background: #f0fdfa;
}

.workflow-mode-card.active {
  border-color: rgba(20, 184, 166, 0.45);
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.12), rgba(255, 255, 255, 0.95));
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.08);
}

.mode-card-title {
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
}

.workflow-mode-card.active .mode-card-title {
  color: #0f766e;
}

.mode-card-desc {
  flex: 0 0 auto;
  font-size: 11.5px;
  line-height: 1.3;
  color: #64748b;
}

/* Cover column */
.meta-cover-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cover-upload-wrap {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 8px;
  overflow: hidden;
}

.cover-uploader {
  width: 100%;
  height: 100%;
}

.cover-uploader :deep(.el-upload) {
  width: 100%;
  height: 100%;
  display: block;
}

.cover-uploader :deep(.el-upload-dragger) {
  width: 100%;
  height: 100%;
  border: 1.5px dashed #99f6e4;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.1), rgba(255, 255, 255, 0.94)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px);
  background-size: auto, 18px 18px, 18px 18px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  padding: 0;
}

.cover-uploader :deep(.el-upload-dragger:hover) {
  border-color: #2dd4bf;
  background: #f0fdfa;
}

.cover-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}

.cover-ph-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #ccfbf1;
  color: #0f766e;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-ph-text {
  font-size: 12.5px;
  font-weight: 600;
  color: #0f766e;
}

.cover-ph-sub {
  font-size: 11px;
  color: #94a3b8;
}

.cover-preview {
  width: 100%;
  height: 100%;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
}

.cover-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 10px;
  transition: background 0.2s;
}

.cover-preview:hover .cover-preview-overlay {
  background: rgba(15, 23, 42, 0.45);
}

.cover-remove-btn {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: rgba(0, 0, 0, 0.55);
  opacity: 0;
  transition: opacity 0.2s;
  backdrop-filter: blur(6px);
}

.cover-preview:hover .cover-remove-btn {
  opacity: 1;
}

/* Fields column */
.meta-fields-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.meta-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.meta-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  letter-spacing: 0.02em;
}

.meta-required {
  color: #ef4444;
  font-size: 13px;
  line-height: 1;
}

.tag-prefix {
  color: #2dd4bf;
  font-weight: 700;
  font-size: 14px;
}

.render-mode-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.mode-btn {
  all: unset;
  cursor: pointer;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: all 0.16s;
}

.mode-btn:hover {
  border-color: #99f6e4;
  background: #f0fdfa;
}

.mode-btn.active {
  border-color: #0f766e;
  background: #f0fdfa;
}

.mode-btn span {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.mode-btn.active span {
  color: #0f766e;
}

.mode-btn small {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
}

.mode-current-line {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.mode-current-line span {
  font-size: 12.5px;
  font-weight: 800;
  color: #0f766e;
}

.mode-current-line small {
  font-size: 11.5px;
  line-height: 1.5;
  color: #64748b;
}

/* Input styles */
.meta-input-styled :deep(.el-input__wrapper),
.meta-textarea-styled :deep(.el-textarea__inner) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dbe3ef inset;
  font-family: 'Sora', sans-serif;
  font-size: 13px;
  transition: box-shadow 0.2s;
}

.meta-input-styled :deep(.el-input__wrapper:hover),
.meta-textarea-styled :deep(.el-textarea__inner:hover) {
  box-shadow: 0 0 0 1px #5eead4 inset;
}

.meta-input-styled :deep(.el-input__wrapper.is-focus),
.meta-textarea-styled :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 2px #14b8a6 inset;
}

.meta-input-styled :deep(.el-input__count),
.meta-textarea-styled :deep(.el-input__count),
.meta-textarea-styled :deep(.el-input__count-inner) {
  background: transparent;
  font-size: 11px;
}

/* ── Main grid ───────────────────────────────────────────── */
.main-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  padding: 0;
  align-items: start;
  min-height: 0;
}

/* ── Left column ─────────────────────────────────────────── */
.left-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 24px;
}

/* Steps list */
.steps-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-card {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  transition: all 0.2s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
}

.step-card:hover:not(:disabled) {
  transform: translateX(2px);
  border-color: #99f6e4;
}

.step-card.is-selected {
  border-color: #0f766e;
  background: linear-gradient(135deg, #ffffff, #f0fdfa);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.08), 0 2px 8px rgba(15, 118, 110, 0.12);
}

.step-card.is-done {
  border-color: #a7f3d0;
}

.step-card:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.step-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1.5px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.2s;
}

.step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
}

.step-desc {
  font-size: 11.5px;
  color: #94a3b8;
}

.step-status-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  white-space: nowrap;
}

/* Action panel */
.action-panel {
  background:
    linear-gradient(145deg, #ffffff 0%, #ffffff 72%, rgba(240, 253, 250, 0.65) 100%);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 18px 16px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  gap: 14px;
  animation: panelIn 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes panelIn {
  from {
    opacity: 0;
    transform: translateY(6px)
  }

  to {
    opacity: 1;
    transform: translateY(0)
  }
}

.action-panel-header {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.action-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.action-desc {
  font-size: 12px;
  color: #94a3b8;
}

/* Upload area */
.custom-upload {
  width: 100%;
}

:deep(.custom-upload .el-upload) {
  width: 100%;
}

:deep(.custom-upload .el-upload-dragger) {
  width: 100%;
  height: auto;
  padding: 28px 20px;
  border: 1.5px dashed #99f6e4;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.1), rgba(255, 255, 255, 0.95)),
    linear-gradient(rgba(15, 118, 110, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px);
  background-size: auto, 18px 18px, 18px 18px;
  transition: all 0.2s;
}

:deep(.custom-upload .el-upload-dragger:hover) {
  border-color: #0f766e;
  background: #f0fdfa;
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-icon-wrap {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  background: #f0fdfa;
  color: #0f766e;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-main-text {
  font-size: 13.5px;
  font-weight: 600;
  color: #334155;
}

.upload-link {
  color: #0f766e;
  text-decoration: underline;
  cursor: pointer;
}

.upload-sub-text {
  font-size: 11.5px;
  color: #94a3b8;
}

/* File card */
.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.file-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #f0fdfa;
  color: #0f766e;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-name {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-reupload {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 11px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  flex-shrink: 0;
  transition: all 0.15s;
}

.file-reupload:hover {
  background: #e2e8f0;
}

/* State row */
.state-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.state-row.state-success {
  background: #ecfdf5;
  color: #059669;
}

.state-row.state-info {
  background: #f1f5f9;
  color: #64748b;
}

/* Buttons */
.action-btn {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  width: 100%;
  height: 42px;
  border-radius: 11px;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.18s;
  position: relative;
  overflow: hidden;
}

.action-btn.primary {
  background: linear-gradient(135deg, #0f766e, #10b981);
  color: #fff;
  box-shadow: 0 4px 16px rgba(15, 118, 110, 0.28);
}

.action-btn.primary:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 118, 110, 0.38);
}

.action-btn.success {
  background: linear-gradient(135deg, #059669, #10b981);
  color: #fff;
  box-shadow: 0 4px 16px rgba(5, 150, 105, 0.28);
}

.action-btn.success:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(5, 150, 105, 0.38);
}

.action-btn.outline {
  background: #f8fafc;
  color: #475569;
  border: 1.5px solid #e2e8f0;
}

.action-btn.outline:not(:disabled):hover {
  background: #e2e8f0;
  color: #1e293b;
}

.action-btn.publish {
  background: linear-gradient(135deg, #059669, #10b981);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3);
}

.action-btn.publish:not(:disabled):hover {
  box-shadow: 0 6px 20px rgba(5, 150, 105, 0.42);
  transform: translateY(-1px);
}

.action-btn.publish.done {
  background: #ecfdf5;
  color: #059669;
  box-shadow: none;
}

.action-btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Bottom actions */
.bottom-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.right-col {
  min-width: 0;
  min-height: 0;
}

.result-panel {
  background:
    linear-gradient(145deg, #ffffff 0%, #ffffff 74%, rgba(239, 246, 255, 0.72) 100%);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: clamp(520px, calc(100vh - 300px), 760px);
}

/* Tabs */
.result-tabs {
  display: flex;
  position: relative;
  border-bottom: 1px solid #f1f5f9;
  padding: 0 8px;
  background: rgba(248, 250, 252, 0.76);
}

.result-tab {
  all: unset;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 14px 18px;
  font-size: 13.5px;
  font-weight: 600;
  color: #94a3b8;
  position: relative;
  z-index: 1;
  transition: color 0.2s;
}

.result-tab.active {
  color: #0f766e;
}

.result-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2.5px;
  background: #0f766e;
  border-radius: 2px 2px 0 0;
}

.result-tab svg {
  opacity: 0.6;
}

.result-tab.active svg {
  opacity: 1;
}

.plan-editor {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.plan-editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.plan-title {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 4px;
}

.plan-desc {
  font-size: 12.5px;
  line-height: 1.7;
  color: #64748b;
}

.plan-count {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f0fdfa;
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.plan-deck-field {
  display: grid;
  gap: 7px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}

.plan-field-label,
.plan-form-item span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.3;
  font-weight: 800;
}

.plan-card-list {
  display: grid;
  gap: 12px;
}

.plan-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background:
    radial-gradient(circle at 98% 0%, rgba(20, 184, 166, 0.09), transparent 26%),
    #ffffff;
}

.plan-card-index {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0f766e;
  background: #f0fdfa;
  font-size: 12.5px;
  font-weight: 800;
}

.plan-card-body {
  min-width: 0;
  display: grid;
  gap: 12px;
}

.plan-card-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 10px;
  align-items: center;
}

.plan-card-selects {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.plan-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.plan-form-item {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.plan-input :deep(.el-input__wrapper),
.plan-title-input :deep(.el-input__wrapper),
.plan-select :deep(.el-select__wrapper),
.plan-textarea-compact :deep(.el-textarea__inner) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dbe3ef inset;
  background: #f8fafc;
}

.plan-title-input :deep(.el-input__inner) {
  color: #0f172a;
  font-weight: 800;
}

.plan-textarea-compact :deep(.el-textarea__inner) {
  font-size: 13px;
  line-height: 1.65;
}

/* Content area */
.result-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  min-height: 0;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

/* Tree */
:deep(.custom-tree) {
  background: transparent;
}

:deep(.custom-tree .el-tree-node__content) {
  height: 36px;
  border-radius: 8px;
  padding: 0 8px;
  transition: background 0.15s;
}

:deep(.custom-tree .el-tree-node__content:hover) {
  background: #f1f5f9;
}

:deep(.custom-tree .el-tree-node__label) {
  font-size: 13.5px;
  color: #334155;
  font-weight: 500;
}

/* Page overview */
.overview-list {
  display: grid;
  gap: 10px;
}

.overview-card {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background:
    radial-gradient(circle at 98% 0%, rgba(20, 184, 166, 0.1), transparent 28%),
    #ffffff;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
}

.overview-card:hover {
  transform: translateY(-1px);
  border-color: #99f6e4;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.overview-index {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0fdfa;
  color: #0f766e;
  font-size: 13px;
  font-weight: 800;
}

.overview-main {
  min-width: 0;
}

.overview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 7px;
}

.overview-head h3 {
  min-width: 0;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.45;
  font-weight: 800;
}

.overview-content {
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 56px 20px;
  text-align: center;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.08), rgba(255, 255, 255, 0.82)),
    linear-gradient(rgba(15, 118, 110, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.045) 1px, transparent 1px);
  background-size: auto, 18px 18px, 18px 18px;
}

.empty-icon {
  font-size: 40px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: #334155;
}

.empty-desc {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.6;
  max-width: 260px;
}

@media (max-width: 1180px) {

  .create-hero,
  .course-meta-panel,
  .main-grid {
    grid-template-columns: 1fr;
  }

  .create-hero-decoration {
    display: none;
  }

  .left-col {
    position: static;
  }

  .course-mode-section {
    grid-template-columns: 1fr;
  }

  .plan-card-top,
  .plan-form-grid {
    grid-template-columns: 1fr;
  }

  .plan-card-selects {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {

  .create-hero,
  .course-meta-panel,
  .action-panel,
  .result-panel {
    border-radius: 8px;
  }

  .create-hero {
    padding: 18px;
  }

  .create-hero h1 {
    font-size: 25px;
  }

  .workflow-mode-switch,
  .plan-card,
  .plan-card-selects,
  .bottom-actions {
    grid-template-columns: 1fr;
  }

  .result-tabs {
    overflow-x: auto;
  }

  .result-tab {
    flex: 0 0 auto;
  }

  .teacher-page {
    padding: 16px;
  }

  .result-panel {
    height: min(640px, calc(100vh - 160px));
  }
}

/* Impeccable quieter pass for the course creation workbench. */
.teacher-page {
  background: transparent;
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  gap: 18px;
  padding: 24px;
  overflow: hidden;
}

:global(.app-shell--pc .teacher-page) {
  min-height: 100% !important;
  padding: 24px !important;
}

.create-hero {
  grid-template-columns: minmax(0, 1fr) 280px;
  padding: 20px 22px;
  border-color: #dfe1e6;
  background: #fffffe;
  box-shadow: 0 1px 3px rgba(29, 33, 41, 0.06);
}

.create-hero-decoration,
.create-deco-folder,
.create-deco-ring,
.create-deco-spark {
  display: none !important;
}

.create-hero h1 {
  color: #1d2129;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 0;
}

.create-hero p {
  color: #6b7785;
}

.create-hero-chips span {
  border-color: #dfe1e6;
  background: #f7f8fa;
  color: #6b7785;
  font-weight: 500;
}

.create-status-card {
  border-color: #dfe1e6;
  background: #fffffe;
  box-shadow: none;
  backdrop-filter: none;
}

.create-status-head span,
.create-status-grid small,
.meta-label,
.section-eyebrow,
.action-desc {
  color: #6b7785;
  font-weight: 500;
}

.create-status-head strong {
  background: #eef3ff;
  color: #245bdb;
  font-weight: 500;
}

.create-status-grid span,
.draft-tip,
.course-meta-panel,
.action-panel,
.result-panel,
.step-card,
.file-card,
.overview-card,
.plan-card {
  border-color: #dfe1e6;
  background: #fffffe;
  box-shadow: none;
}

.course-meta-panel,
.action-panel,
.result-panel {
  border-radius: 6px;
}

.section-card-head h2,
.action-title,
.overview-head h3,
.plan-title {
  color: #1d2129;
  font-weight: 600;
}

.workflow-mode-card {
  background: #fffffe;
  border-color: #dfe1e6;
  box-shadow: none;
}

.workflow-mode-card:hover,
.workflow-mode-card.active {
  transform: none;
  background: #f7f9ff;
  border-color: #b9c9f7;
  box-shadow: none;
}

.workflow-mode-card.active .mode-card-title,
.mode-current-pill,
.upload-link {
  color: #245bdb;
}

.step-card {
  transition: border-color 0.15s ease, background 0.15s ease;
}

.step-card:hover:not(:disabled),
.step-card.is-selected {
  transform: none;
  border-color: #b9c9f7;
  background: #f7f9ff;
  box-shadow: none;
}

.step-title,
.create-status-grid strong,
.overview-index {
  font-weight: 600;
}

.custom-upload :deep(.el-upload-dragger),
.cover-placeholder,
.empty-state {
  border-color: #dfe1e6;
  background: #f7f8fa;
  box-shadow: none;
}

.upload-icon-wrap,
.cover-ph-icon,
.overview-index {
  background: #eef3ff;
  color: #245bdb;
}

.overview-card {
  background: #fffffe;
  transition: border-color 0.15s ease;
}

.overview-card:hover {
  transform: none;
  border-color: #c8d2e6;
  box-shadow: none;
}

.empty-icon {
  display: none;
}

.empty-title {
  color: #1d2129;
  font-weight: 600;
}

@media (max-width: 1180px) {
  .create-hero {
    grid-template-columns: 1fr;
  }
}

/* Second quieter pass: make this a workflow surface, not a landing section. */
.create-hero {
  display: block;
  padding: 0 0 14px;
  border: 0;
  border-bottom: 1px solid #dfe1e6;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.create-status-card,
.create-hero-chips {
  display: none;
}

.create-hero h1 {
  margin-top: 4px;
  font-size: 22px;
}

.create-hero p {
  max-width: 70ch;
}

.course-meta-panel {
  padding: 24px;
}

.cover-upload-wrap {
  max-width: 520px;
}

.cover-placeholder {
  min-height: 96px;
  padding: 18px;
}

.cover-ph-icon {
  width: 32px;
  height: 32px;
}

.cover-ph-text {
  font-size: 13px;
  font-weight: 500;
}

.section-card-head.course-meta-head {
  margin-bottom: 12px;
}

.section-eyebrow {
  display: none;
}

.course-meta-head h2 {
  font-size: 18px;
}

.main-grid {
  gap: 20px;
  min-height: 0;
}

.steps-list {
  gap: 0;
  border: 1px solid #dfe1e6;
  border-radius: 6px;
  overflow: hidden;
}

.step-card {
  border: 0;
  border-bottom: 1px solid #ebedf0;
  border-radius: 0;
}

.step-card:last-child {
  border-bottom: 0;
}

.action-panel,
.result-panel {
  box-shadow: none;
}

.result-panel {
  height: clamp(520px, calc(100vh - 300px), 760px);
}

.result-content {
  padding: 24px;
}

@media (max-width: 720px) {
  :global(.app-shell--pc .teacher-page) {
    padding: 16px !important;
  }
}
</style>
