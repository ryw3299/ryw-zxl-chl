<script setup>
import { ref, computed } from 'vue'
import { showToast, showDialog } from 'vant'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'
import { parseLesson, getParseStatus, generateScript, getScriptStatus, generateAudio, getAudioStatus, publishLesson, renderLessonPpt } from '@/api/lesson'
import { DEFAULT_SCHOOL_ID } from '@/utils/signature'

const router = useRouter()
const userStore = useUserStore()

// ── 步骤 ──────────────────────────────────────────────────────────────
// flowStep: 'upload' | 'parse' | 'script'
const flowStep = ref('upload')

// ── 文件上传 ──────────────────────────────────────────────────────────
const uploadedFile = ref(null)
const fileInputRef = ref(null)

const onFileChange = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['pptx', 'ppt', 'pdf', 'docx'].includes(ext)) {
    showToast('请上传 PPTX、PPT、PDF 或 DOCX 格式文件')
    return
  }
  if (file.size > 100 * 1024 * 1024) {
    showToast('文件不能超过 100MB')
    return
  }
  uploadedFile.value = file
  // 重新上传时重置后续状态
  parseSuccess.value = false
  parseResult.value = null
  scriptGenerated.value = false
  scriptStructure.value = []
  parseError.value = ''
  generateError.value = ''
}

const reupload = () => {
  uploadedFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
  flowStep.value = 'upload'
  parseSuccess.value = false
  parseResult.value = null
  scriptGenerated.value = false
  scriptStructure.value = []
}

const fileExt = computed(() => uploadedFile.value?.name.split('.').pop().toUpperCase() ?? '')
const fileSize = computed(() => {
  const s = uploadedFile.value?.size ?? 0
  return s > 1024 * 1024 ? `${(s / 1024 / 1024).toFixed(1)} MB` : `${(s / 1024).toFixed(0)} KB`
})

// ── 课程信息 ──────────────────────────────────────────────────────────
const courseNameInput = ref('')
const courseTagInput  = ref('')
const courseDescInput = ref('')
const teachingStyle   = ref('standard')
const coverImageUrl   = ref('')
const coverImageFile  = ref(null)
const coverInputRef   = ref(null)

const styleOptions = [
  { value: 'standard',    label: '标准讲解', desc: '条理清晰，适合大多数课程' },
  { value: 'interactive', label: '互动引导', desc: '多问题引导，增强学生参与' },
  { value: 'case_based',  label: '案例驱动', desc: '以工程案例为主线展开讲解' },
]

const onCoverFileChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    showToast('请上传图片文件')
    return
  }
  coverImageFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    coverImageUrl.value = e.target?.result || ''
  }
  reader.readAsDataURL(file)
}

const removeCoverImage = () => {
  coverImageUrl.value = ''
  coverImageFile.value = null
  if (coverInputRef.value) coverInputRef.value.value = ''
}

// ── 解析状态 ──────────────────────────────────────────────────────────
const parsing         = ref(false)
const parseSuccess    = ref(false)
const parseResult     = ref(null)
const parseTaskId     = ref('')
const parseError      = ref('')

// ── 生成脚本状态 ──────────────────────────────────────────────────────
const generating      = ref(false)
const scriptGenerated = ref(false)
const scriptStructure = ref([])
const scriptTaskId    = ref('')
const generateError   = ref('')
const generatingAudio = ref(false)
const audioTaskId     = ref('')

// 折叠展开的章节
const openSections    = ref(new Set())

// ── 发布 ──────────────────────────────────────────────────────────────
const publishing      = ref(false)
const published       = ref(false)

// ── lessonId ─────────────────────────────────────────────────────────
const backendLessonId = computed(() =>
  parseResult.value?.lessonId || parseResult.value?.parseId || parseTaskId.value
)

// ── 步骤元数据 ────────────────────────────────────────────────────────
const steps = computed(() => [
  {
    key: 'upload',
    label: '上传课件',
    status: flowStep.value === 'upload' ? 'active'
          : (parseSuccess.value || scriptGenerated.value || uploadedFile.value) ? 'done'
          : 'pending',
  },
  {
    key: 'parse',
    label: '解析课件',
    status: flowStep.value === 'parse' ? 'active'
          : parseSuccess.value ? 'done'
          : 'pending',
  },
  {
    key: 'script',
    label: '生成脚本',
    status: flowStep.value === 'script' ? 'active'
          : scriptGenerated.value ? 'done'
          : 'pending',
  },
])

// ── 轮询工具 ──────────────────────────────────────────────────────────
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const pollUntil = async (fn, interval = 2500, maxRounds = 80) => {
  for (let i = 0; i < maxRounds; i++) {
    const res = await fn()
    const status = res?.taskStatus
    if (status === 'completed') return res
    if (status === 'failed') throw new Error(res?.errorMessage || '任务失败，请重试')
    await sleep(interval)
  }
  throw new Error('任务超时，请稍后重试')
}

// ── Step 1 → Step 2 ───────────────────────────────────────────────────
const goToParse = () => {
  if (!uploadedFile.value) { showToast('请先上传课件文件'); return }
  if (!courseNameInput.value.trim()) { showToast('请输入课程名称'); return }
  flowStep.value = 'parse'
}

// ── 开始解析 ──────────────────────────────────────────────────────────
const handleParse = async () => {
  if (!uploadedFile.value) { showToast('请先上传课件文件'); return }
  const currentCourseName = courseNameInput.value.trim()
  if (!currentCourseName) { showToast('请输入课程名称'); return }
  parsing.value = true
  parseError.value = ''
  parseSuccess.value = false

  const formData = new FormData()
  formData.append('file', uploadedFile.value)
  formData.append('schoolId', DEFAULT_SCHOOL_ID)
  formData.append('userId', userStore.userInfo?.userId || '')
  formData.append('courseId', currentCourseName)
  formData.append('fileType', uploadedFile.value.name.split('.').pop().toLowerCase() || 'pdf')
  formData.append('isExtractKeyPoint', 'true')

  try {
    const submission = await parseLesson(formData)
    parseTaskId.value = submission.parseId
    const result = await pollUntil(() => getParseStatus(submission.parseId))
    parseResult.value = result
    parseSuccess.value = true
    showToast({ message: '解析完成', type: 'success' })
  } catch (e) {
    parseError.value = e?.message || '解析失败，请重试'
  } finally {
    parsing.value = false
  }
}

// ── Step 2 → Step 3（生成脚本） ───────────────────────────────────────
const goToScript = () => {
  if (!parseSuccess.value) { showToast('请先完成课件解析'); return }
  flowStep.value = 'script'
}

// ── 生成脚本 ──────────────────────────────────────────────────────────
const handleGenerateScript = async () => {
  if (!parseSuccess.value || !parseTaskId.value) { showToast('请先完成解析'); return }
  generating.value = true
  generateError.value = ''
  scriptGenerated.value = false

  try {
    const submission = await generateScript({
      parseId: parseTaskId.value,
      teachingStyle: teachingStyle.value,
      customOpening: courseDescInput.value,
    })
    scriptTaskId.value = submission.scriptId
    const result = await pollUntil(() => getScriptStatus(submission.scriptId), 2500, 80)
    scriptTaskId.value = result.scriptId
    scriptStructure.value = normalizeScript(result.scriptStructure || [])
    scriptGenerated.value = scriptStructure.value.length > 0
    showToast({ message: '脚本生成成功，正在合成语音...', type: 'success' })

    // 串行触发语音合成
    generatingAudio.value = true
    try {
      const audioSub = await generateAudio({ scriptId: result.scriptId })
      audioTaskId.value = audioSub.audioId
      await pollUntil(() => getAudioStatus(audioSub.audioId), 2500, 80)
      showToast({ message: '讲解语音合成完成', type: 'success' })
    } catch {
      showToast('语音合成失败，脚本已保存')
    } finally {
      generatingAudio.value = false
    }
  } catch (e) {
    generateError.value = e?.message || '脚本生成失败，请重试'
  } finally {
    generating.value = false
  }
}

const normalizeScript = (sections) => sections.map((item, i) => ({
  id: item.sectionId || item.id || `sec-${i}`,
  sectionName: item.sectionName || item.title || `章节 ${i + 1}`,
  content: item.content || item.explainScript || '暂无内容',
  keyPoints: Array.isArray(item.keyPoints) ? item.keyPoints : [],
}))

const toggleSection = (id) => {
  if (openSections.value.has(id)) openSections.value.delete(id)
  else openSections.value.add(id)
  openSections.value = new Set(openSections.value)
}

// ── 解析结果：章节树展示 ──────────────────────────────────────────────
const chapterTree = computed(() => {
  const preview = parseResult.value?.structurePreview || parseResult.value?.rawStructurePreview || parseResult.value
  const chapters = preview?.chapters || []
  return chapters.map((ch, ci) => ({
    id: ch.chapterId || `ch-${ci}`,
    label: ch.chapterName || `章节 ${ci + 1}`,
    children: (ch.subChapters || []).map((sub, si) => ({
      id: sub.subChapterId || `ch-${ci}-sub-${si}`,
      label: sub.subChapterName || `小节 ${si + 1}`,
    })),
  }))
})

const openChapters = ref(new Set())
const toggleChapter = (id) => {
  if (openChapters.value.has(id)) openChapters.value.delete(id)
  else openChapters.value.add(id)
  openChapters.value = new Set(openChapters.value)
}

// ── 操作按钮 ──────────────────────────────────────────────────────────
const handlePublish = async () => {
  if (publishing.value || published.value) return
  const publishName = courseNameInput.value.trim()
  if (!publishName) { showToast('请输入课程名称'); return }
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
    showToast({ message: '智课已发布！', type: 'success' })
  } catch {
    showToast('发布失败，请稍后重试')
  } finally {
    publishing.value = false
  }
}

const goEditScript = () => {
  router.push({
    path: '/m/teacher/script-editor',
    query: {
      lessonId: backendLessonId.value,
      parseId: parseTaskId.value,
      scriptId: scriptTaskId.value,
    },
  })
}

const goPreview = async () => {
  const lessonId = backendLessonId.value
  if (!lessonId) { showToast('未找到课件标识，无法预览'); return }
  try {
    await renderLessonPpt(lessonId)
  } catch {
    showToast('PPT 渲染失败，请稍后重试')
    return
  }
  router.push({
    path: `/lesson/${encodeURIComponent(lessonId)}`,
    query: {
      courseId: courseNameInput.value.trim(),
      courseName: courseNameInput.value.trim(),
      userId: userStore.userInfo?.userId || '',
      role: 'student',
      schoolId: DEFAULT_SCHOOL_ID,
      token: userStore.token || '',
      parseId: parseTaskId.value,
      scriptId: scriptTaskId.value,
      audioId: audioTaskId.value,
    },
  })
}
</script>

<template>
  <div class="create-root">

    <!-- ══ 顶部进度条 ══════════════════════════════════════════ -->
    <div class="stepper">
      <template v-for="(step, i) in steps" :key="step.key">
        <div class="stepper-item" :class="`is-${step.status}`">
          <div class="stepper-dot">
            <svg v-if="step.status === 'done'" width="12" height="12" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <span class="stepper-label">{{ step.label }}</span>
        </div>
        <div v-if="i < steps.length - 1" class="stepper-line"
          :class="{ 'is-done': steps[i + 1].status !== 'pending' || step.status === 'done' }" />
      </template>
    </div>

    <!-- ══ Step 1：上传课件 ═══════════════════════════════════ -->
    <template v-if="flowStep === 'upload'">

      <!-- 文件上传 -->
      <div class="card">
        <div class="card-head">
          <div class="card-icon" style="background:#eef4ff">
            <van-icon name="upgrade" size="20" color="#1677ff" />
          </div>
          <div>
            <strong>上传课件</strong>
            <p>支持 PPTX、PPT、PDF、DOCX，最大 100MB</p>
          </div>
        </div>

        <div class="upload-zone" :class="{ 'has-file': uploadedFile }"
          @click="fileInputRef?.click()">
          <input ref="fileInputRef" type="file" accept=".pptx,.ppt,.pdf,.docx"
            style="display:none" @change="onFileChange" />

          <template v-if="!uploadedFile">
            <van-icon name="description" size="36" color="#c5cdd8" />
            <p class="upload-hint">点击选择课件文件</p>
            <span class="upload-sub">PPTX · PPT · PDF · DOCX</span>
          </template>

          <template v-else>
            <div class="file-preview">
              <div class="file-ext">{{ fileExt }}</div>
              <div class="file-info">
                <strong>{{ uploadedFile.name }}</strong>
                <span>{{ fileSize }}</span>
              </div>
              <van-icon name="success" size="20" color="#12b76a" />
            </div>
          </template>
        </div>
      </div>

      <!-- 课程信息 -->
      <div class="card">
        <div class="card-head">
          <div class="card-icon" style="background:#f5f0ff">
            <van-icon name="setting-o" size="20" color="#7c3aed" />
          </div>
          <div>
            <strong>课程信息</strong>
            <p>填写名称与讲解风格</p>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">课程名称 <span class="req">*</span></label>
          <van-field v-model="courseNameInput" placeholder="例如：数据结构与算法"
            class="form-field" :border="false" />
        </div>

        <div class="form-group">
          <label class="form-label">课程标签 <span class="opt">（可选）</span></label>
          <van-field v-model="courseTagInput" placeholder="例如：CS · 核心"
            class="form-field" :border="false" />
        </div>

        <div class="form-group">
          <label class="form-label">课程封面 <span class="opt">（可选）</span></label>
          <input ref="coverInputRef" type="file" accept="image/*" style="display:none" @change="onCoverFileChange" />
          <button v-if="!coverImageUrl" type="button" class="cover-picker" @click="coverInputRef?.click()">
            <van-icon name="photo-o" size="22" color="#9aa3b2" />
            <span>点击上传封面图</span>
          </button>
          <div v-else class="cover-preview">
            <img :src="coverImageUrl" alt="课程封面" />
            <button type="button" class="cover-remove" @click="removeCoverImage">
              <van-icon name="cross" size="13" />
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">课程简介 <span class="opt">（可选）</span></label>
          <van-field v-model="courseDescInput" type="textarea" rows="2" autosize
            placeholder="简要描述课程目标，将作为脚本开场引导..."
            class="form-field form-field--ta" :border="false" />
        </div>

        <div class="form-group" style="margin-bottom:0">
          <label class="form-label">讲解风格</label>
          <div class="style-list">
            <button v-for="opt in styleOptions" :key="opt.value"
              class="style-item" :class="{ active: teachingStyle === opt.value }"
              @click="teachingStyle = opt.value">
              <strong>{{ opt.label }}</strong>
              <p>{{ opt.desc }}</p>
            </button>
          </div>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="bottom-bar">
        <button class="btn-primary" @click="goToParse">
          <van-icon name="search" size="17" style="margin-right:6px" />
          下一步：解析课件
        </button>
      </div>

    </template>

    <!-- ══ Step 2：解析课件 ═══════════════════════════════════ -->
    <template v-else-if="flowStep === 'parse'">

      <!-- 已上传文件卡 -->
      <div class="card">
        <div class="card-head">
          <div class="card-icon" style="background:#eef4ff">
            <van-icon name="description" size="20" color="#1677ff" />
          </div>
          <div style="flex:1;min-width:0">
            <strong style="display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
              {{ uploadedFile?.name }}
            </strong>
            <p>{{ fileSize }} · {{ fileExt }}</p>
          </div>
          <button class="link-btn" @click="reupload">重新上传</button>
        </div>
      </div>

      <!-- 解析状态 -->
      <div class="card">
        <div class="card-head">
          <div class="card-icon" style="background:#f0fdf4">
            <van-icon name="search" size="20" color="#12b76a" />
          </div>
          <div>
            <strong>解析课件结构</strong>
            <p>AI 自动识别章节与知识点</p>
          </div>
        </div>

        <!-- 解析前提示 -->
        <div v-if="!parsing && !parseSuccess && !parseError"
          class="state-row state-info">
          <van-icon name="info-o" size="15" />
          点击下方按钮开始解析课件结构
        </div>

        <!-- 解析中 -->
        <div v-if="parsing" class="state-row state-active">
          <van-loading size="16px" color="#1677ff" />
          正在解析中，请稍候...
        </div>

        <!-- 解析成功 -->
        <div v-if="parseSuccess && !parsing" class="state-row state-success">
          <van-icon name="success" size="15" color="#12b76a" />
          解析完成！共识别 {{ chapterTree.length }} 个章节
        </div>

        <!-- 解析失败 -->
        <div v-if="parseError && !parsing" class="state-row state-error">
          <van-icon name="warning-o" size="15" />
          {{ parseError }}
        </div>

        <button v-if="!parsing" class="btn-action"
          :class="parseSuccess ? 'btn-outline' : 'btn-blue'"
          @click="handleParse">
          <van-icon :name="parseSuccess ? 'replay' : 'search'" size="16" />
          {{ parseSuccess ? '重新解析' : '开始解析' }}
        </button>
      </div>

      <!-- 章节结构预览 -->
      <div v-if="parseSuccess && chapterTree.length" class="card">
        <div class="card-head" style="margin-bottom:12px">
          <div class="card-icon" style="background:#fffbeb">
            <van-icon name="cluster-o" size="20" color="#d97706" />
          </div>
          <div>
            <strong>知识结构</strong>
            <p>点击章节可展开查看小节</p>
          </div>
        </div>

        <div class="tree-list">
          <div v-for="chapter in chapterTree" :key="chapter.id" class="tree-chapter">
            <button class="tree-chapter-row" @click="toggleChapter(chapter.id)">
              <van-icon
                :name="openChapters.has(chapter.id) ? 'arrow-down' : 'arrow'"
                size="13" color="#9aa3b2" />
              <span class="tree-chapter-label">{{ chapter.label }}</span>
              <span v-if="chapter.children.length" class="tree-badge">{{ chapter.children.length }}</span>
            </button>
            <div v-if="openChapters.has(chapter.id) && chapter.children.length" class="tree-children">
              <div v-for="child in chapter.children" :key="child.id" class="tree-child-row">
                <span class="tree-child-dot" />
                <span class="tree-child-label">{{ child.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部操作 -->
      <div class="bottom-bar two-col">
        <button class="btn-ghost" @click="flowStep = 'upload'">
          <van-icon name="arrow-left" size="15" />
          返回上传
        </button>
        <button class="btn-primary" :disabled="!parseSuccess" @click="goToScript">
          生成脚本
          <van-icon name="arrow" size="15" />
        </button>
      </div>

    </template>

    <!-- ══ Step 3：生成脚本 ═══════════════════════════════════ -->
    <template v-else-if="flowStep === 'script'">

      <!-- 生成触发卡 -->
      <div class="card">
        <div class="card-head">
          <div class="card-icon" style="background:#f0f6ff">
            <van-icon name="star-o" size="20" color="#1677ff" />
          </div>
          <div>
            <strong>AI 生成讲解脚本</strong>
            <p>风格：{{ styleOptions.find(o => o.value === teachingStyle)?.label }}</p>
          </div>
        </div>

        <!-- 未生成 -->
        <div v-if="!generating && !scriptGenerated && !generateError"
          class="state-row state-info">
          <van-icon name="info-o" size="15" />
          基于解析结果，AI 将自动逐章生成讲解脚本
        </div>

        <!-- 生成中 -->
        <div v-if="generating" class="state-row state-active">
          <van-loading size="16px" color="#1677ff" />
          脚本生成中，通常需要 1~3 分钟...
        </div>

        <!-- 已生成 -->
        <div v-if="scriptGenerated && !generating" class="state-row state-success">
          <van-icon name="success" size="15" color="#12b76a" />
          脚本生成完成，共 {{ scriptStructure.length }} 个章节
        </div>

        <!-- 失败 -->
        <div v-if="generateError && !generating" class="state-row state-error">
          <van-icon name="warning-o" size="15" />
          {{ generateError }}
        </div>

        <button v-if="!generating" class="btn-action"
          :class="scriptGenerated ? 'btn-outline' : 'btn-green'"
          @click="handleGenerateScript">
          <van-icon :name="scriptGenerated ? 'replay' : 'star-o'" size="16" />
          {{ scriptGenerated ? '重新生成' : '开始生成脚本' }}
        </button>
      </div>

      <!-- 脚本预览（章节折叠列表） -->
      <div v-if="scriptGenerated && scriptStructure.length" class="card">
        <div class="card-head" style="margin-bottom:12px">
          <div class="card-icon" style="background:#f5f0ff">
            <van-icon name="orders-o" size="20" color="#7c3aed" />
          </div>
          <div>
            <strong>讲解脚本预览</strong>
            <p>点击章节展开查看内容</p>
          </div>
        </div>

        <div class="script-list">
          <div v-for="item in scriptStructure" :key="item.id" class="script-item">
            <button class="script-header" @click="toggleSection(item.id)">
              <van-icon
                :name="openSections.has(item.id) ? 'arrow-down' : 'arrow'"
                size="13" color="#9aa3b2" />
              <span class="script-name">{{ item.sectionName }}</span>
              <span v-if="item.keyPoints.length" class="script-kp-badge">
                {{ item.keyPoints.length }} 要点
              </span>
            </button>

            <div v-if="openSections.has(item.id)" class="script-body">
              <p class="script-content">{{ item.content }}</p>
              <template v-if="item.keyPoints.length">
                <p class="kp-label">关键要点</p>
                <ul class="kp-list">
                  <li v-for="point in item.keyPoints" :key="point">{{ point }}</li>
                </ul>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- 发布成功提示 -->
      <div v-if="published" class="published-banner">
        <van-icon name="checked" size="18" color="#12b76a" />
        智课已成功发布！
      </div>

      <!-- 底部操作 -->
      <div class="bottom-bar">
        <button class="btn-ghost" style="flex:0 0 auto;width:80px" @click="flowStep = 'parse'">
          <van-icon name="arrow-left" size="15" />
          返回
        </button>

        <div class="action-group">
          <button class="action-btn-sm btn-outline" :disabled="!scriptGenerated" @click="goEditScript">
            <van-icon name="edit" size="14" />
            编辑脚本
          </button>
          <button class="action-btn-sm btn-blue-sm" :disabled="!scriptGenerated" @click="goPreview">
            <van-icon name="play-circle-o" size="14" />
            预览智课
          </button>
          <button class="action-btn-sm btn-green-sm"
            :disabled="!scriptGenerated || publishing || published"
            :class="{ done: published }"
            @click="handlePublish">
            <van-loading v-if="publishing" size="14px" color="#fff" />
            <van-icon v-else-if="published" name="checked" size="14" />
            <van-icon v-else name="send-gift-o" size="14" />
            {{ published ? '已发布' : publishing ? '发布中' : '发布智课' }}
          </button>
        </div>
      </div>

    </template>

  </div>
</template>

<style scoped>
.create-root {
  padding: 0 14px 120px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* ══ 进度条 ═════════════════════════════════════════════════ */
.stepper {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  background: #f4f6fa;
  padding: 14px 0 10px;
  margin: 0 -14px;
  padding-left: 14px;
  padding-right: 14px;
}

.stepper-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.stepper-dot {
  width: 26px; height: 26px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  background: #dde3ee;
  color: #9aa3b2;
  transition: all 0.2s;
}

.stepper-item.is-active .stepper-dot {
  background: #1677ff;
  color: #fff;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.18);
}

.stepper-item.is-done .stepper-dot {
  background: #12b76a;
  color: #fff;
}

.stepper-label {
  font-size: 11px;
  font-weight: 600;
  color: #b0b9c8;
  white-space: nowrap;
}

.stepper-item.is-active .stepper-label { color: #1677ff; }
.stepper-item.is-done  .stepper-label { color: #12b76a; }

.stepper-line {
  flex: 1;
  height: 2px;
  background: #dde3ee;
  margin: 0 6px;
  margin-bottom: 16px;
  border-radius: 2px;
  transition: background 0.2s;
}

.stepper-line.is-done { background: #12b76a; }

/* ══ 卡片 ════════════════════════════════════════════════════ */
.card {
  background: #fff;
  border-radius: 20px;
  padding: 18px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.card-icon {
  width: 44px; height: 44px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.card-head > div:not(.card-icon) strong {
  display: block;
  font-size: 15px; font-weight: 700; color: #1a2035;
  margin-bottom: 3px;
}

.card-head > div:not(.card-icon) p { margin: 0; font-size: 12px; color: #9aa3b2; }

/* ══ 上传区 ══════════════════════════════════════════════════ */
.upload-zone {
  border: 2px dashed #e4e8ef;
  border-radius: 16px;
  padding: 28px 16px;
  display: flex; flex-direction: column;
  align-items: center; gap: 8px;
  cursor: pointer;
  background: #fafbfd;
  transition: all 0.18s;
}
.upload-zone:active { opacity: 0.7; }
.upload-zone.has-file { border-color: #12b76a; background: #f8fffa; }
.upload-hint { margin: 0; font-size: 14px; font-weight: 600; color: #6b7a90; }
.upload-sub  { font-size: 11px; color: #b0b9c8; }

.file-preview {
  display: flex; align-items: center; gap: 12px; width: 100%;
}
.file-ext {
  width: 44px; height: 44px; border-radius: 12px;
  background: linear-gradient(135deg,#1677ff,#46aaff);
  color: #fff; font-size: 11px; font-weight: 800;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.file-info { flex: 1; min-width: 0; }
.file-info strong {
  display: block; font-size: 14px; font-weight: 700; color: #1a2035;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-info span { font-size: 12px; color: #9aa3b2; }

/* ══ 表单 ════════════════════════════════════════════════════ */
.form-group { margin-bottom: 16px; }
.form-label {
  display: block; font-size: 13px; font-weight: 700;
  color: #3d4a5f; margin-bottom: 8px;
}
.req { color: #f53f3f; margin-left: 2px; }
.opt { color: #9aa3b2; font-weight: 400; }

.form-field { background: #f5f7fa; border-radius: 12px; padding: 0 14px; }
.form-field--ta { padding: 10px 14px; }

.cover-picker {
  width: 100%;
  height: 92px;
  border-radius: 14px;
  border: 1.5px dashed #d9e1ec;
  background: #fafbfd;
  color: #6b7a90;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
}

.cover-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 14px;
  overflow: hidden;
  background: #f5f7fa;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  color: #fff;
  background: rgba(15, 23, 42, 0.58);
  display: flex;
  align-items: center;
  justify-content: center;
}

.style-list { display: flex; flex-direction: column; gap: 8px; }
.style-item {
  display: flex; flex-direction: column; align-items: flex-start;
  padding: 12px 14px; border-radius: 14px;
  border: 1.5px solid #e4e8ef; background: #fff;
  text-align: left; cursor: pointer; transition: all 0.15s;
}
.style-item strong { font-size: 14px; font-weight: 700; color: #1a2035; margin-bottom: 3px; }
.style-item p { margin: 0; font-size: 12px; color: #9aa3b2; }
.style-item.active { border-color: #1677ff; background: linear-gradient(135deg,#f0f6ff,#e8f0ff); }
.style-item.active strong { color: #1677ff; }

/* ══ 状态行 ══════════════════════════════════════════════════ */
.state-row {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: 12px;
  font-size: 13px; font-weight: 500;
  margin-bottom: 14px;
}
.state-info   { background: #f4f6fa; color: #6b7a90; }
.state-active { background: #eff6ff; color: #1677ff; }
.state-success{ background: #f0fdf4; color: #059669; }
.state-error  { background: #fff5f5; color: #f53f3f; }

/* ══ 操作按钮 ════════════════════════════════════════════════ */
.btn-action {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; height: 44px; border-radius: 12px; border: none;
  font-size: 14px; font-weight: 700; cursor: pointer; transition: all 0.15s;
}
.btn-blue  { background: linear-gradient(135deg,#1677ff,#2a8aff); color:#fff;
             box-shadow: 0 6px 18px rgba(22,119,255,0.28); }
.btn-green { background: linear-gradient(135deg,#059669,#10b981); color:#fff;
             box-shadow: 0 6px 18px rgba(5,150,105,0.28); }
.btn-outline {
  background: #f5f7fa; color: #3d4a5f;
  border: 1.5px solid #e4e8ef !important;
}
.btn-action:active { opacity: 0.8; transform: scale(0.98); }

/* ══ 章节树 ══════════════════════════════════════════════════ */
.tree-list { display: flex; flex-direction: column; gap: 4px; }

.tree-chapter { border-radius: 12px; overflow: hidden; border: 1.5px solid #e8ecf2; }

.tree-chapter-row {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 12px 14px;
  background: #fafbfd; border: none; text-align: left; cursor: pointer;
}
.tree-chapter-label { flex: 1; font-size: 13.5px; font-weight: 700; color: #1a2035; }
.tree-badge {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px;
  background: #eef4ff; color: #1677ff;
}

.tree-children { padding: 6px 14px 10px 30px; background: #fff; }
.tree-child-row {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 5px 0; border-bottom: 1px solid #f0f2f5;
}
.tree-child-row:last-child { border-bottom: none; }
.tree-child-dot {
  width: 5px; height: 5px; border-radius: 50%; background: #1677ff;
  margin-top: 6px; flex-shrink: 0;
}
.tree-child-label { font-size: 13px; color: #4b5563; line-height: 1.6; }

/* ══ 脚本列表 ════════════════════════════════════════════════ */
.script-list { display: flex; flex-direction: column; gap: 8px; }

.script-item {
  border-radius: 14px; border: 1.5px solid #e4e8ef; overflow: hidden;
  transition: border-color 0.15s;
}

.script-header {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 13px 14px;
  background: #fafbfd; border: none; text-align: left; cursor: pointer;
}
.script-name { flex: 1; font-size: 13.5px; font-weight: 700; color: #1a2035; }
.script-kp-badge {
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px;
  background: #f5f0ff; color: #7c3aed;
}

.script-body {
  padding: 12px 14px 14px;
  border-top: 1px solid #f0f2f5;
  background: #fff;
}
.script-content {
  font-size: 13px; line-height: 1.8; color: #374151; margin-bottom: 10px;
}
.kp-label {
  font-size: 11px; font-weight: 700; color: #9aa3b2;
  letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 7px;
}
.kp-list { list-style: none; display: flex; flex-direction: column; gap: 5px; margin: 0; padding: 0; }
.kp-list li {
  display: flex; align-items: flex-start; gap: 7px;
  font-size: 13px; color: #4b5563; line-height: 1.6;
}
.kp-list li::before {
  content: '•'; color: #1677ff; font-size: 10px; margin-top: 4px; flex-shrink: 0;
}

/* ══ 发布成功横幅 ════════════════════════════════════════════ */
.published-banner {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 14px; border-radius: 14px;
  background: #f0fdf4; border: 1.5px solid #bbf7d0;
  font-size: 14px; font-weight: 700; color: #059669;
}

/* ══ 底部操作栏 ══════════════════════════════════════════════ */
.bottom-bar {
  position: fixed;
  bottom: 60px; /* 避开底部 tab bar */
  left: 0; right: 0;
  padding: 12px 16px;
  background: rgba(255,255,255,0.96);
  backdrop-filter: blur(10px);
  border-top: 1px solid #eef0f5;
  display: flex; align-items: center; gap: 10px;
  z-index: 100;
}

.bottom-bar.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.btn-primary {
  flex: 1;
  display: flex; align-items: center; justify-content: center; gap: 6px;
  height: 50px; border-radius: 14px; border: none;
  background: linear-gradient(135deg,#1677ff,#2a8aff);
  color: #fff; font-size: 15px; font-weight: 800; cursor: pointer;
  box-shadow: 0 6px 20px rgba(22,119,255,0.30);
  transition: transform 0.15s, box-shadow 0.15s;
}
.btn-primary:active { transform: scale(0.97); box-shadow: 0 3px 10px rgba(22,119,255,0.2); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; transform: none !important; box-shadow: none !important; }

.btn-ghost {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  height: 50px; border-radius: 14px;
  background: #f5f7fa; border: 1.5px solid #e4e8ef;
  color: #6b7a90; font-size: 14px; font-weight: 700; cursor: pointer;
}
.btn-ghost:active { opacity: 0.7; }

/* 三个操作按钮组 */
.action-group {
  flex: 1;
  display: flex; gap: 8px;
}

.action-btn-sm {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 3px;
  height: 50px; border-radius: 12px; border: none;
  font-size: 12px; font-weight: 700; cursor: pointer;
  transition: all 0.15s;
}
.action-btn-sm:disabled { opacity: 0.38; cursor: not-allowed; }
.action-btn-sm:active:not(:disabled) { transform: scale(0.96); }

.btn-outline.action-btn-sm {
  background: #f5f7fa; color: #3d4a5f;
  border: 1.5px solid #e4e8ef !important;
}
.btn-blue-sm {
  background: linear-gradient(135deg,#1677ff,#2a8aff);
  color: #fff;
  box-shadow: 0 4px 12px rgba(22,119,255,0.25);
}
.btn-green-sm {
  background: linear-gradient(135deg,#059669,#10b981);
  color: #fff;
  box-shadow: 0 4px 12px rgba(5,150,105,0.25);
}
.btn-green-sm.done {
  background: #ecfdf3;
  color: #059669;
  box-shadow: none;
  border: 1.5px solid #bbf7d0 !important;
}

/* 重新上传链接 */
.link-btn {
  all: unset; cursor: pointer;
  font-size: 13px; font-weight: 600; color: #1677ff;
  padding: 4px 8px; border-radius: 8px;
  background: #eef4ff;
  flex-shrink: 0;
}
.link-btn:active { opacity: 0.7; }
</style>
