<script setup>
import { computed } from 'vue'
import { getLessonPreviewImageUrl } from '@/api/lesson'

const props = defineProps({
  lessonId: {
    type: String,
    required: true,
  },
  fileName: {
    type: String,
    default: 'Untitled Lesson',
  },
  totalPages: {
    type: Number,
    default: 1,
  },
  currentPage: {
    type: Number,
    default: 1,
  },
  highlightPages: {
    type: Array,
    default: () => [],
  },
  sectionTitle: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:currentPage'])

const safeCurrentPage = computed(() => {
  const page = Number(props.currentPage || 1)
  const max = Number(props.totalPages || 1)
  return Math.min(Math.max(1, page), max)
})

const canPrev = computed(() => safeCurrentPage.value > 1)
const canNext = computed(() => safeCurrentPage.value < Number(props.totalPages || 1))

const slideUrl = computed(() => {
  return getLessonPreviewImageUrl(props.lessonId, safeCurrentPage.value)
})

const goToPage = (page) => {
  const next = Number(page)
  if (!Number.isFinite(next) || next < 1 || next > Number(props.totalPages || 1)) {
    return
  }
  emit('update:currentPage', next)
}

const goPrev = () => {
  if (canPrev.value) {
    goToPage(safeCurrentPage.value - 1)
  }
}

const goNext = () => {
  if (canNext.value) {
    goToPage(safeCurrentPage.value + 1)
  }
}

const isHighlighted = (page) => props.highlightPages.includes(page)
</script>

<template>
  <el-card class="viewer-card" shadow="never">
    <template #header>
      <div class="viewer-header">
        <div class="header-title">
          <div class="file-name">{{ fileName }}</div>
          <div class="section-title">{{ sectionTitle || 'Current Section' }}</div>
        </div>
        <el-tag type="info" effect="plain">Page {{ safeCurrentPage }} / {{ totalPages }}</el-tag>
      </div>
    </template>

    <div class="preview-box">
      <img :src="slideUrl" class="ppt-image" />
    </div>

    <div class="viewer-actions">
      <el-button :disabled="!canPrev" @click="goPrev">Prev</el-button>
      <el-button type="primary" :disabled="!canNext" @click="goNext">Next</el-button>
    </div>

    <div class="page-list">
      <button
        v-for="page in totalPages"
        :key="page"
        class="page-chip"
        :class="{
          active: page === safeCurrentPage,
          highlight: isHighlighted(page),
        }"
        @click="goToPage(page)"
      >
        {{ page }}
      </button>
    </div>
  </el-card>
</template>

<style scoped>
.viewer-card {
  border: 1px solid #e6ebf2;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.header-title {
  min-width: 0;
}

.file-name {
  font-size: 16px;
  font-weight: 600;
  color: #243447;
}

.section-title {
  margin-top: 4px;
  color: #607d8b;
  font-size: 13px;
}

.preview-box {
  background: linear-gradient(135deg, #f7fbff, #f2f6fc);
  border: 1px dashed #bfd0ea;
  border-radius: 10px;
  min-height: 290px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.ppt-image {
  width: 100%;
  max-height: 480px;
  object-fit: contain;
  border-radius: 8px;
}

.viewer-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.page-list {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
  gap: 8px;
}

.page-chip {
  border: 1px solid #dbe5f1;
  background: #fff;
  color: #44596e;
  border-radius: 8px;
  padding: 6px 0;
  cursor: pointer;
  font-size: 13px;
}

.page-chip.highlight {
  border-color: #8eb7eb;
  background: #eef5ff;
}

.page-chip.active {
  border-color: #409eff;
  color: #1f6fb2;
  font-weight: 600;
}
</style>
