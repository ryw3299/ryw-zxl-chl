<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const filterCourse = ref('')

const courseOptions = [
  { id: '',         label: '全部课程' },
  { id: 'course-1', label: '人工智能导论' },
  { id: 'course-2', label: '机器学习基础' },
  { id: 'course-3', label: '数据结构与算法' },
  { id: 'course-4', label: 'Python 程序设计' },
]

const records = [
  {
    id: 'r-01', date: '2026-04-19', courseId: 'course-1',
    course: '人工智能导论', section: '第3章 · 感知机与激活函数',
    duration: 42, progressGain: 4, pagesViewed: 8, qaCount: 3,
    accent: '#2563eb',
  },
  {
    id: 'r-02', date: '2026-04-19', courseId: 'course-4',
    course: 'Python 程序设计', section: '第7章 · 面向对象编程',
    duration: 28, progressGain: 3, pagesViewed: 6, qaCount: 1,
    accent: '#059669',
  },
  {
    id: 'r-03', date: '2026-04-18', courseId: 'course-2',
    course: '机器学习基础', section: '第4章 · 决策树与随机森林',
    duration: 55, progressGain: 5, pagesViewed: 11, qaCount: 4,
    accent: '#0891b2',
  },
  {
    id: 'r-04', date: '2026-04-18', courseId: 'course-1',
    course: '人工智能导论', section: '第2章 · 线性回归基础',
    duration: 36, progressGain: 3, pagesViewed: 7, qaCount: 2,
    accent: '#2563eb',
  },
  {
    id: 'r-05', date: '2026-04-17', courseId: 'course-3',
    course: '数据结构与算法', section: '第2章 · 链表与栈',
    duration: 48, progressGain: 4, pagesViewed: 9, qaCount: 5,
    accent: '#7c3aed',
  },
  {
    id: 'r-06', date: '2026-04-16', courseId: 'course-4',
    course: 'Python 程序设计', section: '第5章 · 文件读写操作',
    duration: 22, progressGain: 2, pagesViewed: 5, qaCount: 0,
    accent: '#059669',
  },
  {
    id: 'r-07', date: '2026-04-15', courseId: 'course-2',
    course: '机器学习基础', section: '第2章 · 线性回归与梯度下降',
    duration: 61, progressGain: 6, pagesViewed: 13, qaCount: 6,
    accent: '#0891b2',
  },
  {
    id: 'r-08', date: '2026-04-14', courseId: 'course-1',
    course: '人工智能导论', section: '第1章 · AI 发展历程',
    duration: 30, progressGain: 3, pagesViewed: 6, qaCount: 1,
    accent: '#2563eb',
  },
  {
    id: 'r-09', date: '2026-04-13', courseId: 'course-3',
    course: '数据结构与算法', section: '第1章 · 复杂度分析',
    duration: 40, progressGain: 4, pagesViewed: 8, qaCount: 3,
    accent: '#7c3aed',
  },
  {
    id: 'r-10', date: '2026-04-12', courseId: 'course-4',
    course: 'Python 程序设计', section: '第3章 · 函数与闭包',
    duration: 35, progressGain: 3, pagesViewed: 7, qaCount: 2,
    accent: '#059669',
  },
]

const filtered = computed(() =>
  filterCourse.value ? records.filter((r) => r.courseId === filterCourse.value) : records,
)

const grouped = computed(() => {
  const map = new Map()
  filtered.value.forEach((r) => {
    if (!map.has(r.date)) map.set(r.date, [])
    map.get(r.date).push(r)
  })
  return [...map.entries()].map(([date, items]) => ({ date, items }))
})

const totalMinutes = computed(() => records.reduce((s, r) => s + r.duration, 0))
const totalSessions = computed(() => records.length)
const totalQa = computed(() => records.reduce((s, r) => s + r.qaCount, 0))

const formatDate = (d) => {
  const today = '2026-04-19'
  const yesterday = '2026-04-18'
  if (d === today) return '今天'
  if (d === yesterday) return '昨天'
  return d.slice(5).replace('-', '月') + '日'
}
</script>

<template>
  <div class="lh-page">

    <!-- 顶栏 -->
    <div class="lh-topbar">
      <button class="lh-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <span class="lh-topbar-title">学习历史</span>
      <div style="width:36px" />
    </div>

    <!-- 汇总卡 -->
    <div class="lh-summary">
      <div class="lh-sum-item">
        <span class="lh-sum-val">{{ Math.round(totalMinutes / 60) }}h</span>
        <span class="lh-sum-lbl">累计时长</span>
      </div>
      <div class="lh-sum-div" />
      <div class="lh-sum-item">
        <span class="lh-sum-val">{{ totalSessions }}</span>
        <span class="lh-sum-lbl">学习次数</span>
      </div>
      <div class="lh-sum-div" />
      <div class="lh-sum-item">
        <span class="lh-sum-val">{{ totalQa }}</span>
        <span class="lh-sum-lbl">累计问答</span>
      </div>
    </div>

    <!-- 课程筛选 -->
    <div class="lh-filter">
      <button
        v-for="opt in courseOptions"
        :key="opt.id"
        class="lh-chip"
        :class="{ active: filterCourse === opt.id }"
        @click="filterCourse = opt.id"
      >{{ opt.label }}</button>
    </div>

    <!-- 按日期分组的记录 -->
    <div class="lh-groups">
      <div v-for="group in grouped" :key="group.date" class="lh-group">
        <div class="lh-group-date">{{ formatDate(group.date) }}</div>
        <div class="lh-records">
          <div v-for="r in group.items" :key="r.id" class="lh-record" :style="`--accent:${r.accent}`">
            <div class="lh-record-dot" />
            <div class="lh-record-body">
              <div class="lh-record-course">{{ r.course }}</div>
              <div class="lh-record-section">{{ r.section }}</div>
              <div class="lh-record-meta">
                <span>
                  <van-icon name="clock-o" size="11" />
                  {{ r.duration }} 分钟
                </span>
                <span>
                  <van-icon name="description" size="11" />
                  {{ r.pagesViewed }} 页
                </span>
                <span v-if="r.qaCount">
                  <van-icon name="chat-o" size="11" />
                  {{ r.qaCount }} 次问答
                </span>
                <span class="lh-gain">+{{ r.progressGain }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="grouped.length === 0" class="lh-empty">
        <van-icon name="notes-o" size="40" color="#c5cdd8" />
        <p>暂无学习记录</p>
      </div>
    </div>

    <div style="height:28px" />
  </div>
</template>

<style scoped>
.lh-page {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, sans-serif;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.lh-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
  position: sticky; top: 0; z-index: 10;
}

.lh-back {
  width: 36px; height: 36px; border: none; background: #f5f7fa;
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  color: #1a2035; cursor: pointer;
}

.lh-topbar-title { font-size: 17px; font-weight: 800; color: #1a2035; }

/* 汇总 */
.lh-summary {
  margin: 14px 14px 0;
  background: linear-gradient(135deg, #1677ff, #2a8aff 60%, #46aaff);
  border-radius: 20px;
  padding: 18px 20px;
  display: flex; align-items: center; justify-content: space-around;
  box-shadow: 0 6px 20px rgba(22, 119, 255, 0.28);
}

.lh-sum-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }

.lh-sum-val { font-size: 26px; font-weight: 800; color: #fff; }

.lh-sum-lbl { font-size: 11px; color: rgba(255,255,255,0.7); }

.lh-sum-div { width: 1px; height: 36px; background: rgba(255,255,255,0.25); }

/* 筛选 */
.lh-filter {
  display: flex; gap: 8px;
  padding: 12px 14px;
  overflow-x: auto; scrollbar-width: none;
}
.lh-filter::-webkit-scrollbar { display: none; }

.lh-chip {
  flex-shrink: 0; border: none;
  padding: 7px 14px; border-radius: 999px;
  font-size: 13px; font-weight: 600;
  color: #6b7a90; background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
}

.lh-chip.active { color: #fff; background: #1677ff; box-shadow: 0 4px 12px rgba(22,119,255,0.3); }

/* 分组 */
.lh-groups { padding: 0 14px; display: flex; flex-direction: column; gap: 18px; }

.lh-group-date {
  font-size: 12px; font-weight: 700; color: #9aa3b2;
  letter-spacing: 0.06em; text-transform: uppercase;
  margin-bottom: 8px;
}

.lh-records {
  display: flex; flex-direction: column; gap: 0;
  background: #fff; border-radius: 16px;
  overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}

.lh-record {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #f5f7fa;
  position: relative;
}
.lh-record:last-child { border-bottom: none; }

.lh-record-dot {
  flex-shrink: 0;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--accent, #1677ff);
  margin-top: 5px;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent, #1677ff) 15%, white);
}

.lh-record-body { flex: 1; min-width: 0; }

.lh-record-course {
  font-size: 13px; font-weight: 700;
  color: var(--accent, #1677ff);
  margin-bottom: 2px;
}

.lh-record-section {
  font-size: 14px; font-weight: 600; color: #1a2035;
  margin-bottom: 6px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.lh-record-meta {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}

.lh-record-meta span {
  display: flex; align-items: center; gap: 3px;
  font-size: 11px; color: #9aa3b2; font-weight: 500;
}

.lh-gain {
  color: #12b76a !important;
  font-weight: 700 !important;
  background: #ecfdf3;
  padding: 2px 7px;
  border-radius: 999px;
}

.lh-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 48px 0; gap: 10px;
  color: #9aa3b2; font-size: 14px;
}
</style>
