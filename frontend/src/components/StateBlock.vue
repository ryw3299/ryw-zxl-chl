<script setup>
const props = defineProps({
  mode: {
    type: String,
    default: 'empty', // empty | loading | error
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
  actionText: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['action'])

const iconMap = {
  empty: '○',
  loading: '…',
  error: '!',
}

const onAction = () => {
  emit('action')
}
</script>

<template>
  <div class="state-block" :class="`is-${mode}`" role="status" aria-live="polite">
    <div class="state-icon">{{ iconMap[mode] || iconMap.empty }}</div>
    <h3 class="state-title">{{ title }}</h3>
    <p v-if="description" class="state-desc">{{ description }}</p>
    <el-button v-if="actionText" type="primary" plain @click="onAction">{{ actionText }}</el-button>
  </div>
</template>

<style scoped>
.state-block {
  min-height: 220px;
  border-radius: 14px;
  border: 1px dashed #d7e3ef;
  background: #fbfdff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 10px;
  padding: 20px;
}

.state-icon {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}

.state-title {
  margin: 0;
  font-size: 17px;
  color: #2b3f54;
}

.state-desc {
  max-width: 480px;
  margin: 0;
  font-size: 13px;
  line-height: 1.75;
  color: #70859a;
}

.is-empty .state-icon {
  background: #edf3fb;
  color: #7f95ab;
}

.is-loading .state-icon {
  background: #ebf5ff;
  color: #2f78d6;
}

.is-error .state-icon {
  background: #ffeef0;
  color: #e14b64;
}
</style>
