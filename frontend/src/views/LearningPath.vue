<template>
  <div class="path-page">
    <div class="page-title">个性化学习路径</div>

    <!-- Loading -->
    <section v-if="loading" class="surface-card empty-card">
      <div class="empty-state"><el-icon :size="48" class="is-loading"><Clock /></el-icon><h3>加载中...</h3></div>
    </section>

    <!-- No profile yet -->
    <section v-else-if="!profileExists" class="surface-card empty-card">
      <div class="empty-state">
        <el-icon :size="48"><User /></el-icon>
        <h3>尚未生成学习画像</h3>
        <p>请先完成个人信息初始化，系统将根据你的画像生成个性化学习路径。</p>
        <el-button type="primary" @click="$router.push('/profile/init')">去初始化画像</el-button>
      </div>
    </section>

    <!-- No path yet but profile exists -->
    <section v-else-if="!pathExists && !loading" class="surface-card empty-card">
      <div class="empty-state">
        <el-icon :size="48"><Compass /></el-icon>
        <h3>尚未生成学习路径</h3>
        <p>系统将根据你的六维学生画像智能规划最适合你的学习路线。</p>
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成学习路径</el-button>
      </div>
    </section>

    <template v-if="pathExists">
      <!-- Hero Goal Card -->
      <section class="hero-card">
        <div class="hero-main">
          <div class="hero-copy">
            <span class="hero-caption">你的学习目标</span>
            <h1>{{ currentPath.title }}</h1>
            <p>{{ currentPath.natural_language_summary }}</p>
            <button type="button" class="hero-edit" @click="$router.push('/profile')">
              <el-icon><Edit /></el-icon>
              <span>编辑目标</span>
            </button>
          </div>
          <div class="hero-visual" aria-hidden="true">
            <div class="visual-track track-a"></div>
            <div class="visual-track track-b"></div>
            <div class="visual-point point-a"></div>
            <div class="visual-point point-b"></div>
            <div class="visual-flag"></div>
          </div>
        </div>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-icon" style="background:rgba(59,130,246,0.12);color:#2b6cff"><el-icon><Clock /></el-icon></span>
            <div class="stat-copy"><span class="stat-label">预计总时长</span><strong class="stat-value">{{ totalDuration }}</strong></div>
          </div>
          <div class="stat-item">
            <span class="stat-icon" style="background:rgba(16,185,129,0.12);color:#10b981"><el-icon><Calendar /></el-icon></span>
            <div class="stat-copy"><span class="stat-label">阶段数量</span><strong class="stat-value">{{ stages.length }} 个</strong></div>
          </div>
          <div class="stat-item">
            <span class="stat-icon" style="background:rgba(139,92,246,0.12);color:#8b5cf6"><el-icon><Histogram /></el-icon></span>
            <div class="stat-copy"><span class="stat-label">当前进度</span><strong class="stat-value">{{ progressPercent }}</strong></div>
          </div>
          <div class="stat-item">
            <span class="stat-icon" style="background:rgba(245,158,11,0.14);color:#f59e0b"><el-icon><Flag /></el-icon></span>
            <div class="stat-copy"><span class="stat-label">状态</span><strong class="stat-value" style="color:#10b981">{{ currentPath.status === 'active' ? '进行中' : '已完成' }}</strong></div>
          </div>
        </div>
      </section>

      <!-- Entry cards -->
      <section class="entry-bar">
        <button type="button" class="entry-card" @click="$router.push('/quiz/wrong')">
          <span class="entry-icon wrong"><el-icon><DocumentDelete /></el-icon></span>
          <span class="entry-text"><strong>错题本</strong><small>集中复习高频错题与薄弱点</small></span>
        </button>
        <button type="button" class="entry-card" @click="$router.push('/learning-path/favorites')">
          <span class="entry-icon favorite"><el-icon><Star /></el-icon></span>
          <span class="entry-text"><strong>我的收藏</strong><small>管理常用课程、文档和项目案例</small></span>
        </button>
      </section>

      <!-- Stages -->
      <section class="surface-card">
        <div class="section-head">
          <h2>学习路径阶段规划</h2>
        </div>
        <div class="stage-grid">
          <article v-for="(stage, index) in stages" :key="stage.title" :class="['stage-card', stageColors[index % 4], { active: activeStage === index }]" @click="activeStage = index">
            <div class="stage-head">
              <div class="stage-badge-row">
                <span class="stage-badge">{{ '0' + (index + 1) }}</span>
                <el-tag v-if="index === 0" size="small" type="success" effect="plain">当前阶段</el-tag>
              </div>
              <h3>{{ stage.title }}</h3>
            </div>
            <div class="stage-section">
              <span class="stage-label">阶段目标</span>
              <p>{{ stage.goal }}</p>
            </div>
            <div class="stage-section">
              <span class="stage-label">核心内容</span>
              <ul><li v-for="item in (stage.knowledge_points || [])" :key="item">{{ item }}</li></ul>
            </div>
            <div class="stage-footer">
              <div class="stage-meta"><span>预计时长</span><strong>{{ stage.duration }}</strong></div>
            </div>
            <button type="button" class="stage-action" @click.stop="startStage(stage)">
              {{ index === 0 ? '继续学习' : '开始阶段' }}
            </button>
          </article>
        </div>
      </section>

      <!-- Milestones + Suggestions -->
      <section class="bottom-grid">
        <article class="surface-card">
          <div class="section-head"><h2>关键里程碑</h2></div>
          <div class="milestone-track">
            <div v-for="(item, i) in milestones" :key="item.title" class="milestone-node">
              <div :class="['milestone-icon', { done: i === 0, current: i === 1 }]">
                <el-icon><component :is="i === milestones.length - 1 ? 'Flag' : 'Notebook'" /></el-icon>
              </div>
              <div class="milestone-line" v-if="i < milestones.length - 1"></div>
              <div class="milestone-copy">
                <strong>{{ item.title }}</strong>
                <small>{{ item.duration }}</small>
              </div>
            </div>
          </div>
        </article>
        <article class="surface-card">
          <div class="section-head">
            <h2>路径调整建议</h2>
            <span class="ai-badge"><el-icon><MagicStick /></el-icon><span>AI分析</span></span>
          </div>
          <p class="suggestion-intro">基于你的学习进度和表现，建议进行以下调整：</p>
          <div class="suggestion-list">
            <div v-for="item in suggestions" :key="item.title" class="suggestion-item">
              <span class="suggestion-icon"><el-icon><Warning /></el-icon></span>
              <div class="suggestion-copy"><strong>{{ item.title }}</strong><p>{{ item.desc }}</p></div>
            </div>
          </div>
          <button type="button" class="apply-btn" @click="startStage(stages[0])">应用建议调整</button>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Compass, Edit, Clock, Calendar, Histogram, Flag, DocumentDelete, Star, MagicStick, Warning } from '@element-plus/icons-vue'
import { getPaths, generatePath, getPathDetail } from '@/api/path'
import { getProfile } from '@/api/profile'

const router = useRouter()
const activeStage = ref(0)
const profileExists = ref(false)
const pathExists = ref(false)
const currentPath = ref(null)
const paths = ref([])
const loading = ref(true)
const generating = ref(false)

const stageColors = ['green', 'blue', 'purple', 'orange']

const stages = computed(() => currentPath.value?.path_json?.stages || [])

const totalDuration = computed(() => {
  const stages = currentPath.value?.path_json?.stages || []
  let total = 0
  stages.forEach(s => {
    const match = String(s.duration || '').match(/(\d+)/)
    if (match) total += parseInt(match[1])
  })
  return `约 ${total} 小时`
})

const progressPercent = computed(() => {
  if (!currentPath.value?.path_json?.stages?.length) return '0%'
  const done = currentPath.value.path_json.stages.filter(s => String(s.status || '').includes('完成')).length
  return Math.round(done / currentPath.value.path_json.stages.length * 100) + '%'
})

const milestones = computed(() => (currentPath.value?.path_json?.stages || []).map(s => ({
  title: s.title || '',
  duration: s.duration || '',
})))

const suggestions = [
  { title: '在数据可视化阶段增加 2 小时学习时间', desc: '帮助你更快掌握图表展示与表达技巧。' },
  { title: '建议提前学习特征工程相关内容', desc: '为后续实战项目打好基础。' },
]

async function handleGenerate() {
  generating.value = true
  try {
    const profile = await getProfile()
    const result = await generatePath({ profile_id: profile.id })
    currentPath.value = result
    pathExists.value = true
    await loadPaths()
  } catch (e) {
    console.error('Path generation failed:', e)
  } finally {
    generating.value = false
  }
}

function startStage(stage) {
  const kps = stage.knowledge_points || []
  router.push('/resources?keyword=' + encodeURIComponent(kps[0] || ''))
}

async function loadPaths() {
  try {
    const list = await getPaths()
    paths.value = list || []
    if (list && list.length > 0) {
      currentPath.value = await getPathDetail(list[0].id)
      pathExists.value = true
    }
  } catch {}
}

onMounted(async () => {
  loading.value = true
  try {
    const profile = await getProfile()
    profileExists.value = true
    await loadPaths()
  } catch {
    profileExists.value = false
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.path-page { display: flex; flex-direction: column; gap: 18px; }
.page-title { font-size: 1.85rem; font-weight: 700; color: #1e293b; }
.empty-card { padding: 60px 20px; }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; color: #64748b; text-align: center; }
.empty-state h3 { font-size: 1.1rem; color: #1e293b; }

.hero-card, .entry-card, .surface-card {
  background: #fff; border: 1px solid #e7edf6; border-radius: 18px;
  box-shadow: 0 14px 36px rgba(52, 72, 108, 0.05);
}
.hero-card { overflow: hidden; }
.hero-main {
  min-height: 188px; display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 18px;
  padding: 22px 24px 18px;
  background: linear-gradient(135deg, #edf3ff 0%, #eef5ff 55%, #f7faff 100%);
}
.hero-caption { color: #5f7190; font-size: 0.84rem; }
.hero-copy h1 { margin-top: 6px; color: #1e293b; font-size: 2rem; line-height: 1.15; }
.hero-copy p { margin-top: 10px; max-width: 580px; color: #64748b; font-size: 0.9rem; line-height: 1.7; }
.hero-edit { margin-top: 12px; border: 0; background: transparent; color: #2b6cff; display: inline-flex; align-items: center; gap: 6px; font: inherit; cursor: pointer; }
.hero-visual { position: relative; min-height: 148px; }
.visual-track { position: absolute; border-radius: 999px; background: linear-gradient(90deg, rgba(111,150,255,0.24), rgba(43,108,255,0.5)); }
.track-a { width: 190px; height: 16px; right: 20px; top: 40px; transform: rotate(-18deg); }
.track-b { width: 156px; height: 12px; right: 52px; top: 96px; transform: rotate(18deg); }
.visual-point, .visual-flag { position: absolute; border-radius: 50%; background: #fff; border: 4px solid #7da2ff; box-shadow: 0 12px 24px rgba(82, 118, 195, 0.14); }
.point-a { width: 18px; height: 18px; right: 196px; top: 48px; }
.point-b { width: 18px; height: 18px; right: 64px; top: 92px; }
.visual-flag { width: 24px; height: 24px; right: 116px; top: 18px; border-color: #ff8e54; }
.hero-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 1px solid #e5edf9; }
.stat-item { display: flex; align-items: center; gap: 12px; padding: 16px 18px; }
.stat-item + .stat-item { border-left: 1px solid #edf2f8; }
.stat-icon { width: 38px; height: 38px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; flex: none; }
.stat-copy { display: flex; flex-direction: column; }
.stat-label { color: #94a3b8; font-size: 0.74rem; }
.stat-value { margin-top: 4px; color: #1e293b; font-size: 1.28rem; font-weight: 700; }

.entry-bar { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.entry-card { padding: 16px 18px; display: flex; align-items: center; gap: 14px; cursor: pointer; }
.entry-card:hover { transform: translateY(-1px); box-shadow: 0 16px 36px rgba(52, 72, 108, 0.08); }
.entry-icon { width: 42px; height: 42px; border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; font-size: 18px; flex: none; }
.entry-icon.wrong { background: rgba(245, 158, 11, 0.14); color: #f59e0b; }
.entry-icon.favorite { background: rgba(59, 130, 246, 0.12); color: #2b6cff; }
.entry-text { display: flex; flex-direction: column; }
.entry-text strong { color: #1e293b; font-size: 0.95rem; }
.entry-text small { margin-top: 4px; color: #64748b; font-size: 0.78rem; }

.surface-card { padding: 18px; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-head h2 { color: #1e293b; font-size: 1rem; }
.stage-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.stage-card { border: 1px solid #e7edf6; border-radius: 16px; background: #fff; padding: 16px; cursor: pointer; }
.stage-card.active, .stage-card:hover { border-color: #cfe0ff; box-shadow: 0 12px 30px rgba(52, 72, 108, 0.06); }
.stage-card.green { background: linear-gradient(180deg, #f5fcf8 0%, #ffffff 100%); }
.stage-card.blue { background: linear-gradient(180deg, #f4f8ff 0%, #ffffff 100%); }
.stage-card.purple { background: linear-gradient(180deg, #f8f5ff 0%, #ffffff 100%); }
.stage-card.orange { background: linear-gradient(180deg, #fff8f0 0%, #ffffff 100%); }
.stage-head h3 { margin-top: 10px; color: #1e293b; font-size: 1rem; }
.stage-badge-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.stage-badge { min-width: 28px; height: 28px; padding: 0 8px; border-radius: 999px; background: rgba(43, 108, 255, 0.1); color: #2b6cff; display: inline-flex; align-items: center; justify-content: center; font-size: 0.76rem; font-weight: 700; }
.stage-section { margin-top: 14px; }
.stage-label { color: #64748b; font-size: 0.76rem; }
.stage-section p, .stage-section ul { margin-top: 8px; color: #475569; font-size: 0.8rem; line-height: 1.65; }
.stage-section ul { padding-left: 18px; }
.stage-footer { margin-top: 16px; display: flex; align-items: center; justify-content: space-between; }
.stage-meta { display: flex; flex-direction: column; gap: 4px; }
.stage-meta span { color: #94a3b8; font-size: 0.72rem; }
.stage-meta strong { color: #1e293b; font-size: 0.78rem; }
.stage-action { margin-top: 16px; width: 100%; height: 36px; border: 1px solid #d7e3fb; border-radius: 12px; background: #fff; color: #2b6cff; font: inherit; cursor: pointer; }

.bottom-grid { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.95fr); gap: 18px; }
.milestone-track { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.milestone-node { position: relative; display: flex; flex-direction: column; align-items: center; text-align: center; }
.milestone-icon { width: 34px; height: 34px; border-radius: 50%; background: #eef3ff; color: #94a3b8; display: inline-flex; align-items: center; justify-content: center; z-index: 1; }
.milestone-icon.done { background: #22c55e; color: #fff; }
.milestone-icon.current { background: #2b6cff; color: #fff; box-shadow: 0 0 0 5px rgba(43, 108, 255, 0.12); }
.milestone-line { position: absolute; top: 16px; left: 50%; width: 100%; height: 2px; background: #d9e4f9; }
.milestone-copy { margin-top: 14px; display: flex; flex-direction: column; gap: 4px; }
.milestone-copy strong { color: #1e293b; font-size: 0.84rem; }
.milestone-copy small { color: #94a3b8; font-size: 0.74rem; }
.ai-badge { display: inline-flex; align-items: center; gap: 6px; color: #2b6cff; font-size: 0.76rem; }
.suggestion-intro { color: #64748b; font-size: 0.8rem; }
.suggestion-list { margin-top: 14px; display: flex; flex-direction: column; gap: 14px; }
.suggestion-item { display: flex; align-items: flex-start; gap: 10px; }
.suggestion-icon { width: 26px; height: 26px; border-radius: 50%; background: rgba(43, 108, 255, 0.1); color: #2b6cff; display: inline-flex; align-items: center; justify-content: center; flex: none; }
.suggestion-copy strong { color: #1e293b; font-size: 0.84rem; }
.suggestion-copy p { margin-top: 4px; color: #64748b; font-size: 0.78rem; }
.apply-btn { margin-top: 16px; width: 100%; height: 38px; border: 1px solid #d7e3fb; border-radius: 12px; background: #f8fbff; color: #2b6cff; font: inherit; cursor: pointer; }
</style>
