<script setup>
import {inject, onMounted, ref} from 'vue'
import HeadNavi from '@/components/utils/HeadNavi.vue'
import StudentSideNavi from '@/components/MyAcademyPage/StudentSideNavi.vue'
import MainPage from '@/views/MainPage.vue'
import QAChat from '@/components/MyAcademyPage/QAChat.vue'
import ResourceChat from '@/components/MyAcademyPage/ResourceChat.vue'
import ImageChat from '@/components/MyAcademyPage/ImageChat.vue'
import GoToLearning from '@/components/MyAcademyPage/GoToLearning.vue'
import LearningProgress from '@/components/MyAcademyPage/LearningProgress.vue'
import ProblemHistory from '@/components/MyAcademyPage/ProblemHistory.vue'
import DevelopingPage from '@/components/MyAcademyPage/DevelopingPage.vue'
import AIEvaluation from '@/components/MyAcademyPage/AIEvaluation.vue'
import EmotionRecord from '@/components/UseCenterPage/EmotionRecord.vue'
import MyAcademyPage from '@/views/MyAcademy/MyAcademyPage.vue'
import StudentDemoPage from '@/views/StudentDemoPage.vue'

const windowWidth = inject('windowWidth')
const showAside = ref(true)
const activeTab = ref('home')

const rescaleElement = () => {
  showAside.value = !windowWidth?.value || windowWidth.value >= 800
}

onMounted(() => {
  rescaleElement()
  window.addEventListener('resize', rescaleElement)
})

const handleSwitchTab = (tabName) => {
  activeTab.value = tabName
}
</script>

<template>
  <el-container class="student-shell">
    <el-header class="student-shell-header">
      <HeadNavi />
    </el-header>
    <el-container class="student-shell-body">
      <el-aside v-show="showAside" class="student-shell-aside">
        <StudentSideNavi :active-tab="activeTab" @switch-tab="handleSwitchTab" />
      </el-aside>
      <el-main class="student-shell-main">
        <MainPage v-if="activeTab === 'home'" />
        <QAChat v-else-if="activeTab === 'qa'" />
        <ResourceChat v-else-if="activeTab === 'resources'" />
        <ImageChat v-else-if="activeTab === 'images'" />
        <GoToLearning v-else-if="activeTab === 'learning'" />
        <LearningProgress v-else-if="activeTab === 'progress'" />
        <ProblemHistory v-else-if="activeTab === 'problem'" />
        <DevelopingPage v-else-if="activeTab === 'graph'" />
        <AIEvaluation v-else-if="activeTab === 'evaluation'" />
        <div v-else-if="activeTab === 'emotion'" class="emotion-placeholder">
          <el-card shadow="hover">
            <div class="Space-Between-Flex" style="margin-left: 12px; margin-right: 12px">
              <el-text style="font-weight: bold; font-size: 16px">你的任何一丝小情绪都被我们时刻关注着✨~</el-text>
            </div>
            <el-divider style="margin-top: 16px; margin-bottom: 16px" />
            <el-empty description="暂无情绪记录" />
          </el-card>
        </div>
        <MyAcademyPage v-else-if="activeTab === 'courses'" />
        <MainPage v-else-if="activeTab === 'public'" />
        <StudentDemoPage v-else-if="activeTab === 'knowledge'" />
        <DevelopingPage v-else />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.student-shell {
  height: 100vh;
  width: 100vw;
}
.student-shell-header {
  padding: 0;
  height: 56px;
}
.student-shell-body {
  min-height: 0;
}
.student-shell-aside {
  width: 240px;
  border-right: 1px solid var(--el-border-color-light);
  background: oklch(0.98 0.005 278);
  overflow-y: auto;
}
.student-shell-main {
  min-width: 0;
  height: 100%;
  padding: 22px 28px 40px;
  overflow: auto;
  background: oklch(0.975 0.008 278);
}
.emotion-placeholder {
  padding: 32px;
  max-width: 1024px;
  margin: 0 auto;
  border: #8080FF 1px solid;
  border-radius: 8px;
  box-shadow: #8080FF 0 0 4px;
  background: var(--el-bg-color);
}
</style>