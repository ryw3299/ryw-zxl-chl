<script setup>

import {StarFilled} from "@element-plus/icons-vue";
import ProblemCard from "@/components/MyAcademyPage/GoToLearning/ProblemCard.vue";
import {onMounted, ref} from "vue";
import MyCourseCard from "@/components/MyAcademyPage/GoToLearning/MyCourseCard.vue";

const problems = ref([
  { id: 1, cid: 101, type: "简答", title: "请简述深度学习与传统机器学习的区别", difficulty: 72, importance: 85, innovation: 60, holistic: 75 },
  { id: 2, cid: 102, type: "考勤", title: "第三章课堂签到", difficulty: 10, importance: 90, innovation: 5, holistic: 20 },
  { id: 3, cid: 101, type: "选择", title: "以下哪个不是常见的激活函数？", difficulty: 45, importance: 70, innovation: 30, holistic: 55 },
]);

const course = ref([
  { Course_id: 101, name: "人工智能导论", image: "https://picsum.photos/seed/ai101/256/128", description: "涵盖AI基础概念、机器学习与深度学习入门", illustration: "适合零基础同学，配合实验项目理解核心算法" },
  { Course_id: 102, name: "数据结构与算法", image: "https://picsum.photos/seed/ds102/256/128", description: "系统学习常见数据结构及经典算法设计", illustration: "注重编程实践，每周配套在线OJ练习" },
]);

</script>

<template>
  <div id="info-div">
    <el-scrollbar style="width: 100%;margin-top:18px; border: 1px solid #8080ff88; border-radius: 8px; box-shadow: 0 0 3px #8080ff">
      <el-divider content-position="left">
        <el-text style="font-size: 22px">
          推荐题目
        </el-text>
      </el-divider>
      <div id="info-container" style="max-width: 720px">
        <ProblemCard  v-for="problem in problems" :problem="problem"/>
      </div>
    </el-scrollbar>
    <div style="width: 100%; display: flex; justify-content: flex-end; margin-top: 16px">
      <el-button type="primary" :icon="StarFilled">点击让小慧换一组推荐题目</el-button>
    </div>
  </div>
  <div id="course-div">
    <el-scrollbar>
      <el-divider content-position="left">
        <el-text style="font-size: 22px">
          我的课程
        </el-text>
      </el-divider>
      <div id="course-container" style="height: 640px">
        <el-scrollbar>
          <MyCourseCard
              style="margin-bottom: 24px"
              v-for="brief in course"
              :brief="brief"/>
        </el-scrollbar>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>
#info-container {
  display: inline-flex;
  padding: 16px
}
#info-div{
  padding-right: 24px;
  height: 100%;
}
</style>