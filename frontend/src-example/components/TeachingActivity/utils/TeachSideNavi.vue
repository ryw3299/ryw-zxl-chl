<script setup>
import {
  DataAnalysis,
  FolderOpened,
  HomeFilled,
  Reading,
  SetUp,
} from "@element-plus/icons-vue";

const props = defineProps({
  activeTab: { type: String, default: 'overview' }
})
const emit = defineEmits(['switchTab'])

const onMenuSelect = (index) => {
  emit('switchTab', index)
}
</script>

<template>
    <el-card style="height: 100%">
      <el-menu
          :default-openeds="[]"
          :default-active="props.activeTab"
          @select="onMenuSelect">
        <el-menu-item index="overview">
          <el-icon><HomeFilled/></el-icon>
          <template #title>教学总览</template>
        </el-menu-item>
        <el-sub-menu index="prep">
          <template #title>
            <el-icon><SetUp/></el-icon>
            <span>备课助手</span>
          </template>
          <el-menu-item index="prep-qa">智能问答</el-menu-item>
          <el-menu-item index="prep-smart">智慧备课</el-menu-item>
          <el-menu-item index="prep-image">图片生成</el-menu-item>
          <el-menu-item index="prep-ppt">创作PPT</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="smart-class">
          <template #title>
            <el-icon><Reading/></el-icon>
            <span>智课管理</span>
          </template>
          <el-menu-item index="smart-overview">课程总览</el-menu-item>
          <el-menu-item index="smart-workshop">智课工坊</el-menu-item>
          <el-menu-item index="smart-script">讲稿精修</el-menu-item>
          <el-menu-item index="smart-resource">课程资源</el-menu-item>
          <el-menu-item index="smart-publish">发布管理</el-menu-item>
          <el-menu-item index="smart-analysis">学情分析</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="data">
          <el-icon><DataAnalysis/></el-icon>
          <template #title>数据中台</template>
        </el-menu-item>
        <el-sub-menu index="resource">
          <template #title>
            <el-icon><FolderOpened/></el-icon>
            <span>课程资源平台</span>
          </template>
          <el-menu-item index="resource-my">我的课程</el-menu-item>
          <el-menu-item index="resource-public">公开资源</el-menu-item>
          <el-menu-item index="resource-lib">知识库</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-card>
</template>

<style scoped>

</style>