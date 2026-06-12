<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const shellClass = computed(() => route.meta?.shellClass || 'app-shell--pc')
</script>

<template>
  <div :class="['app-shell', shellClass]">
    <router-view v-slot="{ Component }">
      <transition name="shell-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style>
:root {
  color-scheme: light;
  --app-bg: #f5f6f8;
  --app-text: #1d2129;
  --app-muted: #6b7785;
  --app-radius: 6px;
  --app-border: #dfe1e6;
  --app-primary: #3370ff;
  --app-primary-strong: #245bdb;
  --app-mobile-bg: #f5f6f8;
  --app-mobile-surface: #fffffe;
  --app-mobile-soft: #f7f8fa;
  --app-mobile-line: rgba(29, 33, 41, 0.1);
  --app-mobile-shadow: 0 1px 3px rgba(29, 33, 41, 0.06);
}

* {
  box-sizing: border-box;
}

html {
  background: var(--app-bg);
}

body {
  margin: 0;
  font-family: "PingFang SC", "MiSans", "Microsoft YaHei", "Hiragino Sans GB", "Noto Sans CJK SC",
    sans-serif;
  color: var(--app-text);
  background: var(--app-bg);
}

#app {
  min-height: 100dvh;
}

.app-shell {
  min-height: 100vh;
}

.app-shell--auth {
  min-height: 100vh;
  padding: 0;
  background: var(--app-bg);
}

.app-shell--mobile,
html:has(.app-shell--mobile) {
  overscroll-behavior: none;
}
html:has(.app-shell--mobile),
body:has(.app-shell--mobile) {
  height: 100dvh;
  overflow: hidden;
}

.app-shell--pc {
  padding: 16px;
}

.app-shell--mobile {
  padding: 0;
  height: 100dvh;
  min-height: 100dvh;
  overflow: hidden;
  background: var(--app-mobile-bg);
}

button,
.el-button {
  border-radius: var(--app-radius);
}

@media (min-width: 768px) {
  .app-shell--mobile {
    width: min(100%, 430px);
    margin: 0 auto;
    height: 100dvh;
    min-height: 100dvh;
    box-shadow:
      0 0 0 1px rgba(126, 147, 182, 0.12),
      0 10px 30px rgba(29, 33, 41, 0.08);
  }
}

.shell-fade-enter-active,
.shell-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.shell-fade-enter-from,
.shell-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
