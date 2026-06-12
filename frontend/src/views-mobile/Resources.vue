<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { loadResourceLibrary } from '@/momo/resourceLibraryData'

const router = useRouter()

const allResources = ref(loadResourceLibrary())
const searchKeyword = ref('')
const selectedCourseId = ref('')

const courseCatalog = [
  { id: '', name: '全部课程', accent: '#1677ff' },
  { id: 'course-1', name: '人工智能导论', accent: '#2563eb' },
  { id: 'course-2', name: '机器学习基础', accent: '#0891b2' },
  { id: 'course-3', name: '数据结构与算法', accent: '#7c3aed' },
  { id: 'course-4', name: 'Python 程序设计', accent: '#059669' },
]

const fileTypeIcon = { PDF: '📄', ZIP: '📦', DOCX: '📝', PPTX: '📊', MP4: '🎬' }

const filteredResources = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  return allResources.value.filter((item) => {
    const matchCourse = !selectedCourseId.value || item.courseId === selectedCourseId.value
    const matchKw = !kw || `${item.title} ${item.description} ${item.courseName}`.toLowerCase().includes(kw)
    return matchCourse && matchKw
  })
})

const selectedCourseAccent = computed(
  () => courseCatalog.find((c) => c.id === selectedCourseId.value)?.accent || '#1677ff',
)
</script>

<template>
  <div class="res-page">

    <!-- 顶栏 -->
    <div class="res-topbar">
      <button class="res-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <span class="res-topbar-title">课程资源</span>
      <div style="width:36px" />
    </div>

    <!-- 搜索栏 -->
    <div class="res-search-wrap">
      <van-search v-model="searchKeyword" placeholder="搜索资源名称或描述" background="transparent" shape="round" />
    </div>

    <!-- 课程筛选 -->
    <div class="res-course-filter">
      <button v-for="course in courseCatalog" :key="course.id" class="res-course-chip"
        :class="{ active: selectedCourseId === course.id }"
        :style="selectedCourseId === course.id ? `--chip-color:${course.accent}` : ''"
        @click="selectedCourseId = course.id">
        {{ course.name }}
      </button>
    </div>

    <!-- 资源列表 -->
    <div class="res-list">
      <div v-if="filteredResources.length === 0" class="res-empty">
        <van-icon name="description" size="40" color="#c5cdd8" />
        <p>暂无匹配资源</p>
      </div>

      <div v-for="item in filteredResources" :key="item.id" class="res-card"
        :style="`--accent:${item.accent || selectedCourseAccent}`">
        <div class="res-card-left">
          <div class="res-type-badge">
            <span class="res-type-icon">{{ fileTypeIcon[item.fileType] || '📎' }}</span>
            <span class="res-type-label">{{ item.fileType }}</span>
          </div>
        </div>
        <div class="res-card-body">
          <div class="res-card-title">{{ item.title }}</div>
          <div class="res-card-course">{{ item.courseName }}</div>
          <p class="res-card-desc">{{ item.description }}</p>
          <div class="res-card-meta">
            <span class="res-meta-item">
              <van-icon name="down" size="11" />
              {{ item.downloadCount }} 次
            </span>
            <span class="res-meta-item">{{ item.fileSize }}</span>
            <span class="res-meta-item">{{ item.uploadedAt?.slice(0, 10) }}</span>
          </div>
          <div class="res-card-tags">
            <span v-for="tag in item.tags" :key="tag" class="res-tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </div>

    <div style="height:28px" />
  </div>
</template>

<style scoped>
.res-page {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, 'Sora', sans-serif;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

/* 顶栏 */
.res-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
  position: sticky;
  top: 0;
  z-index: 10;
}

.res-back {
  width: 36px;
  height: 36px;
  border: none;
  background: #f5f7fa;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1a2035;
  cursor: pointer;
}

.res-topbar-title {
  font-size: 17px;
  font-weight: 800;
  color: #1a2035;
}

/* 搜索 */
.res-search-wrap {
  background: #fff;
  padding: 4px 8px 8px;
  border-bottom: 1px solid #f0f2f5;
}

/* 课程筛选 */
.res-course-filter {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  overflow-x: auto;
  scrollbar-width: none;
}

.res-course-filter::-webkit-scrollbar {
  display: none;
}

.res-course-chip {
  flex-shrink: 0;
  border: none;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: #6b7a90;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.18s;
  white-space: nowrap;
}

.res-course-chip.active {
  color: #fff;
  background: var(--chip-color, #1677ff);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--chip-color, #1677ff) 35%, transparent);
}

/* 资源列表 */
.res-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 14px;
}

.res-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 0;
  gap: 10px;
  color: #9aa3b2;
  font-size: 14px;
}

.res-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #eef1f6;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  border-left: 3px solid var(--accent, #1677ff);
}

.res-card-left {
  flex-shrink: 0;
}

.res-type-badge {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  background: color-mix(in srgb, var(--accent, #1677ff) 10%, white);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
}

.res-type-icon {
  font-size: 18px;
  line-height: 1;
}

.res-type-label {
  font-size: 8px;
  font-weight: 800;
  color: var(--accent, #1677ff);
  letter-spacing: 0.04em;
}

.res-card-body {
  flex: 1;
  min-width: 0;
}

.res-card-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a2035;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.res-card-course {
  margin-top: 2px;
  font-size: 11px;
  color: var(--accent, #1677ff);
  font-weight: 600;
}

.res-card-desc {
  margin: 6px 0 0;
  font-size: 12px;
  color: #6b7a90;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.res-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.res-meta-item {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #9aa3b2;
  font-weight: 500;
}

.res-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.res-tag {
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent, #1677ff);
  background: color-mix(in srgb, var(--accent, #1677ff) 10%, white);
}
</style>
