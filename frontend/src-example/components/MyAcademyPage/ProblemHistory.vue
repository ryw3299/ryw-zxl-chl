<script setup>

import {onMounted, ref} from "vue";
import ProblemHistoryCard from "@/components/MyAcademyPage/ProblemHistory/ProblemHistoryCard.vue";

const problemHistory = ref([
  { pid: 1, type: "简答", title: "请简述深度学习与传统机器学习的区别", difficulty: 72, importance: 85, innovation: 60, holistic: 75, score: 88, time: "2026-05-18" },
  { pid: 2, type: "选择", title: "以下哪个不是常见的激活函数？", difficulty: 45, importance: 70, innovation: 30, holistic: 55, score: 100, time: "2026-05-17" },
  { pid: 3, type: "简答", title: "解释反向传播算法的原理", difficulty: 80, importance: 95, innovation: 50, holistic: 78, score: 72, time: "2026-05-15" },
  { pid: 4, type: "选择", title: "卷积神经网络中池化层的作用是？", difficulty: 35, importance: 60, innovation: 20, holistic: 45, score: 90, time: "2026-05-14" },
  { pid: 5, type: "简答", title: "什么是过拟合？如何避免？", difficulty: 55, importance: 80, innovation: 40, holistic: 65, score: 65, time: "2026-05-12" },
])

</script>

<template>
  <div style="height: 720px">
    <el-scrollbar>
      <el-divider content-position="left">
        <el-text style="font-size: 22px">
          做题历史
        </el-text>
      </el-divider>
      <div class="glowing-container" style="margin-top: 36px; max-height: 740px" >
        <el-scrollbar>
          <ProblemHistoryCard
              v-for="ph in problemHistory"
              :problemHistory="ph"
              style="margin-bottom: 24px"
          />
        </el-scrollbar>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>

</style>