<script setup>
import {inject, onMounted, ref, watch, onBeforeUnmount} from "vue";
import {useThemeVars} from "naive-ui";
import AIOpinion from "@/components/utils/AIOpinion.vue";
import * as echarts from "echarts/core";

const themeVars = useThemeVars()

const progress = ref([
  { cname: "人工智能导论", progress: 78 },
  { cname: "数据结构与算法", progress: 62 },
  { cname: "计算机网络", progress: 45 },
  { cname: "操作系统", progress: 33 },
])
const progressValue = ref([78, 62, 45, 33])

const activity = ref([
  { date: "05-14", time: 120 },
  { date: "05-15", time: 90 },
  { date: "05-16", time: 150 },
  { date: "05-17", time: 80 },
  { date: "05-18", time: 200 },
  { date: "05-19", time: 170 },
  { date: "05-20", time: 140 },
])

const course_progress = progress.value
const learning_activity = activity.value

const isDark = inject('isDark')
const chartContainer = ref(null)
let myChart = null

const initChart = ()=>{
  if(!chartContainer.value) return
  if(isDark.value) {
    myChart = echarts.init(chartContainer.value, 'dark');
  }
  else {
    myChart = echarts.init(chartContainer.value, 'light');
  }

  let xData = []
  let yValue = []
  for (let i = 0; i < activity.value.length; i++) {
    xData.push(activity.value[i].date)
    yValue.push(activity.value[i].time)
  }
  let option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['总学习时长']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    toolbox: {
      feature: {
        saveAsImage: {}
      }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xData
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '总学习时长',
        type: 'line',
        stack: '总量',
        data: yValue
      }
    ]
  };
  myChart.setOption(option);
}

onMounted(()=>{
  initChart()
  watch(isDark, (newVal) => {
    if(myChart) myChart.dispose()
    setTimeout(() => {
      initChart()
    }, 200)
  })

  window.addEventListener('resize', () => {
    myChart?.resize()
  })
})

onBeforeUnmount(()=>{
  myChart?.dispose()
})
</script>

<template>
  <div id="course-div">
    <el-divider content-position="left">
      <el-text style="font-size: 22px">
        学习进度
      </el-text>
    </el-divider>
    <div id="course-container">
      <div class="Space-Between-Flex">
        <div style="width: 70%">
          <div style="display:flex; margin-bottom: 12px; margin-left: 24px; margin-right: 24px"
               v-for="item in progress">
            <el-text size="large" style="width:160px; white-space: nowrap">
              {{ item.cname }}：
            </el-text>
            <n-progress
                type="line"
                :indicator-placement="'inside'"
                :height="24"
                :status="item.progress > 80 ? 'success' : item.progress>60 ? 'default': item.progress > 40? 'warning':'error'"
                :percentage="item.progress"
                processing
            />
          </div>
        </div>
        <div style="width: 30%; height:100%;" class="Center-Flex">
          <n-progress
              type="multiple-circle"
              processing
              :stroke-width="6"
              :circle-gap="0.5"
              :percentage="progressValue"
              :color="[
                        themeVars.successColor,
                        themeVars.infoColor,
                        themeVars.warningColor,
                        themeVars.errorColor
                      ]"
              :rail-style="[
                        { stroke: themeVars.successColor, opacity: 0.3 },
                        { stroke: themeVars.infoColor, opacity: 0.3 },
                        { stroke: themeVars.warningColor, opacity: 0.3 },
                        { stroke: themeVars.errorColor, opacity: 0.3 }
                      ]"
          >
            <el-text type="primary" size="large">学习圆环</el-text>
          </n-progress>
        </div>
      </div>
      <AIOpinion
          style="margin-top: 36px"
          :prompt="'以下是我的各课学习进度，给我来点一句简短的建议：' + JSON.stringify(course_progress)"/>
    </div>
  </div>
  <div id="course-div" style="margin-bottom: 24px; margin-right: 12px; margin-left: 12px">
    <el-divider content-position="left">
      <el-text style="font-size: 22px">
        学习活动
      </el-text>
    </el-divider>
    <div id="info-container" class="Center-Flex" style="width: 100%">
      <div ref="chartContainer"
           style="width: 92%; height: 360px; margin-top: 24px;
                     box-shadow: 0 0 8px #8080ff; border-radius: 8px"></div>
    </div>
    <AIOpinion
        style="margin-top: 36px; margin-right: 24px"
        :prompt="'以下是我的各课学习时长，给我来点一句简短的建议：' + JSON.stringify(learning_activity)"/>
  </div>
</template>

<style scoped>

</style>