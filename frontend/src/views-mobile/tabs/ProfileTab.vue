<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLessonStore } from '@/store/lessonStore'

const router = useRouter()
const lessonStore = useLessonStore()

const props = defineProps({
  progressPercent: { type: Number, default: 0 },
})

const userId = computed(() => lessonStore.platformContext?.userId || '学生用户')
const courseId = computed(() => lessonStore.platformContext?.courseId || '未同步')
const role = computed(() => lessonStore.platformContext?.role || 'student')
const roleLabel = computed(() => role.value === 'teacher' ? '教师' : '学生')

// 头像展示：中文取首字，普通英文名取首字母大写，demo-xxx / UUID 等机器 ID 统一显示图标
const avatarText = computed(() => {
  const id = userId.value
  if (!id || id === '学生用户') return null
  // 中文姓名
  if (/^[\u4e00-\u9fa5]/.test(id)) return id.charAt(0)
  // 短英文名（≤ 10 且不含连字符数字后缀），取首字母
  if (/^[a-zA-Z]/.test(id) && id.length <= 10 && !/[-_]\d+$/.test(id)) {
    return id.charAt(0).toUpperCase()
  }
  // 其余（demo-user-001、UUID 等）返回 null，模板改用图标
  return null
})

const navItems = [
  {
    key: 'knowledge-map',
    icon: 'chart-trending-o',
    label: '知识图谱',
    desc: '可视化本课知识点关联',
    color: '#7c3aed',
    bg: '#f5f0ff',
    path: '/m/knowledge-map',
  },
  {
    key: 'resources',
    icon: 'notes-o',
    label: '学习资源',
    desc: '课件、参考资料与拓展阅读',
    color: '#0ea5e9',
    bg: '#f0f8ff',
    path: '/m/resources',
  },
  {
    key: 'discussion',
    icon: 'chat-o',
    label: '课程讨论',
    desc: '与同学交流、发布提问',
    color: '#16a34a',
    bg: '#f0fdf4',
    path: '/m/discussion',
  },
]

const go = (path) => {
  router.push(path)
}
</script>

<template>
  <div class="profile-root">

    <!-- 用户卡 -->
    <div class="user-card">
      <div class="user-card__bg" />
      <div class="user-card__body">
        <div class="user-avatar">
          <span v-if="avatarText">{{ avatarText }}</span>
          <van-icon v-else name="user-o" size="26" color="#1677ff" />
        </div>
        <div class="user-info">
          <h3 class="user-name">{{ userId }}</h3>
          <span class="user-role">{{ roleLabel }}</span>
        </div>
      </div>

      <!-- 统计行 -->
      <div class="user-stats">
        <div class="stat-item">
          <strong>{{ progressPercent }}%</strong>
          <span>课程进度</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <strong>42 min</strong>
          <span>本日学习</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <strong>3 / 5</strong>
          <span>章节完成</span>
        </div>
      </div>
    </div>

    <!-- 导航列表 -->
    <div class="nav-section">
      <p class="nav-section__title">学习工具</p>
      <div class="nav-list">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="nav-item"
          @click="go(item.path)"
        >
          <div class="nav-item__icon" :style="{ background: item.bg }">
            <van-icon :name="item.icon" size="20" :color="item.color" />
          </div>
          <div class="nav-item__body">
            <strong>{{ item.label }}</strong>
            <p>{{ item.desc }}</p>
          </div>
          <van-icon name="arrow" size="14" color="#c5cdd8" />
        </button>
      </div>
    </div>

    <!-- 课程信息 -->
    <div class="info-card">
      <p class="info-card__title">当前课程</p>
      <div class="info-row">
        <span class="info-label">课程 ID</span>
        <span class="info-value">{{ courseId }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">角色</span>
        <span class="info-value">{{ roleLabel }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">课时进度</span>
        <span class="info-value" style="color: #1677ff; font-weight: 700;">{{ progressPercent }}%</span>
      </div>
    </div>

  </div>
</template>

<style scoped>
.profile-root {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 14px 24px;
  background: #f5f7fa;
  border-radius: inherit;
}

/* ── 用户卡 ── */
.user-card {
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: relative;
  background: #fff;
}

.user-card__bg {
  position: absolute;
  inset: 0;
  height: 90px;
  background: linear-gradient(135deg, #1677ff 0%, #2a8aff 50%, #46aaff 100%);
}

.user-card__body {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 14px;
  padding: 16px 18px 0;
  margin-bottom: 0;
}

.user-avatar {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: #fff;
  border: 3px solid #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 800;
  color: #1677ff;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.user-info {
  padding-bottom: 4px;
}

.user-name {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 800;
  color: #1a2035;
}

.user-role {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: #eef4ff;
  color: #1677ff;
  font-size: 11px;
  font-weight: 700;
}

.user-stats {
  display: flex;
  align-items: center;
  padding: 16px 18px;
  gap: 0;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-item strong {
  font-size: 18px;
  font-weight: 800;
  color: #1a2035;
}

.stat-item span {
  font-size: 11px;
  color: #9aa3b2;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: #eef0f4;
}

/* ── 导航列表 ── */
.nav-section {
  background: #fff;
  border-radius: 20px;
  padding: 16px 16px 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.nav-section__title {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 700;
  color: #9aa3b2;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.nav-list {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  border-top: 1px solid #f3f4f6;
  width: 100%;
  transition: opacity 0.15s;
}

.nav-item:first-child {
  border-top: none;
}

.nav-item:active {
  opacity: 0.65;
}

.nav-item__icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-item__body {
  flex: 1;
  min-width: 0;
}

.nav-item__body strong {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: #1a2035;
  margin-bottom: 3px;
}

.nav-item__body p {
  margin: 0;
  font-size: 12px;
  color: #9aa3b2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 课程信息 ── */
.info-card {
  background: #fff;
  border-radius: 20px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.info-card__title {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 700;
  color: #9aa3b2;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-top: 1px solid #f3f4f6;
}

.info-row:first-of-type {
  border-top: none;
  padding-top: 0;
}

.info-label {
  font-size: 13px;
  color: #9aa3b2;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: #1a2035;
  max-width: 60%;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
