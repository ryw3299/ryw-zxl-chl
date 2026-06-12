<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const title = computed(() => route.meta?.label || '演示功能')
const description = computed(() => route.meta?.description || '这是一个纯前端演示页面，后续可以接入真实业务能力。')
</script>

<template>
  <section class="demo-page">
    <div class="demo-page-copy">
      <p class="eyebrow">本地演示</p>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div class="demo-panel">
      <el-empty description="此功能当前使用前端占位数据" />
    </div>
  </section>
</template>

<style scoped>
.demo-page {
  min-height: 100%;
  border: 1px solid oklch(0.82 0.07 278);
  border-radius: 14px;
  background: oklch(0.995 0.004 278);
  box-shadow: 0 0 0 1px oklch(0.94 0.03 278), 0 14px 34px oklch(0.62 0.11 278 / 0.12);
  padding: 34px;
}

.demo-page-copy {
  max-width: 720px;
}

.eyebrow {
  margin: 0 0 12px;
  color: oklch(0.55 0.16 278);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

h1 {
  margin: 0 0 12px;
  color: oklch(0.24 0.026 278);
  font-size: 28px;
  line-height: 1.2;
}

p {
  color: oklch(0.42 0.028 278);
  line-height: 1.7;
}

.demo-panel {
  margin-top: 36px;
  min-height: 360px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: oklch(0.975 0.008 278);
}
</style>
