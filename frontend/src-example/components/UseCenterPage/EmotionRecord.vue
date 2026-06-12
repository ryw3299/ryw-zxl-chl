<script setup>
import {onMounted, ref} from "vue";
import axios from "axios";
import {ElMessage} from "element-plus";
import EmotionCard from "@/components/UseCenterPage/EmotionRecord/EmotionCard.vue";
import {backendUrl} from "@/assets/static/js/severConfig.js";
import {useAuth} from "@/assets/static/js/useAuth.js"

const {user} = useAuth();

const emotionRecord = ref([])

onMounted(async () => {
  if (!user.value) return
  try {
    const res = await axios.get(backendUrl + 'student/emotion/' + user.value.id)
    emotionRecord.value = res.data
  } catch (err) {
    // demo模式：使用mock数据
    emotionRecord.value = [
      { id: 1, emotion: '开心', score: 85, time: '2026-05-20 09:30', description: '今天学习效率很高，完成了3道练习题' },
      { id: 2, emotion: '平静', score: 60, time: '2026-05-19 14:20', description: '按计划完成了今日学习任务' },
      { id: 3, emotion: '焦虑', score: 35, time: '2026-05-18 20:10', description: '明天有考试，有点紧张' },
      { id: 4, emotion: '兴奋', score: 90, time: '2026-05-17 16:45', description: 'AI评估报告出来了，学习进步明显！' },
      { id: 5, emotion: '疲惫', score: 40, time: '2026-05-16 21:30', description: '连续学习4小时，需要休息一下' },
    ]
  }
})
</script>

<template>
  <div class="emotion-wrapper">
    <el-card shadow="hover">
      <div class="Space-Between-Flex" style="margin-left: 12px; margin-right: 12px">
        <el-text style="font-weight: bold; font-size: 16px">你的任何一丝小情绪都被我们时刻关注着✨~</el-text>
      </div>
      <el-divider style="margin-top: 16px; margin-bottom: 16px" />
      <div style="height: 640px">
        <el-scrollbar>
          <EmotionCard
              v-for="record in emotionRecord"
              :key="record.id"
              :emotion-record="record"
              style="margin-bottom: 12px"
          />
        </el-scrollbar>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.emotion-wrapper {
  padding: 32px;
  max-width: 1024px;
  margin: 0 auto;
  border: #8080FF 1px solid;
  border-radius: 8px;
  box-shadow: #8080FF 0 0 4px;
  background: var(--el-bg-color);
}
</style>