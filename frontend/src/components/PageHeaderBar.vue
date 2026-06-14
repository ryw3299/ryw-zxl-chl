<template>
  <div class="page-header">
    <div class="header-left">
      <h2>{{ title }}</h2>
      <span v-if="subtitle" class="subtitle">{{ subtitle }}</span>
    </div>
    <div class="header-right">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  subtitle: String,
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.subtitle {
  font-size: 13px;
  color: #94a3b8;
}
</style>
