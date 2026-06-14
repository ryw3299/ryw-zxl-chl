<template>
  <div class="reader-page">
    <div class="reader-top-bar">
      <div class="rtb-left">
        <el-icon class="pdf-icon"><Document /></el-icon>
        <div class="rtb-info">
          <span class="rtb-title">{{ resource?.title || '文档标题' }}</span>
          <span class="rtb-sub">{{ resource?.direction || '课程' }} · {{ resource?.created_at?.slice(0, 10) || '2025' }} · {{ totalPages }}页</span>
        </div>
      </div>
      <div class="rtb-right">
        <el-button text @click="$router.go(-1)"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <el-button text @click="handleFavorite"><el-icon><Star /></el-icon> 加入收藏</el-button>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="reader-toolbar">
      <el-button-group>
        <el-button size="small"><el-icon><ArrowLeft /></el-icon></el-button>
        <el-button size="small">{{ currentPage }} / {{ totalPages }}</el-button>
        <el-button size="small"><el-icon><ArrowRight /></el-icon></el-button>
      </el-button-group>
      <span class="toolbar-sep">|</span>
      <span class="toolbar-zoom">100%</span>
      <el-button size="small"><el-icon><ZoomIn /></el-icon></el-button>
      <el-button size="small"><el-icon><ZoomOut /></el-icon></el-button>
      <span class="toolbar-sep">|</span>
      <el-button size="small"><el-icon><FullScreen /></el-icon></el-button>
      <el-button size="small"><el-icon><Printer /></el-icon></el-button>
      <el-button size="small"><el-icon><Download /></el-icon></el-button>
      <span class="toolbar-sep">|</span>
      <el-button size="small" @click="toggleToc">目录</el-button>
    </div>

    <!-- Three-column layout -->
    <div class="reader-body">
      <!-- Left: TOC -->
      <aside class="reader-toc" v-show="showToc">
        <div class="toc-search">
          <el-input placeholder="搜索目录..." size="small" :prefix-icon="Search" />
        </div>
        <div class="toc-tree">
          <div class="toc-item" v-for="(item, i) in toc" :key="i" :class="{ active: i === 0 }">
            <span class="toc-dot"></span>
            <span class="toc-text">{{ item }}</span>
          </div>
        </div>
      </aside>

      <!-- Center: Content -->
      <div class="reader-content" ref="contentRef">
        <div class="doc-header">
          <h1>{{ resource?.title || '文档标题' }}</h1>
        </div>

        <div class="doc-paragraph">
          <p>在数学中，函数是一种将一个集合的元素映射到另一个集合的对应关系。简单来说，给定一个输入值，函数会给出唯一的输出值。函数在数学分析中扮演着核心角色，是描述变量之间依赖关系的基本工具。</p>
        </div>

        <!-- Definition block -->
        <div class="doc-block definition">
          <div class="block-label">定义</div>
          <p>设 A 和 B 是两个非空集合。如果存在一个对应关系 <strong>f</strong>，使得对于 A 中的每个元素 <strong>x</strong>，按照对应关系 <strong>f</strong>，在 B 中有唯一确定的元素 <strong>y</strong> 与之对应，则称 <strong>f</strong> 为从 A 到 B 的一个函数，记作：<strong>y = f(x)</strong>，其中 x 称为自变量，y 称为因变量。</p>
        </div>

        <!-- Key point -->
        <div class="doc-block key-point">
          <div class="block-label">关键点</div>
          <ul>
            <li>函数是一种特殊的对应关系</li>
            <li>每个自变量只能对应唯一的一个因变量</li>
            <li>函数的定义域是自变量 x 的取值范围</li>
            <li>函数的值域是因变量 y 的取值范围</li>
          </ul>
        </div>

        <!-- Example -->
        <div class="doc-block example">
          <div class="block-label">例题讲解</div>
          <p>判断下列对应关系是否为函数：</p>
          <p class="example-q">(1) f: x → x², x ∈ R</p>
          <p class="example-a">解：对于任意实数 x，x² 是唯一确定的实数，所以这是函数。</p>
        </div>
      </div>
    </div>

    <!-- Context menu -->
    <div v-if="showMenu" class="context-menu" :style="{ top: menuY + 'px', left: menuX + 'px' }">
      <button @click="addToSession">添加到会话</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Document, Star, ArrowLeft, ArrowRight, ZoomIn, ZoomOut, FullScreen, Printer, Download, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getResourceDetail } from '@/api/resource'
import { useAssistantStore } from '@/store/assistantStore'

const assistantStore = useAssistantStore()

const route = useRoute()
const resource = ref(null)
const contentRef = ref(null)
const currentPage = ref(8)
const totalPages = ref(24)
const showToc = ref(true)
const showMenu = ref(false)
const menuX = ref(0)
const menuY = ref(0)

const toc = [
  '第1章 集合与函数概念',
  '1.1 函数的概念',
  '1.1.1 变量与常量',
  '1.1.2 函数的定义',
  '1.1.3 函数的表示方法',
  '1.2 函数的性质',
  '1.2.1 单调性',
  '1.2.2 奇偶性',
]

onMounted(async () => {
  try {
    resource.value = await getResourceDetail(route.params.id)
  } catch {
    resource.value = { title: '函数的概念与性质', direction: '数学', created_at: '2025-01-15' }
  }
  document.addEventListener('mouseup', handleSelection)
  document.addEventListener('click', () => { showMenu.value = false })
})

onUnmounted(() => {
  document.removeEventListener('mouseup', handleSelection)
})

function toggleToc() { showToc.value = !showToc.value }

function handleSelection(e) {
  const sel = window.getSelection()
  if (sel && sel.toString().trim().length > 5) {
    menuX.value = e.clientX
    menuY.value = e.clientY
    showMenu.value = true
  }
}

function addToSession() {
  const sel = window.getSelection()
  const text = sel?.toString().trim()
  if (text) {
    assistantStore.addContext({ type: 'text', content: text, pageId: currentPage.value.toString(), resourceId: route.params.id })
    ElMessage.success('已添加到 AI 助教会话')
  }
  showMenu.value = false
}

function handleFavorite() {
  const favs = JSON.parse(localStorage.getItem('favorites') || '[]')
  const id = Number(route.params.id)
  if (!favs.includes(id)) {
    favs.push(id)
    localStorage.setItem('favorites', JSON.stringify(favs))
    ElMessage.success('已加入收藏')
  } else {
    ElMessage.info('该资源已在收藏中')
  }
}
</script>

<style scoped>
.reader-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  margin-bottom: 8px;
}
.rtb-left { display: flex; align-items: center; gap: 12px; }
.pdf-icon { font-size: 28px; color: #dc2626; }
.rtb-info { display: flex; flex-direction: column; }
.rtb-title { font-size: 0.95rem; font-weight: 600; }
.rtb-sub { font-size: 0.75rem; color: var(--text-muted); }

.reader-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  font-size: 0.82rem;
}
.toolbar-sep { color: var(--border); }
.toolbar-zoom { font-size: 0.82rem; color: var(--text-secondary); min-width: 40px; text-align: center; }

.reader-body {
  display: flex;
  gap: 16px;
  position: relative;
}

/* TOC */
.reader-toc {
  width: 220px;
  flex-shrink: 0;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}
.toc-search { margin-bottom: 12px; }
.toc-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}
.toc-item:hover { background: var(--bg-hover); }
.toc-item.active {
  background: var(--bg-selected);
  color: var(--brand-primary);
  font-weight: 500;
}
.toc-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-muted);
  margin-top: 7px;
  flex-shrink: 0;
}
.toc-item.active .toc-dot { background: var(--brand-primary); }

/* Content */
.reader-content {
  flex: 1;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 32px 40px;
  min-height: 400px;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}

.doc-header h1 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--border);
}

.doc-paragraph p {
  font-size: 0.9rem;
  line-height: 1.8;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.doc-block {
  padding: 16px 20px;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.doc-block.definition {
  background: #eff6ff;
  border-left: 3px solid #2563eb;
}

.doc-block.key-point {
  background: #f0fdf4;
  border-left: 3px solid #10b981;
}

.doc-block.example {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
}

.block-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.doc-block p {
  font-size: 0.88rem;
  line-height: 1.8;
  color: var(--text-secondary);
}

.doc-block ul {
  padding-left: 20px;
  margin: 0;
}

.doc-block li {
  font-size: 0.88rem;
  line-height: 1.8;
  color: var(--text-secondary);
}

.example-q {
  font-weight: 500;
  margin-top: 8px;
}

.example-a {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.6);
  border-radius: 6px;
}

/* Context menu */
.context-menu {
  position: fixed;
  z-index: 500;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.context-menu button {
  display: block;
  width: 100%;
  padding: 8px 16px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-primary);
  font-family: inherit;
  text-align: left;
  white-space: nowrap;
}
.context-menu button:hover {
  background: var(--bg-hover);
  color: var(--brand-primary);
}
</style>
