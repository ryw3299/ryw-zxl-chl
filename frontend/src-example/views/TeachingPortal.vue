<script setup>
import {ref, onMounted, inject} from 'vue'
import TeachSideNavi from "@/components/TeachingActivity/utils/TeachSideNavi.vue"
import HeadNavi from "@/components/utils/HeadNavi.vue"
import TeachOverview from "@/views/TeachingPortal/TeachOverview.vue"
import DevelopingPage from "@/components/MyAcademyPage/DevelopingPage.vue"

const windowWidth = inject('windowWidth')
const showAside = ref(true)
const activeTab = ref('overview')

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
  <el-container class="teacher-shell">
    <el-header class="teacher-shell-header">
      <HeadNavi />
    </el-header>
    <el-container class="teacher-shell-body">
      <el-aside v-show="showAside" class="teacher-shell-aside">
        <TeachSideNavi :active-tab="activeTab" @switch-tab="handleSwitchTab" />
      </el-aside>
      <el-main class="teacher-shell-main">
        <TeachOverview v-if="activeTab === 'overview'" />
        <DevelopingPage v-else />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.teacher-shell {
  height: 100vh;
  width: 100vw;
}
.teacher-shell-header {
  padding: 0;
  height: 56px;
}
.teacher-shell-body {
  min-height: 0;
}
.teacher-shell-aside {
  width: 240px;
  border-right: 1px solid var(--el-border-color-light);
  background: oklch(0.98 0.005 278);
  overflow-y: auto;
}
.teacher-shell-main {
  min-width: 0;
  height: 100%;
  padding: 22px 28px 40px;
  overflow: auto;
  background: oklch(0.975 0.008 278);
}
</style>