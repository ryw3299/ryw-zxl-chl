<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  buildLessonPreviewImageUrl,
  getCoursewareStatus,
  getLessonNarration,
  getLessonPreviewMeta,
  listLessons,
  publishLesson,
} from '@/api/lesson'
import { useRoute } from 'vue-router'

const route = useRoute()

const levels = [
  { key: 'A', title: '基础版', tag: '最慢 / 最详细', audience: '基础薄弱 / 初学者', duration: '12-15 分钟', pages: '约15页', color: '#18a981' },
  { key: 'B', title: '标准版', tag: '适中 / 平衡', audience: '一般水平学生', duration: '7-9 分钟', pages: '约10页', color: '#3478f6' },
  { key: 'C', title: '进阶版', tag: '较快 / 精练', audience: '中等偏上 / 进阶学习者', duration: '5-6 分钟', pages: '约6页', color: '#f5a524' },
  { key: 'D', title: '拓展版', tag: '最快 / 最精炼', audience: '高水平 / 拓展提升', duration: '3-4 分钟', pages: '约3页', color: '#ef6b4a' },
]

const lessons = ref([])
const selectedLessonId = ref('')
const currentSlide = ref(1)
const currentLevel = ref('B')
const previewMeta = ref(null)
const coursewareStatus = ref(null)
const narrationByLevel = ref({})
const draftScript = ref('')
const loadingLessons = ref(false)
const loadingPreview = ref(false)
const loadingNarration = ref(false)
const publishing = ref(false)

const selectedLesson = computed(() => lessons.value.find((item) => item.lessonId === selectedLessonId.value) || null)
const slideCount = computed(() => Math.max(1, Number(previewMeta.value?.slideCount || currentNarrationSlides.value.length || 1)))
const currentLevelMeta = computed(() => levels.find((item) => item.key === currentLevel.value) || levels[1])
const currentNarration = computed(() => narrationByLevel.value[currentLevel.value]?.narration || null)
const currentNarrationSlides = computed(() => {
  const slides = currentNarration.value?.slides
  return Array.isArray(slides) ? slides : []
})
const currentNarrationSlide = computed(() => {
  const slides = currentNarrationSlides.value
  return slides.find((item) => Number(item.slide_id || item.slideId || item.page) === currentSlide.value)
    || slides[Math.max(0, currentSlide.value - 1)]
    || null
})
const slidePreviewUrl = computed(() => (
  selectedLessonId.value
    ? buildLessonPreviewImageUrl(selectedLessonId.value, currentSlide.value, { v: previewMeta.value?.taskStatus || 'ready' })
    : ''
))
const visibleThumbs = computed(() => {
  const total = slideCount.value
  const windowSize = Math.min(5, total)
  const start = Math.max(1, Math.min(currentSlide.value - 1, Math.max(1, total - windowSize + 1)))
  return Array.from({ length: windowSize }, (_, index) => start + index).filter((page) => page <= total)
})
const totalScriptPages = computed(() => Math.max(1, currentNarrationSlides.value.length || slideCount.value))
const canPrev = computed(() => currentSlide.value > 1)
const canNext = computed(() => currentSlide.value < slideCount.value)
const pageTitle = computed(() => currentNarrationSlide.value?.topic || selectedLesson.value?.lessonName || `第 ${currentSlide.value} 页讲稿`)

const normalizeLessons = (items) => items
  .filter((item) => item?.lessonId)
  .map((item) => ({
    ...item,
    lessonName: item.lessonName || item.lessonId,
  }))

const loadLessons = async () => {
  loadingLessons.value = true
  try {
    const result = await listLessons('', { silent: true })
    lessons.value = normalizeLessons(Array.isArray(result?.lessons) ? result.lessons : [])
    const queryLessonId = typeof route.query.lessonId === 'string' ? route.query.lessonId : ''
    selectedLessonId.value = lessons.value.some((item) => item.lessonId === queryLessonId)
      ? queryLessonId
      : lessons.value[0]?.lessonId || ''
  } catch {
    lessons.value = []
  } finally {
    loadingLessons.value = false
  }
}

const loadPreview = async () => {
  if (!selectedLessonId.value) return
  loadingPreview.value = true
  try {
    previewMeta.value = await getLessonPreviewMeta(selectedLessonId.value)
  } catch (error) {
    previewMeta.value = null
    ElMessage.warning(error?.userMessage || 'PPT 预览暂不可用')
  } finally {
    loadingPreview.value = false
  }
}

const loadStatus = async () => {
  if (!selectedLessonId.value) return
  try {
    coursewareStatus.value = await getCoursewareStatus(selectedLessonId.value)
  } catch {
    coursewareStatus.value = null
  }
}

const loadNarration = async (level = currentLevel.value) => {
  if (!selectedLessonId.value || narrationByLevel.value[level]) return
  loadingNarration.value = true
  try {
    const result = await getLessonNarration(selectedLessonId.value, level)
    narrationByLevel.value = { ...narrationByLevel.value, [level]: result }
  } catch (error) {
    ElMessage.warning(error?.userMessage || `${level} 档讲稿暂不可用`)
  } finally {
    loadingNarration.value = false
  }
}

const selectLevel = async (level) => {
  currentLevel.value = level
  await loadNarration(level)
}

const goSlide = (page) => {
  const next = Number(page)
  if (!Number.isInteger(next) || next < 1 || next > slideCount.value) return
  currentSlide.value = next
}

const prevSlide = () => { if (canPrev.value) goSlide(currentSlide.value - 1) }
const nextSlide = () => { if (canNext.value) goSlide(currentSlide.value + 1) }

const handleLocalSave = () => {
  ElMessage.info('当前只接入了现有读取接口，讲稿保存接口暂未接入')
}

const handlePublish = async () => {
  if (!selectedLesson.value) return
  publishing.value = true
  try {
    await publishLesson({
      lessonId: selectedLesson.value.lessonId,
      lessonName: selectedLesson.value.lessonName,
      courseDesc: selectedLesson.value.courseDesc || '',
      tag: selectedLesson.value.tag || '',
      coverUrl: selectedLesson.value.coverUrl || '',
    })
    ElMessage.success('已发布到课堂')
  } catch (error) {
    ElMessage.warning(error?.userMessage || '发布失败')
  } finally {
    publishing.value = false
  }
}

watch(selectedLessonId, async () => {
  currentSlide.value = 1
  narrationByLevel.value = {}
  draftScript.value = ''
  await Promise.all([loadPreview(), loadStatus(), loadNarration(currentLevel.value)])
})

watch([currentNarrationSlide, currentLevel], () => {
  draftScript.value = currentNarrationSlide.value?.script || ''
}, { immediate: true })

onMounted(loadLessons)
</script>

<template>
  <div class="prep-page">
    <header class="prep-topbar">
      <div>
        <h1>多节奏讲稿编辑台</h1>
        <p>一页 PPT，对应多页讲稿，支持查看与本地微调</p>
      </div>
      <label class="lesson-picker">
        <span>当前智课</span>
        <select v-model="selectedLessonId" :disabled="loadingLessons || !lessons.length">
          <option v-for="lesson in lessons" :key="lesson.lessonId" :value="lesson.lessonId">
            {{ lesson.lessonName }}
          </option>
        </select>
      </label>
      <div class="top-actions">
        <button class="ghost-btn" type="button" @click="handleLocalSave">保存修改</button>
        <button class="primary-btn" type="button" :disabled="publishing || !selectedLessonId" @click="handlePublish">
          {{ publishing ? '发布中...' : '发布到课堂' }}
        </button>
      </div>
    </header>

    <div v-if="!selectedLessonId" class="empty-state">
      <strong>暂无可备课的智课</strong>
      <span>请先在课程创建中完成课件生成。</span>
    </div>

    <main v-else class="prep-layout">
      <div class="level-grid">
        <button
          v-for="level in levels"
          :key="level.key"
          type="button"
          class="level-card"
          :class="{ active: currentLevel === level.key }"
          :style="{ '--level-color': level.color }"
          @click="selectLevel(level.key)"
        >
          <span class="level-icon">{{ level.key }}</span>
          <strong>{{ level.title }}</strong>
          <em>{{ level.tag }}</em>
          <p><span>适合学情</span>{{ level.audience }}</p>
          <p><span>预计时长</span>{{ level.duration }}</p>
          <p><span>讲稿页数</span>{{ level.pages }}</p>
          <i v-if="currentLevel === level.key">✓</i>
        </button>
      </div>

      <div class="prep-workbench">
        <aside class="preview-column">
        <section class="preview-card">
          <div class="preview-head">
            <strong>PPT 第{{ String(currentSlide).padStart(2, '0') }}页</strong>
            <span>/ 共{{ slideCount }}页</span>
            <button type="button" :disabled="!canPrev" @click="prevSlide">‹</button>
            <button type="button" :disabled="!canNext" @click="nextSlide">›</button>
          </div>
          <div class="slide-frame">
            <img v-if="previewMeta?.taskStatus === 'completed'" :src="slidePreviewUrl" :alt="`第 ${currentSlide} 页 PPT 预览`" />
            <div v-else class="slide-placeholder">
              {{ loadingPreview ? '正在加载 PPT 预览...' : (previewMeta?.errorMessage || '该智课暂无 PPT 预览') }}
            </div>
          </div>
          <div class="thumb-row">
            <button
              v-for="page in visibleThumbs"
              :key="page"
              type="button"
              :class="{ active: page === currentSlide }"
              @click="goSlide(page)"
            >
              <img v-if="previewMeta?.taskStatus === 'completed'" :src="buildLessonPreviewImageUrl(selectedLessonId, page)" alt="" />
              <span>{{ String(page).padStart(2, '0') }}</span>
            </button>
          </div>
        </section>

        <section class="points-card">
          <div>
            <h3>本页教学要点</h3>
            <button type="button">编辑</button>
          </div>
          <ul>
            <li>{{ pageTitle }}</li>
            <li>当前讲稿：{{ currentLevelMeta.title }} · {{ currentLevelMeta.tag }}</li>
            <li>课件状态：{{ coursewareStatus?.taskStatus || previewMeta?.taskStatus || '未知' }}</li>
          </ul>
        </section>
        </aside>

        <section class="editor-column">
          <div class="script-panel">
          <div class="toolbar">
            <select>
              <option>正文</option>
            </select>
            <span></span>
            <button type="button">↶</button>
            <button type="button">↷</button>
            <button type="button">B</button>
            <button type="button">I</button>
            <button type="button">U</button>
            <button type="button">☷</button>
            <button type="button">☰</button>
            <p>自动保存未接入</p>
          </div>

          <article class="script-page">
            <div class="script-page-head">
              <h2>{{ currentSlide }}、{{ pageTitle }}</h2>
              <span>第 {{ Math.min(currentSlide, totalScriptPages) }} / {{ totalScriptPages }} 页</span>
            </div>
            <textarea
              v-model="draftScript"
              :placeholder="loadingNarration ? '正在加载讲稿...' : '该页暂无讲稿内容'"
            />
          </article>

          <div class="pagination">
            <button type="button" :disabled="!canPrev" @click="prevSlide">上一页</button>
            <button
              v-for="page in [1, 2, 3]"
              :key="page"
              type="button"
              :class="{ active: page === currentSlide }"
              :disabled="page > slideCount"
              @click="goSlide(page)"
            >
              {{ page }}
            </button>
            <span>...</span>
            <button type="button" :class="{ active: currentSlide === slideCount }" @click="goSlide(slideCount)">
              {{ slideCount }}
            </button>
            <button type="button" :disabled="!canNext" @click="nextSlide">下一页</button>
            <label>
              跳转到
              <input :value="currentSlide" type="number" min="1" :max="slideCount" @change="goSlide($event.target.value)" />
              / {{ slideCount }} 页
            </label>
          </div>
          </div>

        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.prep-page {
  min-height: 100%;
  padding: 22px 34px 28px;
  color: #10182f;
  background: #f7f9fd;
}

.prep-topbar {
  display: grid;
  grid-template-columns: 1fr 320px auto;
  align-items: center;
  gap: 22px;
  margin-bottom: 18px;
}

.prep-topbar h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.15;
  font-weight: 900;
}

.prep-topbar p {
  margin: 7px 0 0;
  color: #6b778d;
  font-size: 15px;
  font-weight: 650;
}

.lesson-picker {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  border: 1px solid #dfe6f2;
  border-radius: 10px;
  padding: 0 12px;
  background: #fff;
  color: #6b778d;
  font-size: 13px;
  font-weight: 720;
}

.lesson-picker select {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: #17213a;
  font: inherit;
}

.top-actions {
  display: flex;
  gap: 12px;
}

.ghost-btn,
.primary-btn {
  height: 44px;
  border-radius: 10px;
  padding: 0 26px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.ghost-btn {
  border: 1px solid #dfe6f2;
  background: #fff;
  color: #24324a;
}

.primary-btn {
  border: 0;
  color: #fff;
  background: linear-gradient(135deg, #3478f6, #18a981);
  box-shadow: 0 10px 20px rgba(52, 120, 246, 0.2);
}

.empty-state {
  height: 520px;
  display: grid;
  place-content: center;
  gap: 10px;
  border: 1px dashed #ccd7e8;
  border-radius: 16px;
  background: #fff;
  text-align: center;
}

.prep-layout {
  display: block;
}

.prep-workbench {
  display: grid;
  grid-template-columns: minmax(560px, 0.52fr) minmax(520px, 0.48fr);
  gap: 16px;
  align-items: stretch;
}

.preview-column {
  display: grid;
  gap: 8px;
}

.preview-card,
.points-card,
.script-panel {
  border: 1px solid #dfe6f2;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(22, 34, 58, 0.04);
}

.preview-card {
  padding: 24px 26px 14px;
}

.preview-head {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 18px;
}

.preview-head strong {
  font-size: 16px;
}

.preview-head span {
  color: #7a879a;
}

.preview-head button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 8px;
  background: #f3f6fb;
  color: #27344d;
  font-size: 22px;
  cursor: pointer;
}

.preview-head button:first-of-type {
  margin-left: auto;
}

.slide-frame {
  aspect-ratio: 16 / 7.7;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid #e3e9f3;
  border-radius: 12px;
  background: #f8fafd;
}

.slide-frame img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.slide-placeholder {
  padding: 24px;
  color: #7b879a;
  text-align: center;
  font-weight: 700;
}

.thumb-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.thumb-row button {
  height: 70px;
  border: 1px solid #e2e8f2;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
  cursor: pointer;
}

.thumb-row button.active {
  border-color: #3478f6;
  box-shadow: 0 0 0 2px rgba(52, 120, 246, 0.14);
}

.thumb-row img {
  width: 100%;
  height: 48px;
  object-fit: cover;
}

.thumb-row span {
  display: block;
  color: #475569;
  font-size: 12px;
  font-weight: 760;
}

.points-card {
  padding: 14px 26px 16px;
}

.points-card div {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.points-card h3 {
  margin: 0;
  font-size: 16px;
}

.points-card button {
  border: 0;
  color: #3478f6;
  background: transparent;
  font-weight: 800;
}

.points-card ul {
  display: grid;
  grid-template-columns: 1.2fr 1.1fr 0.9fr;
  gap: 14px;
  margin: 14px 0 0;
  padding-left: 0;
  color: #56647a;
  font-size: 14px;
  line-height: 1.5;
  list-style: none;
}

.editor-column {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.level-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.level-card {
  position: relative;
  min-height: 124px;
  border: 1px solid #dfe6f2;
  border-radius: 12px;
  background: #fff;
  padding: 18px 22px 14px;
  text-align: left;
  color: #17213a;
  font-family: inherit;
  cursor: pointer;
}

.level-card.active {
  border-color: var(--level-color);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--level-color) 18%, transparent);
}

.level-icon {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  margin-right: 10px;
  border: 2px solid var(--level-color);
  border-radius: 6px;
  color: var(--level-color);
  background: color-mix(in srgb, var(--level-color) 8%, white);
  font-weight: 900;
}

.level-card strong {
  font-size: 18px;
  font-weight: 900;
}

.level-card em {
  float: right;
  margin-top: 4px;
  border-radius: 8px;
  padding: 4px 8px;
  color: var(--level-color);
  background: color-mix(in srgb, var(--level-color) 10%, white);
  font-size: 12px;
  font-style: normal;
  font-weight: 850;
}

.level-card p {
  display: grid;
  grid-template-columns: 68px 1fr;
  gap: 8px;
  margin: 12px 0 0;
  color: #2f3b52;
  font-size: 13px;
  font-weight: 720;
}

.level-card p + p {
  margin-top: 8px;
}

.level-card p span {
  color: #7b879a;
}

.level-card i {
  position: absolute;
  top: -9px;
  right: -9px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: #2563ff;
  font-style: normal;
}

.script-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 42px;
  color: #71809a;
}

.toolbar select,
.toolbar button {
  height: 32px;
  border: 1px solid #e2e8f2;
  border-radius: 8px;
  background: #fff;
  color: #46556d;
  font: inherit;
}

.toolbar select {
  padding: 0 18px;
}

.toolbar button {
  min-width: 32px;
  padding: 0 9px;
}

.toolbar span {
  width: 1px;
  height: 24px;
  background: #e2e8f2;
}

.toolbar p {
  margin-left: auto;
  font-size: 13px;
}

.script-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 424px;
  border: 1px solid #e0e7f2;
  border-radius: 12px;
  padding: 26px 36px;
  background: #fff;
}

.script-page-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.script-page h2 {
  margin: 0;
  font-size: 22px;
}

.script-page-head span {
  height: 30px;
  border-radius: 999px;
  padding: 6px 13px;
  color: #7b879a;
  background: #f3f6fb;
  font-size: 13px;
  font-weight: 800;
}

.script-page textarea {
  width: 100%;
  flex: 1;
  min-height: 312px;
  border: 0;
  outline: 0;
  resize: vertical;
  color: #263247;
  background: transparent;
  font-family: inherit;
  font-size: 16px;
  line-height: 2;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}

.pagination button {
  min-width: 38px;
  height: 34px;
  border: 1px solid #e1e7f1;
  border-radius: 8px;
  background: #fff;
  color: #40506a;
  font-family: inherit;
  font-weight: 760;
  cursor: pointer;
}

.pagination button.active {
  border-color: #3478f6;
  color: #fff;
  background: #3478f6;
}

.pagination label {
  margin-left: auto;
  color: #738199;
  font-size: 13px;
  font-weight: 720;
}

.pagination input {
  width: 52px;
  height: 32px;
  margin: 0 8px;
  border: 1px solid #e1e7f1;
  border-radius: 8px;
  text-align: center;
  font: inherit;
}

@media (max-width: 1280px) {
  .prep-topbar,
  .prep-workbench {
    grid-template-columns: 1fr;
  }

  .level-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
