<template>
  <div class="generated-page">
    <div class="gen-header">
      <h1>个性化资源生成</h1>
      <p>基于你的学习画像与学习路径，AI 为你定制专属学习资源</p>
    </div>

    <!-- User Overview -->
    <div class="user-overview">
      <div class="uo-avatar">{{ (userStore.username || '用')[0] }}</div>
      <div class="uo-info">
        <span class="uo-name">{{ userStore.username || '用户' }} <span class="uo-level">Lv.6</span></span>
        <span class="uo-meta">计算机科学与技术 · 大二</span>
      </div>
      <div class="uo-stats">
        <div class="uos-item"><span class="uos-label">学习目标</span><span class="uos-val">AI 应用开发</span></div>
        <div class="uos-item"><span class="uos-label">当前阶段</span><span class="uos-val">基础夯实</span></div>
        <div class="uos-item"><span class="uos-label">薄弱知识点</span><span class="uos-val weak">数据结构</span></div>
        <div class="uos-item"><span class="uos-label">偏好资源</span><span class="uos-val">文档 · 视频</span></div>
      </div>
    </div>

    <div class="gen-grid">
      <!-- Left: Config -->
      <div class="gen-config">
        <div class="card">
          <div class="card-header">生成资源设置</div>
          <div class="card-body">
            <!-- Resource type tabs -->
            <div class="type-tabs">
              <button v-for="t in types" :key="t.key" :class="['type-tab', { active: form.type === t.key }]" @click="form.type = t.key">
                <span>{{ t.label.charAt(0) }}</span>
                <span>{{ t.label }}</span>
              </button>
            </div>

            <el-form label-position="top" class="gen-form">
              <el-form-item label="主题">
                <el-input v-model="form.topic" placeholder="例如：线性回归" />
              </el-form-item>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="难度级别">
                    <el-select v-model="form.difficulty" style="width: 100%">
                      <el-option label="入门" value="beginner" />
                      <el-option label="中等" value="intermediate" />
                      <el-option label="高级" value="advanced" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="内容风格">
                    <el-select v-model="form.style" style="width: 100%">
                      <el-option label="通俗易懂" value="simple" />
                      <el-option label="专业详细" value="detailed" />
                      <el-option label="案例驱动" value="case" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="学习阶段">
                    <el-select v-model="form.stage" style="width: 100%">
                      <el-option label="入门" value="beginner" />
                      <el-option label="进阶" value="intermediate" />
                      <el-option label="高级" value="advanced" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="输出长度">
                    <el-select v-model="form.length" style="width: 100%">
                      <el-option label="简短（800-1500字）" value="short" />
                      <el-option label="中等（1500-2500字）" value="medium" />
                      <el-option label="详细（2500-4000字）" value="long" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="输出语言">
                <el-radio-group v-model="form.language">
                  <el-radio value="zh">中文</el-radio>
                  <el-radio value="en">英文</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="补充要求">
                <el-input v-model="form.requirements" type="textarea" :rows="2" placeholder="例如：多包含实际案例、配代码示例..." />
              </el-form-item>
            </el-form>

            <div class="gen-actions">
              <el-button type="primary" size="large" :loading="generating" @click="handleGenerate">
                <el-icon><MagicStick /></el-icon> 一键生成
              </el-button>
              <el-button size="large" @click="saveTemplate">保存模板</el-button>
            </div>
          </div>
        </div>

        <!-- Multi-agent workflow -->
        <div class="card workflow-card">
          <div class="card-header">多智能体协同工作流程</div>
          <div class="card-body">
            <div class="workflow-steps">
              <div class="wf-step" v-for="(step, i) in workflowSteps" :key="i">
                <div class="wf-icon" :style="{ background: step.done ? '#10b981' : '#e2e8f0' }">
                  <el-icon v-if="step.done" color="white" :size="14"><Check /></el-icon>
                  <span v-else style="color: #94a3b8; font-size: 12px">{{ i + 1 }}</span>
                </div>
                <div class="wf-info">
                  <span class="wf-name">{{ step.name }}</span>
                  <span :class="['wf-status', step.done ? 'done' : '']">{{ step.status }}</span>
                </div>
                <div v-if="i < workflowSteps.length - 1" class="wf-arrow">
                  <el-icon><ArrowRight /></el-icon>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Result Preview -->
      <div class="gen-result">
        <div class="card">
          <div class="card-header">生成结果预览</div>
          <div class="card-body">
            <StateBlock
              v-if="!currentResult && !generating"
              empty-text="配置参数后点击「一键生成」"
            />
            <div v-else-if="generating" class="generating-state">
              <div class="gen-spinner"></div>
              <p>AI 正在生成中，请稍候...</p>
              <p class="gen-sub">多智能体协同处理中</p>
            </div>
            <div v-else-if="currentResult">
              <div class="result-tabs">
                <button
                  v-for="tab in resultTabs"
                  :key="tab.key"
                  :class="['result-tab', { active: activeResultTab === tab.key }]"
                  @click="activeResultTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </div>
              <MarkdownRenderer :content="currentResult.content" />
            </div>
          </div>
        </div>

        <!-- History -->
        <div class="card">
          <div class="card-header">生成历史</div>
          <div class="card-body">
            <div v-if="!history.length" class="empty-history">
              <p>暂无生成记录</p>
            </div>
            <div v-else>
              <div class="history-item" v-for="item in history" :key="item.id" @click="viewHistory(item)">
                <el-tag size="small" effect="plain">{{ typeLabel(item.resource_type) }}</el-tag>
                <span class="hi-title">{{ item.title }}</span>
                <span class="hi-date">{{ item.created_at?.slice(0, 10) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { MagicStick, Check, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { generateResource, getGeneratedResources, getGeneratedResourceDetail } from '@/api/generatedResource'
import StateBlock from '@/components/StateBlock.vue'
import { useUserStore } from '@/store/userStore'
const userStore = useUserStore()

const generating = ref(false)
const history = ref([])
const currentResult = ref(null)
const activeResultTab = ref('document')

const form = reactive({
  type: 'document',
  topic: '',
  difficulty: 'intermediate',
  style: 'simple',
  stage: 'beginner',
  length: 'medium',
  language: 'zh',
  requirements: '',
})

const types = [
  { key: 'document', label: '学习文档' },
  { key: 'ppt', label: 'PPT课件' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'quiz', label: '练习题' },
  { key: 'project', label: '项目任务书' },
  { key: 'video_script', label: '短视频讲解' },
]

const resultTabs = [
  { key: 'document', label: '文档预览' },
  { key: 'ppt', label: 'PPT预览' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'quiz', label: '题目册' },
  { key: 'script', label: '脚本预览' },
]

const workflowSteps = [
  { name: '学情分析', status: '完成', done: true },
  { name: '知识检索', status: '进行中', done: false },
  { name: '教学设计', status: '待开始', done: false },
  { name: '内容生成', status: '待开始', done: false },
  { name: '质量评估', status: '待开始', done: false },
]

const typeMap = { document: '文档', ppt: 'PPT', mindmap: '导图', quiz: '练习', project: '项目', video_script: '脚本' }
function typeLabel(t) { return typeMap[t] || t }

onMounted(fetchHistory)

async function fetchHistory() {
  try { history.value = await getGeneratedResources() } catch {}
}

async function handleGenerate() {
  generating.value = true
  try {
    currentResult.value = await generateResource({
      resource_type: form.type,
      knowledge_points: form.topic ? [form.topic] : ['Python'],
      difficulty: form.difficulty,
      style: form.style,
    })
    ElMessage.success('资源已生成')
    await fetchHistory()
  } catch {
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}

async function viewHistory(item) {
  try {
    currentResult.value = await getGeneratedResourceDetail(item.id)
  } catch {}
}

function saveTemplate() {
  const template = { ...form }
  localStorage.setItem('resourceTemplate', JSON.stringify(template))
  ElMessage.success('模板已保存')
}
</script>

<style scoped>
.gen-header { margin-bottom: 20px; }
.gen-header h1 { font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }
.gen-header p { font-size: 0.85rem; color: var(--text-secondary); }

.user-overview {
  display: flex;
  align-items: center;
  gap: 20px;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 20px;
}
.uo-avatar {
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  color: white; display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700;
}
.uo-info { display: flex; flex-direction: column; }
.uo-name { font-size: 0.95rem; font-weight: 600; }
.uo-level { padding: 1px 6px; border-radius: 8px; background: var(--brand-primary-light); color: var(--brand-primary); font-size: 0.65rem; font-weight: 600; margin-left: 6px; }
.uo-meta { font-size: 0.75rem; color: var(--text-muted); }
.uo-stats { display: flex; gap: 20px; margin-left: auto; }
.uos-item { display: flex; flex-direction: column; align-items: center; }
.uos-label { font-size: 0.7rem; color: var(--text-muted); }
.uos-val { font-size: 0.85rem; font-weight: 500; }
.uos-val.weak { color: #ef4444; }

.gen-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
}

.card { margin-bottom: 16px; }

.type-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}
.type-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: white;
  cursor: pointer;
  font-size: 0.72rem;
  color: var(--text-secondary);
  transition: all 0.2s;
  font-family: inherit;
}
.type-tab:hover { border-color: var(--brand-primary); }
.type-tab.active { border-color: var(--brand-primary); background: var(--bg-selected); color: var(--brand-primary); font-weight: 500; }

.gen-form { margin-bottom: 16px; }

.gen-actions { display: flex; gap: 12px; }

.workflow-steps { display: flex; flex-direction: column; gap: 8px; }
.wf-step { display: flex; align-items: center; gap: 10px; }
.wf-icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.wf-info { flex: 1; }
.wf-name { display: block; font-size: 0.82rem; color: var(--text-primary); }
.wf-status { font-size: 0.7rem; color: var(--text-muted); }
.wf-status.done { color: #10b981; }
.wf-arrow { color: var(--text-muted); }

.gen-result { min-width: 0; }

.generating-state {
  display: flex; flex-direction: column; align-items: center;
  padding: 48px 0; gap: 12px;
}
.gen-spinner {
  width: 40px; height: 40px; border: 3px solid var(--border);
  border-top-color: var(--brand-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.gen-sub { font-size: 0.78rem; color: var(--text-muted); }

.result-tabs {
  display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap;
}
.result-tab {
  padding: 6px 14px; border-radius: 16px; border: 1px solid var(--border);
  background: white; font-size: 0.78rem; color: var(--text-secondary);
  cursor: pointer; font-family: inherit; transition: all 0.2s;
}
.result-tab.active { background: var(--brand-primary); color: white; border-color: var(--brand-primary); }

.empty-history { text-align: center; padding: 20px; color: var(--text-muted); font-size: 0.85rem; }
.history-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-light); cursor: pointer; }
.history-item:last-child { border-bottom: none; }
.hi-title { flex: 1; font-size: 0.82rem; color: var(--text-primary); }
.hi-date { font-size: 0.72rem; color: var(--text-muted); }
</style>
