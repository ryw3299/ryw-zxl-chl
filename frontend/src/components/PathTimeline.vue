<template>
  <div class="path-timeline">
    <el-timeline>
      <el-timeline-item
        v-for="stage in stages"
        :key="stage.stage_index"
        :timestamp="stage.duration"
        placement="top"
        color="#4f46e5"
      >
        <div class="stage-header">
          <h4>阶段{{ stage.stage_index }}：{{ stage.title }}</h4>
        </div>
        <p class="stage-goal">{{ stage.goal }}</p>
        <div v-if="stage.knowledge_points?.length" class="stage-tags">
          <el-tag v-for="kp in stage.knowledge_points" :key="kp" size="small" effect="plain">{{ kp }}</el-tag>
        </div>
        <div v-if="stage.assessment" class="stage-assessment">
          <el-tag type="warning" size="small">验收：{{ stage.assessment }}</el-tag>
        </div>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
defineProps({
  stages: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.path-timeline {
  padding: 16px 0;
}
.stage-header h4 {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}
.stage-goal {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}
.stage-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.stage-assessment {
  margin-top: 4px;
}
</style>
