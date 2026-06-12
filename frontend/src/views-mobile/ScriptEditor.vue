<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { showToast, showLoadingToast, closeToast, showConfirmDialog } from 'vant'
import { editScript, getScriptStatus, renderLessonPpt } from '@/api/lesson'
import { useLessonStore } from '@/store/lessonStore'

const route = useRoute()
const router = useRouter()
const lessonStore = useLessonStore()

const normalizeQuery = (v, d = '') => (Array.isArray(v) ? v[0] || d : (typeof v === 'string' && v ? v : d))

const scriptId = computed(() => normalizeQuery(route.query.scriptId))
const lessonId = computed(() => normalizeQuery(route.query.lessonId))

const loading = ref(false)
const saving = ref(false)
const sections = ref([])
const activeIdx = ref(0)
const savedSignature = ref('')
const newKeyPoint = ref('')

const current = computed(() => sections.value[activeIdx.value] || null)
const dirty = computed(() => JSON.stringify(sections.value) !== savedSignature.value)

const fallbackSections = [
  { sectionId: 'sec001', sectionName: '开场导入', content: '欢迎来到本节课程。先建立学习目标，再进入核心内容。', keyPoints: ['学习目标', '课程结构'] },
  { sectionId: 'sec002', sectionName: '核心内容讲解', content: '本部分围绕关键概念展开，通过例子建立认知连接。', keyPoints: ['关键概念', '示例讲解'] },
  { sectionId: 'sec003', sectionName: '总结与延伸', content: '回顾重点并引导学生提出延伸问题。', keyPoints: ['重点回顾', '延伸问题'] },
]

const normalizeSections = (list = []) => list.map((item, i) => ({
  sectionId: item.sectionId || `sec${String(i + 1).padStart(3, '0')}`,
  sectionName: item.sectionName || item.title || `章节 ${i + 1}`,
  content: item.content || item.explainScript || '',
  keyPoints: [...(item.keyPoints || item.keywords || [])],
}))

const loadScript = async () => {
  loading.value = true
  try {
    if (scriptId.value) {
      const result = await getScriptStatus(scriptId.value)
      const remote = normalizeSections(result.scriptStructure || [])
      if (remote.length) {
        sections.value = remote
      } else if (lessonStore.lessonInfo.sections?.length) {
        sections.value = normalizeSections(lessonStore.lessonInfo.sections)
      } else {
        sections.value = normalizeSections(fallbackSections)
      }
    } else if (lessonStore.lessonInfo.sections?.length) {
      sections.value = normalizeSections(lessonStore.lessonInfo.sections)
    } else {
      sections.value = normalizeSections(fallbackSections)
    }
    savedSignature.value = JSON.stringify(sections.value)
  } catch {
    showToast('脚本加载失败，已载入示例内容')
    sections.value = normalizeSections(fallbackSections)
    savedSignature.value = JSON.stringify(sections.value)
  } finally {
    loading.value = false
  }
}

const addKeyPoint = () => {
  const text = newKeyPoint.value.trim()
  if (!text || !current.value) return
  if (current.value.keyPoints.includes(text)) {
    showToast('该关键词已存在')
    newKeyPoint.value = ''
    return
  }
  current.value.keyPoints.push(text)
  newKeyPoint.value = ''
}

const removeKeyPoint = (i) => {
  if (current.value) current.value.keyPoints.splice(i, 1)
}

const handleSave = async () => {
  if (!sections.value.length) return
  if (saving.value) return
  saving.value = true
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    if (scriptId.value) {
      await editScript({
        scriptId: scriptId.value,
        scriptStructure: sections.value.map((s) => ({
          sectionId: s.sectionId,
          sectionName: (s.sectionName || '').trim() || '未命名章节',
          content: s.content,
          duration: Math.max(15, Math.round((s.content || '').length / 6)),
          relatedChapterId: s.sectionId,
          keyPoints: s.keyPoints.map((p) => p.trim()).filter(Boolean),
        })),
      })
      if (lessonId.value) await renderLessonPpt(lessonId.value)
    }
    lessonStore.setLessonInfo({
      sections: sections.value.map((s) => ({
        sectionId: s.sectionId,
        title: s.sectionName,
        explainScript: s.content,
        keywords: s.keyPoints,
      })),
    })
    savedSignature.value = JSON.stringify(sections.value)
    closeToast()
    showToast({ message: scriptId.value ? '已保存，PPT 已触发重新渲染' : '已保存', type: 'success' })
  } catch {
    closeToast()
    showToast('保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const handleBack = async () => {
  if (dirty.value) {
    try {
      await showConfirmDialog({
        title: '尚未保存',
        message: '离开将丢失未保存的修改，确定返回？',
        confirmButtonText: '返回',
        cancelButtonText: '继续编辑',
      })
    } catch {
      return
    }
  }
  router.back()
}

onBeforeRouteLeave(async (to, from) => {
  if (!dirty.value) return true
  try {
    await showConfirmDialog({
      title: '尚未保存',
      message: '离开将丢失未保存的修改，确定离开？',
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑',
    })
    return true
  } catch {
    return false
  }
})

onMounted(loadScript)
</script>

<template>
  <div class="editor-root">
    <!-- 顶部栏 -->
    <van-nav-bar
      title="脚本编辑"
      left-text="返回"
      left-arrow
      fixed
      placeholder
      safe-area-inset-top
      @click-left="handleBack"
    >
      <template #right>
        <van-button
          type="primary"
          size="small"
          :loading="saving"
          :disabled="!dirty || loading"
          @click="handleSave"
        >
          {{ dirty ? '保存' : '已保存' }}
        </van-button>
      </template>
    </van-nav-bar>

    <div v-if="loading" class="editor-loading">
      <van-loading color="#1677ff" size="28" />
      <p>加载脚本中…</p>
    </div>

    <template v-else>
      <!-- 章节横向 tab -->
      <div class="section-tabs">
        <button
          v-for="(sec, i) in sections"
          :key="sec.sectionId"
          class="section-tab"
          :class="{ 'is-active': i === activeIdx }"
          @click="activeIdx = i"
        >
          <span class="section-tab__index">{{ i + 1 }}</span>
          <span class="section-tab__name">{{ sec.sectionName || '未命名' }}</span>
        </button>
      </div>

      <!-- 当前章节编辑区 -->
      <div v-if="current" class="editor-panel">
        <div class="field-group">
          <label class="field-label">章节名称</label>
          <van-field
            v-model="current.sectionName"
            placeholder="请输入章节名称"
            :border="false"
            class="sec-name-input"
          />
        </div>

        <div class="field-group">
          <label class="field-label">
            讲解脚本
            <span class="field-tip">{{ (current.content || '').length }} 字</span>
          </label>
          <van-field
            v-model="current.content"
            type="textarea"
            :rows="8"
            autosize
            :border="false"
            placeholder="请输入该章节的讲解脚本内容"
            class="sec-content-input"
          />
        </div>

        <div class="field-group">
          <label class="field-label">
            核心关键词
            <span class="field-tip">{{ current.keyPoints.length }} 项</span>
          </label>
          <div class="keypoint-list">
            <span
              v-for="(kp, i) in current.keyPoints"
              :key="`${kp}-${i}`"
              class="keypoint-chip"
            >
              {{ kp }}
              <van-icon name="cross" size="12" @click="removeKeyPoint(i)" />
            </span>
            <p v-if="!current.keyPoints.length" class="keypoint-empty">尚未添加关键词</p>
          </div>
          <div class="keypoint-add">
            <van-field
              v-model="newKeyPoint"
              placeholder="添加关键词（回车或点击 + 确认）"
              :border="false"
              class="keypoint-input"
              @keydown.enter="addKeyPoint"
            />
            <button class="keypoint-add-btn" :disabled="!newKeyPoint.trim()" @click="addKeyPoint">
              <van-icon name="plus" size="18" />
            </button>
          </div>
        </div>
      </div>

      <!-- 底部保存按钮（容易触达） -->
      <div class="bottom-bar">
        <van-button
          block
          round
          type="primary"
          :loading="saving"
          :disabled="!dirty"
          @click="handleSave"
        >
          {{ dirty ? '保存修改' : '已保存' }}
        </van-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.editor-root {
  position: relative;
  min-height: 100dvh;
  background: linear-gradient(180deg, #f5f8fd 0%, #eef3fb 100%);
  padding-bottom: calc(24px + env(safe-area-inset-bottom, 0px));
}

.editor-loading {
  padding: 80px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  color: #6b7a90;
}

/* ── 章节 tab ── */
.section-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
  scrollbar-width: none;
}
.section-tabs::-webkit-scrollbar { display: none; }

.section-tab {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1.5px solid #e5e8f0;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  max-width: 160px;
}
.section-tab__index {
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #e5e8f0;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.section-tab__name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}
.section-tab.is-active {
  background: linear-gradient(135deg, #1677ff, #46aaff);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 4px 14px rgba(22, 119, 255, 0.3);
}
.section-tab.is-active .section-tab__index {
  background: rgba(255, 255, 255, 0.3);
  color: #fff;
}

/* ── 编辑面板 ── */
.editor-panel {
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-group {
  background: #fff;
  border-radius: 14px;
  padding: 14px 14px 6px;
  box-shadow: 0 2px 10px rgba(22, 119, 255, 0.05);
}

.field-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #1a2035;
  margin-bottom: 6px;
}
.field-tip {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
}

.sec-name-input :deep(.van-field__control),
.sec-content-input :deep(.van-field__control) {
  font-size: 14px;
  color: #1a2035;
  line-height: 1.7;
}
.sec-content-input :deep(.van-field__control) {
  min-height: 120px;
}

/* ── 关键词 ── */
.keypoint-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
  padding: 6px 0 4px;
  min-height: 28px;
}
.keypoint-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 4px 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #eef4ff, #f5f0ff);
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid rgba(22, 119, 255, 0.15);
}
.keypoint-chip .van-icon {
  cursor: pointer;
  padding: 3px;
  border-radius: 50%;
  background: rgba(22, 119, 255, 0.12);
  transition: background 0.15s;
}
.keypoint-chip .van-icon:active { background: rgba(245, 63, 63, 0.2); color: #f53f3f; }
.keypoint-empty {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

.keypoint-add {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e5e8f0;
}
.keypoint-input {
  flex: 1;
  background: #f5f7fa;
  border-radius: 10px;
  padding: 4px 8px;
}
.keypoint-input :deep(.van-field__control) {
  font-size: 13px;
}
.keypoint-add-btn {
  width: 36px; height: 36px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #1677ff, #46aaff);
  color: #fff;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: opacity 0.15s;
}
.keypoint-add-btn:disabled {
  background: #e5e8f0;
  color: #94a3b8;
  cursor: not-allowed;
}

/* ── 底部保存 ── */
.bottom-bar {
  position: sticky;
  bottom: 0;
  padding: 12px 14px calc(16px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(180deg, transparent, rgba(238, 243, 251, 0.9) 30%, #eef3fb);
  z-index: 5;
}
</style>
