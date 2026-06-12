<script setup>
import {inject, onMounted, ref, watch} from "vue";
import axios from "axios";
import {StarFilled} from "@element-plus/icons-vue";
import AITextLong from "@/components/utils/AITextLong.vue";
import {backendUrl} from "@/assets/static/js/severConfig.js";
import {useAuth} from "@/assets/static/js/useAuth.js"

const {user} = useAuth();

const isActivityReady = ref(false)
const isProgressReady = ref(false)
const isEmotionReady = ref(false)

const progress = ref([])
const fetchProgress = async () => {
  axios.get(backendUrl + 'student/course/progress/' + user.value.ident).then(res => {
    progress.value = res.data
    isProgressReady.value = true
  }).catch(err => {
    console.log(err)
  })
}

const activity = ref([])
const fetchActivity = async () => {
  axios.get(backendUrl + 'student/activity/' + user.value.ident).then(res => {
    activity.value = res.data
    isActivityReady.value = true
  }).catch(err => {
    console.log(err)
  })
}

const emotion = ref('')
const fetchEmotion = async () => {
  axios.get(backendUrl + 'student/emotion/status/' + user.value.ident).then(res => {
    emotion.value = res.data.message
    isEmotionReady.value = true
  }).catch(err => {
    console.log(err)
  })
}

onMounted(async () => {
  await fetchProgress()
  await fetchActivity()
  await fetchEmotion()
})
</script>

<template>
  <div style="height: 720px">
    <el-scrollbar>
      <el-divider content-position="left">
        <el-text style="font-size: 22px">
          AI评估
        </el-text>
      </el-divider>
      <div class="Center-Flex">
        <el-button type="primary" :icon="StarFilled">让小慧重新生成一份~</el-button>
      </div>
      <AITextLong
          style="margin-top: 36px; margin-left: 8px; margin-right: 8px;"
          v-if="isActivityReady&&isProgressReady&&isEmotionReady"
          :prompt="'以下是我的各课学习进度：' + JSON.stringify(progress)
          + '以下是我的每日学习时长' + JSON.stringify(activity)
          + '以下是我的当前情绪活跃度（范围0-100）' + emotion +
          '请你根据这些数据，结合我的情绪活跃度，总结评估我的学习情况，并为我提出个性化学习方案，回复的时候请使用Markdown格式进行排版. 并进行标题分级，内容尽量详细充实。'"/>
      <div class="Center-Flex" style="flex-direction: column; margin-top: 24px">
        <el-text>你对小慧为你定制的学习计划感到满意吗？</el-text>
        <n-rate allow-half />
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>

</style>
