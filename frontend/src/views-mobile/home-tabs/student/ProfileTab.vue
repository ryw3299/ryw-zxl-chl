<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const userStore = useUserStore()

const userId = computed(() => userStore.userInfo.userId || '同学')
const displayName = computed(() => /^demo/.test(userId.value) ? '演示用户' : userId.value)

const avatarText = computed(() => {
  const id = userId.value
  if (/^[\u4e00-\u9fa5]/.test(id)) return id.charAt(0)
  if (/^[a-zA-Z]/.test(id) && id.length <= 10 && !/[-_]\d+$/.test(id)) return id.charAt(0).toUpperCase()
  return null
})

const stats = [
  { label: '学习天数', value: '12', unit: '天' },
  { label: '完成课时', value: '3', unit: '门' },
  { label: '练习题', value: '47', unit: '题' },
]

const menuGroups = [
  {
    title: '学习记录',
    items: [
      { icon: 'notes-o',          label: '学习历史',  desc: '查看历次学习记录',         path: '/m/learning-history' },
      { icon: 'medal-o',          label: '排行榜',    desc: '查看班级学习排名与动态',   path: '/m/leaderboard' },
    ],
  },
  {
    title: '学习工具',
    items: [
      { icon: 'cluster-o',  label: '知识图谱',  desc: '可视化知识关联',                 path: '/m/knowledge-map' },
      { icon: 'orders-o',   label: '课程资源',  desc: '查看课件、讲义与补充资料',       path: '/m/resources' },
    ],
  },
]
</script>

<template>
  <div class="profile-root">

    <!-- 用户信息卡 -->
    <div class="user-card">
      <div class="user-card__bg" />
      <div class="user-card__inner">
        <div class="user-avatar">
          <span v-if="avatarText">{{ avatarText }}</span>
          <van-icon v-else name="user-o" size="28" color="#1677ff" />
        </div>
        <div class="user-info">
          <h3>{{ displayName }}</h3>
          <span class="user-role">学生</span>
        </div>
      </div>
      <div class="user-stats">
        <div v-for="s in stats" :key="s.label" class="stat-cell">
          <strong>{{ s.value }}<em>{{ s.unit }}</em></strong>
          <span>{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- 菜单组 -->
    <div v-for="group in menuGroups" :key="group.title" class="menu-group">
      <p class="menu-group__title">{{ group.title }}</p>
      <div class="menu-list">
        <button
          v-for="item in group.items"
          :key="item.label"
          class="menu-item"
          @click="router.push(item.path)"
        >
          <div class="menu-item__icon">
            <van-icon :name="item.icon" size="20" color="#1677ff" />
          </div>
          <div class="menu-item__body">
            <strong>{{ item.label }}</strong>
            <p>{{ item.desc }}</p>
          </div>
          <van-icon name="arrow" size="14" color="#c5cdd8" />
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.profile-root {
  padding: 14px 14px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── 用户卡 ── */
.user-card {
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(22, 119, 255, 0.12);
  position: relative;
  background: #fff;
}

.user-card__bg {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 88px;
  background: linear-gradient(135deg, #1677ff 0%, #2a8aff 60%, #46aaff 100%);
}

.user-card__inner {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 14px;
  padding: 16px 18px 0;
}

.user-avatar {
  width: 66px; height: 66px;
  border-radius: 20px;
  background: #fff;
  border: 3px solid #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 800;
  color: #1677ff;
  box-shadow: 0 4px 14px rgba(0,0,0,0.1);
  flex-shrink: 0;
}

.user-info { padding-bottom: 4px; }
.user-info h3 { margin: 0 0 6px; font-size: 19px; font-weight: 800; color: #1a2035; }
.user-role {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: #eef4ff;
  color: #1677ff;
  font-size: 11px; font-weight: 700;
}

.user-stats {
  display: flex;
  padding: 16px 18px;
}

.stat-cell {
  flex: 1;
  text-align: center;
  border-right: 1px solid #f0f2f5;
}
.stat-cell:last-child { border-right: none; }

.stat-cell strong {
  display: block;
  font-size: 20px; font-weight: 800;
  color: #1a2035;
}

.stat-cell strong em {
  font-style: normal;
  font-size: 12px;
  color: #9aa3b2;
  margin-left: 2px;
}

.stat-cell span {
  display: block;
  font-size: 11px;
  color: #9aa3b2;
  margin-top: 2px;
}

/* ── 菜单组 ── */
.menu-group__title {
  margin: 0 0 10px;
  font-size: 12px; font-weight: 700;
  color: #9aa3b2;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.menu-list {
  background: #fff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
  cursor: pointer;
  border-top: 1px solid #f3f4f6;
  transition: opacity 0.15s;
}
.menu-item:first-child { border-top: none; }
.menu-item:active { opacity: 0.65; }

.menu-item__icon {
  width: 42px; height: 42px;
  border-radius: 13px;
  background: #eef4ff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.menu-item__body { flex: 1; min-width: 0; }
.menu-item__body strong { display: block; font-size: 15px; font-weight: 700; color: #1a2035; margin-bottom: 3px; }
.menu-item__body p { margin: 0; font-size: 12px; color: #9aa3b2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
