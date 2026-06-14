<template>
  <div class="resource-card" @click="$emit('click')">
    <div class="card-type">
      <el-tag :type="typeTag" size="small">{{ typeLabel }}</el-tag>
    </div>
    <h4 class="card-title">{{ title }}</h4>
    <p class="card-desc">{{ description }}</p>
    <div class="card-meta">
      <el-tag v-if="direction" size="small" effect="plain">{{ direction }}</el-tag>
      <el-tag v-if="difficulty" :type="diffTag" size="small" effect="plain">{{ diffLabel }}</el-tag>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  description: String,
  resourceType: String,
  direction: String,
  difficulty: String,
})

defineEmits(['click'])

const typeLabel = computed(() => {
  const map = { course: '课程', document: '文档', video: '视频', quiz: '题库', project: '项目' }
  return map[props.resourceType] || props.resourceType
})

const typeTag = computed(() => {
  const map = { course: '', document: 'info', video: 'warning', quiz: 'success', project: 'danger' }
  return map[props.resourceType] || ''
})

const diffLabel = computed(() => {
  const map = { beginner: '入门', intermediate: '中级', advanced: '高级' }
  return map[props.difficulty] || props.difficulty
})

const diffTag = computed(() => {
  const map = { beginner: 'success', intermediate: 'warning', advanced: 'danger' }
  return map[props.difficulty] || ''
})
</script>

<style scoped>
.resource-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}
.resource-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}
.card-type {
  margin-bottom: 8px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-desc {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
