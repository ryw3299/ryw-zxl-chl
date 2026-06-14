<template>
  <div class="radar-wrapper">
    <div ref="chartRef" class="radar-chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dimensions: {
    type: Array,
    default: () => [],
  },
  height: {
    type: Number,
    default: 360,
  },
})

const chartRef = ref(null)
let chartInstance = null

function renderChart() {
  if (!chartRef.value || !props.dimensions.length) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const indicators = props.dimensions.map((d) => ({
    name: d.name,
    max: 100,
  }))

  chartInstance.setOption({
    radar: {
      indicator: indicators,
      center: ['50%', '50%'],
      radius: '65%',
      axisName: {
        color: '#475569',
        fontSize: 12,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(79, 70, 229, 0.02)', 'rgba(79, 70, 229, 0.05)'],
        },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.dimensions.map((d) => d.score),
            name: '当前画像',
            areaStyle: {
              color: 'rgba(79, 70, 229, 0.2)',
            },
            lineStyle: {
              color: '#4f46e5',
              width: 2,
            },
            itemStyle: {
              color: '#4f46e5',
            },
          },
        ],
      },
    ],
    tooltip: {
      trigger: 'item',
    },
  })
}

onMounted(() => {
  renderChart()
})

watch(() => props.dimensions, renderChart, { deep: true })

onBeforeUnmount(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.radar-wrapper {
  width: 100%;
}
.radar-chart {
  width: 100%;
  height: v-bind('height + "px"');
}
</style>
