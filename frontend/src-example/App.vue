<script setup>
import { onMounted, provide, ref } from 'vue'
import { NConfigProvider, darkTheme } from 'naive-ui'
import { useDark } from '@vueuse/core'
import { particleOption } from '@/assets/static/js/particleOption.js'

const windowWidth = ref(window.innerWidth)
const windowHeight = ref(window.innerHeight)
const isDark = useDark()
const showParticles = ref(true)
const showAssistant = ref(false)

provide('windowWidth', windowWidth)
provide('windowHeight', windowHeight)
provide('isDark', isDark)
provide('showParticles', showParticles)
provide('showAssistant', showAssistant)

const rescaleElement = () => {
  windowWidth.value = window.innerWidth
  windowHeight.value = window.innerHeight
}

onMounted(() => {
  rescaleElement()
  window.addEventListener('resize', rescaleElement)
})

const themeOverrides = {
  common: {
    primaryColor: '#8080ff',
    infoColor: '#8080ff',
    successColor: 'var(--el-color-success)',
    warningColor: 'var(--el-color-warning)',
    errorColor: 'var(--el-color-error)',
  },
}

const darkThemeOverrides = {
  common: {
    primaryColor: '#8080ff',
    infoColor: '#8080ff',
  },
}
</script>

<template>
  <n-config-provider
    class="app-shell"
    :theme-overrides="isDark ? darkThemeOverrides : themeOverrides"
    :theme="isDark ? darkTheme : null"
  >
    <RouterView />
  </n-config-provider>

  <vue-particles
    v-if="showParticles"
    id="tsparticles"
    :options="particleOption"
  />
</template>

<style scoped>
.app-shell {
  position: relative;
  z-index: 2;
  height: 100vh;
  width: 100vw;
  overflow: auto;
}

#tsparticles {
  position: fixed;
  margin: 0;
  padding: 0;
  left: 0;
  top: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
}
</style>
