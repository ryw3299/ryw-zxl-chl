<script setup>
import {
  ChatLineRound,
  FolderOpened,
  HomeFilled,
  MagicStick,
  Reading,
} from "@element-plus/icons-vue";

const props = defineProps({
  activeTab: { type: String, default: 'home' }
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
        <el-menu-item index="home">
          <el-icon><HomeFilled/></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-sub-menu index="assistant">
          <template #title>
            <el-icon><ChatLineRound/></el-icon>
            <span>学习助手</span>
          </template>
          <el-menu-item index="qa">智能问答</el-menu-item>
          <el-menu-item index="resources">资源推荐</el-menu-item>
          <el-menu-item index="images">图片生成</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="learning-group">
          <template #title>
            <el-icon><Reading/></el-icon>
            <span>我的智课</span>
          </template>
          <el-menu-item index="learning">前往学习</el-menu-item>
          <el-menu-item index="progress">学习进度</el-menu-item>
          <el-menu-item index="problem">做题历史</el-menu-item>
          <el-menu-item index="graph">知识图谱</el-menu-item>
          <el-menu-item index="evaluation">AI评估</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="emotion">
          <el-icon><MagicStick/></el-icon>
          <template #title>情绪记录</template>
        </el-menu-item>
        <el-sub-menu index="courses-group">
          <template #title>
            <el-icon><FolderOpened/></el-icon>
            <span>课程资源平台</span>
          </template>
          <el-menu-item index="courses">我的课程</el-menu-item>
          <el-menu-item index="public">公共课程</el-menu-item>
          <el-menu-item index="knowledge">知识库</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-card>
</template>

<style scoped>

</style>