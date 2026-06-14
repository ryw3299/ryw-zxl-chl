<template>
  <div class="authenticated-layout">
    <AppSidebar />
    <div class="layout-main">
      <AppHeader />
      <main class="layout-content">
        <router-view />
      </main>
    </div>
    <AssistantPanel />
  </div>
</template>

<script setup>
import AppSidebar from '@/components/AppSidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import AssistantPanel from '@/components/AssistantPanel.vue'
</script>

<style scoped>
.authenticated-layout {
  display: flex;
  min-height: 100vh;
}

.layout-main {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.layout-content {
  flex: 1;
  padding: 24px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}
</style>
