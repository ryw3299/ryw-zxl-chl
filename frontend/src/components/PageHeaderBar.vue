<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  statusText: {
    type: String,
    default: '',
  },
  statusType: {
    type: String,
    default: 'info',
  },
  breadcrumbs: {
    type: Array,
    default: () => [],
  },
})

const router = useRouter()

const onCrumbClick = (item) => {
  if (!item || !item.to) {
    return
  }
  router.push(item.to)
}
</script>

<template>
  <div class="page-header-bar">
    <div class="header-main">
      <nav v-if="breadcrumbs.length" class="breadcrumbs" aria-label="Breadcrumb">
        <template v-for="(item, index) in breadcrumbs" :key="`${item.label}-${index}`">
          <button
            v-if="item.to && !item.current"
            class="crumb crumb-link"
            type="button"
            @click="onCrumbClick(item)"
          >
            {{ item.label }}
          </button>
          <span v-else class="crumb" :class="{ current: item.current }">{{ item.label }}</span>
          <span v-if="index < breadcrumbs.length - 1" class="crumb-sep">/</span>
        </template>
      </nav>

      <div class="title-row">
        <h1 class="title">{{ title }}</h1>
        <el-tag v-if="statusText" size="small" :type="statusType" effect="plain">{{ statusText }}</el-tag>
      </div>

      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>

    <div class="header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.header-main {
  min-width: 0;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #7b90a5;
}

.crumb {
  color: inherit;
}

.crumb-link {
  all: unset;
  cursor: pointer;
  color: #4a6a8a;
}

.crumb-link:hover {
  color: #1f72d9;
}

.crumb.current {
  color: #2b3f54;
  font-weight: 600;
}

.crumb-sep {
  color: #9db0c2;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  margin: 0;
  color: #1f344a;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 7px 0 0;
  color: #6f8194;
  font-size: 14px;
  line-height: 1.7;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
