<script setup>
import { computed, ref } from 'vue'
import { adjustProgress } from '@/api/progress'

const props = defineProps({
  courseId: {
    type: String,
    default: '',
  },
  lessonId: {
    type: String,
    default: '',
  },
  sectionId: {
    type: String,
    default: '',
  },
  currentSectionTitle: {
    type: String,
    default: '未开始章节',
  },
  overallProgress: {
    type: Number,
    default: 0,
  },
  understandingLevel: {
    type: String,
    default: '待评估',
  },
  recommendedActions: {
    type: Array,
    default: () => ['继续当前章节', '补充讲解', '加快节奏'],
  },
})

const emit = defineEmits(['adjusted'])
const loadingAction = ref('')

const levelType = computed(() => {
  if (props.understandingLevel.includes('良好') || props.understandingLevel.includes('深入')) {
    return 'success'
  }
  if (props.understandingLevel.includes('待')) {
    return 'info'
  }
  return 'warning'
})

const handleAdjust = async (action) => {
  loadingAction.value = action
  try {
    const result = await adjustProgress({
      courseId: props.courseId,
      lessonId: props.lessonId,
      sectionId: props.sectionId,
      action,
    })
    emit('adjusted', result)
  } finally {
    loadingAction.value = ''
  }
}
</script>

<template>
  <el-card class="progress-card" shadow="never">
    <template #header>
      <span>学习进度与节奏建议</span>
    </template>

    <div class="progress-item">
      <span class="label">当前章节</span>
      <strong>{{ currentSectionTitle }}</strong>
    </div>

    <div class="progress-item">
      <span class="label">总体进度</span>
      <el-progress :percentage="overallProgress" :stroke-width="12" />
    </div>

    <div class="progress-item">
      <span class="label">理解程度</span>
      <el-tag :type="levelType">{{ understandingLevel }}</el-tag>
    </div>

    <div class="progress-item">
      <span class="label">后续动作建议</span>
      <div class="action-list">
        <el-button
          v-for="action in recommendedActions"
          :key="action"
          size="small"
          :loading="loadingAction === action"
          @click="handleAdjust(action)"
        >
          {{ action }}
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.progress-card {
  border: 1px solid #e6ebf2;
}

.progress-item + .progress-item {
  margin-top: 14px;
}

.label {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 12px;
  color: #647689;
}

.action-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
