<template>
  <div class="section">
    <h2>知识库管理</h2>
    <p class="section-desc">
      管理预索引知识库。将课件（PPT/PPTX）预先向量化，QA 时直接检索，无需即时构建索引。
    </p>

    <!-- ── List existing KBs ── -->
    <div class="api-card">
      <div class="api-header" @click="listOpen = !listOpen">
        <div class="api-title-row">
          <span class="method-badge get">GET</span>
          <code class="api-path">/internal/kb/list</code>
          <span class="api-desc">已有知识库</span>
          <span v-if="kbList.length" class="kb-count">{{ kbList.length }} 个</span>
        </div>
        <span class="expand-icon">{{ listOpen ? '▾' : '▸' }}</span>
      </div>
      <div v-show="listOpen" class="api-body">
        <button class="send-btn" :disabled="listLoading" @click="fetchList">
          {{ listLoading ? '加载中...' : '刷新列表' }}
        </button>
        <div v-if="kbList.length" class="kb-grid">
          <div v-for="kb in kbList" :key="kb.kbId" class="kb-card" :class="'st-' + kb.status">
            <div class="kb-card-header">
              <span class="kb-name">{{ kb.kbName || kb.kbId }}</span>
              <span class="kb-status">{{ kb.status }}</span>
            </div>
            <div class="kb-card-body">
              <div class="kb-stat"><span class="kb-stat-label">KB ID</span><code>{{ kb.kbId }}</code></div>
              <div class="kb-stat"><span class="kb-stat-label">课程</span><code>{{ kb.courseId }}</code></div>
              <div class="kb-stat"><span class="kb-stat-label">Chunks</span><span>{{ kb.chunkCount }}</span></div>
              <div class="kb-stat"><span class="kb-stat-label">来源</span><span>{{ kb.sourceCount }}</span></div>
            </div>
            <div class="kb-card-actions">
              <button class="mini-btn" @click="viewStatus(kb.kbId)">详情</button>
            </div>
          </div>
        </div>
        <div v-else-if="!listLoading" class="empty-hint">暂无知识库，请先创建。</div>
      </div>
    </div>

    <!-- ── KB detail/status ── -->
    <div v-if="detailData" class="api-card">
      <div class="api-header" @click="detailData = null">
        <div class="api-title-row">
          <span class="method-badge get">DETAIL</span>
          <span class="api-desc">{{ detailData.kbName || detailData.kbId }}</span>
        </div>
        <span class="expand-icon">✕</span>
      </div>
      <div class="api-body">
        <pre class="response-body">{{ JSON.stringify(detailData, null, 2) }}</pre>
      </div>
    </div>

    <!-- ── Create KB ── -->
    <ApiTester
      title="创建知识库"
      path="/internal/kb/create"
      :fields="[
        { name: 'courseId', label: '课程ID', placeholder: 'cou30001', default: 'cou30001' },
        { name: 'kbName', label: '知识库名称', placeholder: '材料力学知识库' },
        { name: 'indexBackend', label: '索引后端', options: ['faiss', 'numpy'], default: 'faiss' },
      ]"
    />

    <!-- ── Add sources ── -->
    <ApiTester
      title="添加来源"
      path="/internal/kb/addSources"
      :fields="[
        { name: 'kbId', label: '知识库ID', placeholder: 'kb_xxxx' },
        { name: 'lessonIds', label: '智课ID列表(JSON)', type: 'json', placeholder: '[&quot;lesson20240520001&quot;]' },
      ]"
    />

    <!-- ── Build index ── -->
    <ApiTester
      title="构建索引"
      path="/internal/kb/build"
      :fields="[
        { name: 'kbId', label: '知识库ID', placeholder: 'kb_xxxx' },
        { name: 'lessonIds', label: '智课ID列表(可选, JSON)', type: 'json', placeholder: '[]' },
      ]"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import http from '../api/request.js'
import ApiTester from './ApiTester.vue'

const listOpen = ref(true)
const listLoading = ref(false)
const kbList = ref([])
const detailData = ref(null)

async function fetchList() {
  listLoading.value = true
  try {
    const res = await http.get('/internal/kb/list')
    kbList.value = res.data?.data || []
  } catch (e) {
    kbList.value = []
  } finally {
    listLoading.value = false
  }
}

async function viewStatus(kbId) {
  try {
    const res = await http.get(`/internal/kb/status/${kbId}`)
    detailData.value = res.data?.data || res.data
  } catch (e) {
    detailData.value = { error: e.message }
  }
}

fetchList()
</script>

<style scoped>
.section-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.kb-count {
  font-size: 11px;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 2px 8px;
  border-radius: 10px;
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.kb-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  background: #fafbfc;
  transition: border-color 0.2s;
}

.kb-card:hover { border-color: var(--primary); }

.kb-card.st-ready { border-left: 3px solid var(--success); }
.kb-card.st-indexing { border-left: 3px solid var(--warning); }
.kb-card.st-failed { border-left: 3px solid var(--error); }
.kb-card.st-draft { border-left: 3px solid var(--border); }

.kb-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.kb-name {
  font-weight: 600;
  font-size: 14px;
}

.kb-status {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.st-ready .kb-status { background: #dcfce7; color: #15803d; }
.st-indexing .kb-status { background: #fef3c7; color: #92400e; }
.st-failed .kb-status { background: #fecdd3; color: #be123c; }
.st-draft .kb-status { background: #e2e8f0; color: #64748b; }

.kb-card-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.kb-stat {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.kb-stat-label {
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  min-width: 40px;
}

.kb-stat code {
  font-size: 11px;
  background: #e2e8f0;
  padding: 1px 4px;
  border-radius: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}

.kb-card-actions {
  margin-top: 10px;
  display: flex;
  gap: 6px;
}

.mini-btn {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.mini-btn:hover { background: #f1f5f9; border-color: var(--primary); }

.empty-hint {
  text-align: center;
  color: var(--text-secondary);
  padding: 30px;
  font-size: 14px;
}
</style>
