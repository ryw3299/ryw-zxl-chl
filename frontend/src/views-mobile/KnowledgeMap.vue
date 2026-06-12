<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { SAMPLE_DATASETS, DEFAULT_DATASET_ID } from '@/data/knowledge_graph_sample'
import { analyzeKnowledgePoints, loadExternalScript } from '@/utils/knowledgeAnalysis'

const router = useRouter()

const CHART_JS_SRC = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
const G6_SRC = 'https://unpkg.com/@antv/g6@4.8.24/dist/g6.min.js'
const POINTS_JSON_URL = `${import.meta.env.BASE_URL || '/'}visual/points.json`
const POINTS_JSON_DATASET_ID = 'visual-points-json'
const PAGE_SIZE = 12
const NETWORK_FIT_PADDING = [48, 48, 48, 48]
const NETWORK_REFIT_DELAYS = [0, 260, 900, 1800, 3000]

const KEYWORD_COLORS = [
  '#2563eb', '#0891b2', '#059669', '#d97706',
  '#dc2626', '#7c3aed', '#be185d', '#0f766e',
  '#4f46e5', '#ca8a04', '#0284c7', '#65a30d',
]
const CHAPTER_COLORS = ['#2563eb', '#0891b2', '#7c3aed', '#059669', '#d97706', '#dc2626', '#64748b']

const createEmptyAnalysis = () => ({
  vocabulary: [],
  freqForCharts: [],
  total: 0,
  edgeCount: 0,
  edgeWeights: new Map(),
  pointKeywords: new Map(),
  pointCount: 0,
})

const activeDatasetId = ref(DEFAULT_DATASET_ID)
const pointsJsonDataset = ref(null)
const minOccurrenceCount = ref(1)
const searchQuery = ref('')
const selectedKeyword = ref('')
const currentPage = ref(1)
const loading = ref(false)
const errorMessage = ref('')
const analysis = ref(createEmptyAnalysis())
const showDatasetPicker = ref(false)

const datasets = computed(() => [...SAMPLE_DATASETS, pointsJsonDataset.value].filter(Boolean))
const activeDataset = computed(() => datasets.value.find((d) => d.id === activeDatasetId.value) || datasets.value[0])
const pointRecords = computed(() => extractPointRecordsFromDataset(activeDataset.value))
const knowledgePoints = computed(() => pointRecords.value.map((item) => item.text))
const keywordRows = computed(() => analysis.value.freqForCharts || [])
const keywordTotal = computed(() => keywordRows.value.reduce((sum, item) => sum + item.c, 0))
const topKeywordRows = computed(() => keywordRows.value.slice(0, 30))

const selectedKeywordRow = computed(() =>
  keywordRows.value.find((item) => item.k === selectedKeyword.value) || null,
)

const summaryCards = computed(() => [
  { key: 'points', label: '知识点条数', value: pointRecords.value.length, tone: 'blue', icon: 'list' },
  { key: 'vocab',  label: '词表规模',   value: analysis.value.vocabulary.length, tone: 'purple', icon: 'spark' },
  { key: 'total',  label: '关键词计数', value: keywordTotal.value, tone: 'green', icon: 'chart' },
  { key: 'edges',  label: '共现边数',   value: analysis.value.edgeCount, tone: 'orange', icon: 'network' },
])

const statusText = computed(() => {
  if (loading.value) return '正在分析知识点并渲染图表...'
  if (!pointRecords.value.length) return '当前数据集暂无知识点'
  return `${pointRecords.value.length} 条知识点 · 词表 ${analysis.value.vocabulary.length} · 共现边 ${analysis.value.edgeCount}`
})

const filteredPointRecords = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const keyword = selectedKeyword.value
  return pointRecords.value
    .map((item, index) => ({
      ...item, index,
      keywords: analysis.value.pointKeywords.get(String(index)) || [],
    }))
    .filter((item) => {
      const matchesKeyword = !keyword || item.keywords.includes(keyword) || item.text.includes(keyword)
      const matchesSearch = !q || item.text.toLowerCase().includes(q)
      return matchesKeyword && matchesSearch
    })
})

const pagedPointRecords = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredPointRecords.value.slice(start, start + PAGE_SIZE)
})

const totalPages = computed(() => Math.ceil(filteredPointRecords.value.length / PAGE_SIZE))

const pieRef = ref(null)
const barRef = ref(null)
const lineRef = ref(null)
const networkRef = ref(null)

let chartLib = null
let g6Lib = null
let pieChart = null
let barChart = null
let lineChart = null
let g6Graph = null
let rerunTimer = null
let runSeq = 0
let pieRowsCache = []
let barRowsCache = []
let kwNodeRegistered = false
let networkFitTimers = []

function normalizeKnowledgePoints(items) {
  return items
    .map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') return item.text || item.content || item.title || item.name || JSON.stringify(item)
      return String(item || '')
    })
    .map((item) => item.trim())
    .filter(Boolean)
}

function extractKnowledgeArray(data) {
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object') {
    if (Array.isArray(data.knowledge_points)) return data.knowledge_points
    if (Array.isArray(data.knowledgePoints)) return data.knowledgePoints
    if (Array.isArray(data.points)) return data.points
  }
  throw new Error('未找到知识点数组')
}

function extractPointRecordsFromDataset(dataset) {
  if (!dataset) return []
  if (Array.isArray(dataset.chapters)) {
    return dataset.chapters.flatMap((chapter, chapterIndex) =>
      normalizeKnowledgePoints(chapter.knowledge_points || []).map((text, index) => ({
        text,
        chapterId: chapter.id || `ch${chapterIndex + 1}`,
        chapterTitle: chapter.title || `第${chapterIndex + 1}章`,
        chapterColor: chapter.color || CHAPTER_COLORS[chapterIndex % CHAPTER_COLORS.length],
        localIndex: index,
      })),
    )
  }
  return normalizeKnowledgePoints(dataset.knowledge_points || dataset.points || []).map((text, index) => ({
    text, chapterId: '', chapterTitle: '', chapterColor: '#2563eb', localIndex: index,
  }))
}

function hexToRgba(hex, alpha = 1) {
  const normalized = String(hex || '').replace('#', '')
  if (!/^[0-9a-f]{6}$/i.test(normalized)) return hex
  const num = parseInt(normalized, 16)
  return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`
}

function colorForKeyword(index, word, rows) {
  const base = KEYWORD_COLORS[index % KEYWORD_COLORS.length]
  const selected = selectedKeyword.value
  if (!selected) return base
  const selectedInRows = rows.some((row) => row.k === selected)
  if (!selectedInRows) return base
  return word === selected ? base : hexToRgba(base, 0.22)
}

function destroyCharts() {
  pieChart?.destroy(); pieChart = null
  barChart?.destroy(); barChart = null
  lineChart?.destroy(); lineChart = null
}

function destroyNetwork() {
  clearNetworkFitTimers()
  if (g6Graph) {
    try { g6Graph.destroy() } catch { /* no-op */ }
    g6Graph = null
  }
}

function clearNetworkFitTimers() {
  networkFitTimers.forEach((t) => clearTimeout(t))
  networkFitTimers = []
}

function fitNetworkView(graph = g6Graph) {
  if (!graph || graph !== g6Graph) return
  try { graph.fitView(NETWORK_FIT_PADDING); graph.fitCenter() } catch { /* no-op */ }
}

function scheduleNetworkFits(graph = g6Graph) {
  clearNetworkFitTimers()
  NETWORK_REFIT_DELAYS.forEach((delay) => {
    networkFitTimers.push(setTimeout(() => fitNetworkView(graph), delay))
  })
}

async function ensureLibraries() {
  if (chartLib && g6Lib) return [chartLib, g6Lib]
  const [Chart, G6] = await Promise.all([
    loadExternalScript(CHART_JS_SRC, 'Chart'),
    loadExternalScript(G6_SRC, 'G6'),
  ])
  chartLib = Chart; g6Lib = G6
  return [Chart, G6]
}

function renderPie(Chart, rows, total) {
  if (!pieRef.value || !rows.length) return
  const top = rows.slice(0, 8)
  const restSum = rows.slice(8).reduce((sum, item) => sum + item.c, 0)
  pieRowsCache = restSum > 0 ? [...top, { k: '其余', c: restSum, rest: true }] : top

  pieChart = new Chart(pieRef.value, {
    type: 'pie',
    data: {
      labels: pieRowsCache.map((item) => item.k),
      datasets: [{
        data: pieRowsCache.map((item) => item.c),
        backgroundColor: pieRowsCache.map((item, i) => item.rest ? '#cbd5e1' : colorForKeyword(i, item.k, pieRowsCache)),
        borderColor: '#ffffff', borderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      onClick(_, elements) {
        if (!elements.length) return
        const item = pieRowsCache[elements[0].index]
        if (item && !item.rest) selectKeyword(item.k)
      },
      plugins: {
        legend: { position: 'bottom', labels: { color: '#475569', font: { size: 11 }, boxWidth: 10, boxHeight: 10 } },
        tooltip: { callbacks: { label(ctx) { const v = Number(ctx.raw || 0); return ` ${ctx.label}: ${v} (${((v / Math.max(total, 1)) * 100).toFixed(1)}%)` } } },
      },
    },
  })
}

function renderBar(Chart, rows, total) {
  if (!barRef.value || !rows.length) return
  barRowsCache = rows.slice(0, 15)
  barChart = new Chart(barRef.value, {
    type: 'bar',
    data: {
      labels: barRowsCache.map((item) => item.k),
      datasets: [{
        label: '出现次数',
        data: barRowsCache.map((item) => item.c),
        backgroundColor: barRowsCache.map((item, i) => colorForKeyword(i, item.k, barRowsCache)),
        borderColor: barRowsCache.map((_, i) => KEYWORD_COLORS[i % KEYWORD_COLORS.length]),
        borderWidth: 1, borderRadius: 4, barPercentage: 0.72, categoryPercentage: 0.84,
      }],
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      onClick(_, elements) {
        if (!elements.length) return
        const row = barRowsCache[elements[0].index]
        if (row) selectKeyword(row.k)
      },
      scales: {
        x: { ticks: { color: '#64748b', font: { size: 10 } }, grid: { color: 'rgba(148,163,184,0.16)' } },
        y: { ticks: { color: '#475569', font: { size: 10 } }, grid: { display: false } },
      },
      plugins: { legend: { display: false } },
    },
  })
}

function renderLine(Chart, rows, total) {
  if (!lineRef.value || !rows.length) return
  const lineRows = rows.slice(0, 30)
  const probs = lineRows.map((item) => item.c / Math.max(total, 1))
  const cumulative = []; let sum = 0
  for (const v of probs) { sum += v; cumulative.push(sum) }

  lineChart = new Chart(lineRef.value, {
    type: 'line',
    data: {
      labels: lineRows.map((_, i) => String(i + 1)),
      datasets: [
        { label: 'P(k)', data: probs.map((v) => +(v * 100).toFixed(4)), borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.12)', fill: true, tension: 0.25, pointRadius: 2, yAxisID: 'y' },
        { label: '累计%', data: cumulative.map((v) => +(v * 100).toFixed(2)), borderColor: '#2563eb', backgroundColor: 'transparent', tension: 0.2, pointRadius: 2, yAxisID: 'y1' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { color: '#64748b', font: { size: 9 }, maxRotation: 0 }, grid: { color: 'rgba(148,163,184,0.12)' } },
        y: { position: 'left', ticks: { color: '#64748b', font: { size: 9 } }, grid: { color: 'rgba(148,163,184,0.12)' } },
        y1: { position: 'right', ticks: { color: '#64748b', font: { size: 9 } }, grid: { drawOnChartArea: false } },
      },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { color: '#475569', boxWidth: 10, boxHeight: 10, font: { size: 10 } } },
        tooltip: { callbacks: { title(items) { return lineRows[items[0]?.dataIndex ?? 0]?.k || '' } } },
      },
    },
  })
}

function renderCharts(Chart, result) {
  destroyCharts()
  Chart.defaults.color = '#64748b'
  Chart.defaults.borderColor = 'rgba(148,163,184,0.18)'
  const rows = result.freqForCharts || []
  const total = rows.reduce((sum, item) => sum + item.c, 0)
  renderPie(Chart, rows, total)
  renderBar(Chart, rows, total)
  renderLine(Chart, rows, total)
}

function splitNodeLabel(text, maxCharsPerLine = 7) {
  const chars = Array.from(String(text || ''))
  if (chars.length <= maxCharsPerLine) return [chars.join('')]
  if (chars.length <= maxCharsPerLine * 2) {
    const splitAt = Math.ceil(chars.length / 2)
    return [chars.slice(0, splitAt).join(''), chars.slice(splitAt).join('')]
  }
  return [chars.slice(0, maxCharsPerLine).join(''), `${chars.slice(maxCharsPerLine, maxCharsPerLine * 2 - 1).join('')}…`]
}

function measureKeywordNode(label, weight = 0) {
  const lines = splitNodeLabel(label)
  const maxLineLength = Math.max(...lines.map((l) => Array.from(l).length), 1)
  const width = Math.min(160, Math.max(56, maxLineLength * 12 + 20))
  const height = Math.max(28, lines.length * 14 + 12 + Number(weight || 0) * 4)
  return { lines, width, height }
}

function registerKeywordNode(G6) {
  if (kwNodeRegistered) return
  kwNodeRegistered = true
  G6.registerNode('kg-kw', {
    draw(cfg, group) {
      const label = String(cfg.label || '')
      const { lines, width, height } = measureKeywordNode(label, cfg.weight)
      const isMax = Boolean(cfg.isMax)
      group.addShape('rect', {
        attrs: { x: -width / 2, y: -height / 2, width, height, radius: 5, fill: isMax ? '#2563eb' : '#ffffff', stroke: isMax ? '#1d4ed8' : '#93c5fd', lineWidth: isMax ? 2 : 1, shadowColor: 'rgba(37,99,235,0.16)', shadowBlur: isMax ? 10 : 4, shadowOffsetY: 2 },
        name: 'bg',
      })
      lines.forEach((line, i) => {
        group.addShape('text', {
          attrs: { text: line, x: 0, y: (i - (lines.length - 1) / 2) * 13, textAlign: 'center', textBaseline: 'middle', fontSize: 10, fontWeight: isMax ? 700 : 600, fill: isMax ? '#ffffff' : '#1e293b' },
          name: 'txt',
        })
      })
      return group.addShape('rect', {
        attrs: { x: -width / 2, y: -height / 2, width, height, radius: 5, fill: 'rgba(0,0,0,0.004)', stroke: 'transparent', cursor: 'grab' },
        name: 'hit',
      })
    },
    setState(name, value, item) {
      const group = item.getContainer()
      const model = item.getModel()
      const bg = group.find((s) => s.get('name') === 'bg')
      const children = group.get('children') || []
      if (name === 'dimmed') children.forEach((s) => s.attr('opacity', value ? 0.18 : 1))
      if (name === 'selected') {
        bg?.attr({ stroke: value ? '#f59e0b' : model.isMax ? '#1d4ed8' : '#93c5fd', lineWidth: value ? 2.4 : model.isMax ? 2 : 1, shadowColor: value ? 'rgba(245,158,11,0.32)' : 'rgba(37,99,235,0.16)', shadowBlur: value ? 14 : model.isMax ? 10 : 4 })
        group.findAll((s) => s.get('name') === 'txt').forEach((s) => s.attr({ fontWeight: value ? 800 : model.isMax ? 700 : 600 }))
      }
    },
  }, 'single-node')
}

function renderNetwork(G6, result) {
  destroyNetwork()
  if (!networkRef.value || !result.freqForCharts.length) return
  registerKeywordNode(G6)
  const container = networkRef.value
  const graphWidth = container.clientWidth || 340
  const graphHeight = container.clientHeight || 400
  const freqMap = new Map(result.freqForCharts.map((item) => [item.k, item.c]))
  const maxCount = Math.max(...result.freqForCharts.map((item) => item.c), 1)
  const nodeSet = new Set()
  const edges = []

  result.edgeWeights.forEach((inner, source) => {
    inner.forEach((weight, target) => {
      if (weight < 1) return
      nodeSet.add(source); nodeSet.add(target)
      edges.push({ id: `${source}||${target}`, source, target, label: `${weight}`, weight })
    })
  })
  for (const { k } of result.freqForCharts.slice(0, 30)) nodeSet.add(k)

  const nodes = [...nodeSet].map((id) => {
    const count = freqMap.get(id) || 1
    const weight = count / maxCount
    const { width, height } = measureKeywordNode(id, weight)
    return { id, label: id, type: 'kg-kw', count, isMax: count === maxCount, weight, layoutSize: Math.max(width, height) + 20 }
  })

  edges.sort((a, b) => b.weight - a.weight)
  const maxWeight = Math.max(...edges.map((e) => e.weight), 1)
  const graphEdges = edges.slice(0, 160).map((edge) => ({
    ...edge,
    style: { stroke: 'rgba(37,99,235,0.35)', lineWidth: 0.6 + (edge.weight / maxWeight) * 3, endArrow: false, opacity: 0.7 },
    labelCfg: { autoRotate: true, style: { fill: '#64748b', fontSize: 9, background: { fill: '#ffffff', stroke: '#dbeafe', padding: [1, 3, 1, 3] } } },
  }))

  g6Graph = new G6.Graph({
    container, width: graphWidth, height: graphHeight,
    layout: { type: 'force', center: [graphWidth / 2, graphHeight / 2], preventOverlap: true, nodeSize: (node) => node.layoutSize || 72, nodeSpacing: 24, linkDistance: 72, nodeStrength: -80, edgeStrength: 0.2 },
    defaultNode: { type: 'kg-kw' }, defaultEdge: { type: 'line' },
    modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
    fitView: true, fitViewPadding: NETWORK_FIT_PADDING, minZoom: 0.1, maxZoom: 2.5,
  })

  g6Graph.data({ nodes, edges: graphEdges })
  g6Graph.render()
  scheduleNetworkFits(g6Graph)

  g6Graph.on('node:click', (evt) => { const model = evt.item?.getModel(); if (model?.id) selectKeyword(model.id) })
  g6Graph.on('canvas:dragstart', clearNetworkFitTimers)
  g6Graph.on('wheelzoom', clearNetworkFitTimers)
  let shouldFit = true
  g6Graph.on('afterlayout', () => { if (!shouldFit) return; shouldFit = false; scheduleNetworkFits(g6Graph) })
  applyNetworkSelection()
}

function applyChartSelection() {
  if (pieChart && pieRowsCache.length) {
    pieChart.data.datasets[0].backgroundColor = pieRowsCache.map((item, i) => item.rest ? '#cbd5e1' : colorForKeyword(i, item.k, pieRowsCache))
    pieChart.update()
  }
  if (barChart && barRowsCache.length) {
    barChart.data.datasets[0].backgroundColor = barRowsCache.map((item, i) => colorForKeyword(i, item.k, barRowsCache))
    barChart.update()
  }
}

function applyNetworkSelection() {
  if (!g6Graph) return
  const keyword = selectedKeyword.value
  const connected = new Set()
  if (keyword) connected.add(keyword)
  if (keyword) {
    g6Graph.getEdges().forEach((edge) => {
      const m = edge.getModel()
      if (m.source === keyword) connected.add(m.target)
      if (m.target === keyword) connected.add(m.source)
    })
  }
  g6Graph.getNodes().forEach((node) => {
    const m = node.getModel()
    g6Graph.setItemState(node, 'selected', keyword && m.id === keyword)
    g6Graph.setItemState(node, 'dimmed', Boolean(keyword && !connected.has(m.id)))
  })
  g6Graph.getEdges().forEach((edge) => {
    const m = edge.getModel()
    const hi = !keyword || m.source === keyword || m.target === keyword
    g6Graph.updateItem(edge, { style: { ...m.style, opacity: hi ? 0.75 : 0.08 } })
  })
  g6Graph.paint()
}

function applySelectionHighlight() {
  applyChartSelection()
  applyNetworkSelection()
}

async function runAnalysis() {
  if (rerunTimer) { clearTimeout(rerunTimer); rerunTimer = null }
  const seq = ++runSeq
  loading.value = true; errorMessage.value = ''
  destroyCharts(); destroyNetwork()
  await nextTick()
  try {
    const points = knowledgePoints.value
    if (!points.length) { analysis.value = createEmptyAnalysis(); return }
    const [Chart, G6] = await ensureLibraries()
    const result = analyzeKnowledgePoints(points, { minCount: minOccurrenceCount.value })
    if (seq !== runSeq) return
    analysis.value = result
    if (selectedKeyword.value && !result.vocabulary.includes(selectedKeyword.value)) selectedKeyword.value = ''
    await nextTick()
    if (seq !== runSeq) return
    renderCharts(Chart, result)
    renderNetwork(G6, result)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    errorMessage.value = message
    showToast({ message: `渲染失败：${message}`, type: 'fail' })
  } finally {
    if (seq === runSeq) loading.value = false
  }
}

function scheduleAnalysis() {
  if (rerunTimer) clearTimeout(rerunTimer)
  rerunTimer = window.setTimeout(runAnalysis, 120)
}

function selectKeyword(word) { selectedKeyword.value = selectedKeyword.value === word ? '' : word }
function clearKeyword() { selectedKeyword.value = '' }

async function loadPointsJsonDataset({ silent = false } = {}) {
  try {
    const response = await fetch(POINTS_JSON_URL, { cache: 'no-cache' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    const points = normalizeKnowledgePoints(extractKnowledgeArray(data))
    if (!points.length) throw new Error('points.json 中没有有效知识点')
    pointsJsonDataset.value = { id: POINTS_JSON_DATASET_ID, label: 'points.json 关键词连结', description: `来自 points.json，${points.length} 条`, knowledge_points: points }
    if (activeDatasetId.value === POINTS_JSON_DATASET_ID) scheduleAnalysis()
    if (!silent) showToast({ message: `已载入 ${points.length} 条`, type: 'success' })
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    pointsJsonDataset.value = { id: POINTS_JSON_DATASET_ID, label: 'points.json 关键词连结', description: `载入失败：${message}`, knowledge_points: [] }
  }
}

function escapeRegExp(text) { return String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') }
function escapeHtml(text) { return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;') }
function highlightText(text) {
  const terms = [...new Set([selectedKeyword.value, searchQuery.value.trim()].filter(Boolean))].sort((a, b) => b.length - a.length)
  let html = escapeHtml(text)
  if (!terms.length) return html
  return html.replace(new RegExp(terms.map((t) => escapeRegExp(escapeHtml(t))).join('|'), 'gi'), (m) => `<mark>${m}</mark>`)
}

function onResize() {
  if (!g6Graph || !networkRef.value) return
  g6Graph.changeSize(networkRef.value.clientWidth, networkRef.value.clientHeight)
  scheduleNetworkFits(g6Graph)
}

watch(activeDatasetId, () => { selectedKeyword.value = ''; searchQuery.value = ''; currentPage.value = 1; scheduleAnalysis() })
watch(minOccurrenceCount, () => { currentPage.value = 1; scheduleAnalysis() })
watch([selectedKeyword, searchQuery], () => { currentPage.value = 1; applySelectionHighlight() })

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await loadPointsJsonDataset({ silent: true })
  await runAnalysis()
})
onBeforeUnmount(() => {
  if (rerunTimer) clearTimeout(rerunTimer)
  window.removeEventListener('resize', onResize)
  destroyCharts(); destroyNetwork()
})
</script>

<template>
  <div class="km-page">

    <!-- 顶栏 -->
    <div class="km-topbar">
      <button class="km-back" @click="router.push('/m/home')">
        <van-icon name="arrow-left" size="18" />
      </button>
      <div class="km-topbar-center">
        <span class="km-topbar-eyebrow">Knowledge Graph</span>
        <span class="km-topbar-title">知识点关键词可视化</span>
      </div>
      <div style="width:36px" />
    </div>

    <div class="km-shell">

      <!-- 数据集选择 -->
      <div class="km-section-card">
        <p class="km-section-label">数据集</p>
        <div class="km-dataset-list">
          <button
            v-for="d in datasets"
            :key="d.id"
            class="km-ds-chip"
            :class="{ active: activeDatasetId === d.id }"
            @click="activeDatasetId = d.id"
          >{{ d.label }}</button>
        </div>
        <p class="km-meta-text">{{ activeDataset?.description || `${pointRecords.length} 条知识点` }}</p>
      </div>

      <!-- 阈值滑块 -->
      <div class="km-section-card km-slider-card">
        <div class="km-slider-head">
          <span>最少出现次数</span>
          <strong>{{ minOccurrenceCount }}</strong>
        </div>
        <van-slider v-model="minOccurrenceCount" :min="1" :max="12" active-color="#2563eb" />
      </div>

      <!-- 状态条 -->
      <div class="km-status" :class="{ 'km-status--loading': loading }">
        <van-loading v-if="loading" size="14px" color="#1d4ed8" style="margin-right:6px" />
        {{ statusText }}
      </div>
      <p v-if="errorMessage" class="km-error">{{ errorMessage }}</p>

      <!-- 摘要卡 -->
      <div class="km-summary-grid">
        <article v-for="card in summaryCards" :key="card.key" class="km-summary-card">
          <span class="km-summary-icon" :class="`kg-icon--${card.tone}`">
            <svg v-if="card.icon === 'list'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13" /><path d="M3 6h.01M3 12h.01M3 18h.01" /></svg>
            <svg v-else-if="card.icon === 'spark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2z" /></svg>
            <svg v-else-if="card.icon === 'chart'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 16l3-4 3 2 4-7" /></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3" /><circle cx="18" cy="7" r="3" /><circle cx="13" cy="18" r="3" /><path d="M8.7 7l6.6.1M7.8 8.4l3.8 7.1M16.5 9.6L14.2 15" /></svg>
          </span>
          <div>
            <div class="km-summary-value">{{ card.value }}</div>
            <div class="km-summary-label">{{ card.label }}</div>
          </div>
        </article>
      </div>

      <!-- 饼图 -->
      <article class="km-panel">
        <div class="km-panel-head">
          <h2>高频关键词占比</h2>
          <p>Top8 + 其余，按文档频次统计</p>
        </div>
        <div class="km-chart-wrap">
          <canvas ref="pieRef" />
          <div v-if="!keywordRows.length && !loading" class="km-empty">暂无数据</div>
        </div>
      </article>

      <!-- 柱状图 -->
      <article class="km-panel">
        <div class="km-panel-head">
          <h2>文档频次 Top15</h2>
          <p>点击柱项可筛选知识点列表</p>
        </div>
        <div class="km-chart-wrap km-chart-wrap--bar">
          <canvas ref="barRef" />
          <div v-if="!keywordRows.length && !loading" class="km-empty">暂无数据</div>
        </div>
      </article>

      <!-- 折线图 -->
      <article class="km-panel">
        <div class="km-panel-head">
          <h2>概率与累计概率</h2>
          <p>前 30 位关键词 P(k) 与累计占比</p>
        </div>
        <div class="km-chart-wrap">
          <canvas ref="lineRef" />
          <div v-if="!keywordRows.length && !loading" class="km-empty">暂无数据</div>
        </div>
      </article>

      <!-- 关联网络 -->
      <article class="km-panel">
        <div class="km-panel-head">
          <div>
            <h2>关键词关联网络</h2>
            <p>节点为关键词，边为共现关系，可拖拽</p>
          </div>
          <button v-if="selectedKeyword" class="km-clear-btn" @click="clearKeyword">
            {{ selectedKeyword }} ✕
          </button>
        </div>
        <div class="km-network-wrap">
          <div v-if="loading" class="km-empty">分析中...</div>
          <div ref="networkRef" class="km-network" />
          <div v-if="!keywordRows.length && !loading" class="km-empty">暂无数据</div>
        </div>
      </article>

      <!-- 关键词排行 -->
      <article class="km-panel">
        <div class="km-panel-head">
          <h2>关键词排行</h2>
          <p>按文档频次降序排列，点击可筛选</p>
        </div>
        <div class="km-rank-list">
          <button
            v-for="(item, index) in topKeywordRows"
            :key="item.k"
            class="km-rank-row"
            :class="{ 'km-rank-row--active': selectedKeyword === item.k }"
            @click="selectKeyword(item.k)"
          >
            <span class="km-rank-no">{{ index + 1 }}</span>
            <span class="km-rank-word" :style="{ color: KEYWORD_COLORS[index % KEYWORD_COLORS.length] }">{{ item.k }}</span>
            <span class="km-rank-track">
              <span class="km-rank-bar" :style="{ width: `${(item.c / Math.max(topKeywordRows[0]?.c || 1, 1)) * 100}%`, background: KEYWORD_COLORS[index % KEYWORD_COLORS.length] }" />
            </span>
            <span class="km-rank-count">{{ item.c }}</span>
          </button>
        </div>
      </article>

      <!-- 知识点追溯 -->
      <article class="km-panel">
        <div class="km-panel-head">
          <div>
            <h2>知识点追溯</h2>
            <p>
              <template v-if="selectedKeywordRow">"{{ selectedKeywordRow.k }}" {{ selectedKeywordRow.c }} 条 · </template>
              共 {{ filteredPointRecords.length }} 条
            </p>
          </div>
        </div>

        <div class="km-search-wrap">
          <van-search v-model="searchQuery" placeholder="搜索知识点" shape="round" background="transparent" />
        </div>

        <div class="km-point-list">
          <article v-for="item in pagedPointRecords" :key="item.index" class="km-point-card">
            <div class="km-point-meta">
              <span>#{{ item.index + 1 }}</span>
              <span v-if="item.chapterTitle" class="km-chapter-tag" :style="{ color: item.chapterColor, borderColor: hexToRgba(item.chapterColor, 0.36), background: hexToRgba(item.chapterColor, 0.08) }">
                {{ item.chapterTitle }}
              </span>
            </div>
            <p v-html="highlightText(item.text)" />
            <div v-if="item.keywords.length" class="km-point-tags">
              <button v-for="kw in item.keywords.slice(0, 6)" :key="kw" :class="{ active: selectedKeyword === kw }" @click="selectKeyword(kw)">{{ kw }}</button>
            </div>
          </article>
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="km-pagination">
          <button class="km-page-btn" :disabled="currentPage <= 1" @click="currentPage--">
            <van-icon name="arrow-left" size="14" />
          </button>
          <span class="km-page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button class="km-page-btn" :disabled="currentPage >= totalPages" @click="currentPage++">
            <van-icon name="arrow" size="14" />
          </button>
        </div>
      </article>

    </div>
  </div>
</template>

<style scoped>
.km-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 40%, #ffffff 100%);
  padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 24px);
}

/* ── 顶栏 ── */
.km-topbar {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(37,99,235,0.08);
}
.km-back {
  width: 36px; height: 36px; border: none; background: #eff6ff;
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  color: #2563eb; cursor: pointer;
}
.km-topbar-center { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.km-topbar-eyebrow { font-size: 10px; font-weight: 700; color: #2563eb; letter-spacing: 0.06em; text-transform: uppercase; }
.km-topbar-title { font-size: 15px; font-weight: 800; color: #0f172a; }

/* ── Shell ── */
.km-shell {
  padding: 14px 14px 0;
  display: flex; flex-direction: column; gap: 12px;
}

/* ── Section 卡 ── */
.km-section-card {
  background: #fff;
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.km-section-label { margin: 0 0 10px; font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; }
.km-dataset-list { display: flex; flex-wrap: wrap; gap: 7px; }
.km-ds-chip {
  padding: 6px 12px; border-radius: 999px; border: 1.5px solid #dbeafe;
  background: #fff; color: #64748b; font-size: 12px; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
}
.km-ds-chip.active { background: #2563eb; border-color: #2563eb; color: #fff; }
.km-meta-text { margin: 10px 0 0; font-size: 11px; color: #94a3b8; line-height: 1.5; }

/* ── 滑块卡 ── */
.km-slider-card { padding: 14px 16px 18px; }
.km-slider-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px; font-weight: 600; color: #334155; }
.km-slider-head strong { font-size: 18px; font-weight: 800; color: #2563eb; }

/* ── 状态条 ── */
.km-status {
  display: flex; align-items: center;
  padding: 9px 14px; border-radius: 10px;
  background: rgba(255,255,255,0.8);
  border: 1px solid rgba(148,163,184,0.2);
  font-size: 12px; color: #475569;
}
.km-status--loading { color: #1d4ed8; background: #eff6ff; border-color: #bfdbfe; }
.km-error { margin: 0; padding: 9px 14px; border-radius: 10px; font-size: 12px; color: #b91c1c; background: #fef2f2; border: 1px solid #fecaca; }

/* ── 摘要卡 ── */
.km-summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.km-summary-card { display: flex; align-items: center; gap: 12px; background: #fff; border-radius: 16px; padding: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
.km-summary-icon { width: 36px; height: 36px; flex-shrink: 0; display: grid; place-items: center; border-radius: 10px; color: #fff; }
.km-summary-icon svg { width: 18px; height: 18px; }
.kg-icon--blue   { background: linear-gradient(135deg, #2563eb, #0284c7); }
.kg-icon--purple { background: linear-gradient(135deg, #7c3aed, #be185d); }
.kg-icon--green  { background: linear-gradient(135deg, #059669, #0f766e); }
.kg-icon--orange { background: linear-gradient(135deg, #d97706, #dc2626); }
.km-summary-value { font-size: 22px; font-weight: 800; color: #0f172a; line-height: 1; }
.km-summary-label { margin-top: 4px; font-size: 11px; color: #64748b; }

/* ── 面板 ── */
.km-panel { background: #fff; border-radius: 18px; padding: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.km-panel-head { margin-bottom: 12px; display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.km-panel-head h2 { margin: 0; font-size: 15px; font-weight: 800; color: #0f172a; }
.km-panel-head p { margin: 4px 0 0; font-size: 11px; color: #94a3b8; }

/* ── 图表 ── */
.km-chart-wrap { position: relative; height: 260px; }
.km-chart-wrap--bar { height: 320px; }
.km-empty { position: absolute; inset: 0; display: grid; place-items: center; color: #94a3b8; font-size: 13px; pointer-events: none; }

/* ── 网络图 ── */
.km-network-wrap { position: relative; height: 360px; border: 1px solid #dbeafe; border-radius: 12px; overflow: hidden; background: radial-gradient(circle at center, #eff6ff, #f8fafc); }
.km-network { width: 100%; height: 100%; }

.km-clear-btn {
  flex-shrink: 0; padding: 5px 10px; border-radius: 8px;
  background: #fffbeb; border: 1px solid #fde68a;
  color: #92400e; font-size: 11px; font-weight: 700; cursor: pointer;
}

/* ── 排行 ── */
.km-rank-list { display: flex; flex-direction: column; gap: 6px; max-height: 400px; overflow-y: auto; }
.km-rank-row {
  width: 100%; display: grid; grid-template-columns: 24px minmax(60px, 90px) minmax(60px, 1fr) 32px;
  align-items: center; gap: 8px; min-height: 30px;
  border: 0; border-radius: 8px; background: transparent; text-align: left; cursor: pointer; padding: 3px 6px;
}
.km-rank-row:active, .km-rank-row--active { background: #f8fafc; }
.km-rank-no { color: #94a3b8; font-size: 11px; font-weight: 800; text-align: right; }
.km-rank-word { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 700; }
.km-rank-track { height: 6px; overflow: hidden; border-radius: 6px; background: #e2e8f0; }
.km-rank-bar { display: block; height: 100%; border-radius: inherit; }
.km-rank-count { color: #475569; font-size: 12px; font-weight: 800; text-align: right; }

/* ── 搜索 ── */
.km-search-wrap { margin: -4px 0 10px; }
.km-search-wrap :deep(.van-search) { padding: 0; }

/* ── 知识点列表 ── */
.km-point-list { display: flex; flex-direction: column; gap: 10px; }
.km-point-card { padding: 12px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fbfdff; }
.km-point-card p { margin: 8px 0 0; color: #334155; font-size: 13px; line-height: 1.65; word-break: break-word; white-space: pre-wrap; }
.km-point-card :deep(mark) { background: #fef3c7; color: #92400e; border-radius: 3px; padding: 0 2px; }
.km-point-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; color: #94a3b8; font-size: 11px; font-weight: 700; }
.km-chapter-tag { display: inline-flex; align-items: center; padding: 2px 6px; border: 1px solid; border-radius: 6px; }
.km-point-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 9px; }
.km-point-tags button { border: 1px solid #dbeafe; border-radius: 6px; background: #eff6ff; color: #1d4ed8; padding: 2px 7px; font-size: 11px; font-weight: 700; cursor: pointer; }
.km-point-tags button.active { border-color: #f59e0b; background: #fffbeb; color: #92400e; }

/* ── 分页 ── */
.km-pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 14px; }
.km-page-btn { width: 34px; height: 34px; border-radius: 10px; border: 1px solid #dbeafe; background: #fff; color: #2563eb; display: flex; align-items: center; justify-content: center; cursor: pointer; }
.km-page-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.km-page-info { font-size: 13px; font-weight: 700; color: #475569; }

.km-rank-list::-webkit-scrollbar { width: 0; }
</style>
