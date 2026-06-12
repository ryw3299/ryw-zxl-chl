<script setup>
/**
 * visual thesis: 延续首页的雾面浅色工作台，用单一空态块承接未完成模块，避免碎片化卡片。
 * content plan: 顶部导航 -> 模块标题 -> 单一空态说明 -> 主按钮。
 * interaction plan: 页面淡入，主按钮轻微上浮，空态区使用轻量 slide-fade。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const title = computed(() => route.meta?.title || '移动端模块')
const description = computed(() => route.meta?.description || '该模块正在移动端适配中。')
</script>

<template>
  <div class="mobile-placeholder">
    <van-nav-bar fixed placeholder :title="title" />

    <main class="mobile-placeholder__main">
      <transition appear name="placeholder-fade">
        <section class="placeholder-panel">
          <span class="placeholder-kicker">MOBILE WORKSPACE</span>
          <h1>{{ title }}</h1>
          <p>{{ description }}</p>
          <van-empty image="search" description="当前先开放学生首页与核心导航结构" />
          <van-button block round type="primary" @click="router.push('/m')">
            返回学生首页
          </van-button>
        </section>
      </transition>
    </main>
  </div>
</template>

<style scoped>
.mobile-placeholder {
  min-height: 100%;
}

.mobile-placeholder__main {
  padding: 16px 16px 28px;
}

.placeholder-panel {
  padding: 28px 20px;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 247, 251, 0.96)),
    #fff;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
}

.placeholder-kicker {
  display: inline-flex;
  margin-bottom: 14px;
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #5b6b84;
}

.placeholder-panel h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.05;
  color: #102a43;
}

.placeholder-panel p {
  margin: 12px 0 20px;
  font-size: 14px;
  line-height: 1.75;
  color: #5b6b84;
}

.placeholder-panel :deep(.van-empty) {
  padding: 18px 0 22px;
}

.placeholder-panel :deep(.van-button) {
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #175cd3, #2e90fa);
  border: none;
}

.placeholder-fade-enter-active,
.placeholder-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.placeholder-fade-enter-from,
.placeholder-fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
