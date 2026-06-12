<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const courses = [
  { id: 'course-1', label: '人工智能导论', color: '#2563eb' },
  { id: 'course-2', label: '机器学习基础', color: '#0891b2' },
  { id: 'course-3', label: '数据结构与算法', color: '#7c3aed' },
  { id: 'course-4', label: 'Python 程序设计', color: '#059669' },
]

const activeCourse = ref('course-1')

const allFeedback = {
  'course-1': [
    { id: 1, student: '林知', rating: 5, tag: '内容清晰', text: '感知机那节讲得非常清楚，AI 助手回答也很及时，解决了我很多疑惑。', time: '2026-04-18' },
    { id: 2, student: '陈屿', rating: 4, tag: '节奏适中', text: '整体节奏合适，但线性代数部分希望能多一些可视化辅助理解。', time: '2026-04-17' },
    { id: 3, student: '宋嘉', rating: 5, tag: '互动丰富', text: '每节课的随堂问答让我印象深刻，有效检验了自己的理解程度。', time: '2026-04-16' },
    { id: 4, student: '周予', rating: 3, tag: '建议增加', text: '希望在课程结束后提供更多习题资源，练习量感觉略少。', time: '2026-04-15' },
    { id: 5, student: '王晴', rating: 4, tag: '内容清晰', text: '讲解逻辑性很强，从基础概念到算法推导循序渐进。', time: '2026-04-14' },
  ],
  'course-2': [
    { id: 1, student: '李明', rating: 5, tag: '案例丰富', text: '决策树那一节用的案例很贴近实际，理解起来直观多了。', time: '2026-04-18' },
    { id: 2, student: '刘佳', rating: 4, tag: '节奏适中', text: 'SVM 部分稍微有点抽象，但 AI 助手解释得很好。', time: '2026-04-17' },
    { id: 3, student: '张伟', rating: 3, tag: '建议增加', text: '希望能增加 sklearn 代码实战部分，光看理论还不够。', time: '2026-04-15' },
    { id: 4, student: '赵云', rating: 5, tag: '互动丰富', text: '随堂小测验很有用，帮助我及时发现了自己的薄弱环节。', time: '2026-04-14' },
  ],
  'course-3': [
    { id: 1, student: '孙鹏', rating: 4, tag: '内容清晰', text: '链表和栈的讲解思路清晰，配合图解很容易理解。', time: '2026-04-18' },
    { id: 2, student: '吴芳', rating: 5, tag: '节奏适中', text: '动态规划章节节奏把握得很好，从易到难，没有跳跃感。', time: '2026-04-16' },
    { id: 3, student: '郑昊', rating: 3, tag: '建议增加', text: '图论部分感觉略快，最短路径算法讲完最好能有更多例题。', time: '2026-04-15' },
  ],
  'course-4': [
    { id: 1, student: '钱悦', rating: 5, tag: '内容清晰', text: '面向对象那章讲得特别棒，三大特性讲解清晰，代码示例到位。', time: '2026-04-19' },
    { id: 2, student: '朱浩', rating: 4, tag: '案例丰富', text: '真实项目案例让课程变得很有趣，从理论到实践的过渡自然。', time: '2026-04-18' },
    { id: 3, student: '冯晨', rating: 5, tag: '互动丰富', text: 'AI 助手的即时答疑功能太好用了，代码报错直接贴给它就行。', time: '2026-04-17' },
    { id: 4, student: '蒋磊', rating: 4, tag: '节奏适中', text: '装饰器那部分稍微绕一点，但讲了两遍后理解了，很有耐心。', time: '2026-04-15' },
    { id: 5, student: '沈琳', rating: 3, tag: '建议增加', text: '希望能增加更多爬虫和数据分析方向的实战内容。', time: '2026-04-14' },
  ],
}

const feedbacks = computed(() => allFeedback[activeCourse.value] || [])
const avgRating = computed(() => {
  const list = feedbacks.value
  if (!list.length) return 0
  return (list.reduce((s, f) => s + f.rating, 0) / list.length).toFixed(1)
})
const ratingDist = computed(() => {
  const dist = [0, 0, 0, 0, 0]
  feedbacks.value.forEach((f) => { dist[f.rating - 1]++ })
  const max = Math.max(...dist) || 1
  return dist.map((count, i) => ({ star: i + 1, count, pct: Math.round(count / max * 100) })).reverse()
})

const tagColors = { '内容清晰': '#2563eb', '节奏适中': '#059669', '互动丰富': '#7c3aed', '案例丰富': '#0891b2', '建议增加': '#f59e0b' }
const tagColor = (tag) => tagColors[tag] || '#6b7a90'

const courseColor = computed(() => courses.find(c => c.id === activeCourse.value)?.color || '#1677ff')
</script>

<template>
  <div class="cf-page">

    <!-- 顶栏 -->
    <div class="cf-topbar">
      <button class="cf-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <span class="cf-topbar-title">课程反馈</span>
      <div style="width:36px" />
    </div>

    <!-- 课程筛选 -->
    <div class="cf-filter">
      <button
        v-for="c in courses"
        :key="c.id"
        class="cf-chip"
        :class="{ active: activeCourse === c.id }"
        :style="activeCourse === c.id ? { background: c.color, color: '#fff', boxShadow: `0 4px 12px ${c.color}44` } : {}"
        @click="activeCourse = c.id"
      >{{ c.label }}</button>
    </div>

    <!-- 评分概况 -->
    <div class="cf-summary">
      <div class="cf-score">
        <span class="cf-score__num" :style="{ color: courseColor }">{{ avgRating }}</span>
        <div class="cf-score__stars">
          <van-icon
            v-for="i in 5"
            :key="i"
            name="star"
            size="14"
            :color="i <= Math.round(Number(avgRating)) ? '#f59e0b' : '#e4e8ef'"
          />
        </div>
        <span class="cf-score__total">{{ feedbacks.length }} 条评价</span>
      </div>
      <div class="cf-rating-dist">
        <div v-for="row in ratingDist" :key="row.star" class="cf-dist-row">
          <span class="cf-dist-star">{{ row.star }}星</span>
          <div class="cf-dist-track">
            <div class="cf-dist-fill" :style="{ width: row.pct + '%', background: courseColor }" />
          </div>
          <span class="cf-dist-count">{{ row.count }}</span>
        </div>
      </div>
    </div>

    <!-- 反馈列表 -->
    <div class="cf-list">
      <div v-for="fb in feedbacks" :key="fb.id" class="cf-item">
        <div class="cf-item__head">
          <div class="cf-avatar" :style="{ background: courseColor }">{{ fb.student }}</div>
          <div class="cf-item__meta">
            <div class="cf-item__stars">
              <van-icon v-for="i in 5" :key="i" name="star" size="12" :color="i <= fb.rating ? '#f59e0b' : '#e4e8ef'" />
            </div>
            <span class="cf-item__time">{{ fb.time }}</span>
          </div>
          <span class="cf-tag" :style="{ color: tagColor(fb.tag), background: tagColor(fb.tag) + '18' }">{{ fb.tag }}</span>
        </div>
        <p class="cf-item__text">{{ fb.text }}</p>
      </div>

      <div v-if="!feedbacks.length" class="cf-empty">
        <van-icon name="comment-o" size="40" color="#c5cdd8" />
        <p>暂无反馈</p>
      </div>
    </div>

    <div style="height:24px" />
  </div>
</template>

<style scoped>
.cf-page {
  min-height: 100vh;
  background: #f5f7fa;
  font-family: -apple-system, sans-serif;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.cf-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f2f5;
  position: sticky; top: 0; z-index: 10;
}
.cf-back {
  width: 36px; height: 36px; border: none; background: #f5f7fa;
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  color: #1a2035; cursor: pointer;
}
.cf-topbar-title { font-size: 17px; font-weight: 800; color: #1a2035; }

/* 筛选 */
.cf-filter {
  display: flex; gap: 8px;
  padding: 12px 14px;
  overflow-x: auto; scrollbar-width: none;
}
.cf-filter::-webkit-scrollbar { display: none; }
.cf-chip {
  flex-shrink: 0; border: none;
  padding: 7px 14px; border-radius: 999px;
  font-size: 13px; font-weight: 600;
  color: #6b7a90; background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
}

/* 评分概况 */
.cf-summary {
  margin: 0 14px 14px;
  background: #fff;
  border-radius: 20px;
  padding: 18px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  display: flex;
  gap: 16px;
  align-items: center;
}
.cf-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  width: 72px;
}
.cf-score__num { font-size: 36px; font-weight: 800; line-height: 1; }
.cf-score__stars { display: flex; gap: 2px; }
.cf-score__total { font-size: 11px; color: #9aa3b2; }

.cf-rating-dist { flex: 1; display: flex; flex-direction: column; gap: 5px; }
.cf-dist-row { display: flex; align-items: center; gap: 7px; }
.cf-dist-star { font-size: 11px; color: #9aa3b2; width: 24px; text-align: right; flex-shrink: 0; }
.cf-dist-track { flex: 1; height: 6px; background: #f0f2f5; border-radius: 999px; overflow: hidden; }
.cf-dist-fill { height: 100%; border-radius: 999px; transition: width 0.35s; }
.cf-dist-count { font-size: 11px; color: #9aa3b2; width: 14px; text-align: right; flex-shrink: 0; }

/* 列表 */
.cf-list { padding: 0 14px; display: flex; flex-direction: column; gap: 10px; }

.cf-item {
  background: #fff;
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.cf-item__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.cf-avatar {
  width: 34px; height: 34px;
  border-radius: 10px;
  color: #fff;
  font-size: 12px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.cf-item__meta { flex: 1; }
.cf-item__stars { display: flex; gap: 2px; margin-bottom: 2px; }
.cf-item__time { font-size: 11px; color: #b0b9c8; }
.cf-tag {
  flex-shrink: 0;
  font-size: 11px; font-weight: 700;
  padding: 3px 10px; border-radius: 999px;
}
.cf-item__text { margin: 0; font-size: 13px; color: #3d4a5f; line-height: 1.7; }

.cf-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 48px 0; gap: 10px;
  color: #9aa3b2; font-size: 14px;
}
</style>
