<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

const router = useRouter()

// ── tabs ──────────────────────────────────────────────
const activeTab = ref('list')  // 'list' | 'upload'

// ── 资源列表（示例数据） ────────────────────────────────
const resources = ref([
  { id: 1, title: '数据结构课程参考书', course: '数据结构与算法', type: 'PDF',  size: '8.2 MB', date: '2026-04-15' },
  { id: 2, title: '线性代数补充习题集', course: '人工智能导论',   type: 'DOCX', size: '1.4 MB', date: '2026-04-10' },
  { id: 3, title: 'Python 实战代码包',  course: 'Python 程序设计', type: 'ZIP',  size: '12.5 MB', date: '2026-04-08' },
])

const typeIcon  = { PPTX: '📊', PPT: '📊', PDF: '📄', ZIP: '📦', DOCX: '📝', MP4: '🎬', PNG: '🖼', JPG: '🖼', XLS: '📑', XLSX: '📑' }
const typeColor = { PPTX: '#7c3aed', PPT: '#7c3aed', PDF: '#f53f3f', ZIP: '#f59e0b', DOCX: '#2563eb', MP4: '#059669' }

// ── 上传资源表单 ───────────────────────────────────────
const courses = ['人工智能导论', '机器学习基础', '数据结构与算法', 'Python 程序设计', '高等数学', '线性代数']

const selectedCourse  = ref('')
const showCoursePicker = ref(false)
const courseColumns = courses.map(c => ({ text: c, value: c }))
const resourceName    = ref('')
const uploadedFile    = ref(null)
const fileInputRef    = ref(null)
const uploading       = ref(false)

const fileExt  = computed(() => uploadedFile.value?.name.split('.').pop().toUpperCase() ?? '')
const fileSize = computed(() => {
  const s = uploadedFile.value?.size ?? 0
  return s > 1024 * 1024 ? `${(s / 1024 / 1024).toFixed(1)} MB` : `${(s / 1024).toFixed(0)} KB`
})

const canSubmit = computed(() =>
  Boolean(selectedCourse.value && resourceName.value.trim() && uploadedFile.value)
)

const onFilePick = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 200 * 1024 * 1024) { showToast('文件不能超过 200MB'); return }
  uploadedFile.value = file
  if (!resourceName.value) resourceName.value = file.name.replace(/\.[^.]+$/, '')
}

const removeFile = () => {
  uploadedFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

const handleUpload = async () => {
  if (!canSubmit.value || uploading.value) return
  uploading.value = true
  // TODO: 接入真实上传 API
  await new Promise(r => setTimeout(r, 1200))
  resources.value.unshift({
    id: Date.now(),
    title: resourceName.value.trim(),
    course: selectedCourse.value,
    type: fileExt.value || 'FILE',
    size: fileSize.value,
    date: new Date().toISOString().slice(0, 10),
  })
  uploading.value   = false
  selectedCourse.value = ''
  resourceName.value   = ''
  uploadedFile.value   = null
  if (fileInputRef.value) fileInputRef.value.value = ''
  activeTab.value = 'list'
  showToast({ message: '资源上传成功', type: 'success', duration: 1400 })
}
</script>

<template>
  <div class="tr-page">

    <!-- 顶栏 -->
    <div class="tr-topbar">
      <button class="tr-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <span class="tr-topbar-title">课程资源管理</span>
      <div style="width:36px" />
    </div>

    <!-- Tab 切换 -->
    <div class="tr-tabs">
      <button class="tr-tab" :class="{ active: activeTab === 'list' }"   @click="activeTab = 'list'">
        <van-icon name="description" size="14" /> 资源库
      </button>
      <button class="tr-tab" :class="{ active: activeTab === 'upload' }" @click="activeTab = 'upload'">
        <van-icon name="plus" size="14" /> 上传资源
      </button>
    </div>

    <!-- ───── 资源列表 ───── -->
    <div v-if="activeTab === 'list'" class="tr-list-wrap">
      <div v-if="!resources.length" class="tr-empty">
        <van-icon name="description" size="40" color="#c5cdd8" />
        <p>暂无资源，点击「上传课件」添加</p>
      </div>
      <div v-for="item in resources" :key="item.id" class="tr-res-card">
        <div class="tr-res-icon" :style="{ background: (typeColor[item.type] || '#1677ff') + '18', color: typeColor[item.type] || '#1677ff' }">
          <span>{{ typeIcon[item.type] || '📎' }}</span>
          <em>{{ item.type }}</em>
        </div>
        <div class="tr-res-body">
          <div class="tr-res-title">{{ item.title }}</div>
          <div class="tr-res-course">{{ item.course }}</div>
          <div class="tr-res-meta">
            <span>{{ item.size }}</span>
            <span>{{ item.date }}</span>
          </div>
        </div>
        <van-icon name="ellipsis" size="16" color="#c5cdd8" />
      </div>
    </div>

    <!-- ───── 上传资源 ───── -->
    <div v-else class="tr-upload-wrap">

      <!-- 选择课程 -->
      <div class="tr-section">
        <p class="tr-section-title">选择课程 <span class="req">*</span></p>
        <div class="tr-picker-field" @click="showCoursePicker = true">
          <span :class="selectedCourse ? 'tr-picker-val' : 'tr-picker-ph'">
            {{ selectedCourse || '请选择课程' }}
          </span>
          <van-icon name="arrow-down" size="14" color="#9aa3b2" />
        </div>
      </div>

      <!-- 课程 Picker 弹层 -->
      <van-popup v-model:show="showCoursePicker" position="bottom" round>
        <van-picker
          :columns="courseColumns"
          :default-index="courseColumns.findIndex(c => c.value === selectedCourse)"
          show-toolbar
          title="选择课程"
          confirm-button-text="确认"
          cancel-button-text="取消"
          @confirm="({ selectedValues }) => { selectedCourse = selectedValues[0]; showCoursePicker = false }"
          @cancel="showCoursePicker = false"
        />
      </van-popup>

      <!-- 资料名称 -->
      <div class="tr-section">
        <p class="tr-section-title">资料名称 <span class="req">*</span></p>
        <van-field
          v-model="resourceName"
          placeholder="例如：第三章补充习题、参考教材 PDF"
          class="tr-input" :border="false"
        />
      </div>

      <!-- 上传文件 -->
      <div class="tr-section">
        <p class="tr-section-title">上传资料文件 <span class="req">*</span></p>
        <label v-if="!uploadedFile" class="tr-upload-zone" @click="fileInputRef?.click()">
          <van-icon name="plus" size="28" color="#1677ff" />
          <span class="tr-upload-main">点击选择资料文件</span>
          <span class="tr-upload-sub">支持 PDF / DOCX / PPT / ZIP / 图片 · 最大 200 MB</span>
          <input ref="fileInputRef" type="file" style="display:none" @change="onFilePick" />
        </label>
        <div v-else class="tr-file-card">
          <div class="tr-file-type-badge">{{ fileExt }}</div>
          <div class="tr-file-info">
            <span class="tr-file-name">{{ uploadedFile.name }}</span>
            <span class="tr-file-size">{{ fileSize }}</span>
          </div>
          <button class="tr-file-remove" @click="removeFile">
            <van-icon name="cross" size="14" />
          </button>
        </div>
      </div>

      <!-- 提交 -->
      <button
        class="tr-btn tr-btn--publish"
        :disabled="!canSubmit || uploading"
        @click="handleUpload"
      >
        <van-loading v-if="uploading" size="16px" color="#fff" />
        <van-icon v-else name="upgrade" size="16" />
        {{ uploading ? '上传中...' : '上传到资源库' }}
      </button>

    </div>

    <div style="height:32px" />
  </div>
</template>

<style scoped>
.tr-page {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, sans-serif;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

/* 顶栏 */
.tr-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
  position: sticky; top: 0; z-index: 10;
}
.tr-back {
  width: 36px; height: 36px; border: none; background: #f5f7fa;
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  color: #1a2035; cursor: pointer;
}
.tr-topbar-title { font-size: 17px; font-weight: 800; color: #1a2035; }

/* Tab */
.tr-tabs {
  display: flex;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
  padding: 0 14px;
  gap: 4px;
}
.tr-tab {
  display: flex; align-items: center; gap: 5px;
  padding: 12px 16px;
  border: none; background: transparent;
  font-size: 14px; font-weight: 600; color: #9aa3b2;
  cursor: pointer; border-bottom: 2px solid transparent;
  transition: all 0.15s;
}
.tr-tab.active { color: #1677ff; border-bottom-color: #1677ff; }

/* ── 资源列表 ── */
.tr-list-wrap { padding: 14px; display: flex; flex-direction: column; gap: 10px; }

.tr-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 60px 0; gap: 10px;
  color: #9aa3b2; font-size: 13px; text-align: center;
}

.tr-res-card {
  display: flex; align-items: center; gap: 12px;
  background: #fff; border-radius: 16px;
  padding: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.tr-res-icon {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
}
.tr-res-icon span { font-size: 20px; line-height: 1; }
.tr-res-icon em { font-style: normal; font-size: 8px; font-weight: 800; letter-spacing: 0.04em; }
.tr-res-body { flex: 1; min-width: 0; }
.tr-res-title { font-size: 14px; font-weight: 700; color: #1a2035; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tr-res-course { font-size: 11px; color: #1677ff; font-weight: 600; margin-top: 2px; }
.tr-res-meta { display: flex; gap: 10px; margin-top: 4px; }
.tr-res-meta span { font-size: 11px; color: #9aa3b2; }

/* ── 上传表单 ── */
.tr-upload-wrap { padding: 14px; display: flex; flex-direction: column; gap: 14px; }

/* 文件类型徽标 */
.tr-file-type-badge {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  background: linear-gradient(135deg,#1677ff,#46aaff);
  color: #fff; font-size: 10px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
}

/* Section */
.tr-section {
  background: #fff; border-radius: 18px;
  padding: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  display: flex; flex-direction: column; gap: 14px;
}
.tr-section-title { margin: 0 0 2px; font-size: 14px; font-weight: 800; color: #1a2035; }

.tr-field { display: flex; flex-direction: column; gap: 7px; }
.tr-field label { font-size: 12px; font-weight: 700; color: #6b7a90; }
.req { color: #f53f3f; }

.tr-input {
  background: #f5f7fa; border-radius: 12px;
  padding: 0 4px;
}
.tr-textarea { min-height: 70px; }

.tr-presets { display: flex; flex-wrap: wrap; gap: 7px; }
.tr-preset-chip {
  padding: 5px 12px; border-radius: 999px; border: 1.5px solid #e4e8ef;
  font-size: 12px; font-weight: 600; color: #6b7a90; background: #f5f7fa;
  cursor: pointer; transition: all 0.15s;
}
.tr-preset-chip.active { background: #eef4ff; border-color: #93c5fd; color: #1677ff; }

/* 上传区 */
.tr-upload-zone {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  min-height: 130px; border: 2px dashed #d4e4ff; border-radius: 16px;
  background: #f8fbff; cursor: pointer; transition: border-color 0.2s;
}
.tr-upload-zone:active { border-color: #1677ff; }
.tr-upload-main { font-size: 14px; font-weight: 700; color: #1677ff; }
.tr-upload-sub  { font-size: 12px; color: #9aa3b2; }

.tr-file-card {
  display: flex; align-items: center; gap: 12px;
  background: #f5f0ff; border-radius: 14px; padding: 12px 14px;
}
.tr-file-info { flex: 1; min-width: 0; }
.tr-file-name { display: block; font-size: 13px; font-weight: 700; color: #1a2035; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tr-file-size { font-size: 11px; color: #9aa3b2; }
.tr-file-remove { border: none; background: transparent; cursor: pointer; padding: 4px; color: #9aa3b2; }


/* Picker 触发框 */
.tr-picker-field {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 16px; border-radius: 12px;
  background: #f5f7fa; cursor: pointer;
  transition: background 0.15s;
}
.tr-picker-field:active { background: #eef1f6; }
.tr-picker-val { font-size: 14px; font-weight: 600; color: #1a2035; }
.tr-picker-ph  { font-size: 14px; color: #b0b9c8; }

/* 按钮 */
.tr-btn {
  display: flex; align-items: center; justify-content: center; gap: 5px;
  padding: 9px 16px; border-radius: 12px; border: none;
  font-size: 13px; font-weight: 700; cursor: pointer;
  white-space: nowrap; transition: all 0.15s;
  flex-shrink: 0;
}
.tr-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.tr-btn--primary { background: #1677ff; color: #fff; box-shadow: 0 4px 12px rgba(22,119,255,0.3); }
.tr-btn--purple  { background: #7c3aed; color: #fff; box-shadow: 0 4px 12px rgba(124,58,237,0.3); }
.tr-btn--success { background: #059669; color: #fff; }
.tr-btn--publish {
  width: 100%; padding: 14px; border-radius: 14px; font-size: 15px;
  background: linear-gradient(135deg, #1677ff, #2a8aff);
  color: #fff; box-shadow: 0 6px 20px rgba(22,119,255,0.32);
  gap: 8px;
}
</style>
