<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { SAMPLE_DATASETS, DEFAULT_DATASET_ID } from '@/data/knowledge_graph_sample'
import { analyzeKnowledgePoints, loadExternalScript } from '@/utils/knowledgeAnalysis'

const CHART_JS_SRC = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
const G6_SRC = 'https://unpkg.com/@antv/g6@4.8.24/dist/g6.min.js'
const POINTS_JSON_URL = `${import.meta.env.BASE_URL || '/'}visual/points.json`
const POINTS_JSON_DATASET_ID = 'visual-points-json'
const PAGE_SIZE = 18
const NETWORK_FIT_PADDING = [72, 88, 72, 88]
const NETWORK_REFIT_DELAYS = [0, 260, 900, 1800, 3000]

const KEYWORD_COLORS = [
  '#2563eb',
  '#0891b2',
  '#2dd4bf',
  '#d97706',
  '#dc2626',
  '#7c3aed',
  '#be185d',
  '#5eead4',
  '#4f46e5',
  '#ca8a04',
  '#0284c7',
  '#65a30d',
]

const CHAPTER_COLORS = ['#2563eb', '#0891b2', '#7c3aed', '#2dd4bf', '#d97706', '#dc2626', '#64748b']

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
const fallbackNetwork = ref({ nodes: [], edges: [] })

const fallbackConnectedWords = computed(() => {
  const keyword = selectedKeyword.value
  const connected = new Set()
  if (!keyword) return connected
  connected.add(keyword)
  fallbackNetwork.value.edges.forEach((edge) => {
    if (edge.source === keyword) connected.add(edge.target)
    if (edge.target === keyword) connected.add(edge.source)
  })
  return connected
})

const datasets = computed(() => [...SAMPLE_DATASETS, pointsJsonDataset.value].filter(Boolean))

const activeDataset = computed(
  () => datasets.value.find((d) => d.id === activeDatasetId.value) || datasets.value[0],
)

const pointRecords = computed(() => extractPointRecordsFromDataset(activeDataset.value))
const knowledgePoints = computed(() => pointRecords.value.map((item) => item.text))
const keywordRows = computed(() => analysis.value.freqForCharts || [])
const keywordTotal = computed(() => keywordRows.value.reduce((sum, item) => sum + item.c, 0))
const topKeywordRows = computed(() => keywordRows.value.slice(0, 30))

const selectedKeywordRow = computed(() =>
  keywordRows.value.find((item) => item.k === selectedKeyword.value) || null,
)

const summaryCards = computed(() => [
  {
    key: 'points',
    label: '知识点条数',
    value: pointRecords.value.length,
    tone: 'blue',
    icon: 'list',
  },
  {
    key: 'vocab',
    label: '词表规模',
    value: analysis.value.vocabulary.length,
    tone: 'purple',
    icon: 'spark',
  },
  {
    key: 'total',
    label: '关键词总计数',
    value: keywordTotal.value,
    tone: 'green',
    icon: 'chart',
  },
  {
    key: 'edges',
    label: '共现边条数',
    value: analysis.value.edgeCount,
    tone: 'orange',
    icon: 'network',
  },
])

const statusText = computed(() => {
  if (loading.value) return '正在分析知识点并渲染图表...'
  if (!pointRecords.value.length) return '当前数据集暂无知识点'
  return `知识点 ${pointRecords.value.length} 条 · 词表 ${analysis.value.vocabulary.length} · 关键词出现总计数 ${keywordTotal.value} · 共现边 ${analysis.value.edgeCount} 条`
})

const filteredPointRecords = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const keyword = selectedKeyword.value
  return pointRecords.value
    .map((item, index) => ({
      ...item,
      index,
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

const activeDatasetDescription = computed(() => {
  const dataset = activeDataset.value
  if (!dataset) return ''
  if (dataset.description) return dataset.description
  if (Array.isArray(dataset.chapters)) return `${dataset.chapters.length} 个章节`
  return `${pointRecords.value.length} 条知识点`
})

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
let fallbackNetworkState = null

function normalizeKnowledgePoints(items) {
  return items
    .map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') {
        return item.text || item.content || item.title || item.name || JSON.stringify(item)
      }
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
  throw new Error('未找到知识点数组，支持 knowledge_points / knowledgePoints / points 或根级数组')
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
    text,
    chapterId: '',
    chapterTitle: '',
    chapterColor: '#2563eb',
    localIndex: index,
  }))
}

function hexToRgba(hex, alpha = 1) {
  const normalized = String(hex || '').replace('#', '')
  if (!/^[0-9a-f]{6}$/i.test(normalized)) return hex
  const num = parseInt(normalized, 16)
  const r = (num >> 16) & 255
  const g = (num >> 8) & 255
  const b = num & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
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
  if (pieChart) {
    pieChart.destroy()
    pieChart = null
  }
  if (barChart) {
    barChart.destroy()
    barChart = null
  }
  if (lineChart) {
    lineChart.destroy()
    lineChart = null
  }
}

function destroyNetwork() {
  clearNetworkFitTimers()
  fallbackNetworkState = null
  fallbackNetwork.value = { nodes: [], edges: [] }
  if (g6Graph) {
    try {
      g6Graph.destroy()
    } catch {
      // G6 destroy can throw during hot reload; the instance is unusable either way.
    }
    g6Graph = null
  }
}

function clearNetworkFitTimers() {
  networkFitTimers.forEach((timer) => clearTimeout(timer))
  networkFitTimers = []
}

function fitNetworkView(graph = g6Graph) {
  if (!graph || graph !== g6Graph) return
  try {
    graph.fitView(NETWORK_FIT_PADDING)
    graph.fitCenter()
  } catch {
    // Graph may already be destroyed during route switches or hot reload.
  }
}

function scheduleNetworkFits(graph = g6Graph) {
  clearNetworkFitTimers()
  NETWORK_REFIT_DELAYS.forEach((delay) => {
    const timer = setTimeout(() => fitNetworkView(graph), delay)
    networkFitTimers.push(timer)
  })
}

async function ensureLibraries() {
  if (chartLib && g6Lib) return [chartLib, g6Lib]
  const [chartResult, g6Result] = await Promise.allSettled([
    chartLib ? Promise.resolve(chartLib) : loadExternalScript(CHART_JS_SRC, 'Chart'),
    g6Lib ? Promise.resolve(g6Lib) : loadExternalScript(G6_SRC, 'G6'),
  ])

  if (chartResult.status === 'fulfilled') chartLib = chartResult.value
  if (g6Result.status === 'fulfilled') g6Lib = g6Result.value

  return [chartLib, g6Lib]
}

function renderPie(Chart, rows, total) {
  if (!pieRef.value || !rows.length) return
  const top = rows.slice(0, 10)
  const restSum = rows.slice(10).reduce((sum, item) => sum + item.c, 0)
  pieRowsCache = restSum > 0 ? [...top, { k: '其余', c: restSum, rest: true }] : top

  pieChart = new Chart(pieRef.value, {
    type: 'pie',
    data: {
      labels: pieRowsCache.map((item) => item.k),
      datasets: [
        {
          data: pieRowsCache.map((item) => item.c),
          backgroundColor: pieRowsCache.map((item, index) =>
            item.rest ? '#cbd5e1' : colorForKeyword(index, item.k, pieRowsCache),
          ),
          borderColor: '#ffffff',
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick(_, elements) {
        if (!elements.length) return
        const item = pieRowsCache[elements[0].index]
        if (!item || item.rest) return
        selectKeyword(item.k)
      },
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#475569', font: { size: 12 }, boxWidth: 12, boxHeight: 12 },
          onClick(_, item) {
            const row = pieRowsCache[item.index]
            if (row && !row.rest) selectKeyword(row.k)
          },
        },
        tooltip: {
          callbacks: {
            label(ctx) {
              const value = Number(ctx.raw || 0)
              const pct = ((value / Math.max(total, 1)) * 100).toFixed(2)
              return ` ${ctx.label}: ${value} 次（${pct}%）`
            },
          },
        },
      },
    },
  })
}

function renderBar(Chart, rows, total) {
  if (!barRef.value || !rows.length) return
  barRowsCache = rows.slice(0, 20)

  barChart = new Chart(barRef.value, {
    type: 'bar',
    data: {
      labels: barRowsCache.map((item) => item.k),
      datasets: [
        {
          label: '出现知识点条数',
          data: barRowsCache.map((item) => item.c),
          backgroundColor: barRowsCache.map((item, index) => colorForKeyword(index, item.k, barRowsCache)),
          borderColor: barRowsCache.map((_, index) => KEYWORD_COLORS[index % KEYWORD_COLORS.length]),
          borderWidth: 1,
          borderRadius: 6,
          barPercentage: 0.64,
          categoryPercentage: 0.82,
        },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      onClick(_, elements) {
        if (!elements.length) return
        const row = barRowsCache[elements[0].index]
        if (row) selectKeyword(row.k)
      },
      scales: {
        x: {
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(148, 163, 184, 0.16)' },
        },
        y: {
          ticks: { color: '#475569', font: { size: 11 } },
          grid: { display: false },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel(ctx) {
              const value = Number(ctx.raw || 0)
              const pct = ((value / Math.max(total, 1)) * 100).toFixed(2)
              return `相对全部关键词计数：${pct}%`
            },
          },
        },
      },
    },
  })
}

function renderLine(Chart, rows, total) {
  if (!lineRef.value || !rows.length) return
  const lineRows = rows.slice(0, 40)
  const probs = lineRows.map((item) => item.c / Math.max(total, 1))
  const cumulative = []
  let sum = 0
  for (const value of probs) {
    sum += value
    cumulative.push(sum)
  }

  lineChart = new Chart(lineRef.value, {
    type: 'line',
    data: {
      labels: lineRows.map((_, index) => String(index + 1)),
      datasets: [
        {
          label: '单关键词概率 P(k)',
          data: probs.map((value) => Number((value * 100).toFixed(4))),
          borderColor: '#2dd4bf',
          backgroundColor: 'rgba(45, 212, 191, 0.12)',
          fill: true,
          tension: 0.25,
          pointRadius: 2,
          yAxisID: 'y',
        },
        {
          label: '累计概率 ΣP',
          data: cumulative.map((value) => Number((value * 100).toFixed(2))),
          borderColor: '#2563eb',
          backgroundColor: 'transparent',
          tension: 0.2,
          pointRadius: 2,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          title: { display: true, text: '按频次排序的名次', color: '#64748b' },
          ticks: { color: '#64748b', maxRotation: 0 },
          grid: { color: 'rgba(148, 163, 184, 0.12)' },
        },
        y: {
          position: 'left',
          title: { display: true, text: 'P × 100 (%)', color: '#64748b' },
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(148, 163, 184, 0.12)' },
        },
        y1: {
          position: 'right',
          title: { display: true, text: '累计 %', color: '#64748b' },
          ticks: { color: '#64748b' },
          grid: { drawOnChartArea: false },
        },
      },
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: { color: '#475569', boxWidth: 12, boxHeight: 12 },
        },
        tooltip: {
          callbacks: {
            title(items) {
              const index = items[0]?.dataIndex ?? 0
              return lineRows[index]?.k || ''
            },
          },
        },
      },
    },
  })
}

function renderCharts(Chart, result) {
  destroyCharts()
  Chart.defaults.color = '#64748b'
  Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.18)'
  const rows = result.freqForCharts || []
  const total = rows.reduce((sum, item) => sum + item.c, 0)
  renderPie(Chart, rows, total)
  renderBar(Chart, rows, total)
  renderLine(Chart, rows, total)
}

function prepareFallbackCanvas(canvas) {
  if (!canvas) return null
  const rect = canvas.parentElement?.getBoundingClientRect()
  const width = Math.max(Math.floor(rect?.width || canvas.clientWidth || 320), 1)
  const height = Math.max(Math.floor(rect?.height || canvas.clientHeight || 260), 1)
  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.floor(width * ratio)
  canvas.height = Math.floor(height * ratio)
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`

  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
  ctx.clearRect(0, 0, width, height)
  ctx.font = '12px "Microsoft YaHei", sans-serif'
  ctx.textBaseline = 'middle'
  return { ctx, width, height }
}

function drawFallbackPie(canvas, rows, total) {
  const prepared = prepareFallbackCanvas(canvas)
  if (!prepared || !rows.length) return
  const { ctx, width, height } = prepared
  const top = rows.slice(0, 8)
  const rest = rows.slice(8).reduce((sum, item) => sum + item.c, 0)
  const data = rest > 0 ? [...top, { k: '其余', c: rest, rest: true }] : top
  const cx = width * 0.34
  const cy = height * 0.52
  const radius = Math.min(width * 0.2, height * 0.32)
  let start = -Math.PI / 2

  data.forEach((item, index) => {
    const angle = (item.c / Math.max(total, 1)) * Math.PI * 2
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.arc(cx, cy, radius, start, start + angle)
    ctx.closePath()
    ctx.fillStyle = item.rest ? '#cbd5e1' : KEYWORD_COLORS[index % KEYWORD_COLORS.length]
    ctx.fill()
    start += angle
  })

  ctx.beginPath()
  ctx.arc(cx, cy, radius * 0.52, 0, Math.PI * 2)
  ctx.fillStyle = '#ffffff'
  ctx.fill()
  ctx.fillStyle = '#0f172a'
  ctx.font = '700 22px "Microsoft YaHei", sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(String(total), cx, cy - 6)
  ctx.fillStyle = '#64748b'
  ctx.font = '12px "Microsoft YaHei", sans-serif'
  ctx.fillText('总频次', cx, cy + 18)

  data.slice(0, 8).forEach((item, index) => {
    const x = width * 0.62
    const y = 44 + index * 28
    ctx.fillStyle = KEYWORD_COLORS[index % KEYWORD_COLORS.length]
    ctx.fillRect(x, y - 6, 10, 10)
    ctx.fillStyle = '#334155'
    ctx.textAlign = 'left'
    ctx.font = '700 12px "Microsoft YaHei", sans-serif'
    ctx.fillText(item.k, x + 16, y)
    ctx.fillStyle = '#94a3b8'
    ctx.textAlign = 'right'
    ctx.fillText(String(item.c), width - 18, y)
  })
}

function drawFallbackBar(canvas, rows) {
  const prepared = prepareFallbackCanvas(canvas)
  if (!prepared || !rows.length) return
  const { ctx, width, height } = prepared
  const data = rows.slice(0, 12)
  const max = Math.max(...data.map((item) => item.c), 1)
  const left = 92
  const top = 24
  const rowHeight = Math.min(22, (height - 48) / data.length)

  data.forEach((item, index) => {
    const y = top + index * rowHeight
    const barWidth = ((width - left - 50) * item.c) / max
    ctx.fillStyle = '#475569'
    ctx.textAlign = 'right'
    ctx.font = '700 11px "Microsoft YaHei", sans-serif'
    ctx.fillText(item.k, left - 10, y + rowHeight / 2)
    ctx.fillStyle = 'rgba(219, 234, 254, 0.88)'
    ctx.fillRect(left, y + 4, width - left - 50, rowHeight - 8)
    ctx.fillStyle = KEYWORD_COLORS[index % KEYWORD_COLORS.length]
    ctx.fillRect(left, y + 4, barWidth, rowHeight - 8)
    ctx.fillStyle = '#64748b'
    ctx.textAlign = 'left'
    ctx.fillText(String(item.c), left + barWidth + 8, y + rowHeight / 2)
  })
}

function drawFallbackLine(canvas, rows, total) {
  const prepared = prepareFallbackCanvas(canvas)
  if (!prepared || !rows.length) return
  const { ctx, width, height } = prepared
  const data = rows.slice(0, 32)
  const left = 42
  const right = 24
  const top = 24
  const bottom = 36
  const chartWidth = width - left - right
  const chartHeight = height - top - bottom
  let sum = 0
  const points = data.map((item, index) => {
    sum += item.c / Math.max(total, 1)
    return {
      x: left + (index / Math.max(data.length - 1, 1)) * chartWidth,
      y: top + (1 - sum) * chartHeight,
    }
  })

  ctx.strokeStyle = '#e2e8f0'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(left, top)
  ctx.lineTo(left, height - bottom)
  ctx.lineTo(width - right, height - bottom)
  ctx.stroke()

  ctx.beginPath()
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y)
    else ctx.lineTo(point.x, point.y)
  })
  ctx.strokeStyle = '#2dd4bf'
  ctx.lineWidth = 3
  ctx.stroke()

  points.forEach((point) => {
    ctx.beginPath()
    ctx.arc(point.x, point.y, 2.5, 0, Math.PI * 2)
    ctx.fillStyle = '#2dd4bf'
    ctx.fill()
  })

  ctx.fillStyle = '#64748b'
  ctx.textAlign = 'left'
  ctx.font = '12px "Microsoft YaHei", sans-serif'
  ctx.fillText('累计概率曲线', left, height - 14)
}

function renderFallbackCharts(result) {
  destroyCharts()
  const rows = result.freqForCharts || []
  const total = rows.reduce((sum, item) => sum + item.c, 0)
  drawFallbackPie(pieRef.value, rows, total)
  drawFallbackBar(barRef.value, rows)
  drawFallbackLine(lineRef.value, rows, total)
}

function splitNodeLabel(text, maxCharsPerLine = 9) {
  const chars = Array.from(String(text || ''))
  if (chars.length <= maxCharsPerLine) return [chars.join('')]
  if (chars.length <= maxCharsPerLine * 2) {
    const splitAt = Math.ceil(chars.length / 2)
    return [chars.slice(0, splitAt).join(''), chars.slice(splitAt).join('')]
  }
  return [
    chars.slice(0, maxCharsPerLine).join(''),
    `${chars.slice(maxCharsPerLine, maxCharsPerLine * 2 - 1).join('')}…`,
  ]
}

function measureKeywordNode(label, weight = 0) {
  const lines = splitNodeLabel(label)
  const maxLineLength = Math.max(...lines.map((line) => Array.from(line).length), 1)
  const width = Math.min(220, Math.max(72, maxLineLength * 14 + 30))
  const height = Math.max(34, lines.length * 17 + 16 + Number(weight || 0) * 6)
  return { lines, width, height }
}

function setNetworkCursor(cursor) {
  if (!g6Graph) return
  const canvas = g6Graph.get('canvas')
  const el = canvas && canvas.get('el')
  if (el?.style) el.style.cursor = cursor || ''
}

function approxNodeRadius(item) {
  try {
    const box = item.getBBox()
    return Math.sqrt((box.width * box.width + box.height * box.height) / 4) + 8
  } catch {
    return 36
  }
}

function bindSoftRepulsionWhileDragging(graph) {
  const jelly = 0.34
  graph.on('node:drag', (evt) => {
    const dragged = evt.item
    if (!dragged || (typeof dragged.getType === 'function' && dragged.getType() !== 'node')) return
    const draggedModel = dragged.getModel()
    const x0 = draggedModel.x
    const y0 = draggedModel.y
    if (typeof x0 !== 'number' || typeof y0 !== 'number') return

    const r0 = approxNodeRadius(dragged)
    for (const node of graph.getNodes()) {
      if (node === dragged) continue
      const model = node.getModel()
      const x1 = model.x
      const y1 = model.y
      if (typeof x1 !== 'number' || typeof y1 !== 'number') continue
      const r1 = approxNodeRadius(node)
      const dx = x1 - x0
      const dy = y1 - y0
      const distance = Math.hypot(dx, dy)
      const required = r0 + r1 + 12
      if (distance >= required || distance < 1e-6) continue
      const push = (required - distance) * jelly
      graph.updateItem(node, {
        x: x1 + (dx / distance) * push,
        y: y1 + (dy / distance) * push,
      })
    }
  })
}

function reheatForceLayout(graph) {
  try {
    const layoutController = graph.get('layoutController')
    const method =
      layoutController?.layoutMethod ||
      (Array.isArray(layoutController?.layoutMethods) && layoutController.layoutMethods[0])
    const simulation = method?.forceSimulation || method?.simulation
    if (simulation && typeof simulation.alpha === 'function') {
      const current = typeof simulation.alpha() === 'number' ? simulation.alpha() : 0
      simulation.alpha(Math.max(current, 0.42))
      if (typeof simulation.restart === 'function') simulation.restart()
    }
  } catch {
    // Layout reheating is best-effort; dragging still works without it.
  }
}

function registerKeywordNode(G6) {
  if (kwNodeRegistered) return
  kwNodeRegistered = true
  G6.registerNode(
    'kg-kw',
    {
      draw(cfg, group) {
        const label = String(cfg.label || '')
        const { lines, width, height } = measureKeywordNode(label, cfg.weight)
        const isMax = Boolean(cfg.isMax)
        group.addShape('rect', {
          attrs: {
            x: -width / 2,
            y: -height / 2,
            width,
            height,
            radius: 6,
            fill: isMax ? '#2563eb' : '#ffffff',
            stroke: isMax ? '#1d4ed8' : '#93c5fd',
            lineWidth: isMax ? 2 : 1.2,
            shadowColor: 'rgba(37, 99, 235, 0.16)',
            shadowBlur: isMax ? 12 : 6,
            shadowOffsetY: 2,
          },
          name: 'bg',
        })
        lines.forEach((line, index) => {
          group.addShape('text', {
            attrs: {
              text: line,
              x: 0,
              y: (index - (lines.length - 1) / 2) * 16,
              textAlign: 'center',
              textBaseline: 'middle',
              fontSize: 11,
              fontWeight: isMax ? 700 : 600,
              fill: isMax ? '#ffffff' : '#1e293b',
            },
            name: 'txt',
          })
        })
        return group.addShape('rect', {
          attrs: {
            x: -width / 2,
            y: -height / 2,
            width,
            height,
            radius: 6,
            fill: 'rgba(0,0,0,0.004)',
            stroke: 'transparent',
            cursor: 'grab',
          },
          name: 'hit',
        })
      },
      setState(name, value, item) {
        const group = item.getContainer()
        const model = item.getModel()
        const bg = group.find((shape) => shape.get('name') === 'bg')
        const txt = group.find((shape) => shape.get('name') === 'txt')
        const children = group.get('children') || []

        if (name === 'dimmed') {
          children.forEach((shape) => shape.attr('opacity', value ? 0.18 : 1))
        }
        if (name === 'selected') {
          bg?.attr({
            stroke: value ? '#f59e0b' : model.isMax ? '#1d4ed8' : '#93c5fd',
            lineWidth: value ? 2.6 : model.isMax ? 2 : 1.2,
            shadowColor: value ? 'rgba(245, 158, 11, 0.32)' : 'rgba(37, 99, 235, 0.16)',
            shadowBlur: value ? 16 : model.isMax ? 12 : 6,
          })
          const txtShapes = group.findAll((shape) => shape.get('name') === 'txt')
          txtShapes.forEach((shape) => shape.attr({ fontWeight: value ? 800 : model.isMax ? 700 : 600 }))
        }
      },
    },
    'single-node',
  )
}

function renderNetwork(G6, result) {
  destroyNetwork()
  if (!networkRef.value || !result.freqForCharts.length) return

  registerKeywordNode(G6)

  const container = networkRef.value
  const graphWidth = container.clientWidth || 900
  const graphHeight = container.clientHeight || 540
  const freqMap = new Map(result.freqForCharts.map((item) => [item.k, item.c]))
  const maxCount = Math.max(...result.freqForCharts.map((item) => item.c), 1)
  const nodeSet = new Set()
  const edges = []

  result.edgeWeights.forEach((inner, source) => {
    inner.forEach((weight, target) => {
      if (weight < 1) return
      nodeSet.add(source)
      nodeSet.add(target)
      edges.push({
        id: `${source}||${target}`,
        source,
        target,
        label: `共现 ${weight}`,
        weight,
      })
    })
  })

  for (const { k } of result.freqForCharts.slice(0, 40)) {
    nodeSet.add(k)
  }

  const nodes = [...nodeSet].map((id) => {
    const count = freqMap.get(id) || 1
    const weight = count / maxCount
    const { width, height } = measureKeywordNode(id, weight)
    return {
      id,
      label: id,
      type: 'kg-kw',
      count,
      isMax: count === maxCount,
      weight,
      layoutSize: Math.max(width, height) + 28,
    }
  })

  edges.sort((a, b) => b.weight - a.weight)
  const maxWeight = Math.max(...edges.map((item) => item.weight), 1)
  const graphEdges = edges.slice(0, 220).map((edge) => ({
    ...edge,
    style: {
      stroke: 'rgba(37, 99, 235, 0.38)',
      lineWidth: 0.8 + (edge.weight / maxWeight) * 4,
      endArrow: false,
      opacity: 0.72,
    },
    labelCfg: {
      autoRotate: true,
      style: {
        fill: '#64748b',
        fontSize: 10,
        background: { fill: '#ffffff', stroke: '#dbeafe', padding: [2, 4, 2, 4] },
      },
    },
  }))

  g6Graph = new G6.Graph({
    container,
    width: graphWidth,
    height: graphHeight,
    layout: {
      type: 'force',
      center: [graphWidth / 2, graphHeight / 2],
      preventOverlap: true,
      nodeSize: (node) => node.layoutSize || 96,
      nodeSpacing: 34,
      linkDistance: 96,
      nodeStrength: -95,
      edgeStrength: 0.24,
    },
    defaultNode: { type: 'kg-kw' },
    defaultEdge: { type: 'line' },
    modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
    fitView: true,
    fitViewPadding: NETWORK_FIT_PADDING,
    minZoom: 0.12,
    maxZoom: 2.5,
  })

  g6Graph.data({ nodes, edges: graphEdges })
  g6Graph.render()
  scheduleNetworkFits(g6Graph)

  bindSoftRepulsionWhileDragging(g6Graph)
  g6Graph.on('node:mouseenter', () => setNetworkCursor('grab'))
  g6Graph.on('node:mouseleave', () => setNetworkCursor(''))
  g6Graph.on('node:dragstart', () => {
    clearNetworkFitTimers()
    setNetworkCursor('grabbing')
  })
  g6Graph.on('node:dragend', (evt) => {
    reheatForceLayout(g6Graph)
    const item = evt.item
    if (item && typeof item.getType === 'function' && item.getType() === 'node') setNetworkCursor('grab')
    else setNetworkCursor('')
  })
  g6Graph.on('node:click', (evt) => {
    const model = evt.item?.getModel()
    if (model?.id) selectKeyword(model.id)
  })
  g6Graph.on('canvas:dragstart', clearNetworkFitTimers)
  g6Graph.on('wheelzoom', clearNetworkFitTimers)

  let shouldFitAfterLayout = true
  g6Graph.on('afterlayout', () => {
    if (!shouldFitAfterLayout) return
    shouldFitAfterLayout = false
    scheduleNetworkFits(g6Graph)
  })

  applySelectionHighlight()
}

function renderNetworkFallback(result) {
  destroyNetwork()
  if (!networkRef.value || !result.freqForCharts.length) return

  const rows = result.freqForCharts.slice(0, 24)
  const maxCount = Math.max(...rows.map((item) => item.c), 1)
  const positions = new Map()
  const nodes = rows.map((item, index) => {
    const isCenter = index === 0
    const angle = -Math.PI / 2 + ((index - 1) / Math.max(rows.length - 1, 1)) * Math.PI * 2
    const radiusX = index < 9 ? 31 : 42
    const radiusY = index < 9 ? 27 : 38
    const node = {
      ...item,
      x: isCenter ? 50 : 50 + Math.cos(angle) * radiusX,
      y: isCenter ? 50 : 50 + Math.sin(angle) * radiusY,
      color: KEYWORD_COLORS[index % KEYWORD_COLORS.length],
      scale: 0.88 + (item.c / maxCount) * 0.34,
    }
    positions.set(item.k, node)
    return node
  })

  const visibleWords = new Set(nodes.map((item) => item.k))
  const edges = []
  result.edgeWeights.forEach((inner, source) => {
    if (!visibleWords.has(source)) return
    inner.forEach((weight, target) => {
      if (!visibleWords.has(target) || weight < 1) return
      edges.push({ source, target, weight })
    })
  })
  edges.sort((a, b) => b.weight - a.weight)
  const maxWeight = Math.max(...edges.map((item) => item.weight), 1)

  fallbackNetwork.value = {
    nodes,
    edges: edges
      .slice(0, 72)
      .map((edge) => {
        const source = positions.get(edge.source)
        const target = positions.get(edge.target)
        if (!source || !target) return null
        return {
          ...edge,
          x1: source.x,
          y1: source.y,
          x2: target.x,
          y2: target.y,
          width: 0.14 + (edge.weight / maxWeight) * 0.74,
        }
      })
      .filter(Boolean),
  }
}

function fallbackNodeStyle(node) {
  return {
    left: `${node.x}%`,
    top: `${node.y}%`,
    '--node-color': node.color,
    '--node-scale': node.scale,
  }
}

function isFallbackNodeDimmed(word) {
  return Boolean(selectedKeyword.value && !fallbackConnectedWords.value.has(word))
}

function isFallbackEdgeDimmed(edge) {
  const keyword = selectedKeyword.value
  return Boolean(keyword && edge.source !== keyword && edge.target !== keyword)
}

function applyChartSelection() {
  if (pieChart && pieRowsCache.length) {
    pieChart.data.datasets[0].backgroundColor = pieRowsCache.map((item, index) =>
      item.rest ? '#cbd5e1' : colorForKeyword(index, item.k, pieRowsCache),
    )
    pieChart.update()
  }

  if (barChart && barRowsCache.length) {
    barChart.data.datasets[0].backgroundColor = barRowsCache.map((item, index) =>
      colorForKeyword(index, item.k, barRowsCache),
    )
    barChart.update()
  }
}

function applyNetworkSelection() {
  if (!g6Graph) {
    applyFallbackNetworkSelection()
    return
  }

  const keyword = selectedKeyword.value
  const connected = new Set()
  if (keyword) connected.add(keyword)

  if (keyword) {
    g6Graph.getEdges().forEach((edge) => {
      const model = edge.getModel()
      if (model.source === keyword) connected.add(model.target)
      if (model.target === keyword) connected.add(model.source)
    })
  }

  g6Graph.getNodes().forEach((node) => {
    const model = node.getModel()
    g6Graph.setItemState(node, 'selected', keyword && model.id === keyword)
    g6Graph.setItemState(node, 'dimmed', Boolean(keyword && !connected.has(model.id)))
  })

  g6Graph.getEdges().forEach((edge) => {
    const model = edge.getModel()
    const highlighted = !keyword || model.source === keyword || model.target === keyword
    g6Graph.updateItem(edge, {
      style: {
        ...model.style,
        opacity: highlighted ? 0.78 : 0.08,
      },
      labelCfg: {
        ...model.labelCfg,
        style: {
          ...model.labelCfg?.style,
          opacity: highlighted ? 1 : 0.12,
        },
      },
    })
  })
  g6Graph.paint()
}

function applyFallbackNetworkSelection() {
  if (!fallbackNetworkState) return

  const keyword = selectedKeyword.value
  const connected = new Set()
  if (keyword) connected.add(keyword)

  fallbackNetworkState.lines.forEach((line) => {
    const source = line.dataset.source
    const target = line.dataset.target
    if (source === keyword) connected.add(target)
    if (target === keyword) connected.add(source)
  })

  fallbackNetworkState.buttons.forEach((button) => {
    const word = button.dataset.word
    button.classList.toggle('is-selected', Boolean(keyword && word === keyword))
    button.classList.toggle('is-dimmed', Boolean(keyword && !connected.has(word)))
  })

  fallbackNetworkState.lines.forEach((line) => {
    const source = line.dataset.source
    const target = line.dataset.target
    const active = !keyword || source === keyword || target === keyword
    line.classList.toggle('is-dimmed', !active)
  })
}

function applySelectionHighlight() {
  applyChartSelection()
  applyNetworkSelection()
}

async function runAnalysis() {
  if (rerunTimer) {
    clearTimeout(rerunTimer)
    rerunTimer = null
  }

  const seq = ++runSeq
  loading.value = true
  errorMessage.value = ''
  destroyCharts()
  destroyNetwork()

  await nextTick()

  try {
    const points = knowledgePoints.value
    if (!points.length) {
      analysis.value = createEmptyAnalysis()
      return
    }

    const [Chart, G6] = await ensureLibraries()
    const result = analyzeKnowledgePoints(points, {
      minCount: minOccurrenceCount.value,
    })

    if (seq !== runSeq) return
    analysis.value = result
    if (selectedKeyword.value && !result.vocabulary.includes(selectedKeyword.value)) {
      selectedKeyword.value = ''
    }

    await nextTick()
    if (seq !== runSeq) return
    if (Chart) renderCharts(Chart, result)
    else renderFallbackCharts(result)

    if (G6) renderNetwork(G6, result)
    else renderNetworkFallback(result)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    errorMessage.value = message
    ElMessage.error(`知识图谱渲染失败：${message}`)
  } finally {
    if (seq === runSeq) loading.value = false
  }
}

function scheduleAnalysis() {
  if (rerunTimer) clearTimeout(rerunTimer)
  rerunTimer = window.setTimeout(() => {
    runAnalysis()
  }, 120)
}

function selectKeyword(word) {
  selectedKeyword.value = selectedKeyword.value === word ? '' : word
}

function clearKeyword() {
  selectedKeyword.value = ''
}

async function loadPointsJsonDataset({ silent = false } = {}) {
  try {
    const response = await fetch(POINTS_JSON_URL, { cache: 'no-cache' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const data = await response.json()
    const points = normalizeKnowledgePoints(extractKnowledgeArray(data))
    if (!points.length) throw new Error('points.json 中没有有效知识点')

    pointsJsonDataset.value = {
      id: POINTS_JSON_DATASET_ID,
      label: 'points.json 关键词连结',
      description: '来自 frontend/public/visual/points.json，用原始知识点构建关键词共现网络',
      knowledge_points: points,
    }

    if (activeDatasetId.value === POINTS_JSON_DATASET_ID) scheduleAnalysis()
    if (!silent) ElMessage.success(`已载入 points.json：${points.length} 条知识点`)
    return true
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    pointsJsonDataset.value = {
      id: POINTS_JSON_DATASET_ID,
      label: 'points.json 关键词连结',
      description: `载入失败：${message}`,
      knowledge_points: [],
    }
    if (!silent) ElMessage.error(`载入 points.json 失败：${message}`)
    return false
  }
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function highlightText(text) {
  const terms = [...new Set([selectedKeyword.value, searchQuery.value.trim()].filter(Boolean))]
    .sort((a, b) => b.length - a.length)
  let html = escapeHtml(text)
  if (!terms.length) return html

  const pattern = terms.map((term) => escapeRegExp(escapeHtml(term))).join('|')
  return html.replace(new RegExp(pattern, 'gi'), (match) => `<mark>${match}</mark>`)
}

function onResize() {
  if (!g6Graph || !networkRef.value) return
  g6Graph.changeSize(networkRef.value.clientWidth, networkRef.value.clientHeight)
  scheduleNetworkFits(g6Graph)
}

watch(activeDatasetId, () => {
  selectedKeyword.value = ''
  searchQuery.value = ''
  currentPage.value = 1
  scheduleAnalysis()
})

watch(minOccurrenceCount, () => {
  currentPage.value = 1
  scheduleAnalysis()
})

watch([selectedKeyword, searchQuery], () => {
  currentPage.value = 1
  applySelectionHighlight()
})

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await loadPointsJsonDataset({ silent: true })
  await runAnalysis()
})

onBeforeUnmount(() => {
  if (rerunTimer) clearTimeout(rerunTimer)
  window.removeEventListener('resize', onResize)
  destroyCharts()
  destroyNetwork()
})
</script>

<template>
  <div class="kg-page">
    <div class="kg-shell">
      <header class="kg-header">
        <div class="kg-heading">
          <span class="view-kicker">KNOWLEDGE GRAPH</span>
          <h1>知识点关键词可视化分析</h1>
          <p class="kg-subtitle">通过 NLP 自动提取课程知识点关键词，基于共现频率构建交互式知识网络，直观呈现概念关联强度</p>
        </div>
        <div class="kg-actions">
          <el-select v-model="activeDatasetId" class="kg-dataset-select" size="large">
            <el-option v-for="dataset in datasets" :key="dataset.id" :label="dataset.label" :value="dataset.id" />
          </el-select>
        </div>
      </header>

      <section class="kg-control-band">
        <div class="kg-dataset-meta">
          <strong>{{ activeDataset?.label }}</strong>
          <span>{{ activeDatasetDescription }}</span>
        </div>
        <label class="kg-control">
          <span>最少出现次数</span>
          <strong>{{ minOccurrenceCount }}</strong>
          <el-slider v-model="minOccurrenceCount" :min="1" :max="12" :show-tooltip="false" />
        </label>
      </section>

      <p class="kg-status" :class="{ 'kg-status--loading': loading }">{{ statusText }}</p>
      <p v-if="errorMessage" class="kg-error">{{ errorMessage }}</p>

      <section class="kg-summary-grid">
        <article v-for="card in summaryCards" :key="card.key" class="kg-summary-card">
          <span class="kg-summary-icon" :class="`kg-summary-icon--${card.tone}`">
            <svg v-if="card.icon === 'list'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 6h13M8 12h13M8 18h13" />
              <path d="M3 6h.01M3 12h.01M3 18h.01" />
            </svg>
            <svg v-else-if="card.icon === 'spark'" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2">
              <path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2z" />
            </svg>
            <svg v-else-if="card.icon === 'chart'" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              stroke-width="2">
              <path d="M4 19V5" />
              <path d="M4 19h16" />
              <path d="M8 16l3-4 3 2 4-7" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="6" cy="6" r="3" />
              <circle cx="18" cy="7" r="3" />
              <circle cx="13" cy="18" r="3" />
              <path d="M8.7 7l6.6.1M7.8 8.4l3.8 7.1M16.5 9.6L14.2 15" />
            </svg>
          </span>
          <div>
            <div class="kg-summary-value">{{ card.value }}</div>
            <div class="kg-summary-label">{{ card.label }}</div>
          </div>
        </article>
      </section>

      <article class="kg-panel kg-panel--wide">
        <div class="kg-panel-head kg-panel-head--network">
          <div>
            <h2>关键词关联网络</h2>
            <p>节点为关键词，边权为同一条知识点中的共现次数</p>
          </div>
          <div v-if="selectedKeyword" class="kg-selected">
            <span>当前聚焦：{{ selectedKeyword }}</span>
            <button type="button" @click="clearKeyword">清除</button>
          </div>
        </div>
        <div class="kg-network-wrap">
          <div v-if="loading" class="kg-loading">分析中...</div>
          <div ref="networkRef" class="kg-network">
            <div v-if="fallbackNetwork.nodes.length" class="kg-network-fallback">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <line v-for="edge in fallbackNetwork.edges" :key="`${edge.source}-${edge.target}`"
                  class="kg-network-edge" :class="{ 'is-dimmed': isFallbackEdgeDimmed(edge) }" :x1="edge.x1"
                  :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" :stroke-width="edge.width" />
              </svg>
              <button v-for="node in fallbackNetwork.nodes" :key="node.k" class="kg-network-node" :class="{
                'is-selected': selectedKeyword === node.k,
                'is-dimmed': isFallbackNodeDimmed(node.k),
              }" type="button" :style="fallbackNodeStyle(node)" :title="node.k" @click="selectKeyword(node.k)">
                <span>{{ splitNodeLabel(node.k, 7).join('\n') }}</span>
                <small>{{ node.c }}</small>
              </button>
            </div>
          </div>
          <div v-if="!keywordRows.length && !loading" class="kg-empty kg-empty--network">暂无可展示网络</div>
        </div>
      </article>

      <section class="kg-chart-grid">
        <article class="kg-panel">
          <div class="kg-panel-head">
            <div>
              <h2>高频关键词占比</h2>
              <p>Top10 + 其余，按文档频次统计</p>
            </div>
          </div>
          <div class="kg-chart-wrap">
            <canvas ref="pieRef"></canvas>
            <div v-if="!keywordRows.length && !loading" class="kg-empty">暂无可展示关键词</div>
          </div>
        </article>

        <article class="kg-panel">
          <div class="kg-panel-head">
            <div>
              <h2>文档频次 Top20</h2>
              <p>点击柱状项可筛选知识点列表</p>
            </div>
          </div>
          <div class="kg-chart-wrap">
            <canvas ref="barRef"></canvas>
            <div v-if="!keywordRows.length && !loading" class="kg-empty">暂无可展示关键词</div>
          </div>
        </article>
      </section>

      <article class="kg-panel kg-panel--wide">
        <div class="kg-panel-head">
          <div>
            <h2>概率与累计概率</h2>
            <p>前 40 位关键词的 P(k) 与累计占比</p>
          </div>
        </div>
        <div class="kg-chart-wrap kg-chart-wrap--line">
          <canvas ref="lineRef"></canvas>
          <div v-if="!keywordRows.length && !loading" class="kg-empty">暂无可展示关键词</div>
        </div>
      </article>

      <section class="kg-bottom-grid">
        <article class="kg-panel">
          <div class="kg-panel-head">
            <div>
              <h2>关键词排行</h2>
              <p>按文档频次降序排列</p>
            </div>
          </div>
          <div class="kg-rank-list">
            <button v-for="(item, index) in topKeywordRows" :key="item.k" class="kg-rank-row"
              :class="{ 'kg-rank-row--active': selectedKeyword === item.k }" type="button"
              @click="selectKeyword(item.k)">
              <span class="kg-rank-no">{{ index + 1 }}</span>
              <span class="kg-rank-word" :style="{ color: KEYWORD_COLORS[index % KEYWORD_COLORS.length] }">
                {{ item.k }}
              </span>
              <span class="kg-rank-track">
                <span class="kg-rank-bar" :style="{
                  width: `${(item.c / Math.max(topKeywordRows[0]?.c || 1, 1)) * 100}%`,
                  background: KEYWORD_COLORS[index % KEYWORD_COLORS.length],
                }"></span>
              </span>
              <span class="kg-rank-count">{{ item.c }}</span>
            </button>
          </div>
        </article>

        <article class="kg-panel">
          <div class="kg-list-head">
            <div>
              <h2>知识点追溯</h2>
              <p>
                <template v-if="selectedKeywordRow">
                  "{{ selectedKeywordRow.k }}" 出现 {{ selectedKeywordRow.c }} 条 ·
                </template>
                共 {{ filteredPointRecords.length }} 条
              </p>
            </div>
            <el-input v-model="searchQuery" class="kg-search" placeholder="搜索知识点" clearable size="large" />
          </div>

          <div class="kg-point-list">
            <article v-for="item in pagedPointRecords" :key="item.index" class="kg-point-card">
              <div class="kg-point-meta">
                <span>#{{ item.index + 1 }}</span>
                <span v-if="item.chapterTitle" class="kg-chapter-tag"
                  :style="{ color: item.chapterColor, borderColor: hexToRgba(item.chapterColor, 0.36), background: hexToRgba(item.chapterColor, 0.08) }">
                  {{ item.chapterTitle }}
                </span>
              </div>
              <p v-html="highlightText(item.text)"></p>
              <div v-if="item.keywords.length" class="kg-point-tags">
                <button v-for="keyword in item.keywords.slice(0, 8)" :key="keyword" type="button"
                  :class="{ active: selectedKeyword === keyword }" @click="selectKeyword(keyword)">
                  {{ keyword }}
                </button>
              </div>
            </article>
          </div>

          <el-pagination v-if="filteredPointRecords.length > PAGE_SIZE" v-model:current-page="currentPage"
            :page-size="PAGE_SIZE" :total="filteredPointRecords.length" layout="prev, pager, next" small
            class="kg-pagination" />
        </article>
      </section>
    </div>
  </div>
</template>

<style scoped>
.kg-page {
  width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  overflow-x: hidden;
  background: #f8fafc;
  padding: 28px 42px 28px;
}

.kg-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: min(100%, 1580px);
  min-width: 0;
  margin: 0 auto;
}

.kg-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.kg-heading {
  min-width: 280px;
}

.kg-eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.kg-heading h1 {
  margin: 0;
  color: #0f172a;
  font-size: 30px;
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: 0;
  letter-spacing: 0;
}

.kg-heading p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
}

.kg-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.kg-dataset-select {
  width: 230px;
}

.kg-control-band {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(220px, 360px);
  gap: 12px;
  align-items: stretch;
}

.kg-dataset-meta,
.kg-control {
  min-width: 0;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.kg-dataset-meta {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.kg-dataset-meta strong {
  color: #0f172a;
  font-size: 15px;
}

.kg-dataset-meta span,
.kg-control span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.kg-control {
  display: grid;
  grid-template-columns: 1fr auto;
  column-gap: 10px;
  align-items: center;
}

.kg-control strong {
  color: #0f172a;
  font-size: 16px;
}

.kg-control :deep(.el-slider) {
  grid-column: 1 / -1;
  height: 26px;
}

.kg-status,
.kg-error {
  margin: 0;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
}

.kg-status {
  color: #475569;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.kg-status--loading {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.kg-error {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.kg-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.kg-summary-card {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 18px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.kg-summary-icon {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #ffffff;
}

.kg-summary-icon svg {
  width: 22px;
  height: 22px;
}

.kg-summary-icon--blue {
  background: linear-gradient(135deg, #2563eb, #0284c7);
}

.kg-summary-icon--purple {
  background: linear-gradient(135deg, #7c3aed, #be185d);
}

.kg-summary-icon--green {
  background: linear-gradient(135deg, #99f6e4, #5eead4);
}

.kg-summary-icon--orange {
  background: linear-gradient(135deg, #d97706, #dc2626);
}

.kg-summary-value {
  color: #0f172a;
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}

.kg-summary-label {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.kg-chart-grid,
.kg-bottom-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
}

.kg-bottom-grid {
  grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.2fr);
}

.kg-panel {
  min-width: 0;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.045);
}

.kg-panel--wide {
  width: 100%;
}

.kg-panel-head,
.kg-list-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.kg-panel-head h2,
.kg-list-head h2 {
  margin: 0;
  color: #0f172a;
  font-size: 16px;
  font-weight: 800;
}

.kg-panel-head p,
.kg-list-head p {
  margin: 5px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.45;
}

.kg-panel-head--network {
  align-items: center;
}

.kg-selected {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  max-width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
}

.kg-selected button {
  border: 0;
  background: transparent;
  color: #b45309;
  font: inherit;
  cursor: pointer;
}

.kg-chart-wrap {
  position: relative;
  height: 300px;
}

.kg-chart-wrap canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.kg-chart-wrap--line {
  height: 320px;
}

.kg-network-wrap {
  position: relative;
  height: 560px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  overflow: hidden;
  background:
    radial-gradient(circle at center, rgba(239, 246, 255, 0.96), rgba(248, 250, 252, 0.98)),
    #f8fafc;
}

.kg-network {
  position: relative;
  width: 100%;
  height: 100%;
}

.kg-network-fallback {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.kg-network-fallback svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.kg-network-edge {
  stroke: rgba(94, 234, 212, 0.38);
  transition: opacity 0.2s ease;
}

.kg-network-edge.is-dimmed {
  opacity: 0.08;
}

.kg-network-node {
  position: absolute;
  transform: translate(-50%, -50%) scale(var(--node-scale, 1));
  min-width: 70px;
  max-width: 122px;
  min-height: 38px;
  border: 1px solid color-mix(in srgb, var(--node-color, #5eead4) 42%, #ffffff);
  border-radius: 8px;
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  padding: 8px 10px;
  text-align: center;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    opacity 0.2s ease;
}

.kg-network-node span {
  display: block;
  white-space: pre-line;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.25;
}

.kg-network-node small {
  display: inline-flex;
  margin-top: 4px;
  color: var(--node-color, #14b8a6);
  font-size: 11px;
  font-weight: 800;
}

.kg-network-node:hover,
.kg-network-node.is-selected {
  border-color: var(--node-color, #5eead4);
  box-shadow: 0 14px 28px rgba(94, 234, 212, 0.16);
}

.kg-network-node.is-selected {
  background: color-mix(in srgb, var(--node-color, #5eead4) 12%, #ffffff);
}

.kg-network-node.is-dimmed {
  opacity: 0.28;
}

.kg-loading,
.kg-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
  pointer-events: none;
}

.kg-empty--network {
  background: rgba(248, 250, 252, 0.84);
}

.kg-rank-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 580px;
  overflow-y: auto;
  padding-right: 4px;
}

.kg-rank-row {
  width: 100%;
  display: grid;
  grid-template-columns: 28px minmax(82px, 120px) minmax(80px, 1fr) 42px;
  align-items: center;
  gap: 10px;
  min-height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.kg-rank-row:hover,
.kg-rank-row--active {
  background: #f8fafc;
}

.kg-rank-no {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
  text-align: right;
}

.kg-rank-word {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 800;
}

.kg-rank-track {
  height: 8px;
  overflow: hidden;
  border-radius: 8px;
  background: #e2e8f0;
}

.kg-rank-bar {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.kg-rank-count {
  color: #475569;
  font-size: 12px;
  font-weight: 800;
  text-align: right;
}

.kg-search {
  width: 260px;
  flex: 0 0 auto;
}

.kg-point-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 12px;
  max-height: 600px;
  overflow-y: auto;
  padding-right: 4px;
}

.kg-point-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fbfdff;
}

.kg-point-card p {
  margin: 8px 0 0;
  color: #334155;
  font-size: 13px;
  line-height: 1.62;
  word-break: break-word;
}

.kg-point-card :deep(mark) {
  background: #fef3c7;
  color: #92400e;
  border-radius: 3px;
  padding: 0 2px;
}

.kg-point-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
}

.kg-chapter-tag {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 2px 7px;
  border: 1px solid;
  border-radius: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kg-point-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.kg-point-tags button {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 3px 7px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.kg-point-tags button.active {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #92400e;
}

.kg-pagination {
  margin-top: 14px;
  justify-content: center;
}

.kg-rank-list::-webkit-scrollbar,
.kg-point-list::-webkit-scrollbar {
  width: 6px;
}

.kg-rank-list::-webkit-scrollbar-thumb,
.kg-point-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

@media (max-width: 1180px) {
  .kg-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .kg-actions {
    justify-content: flex-start;
  }

  .kg-control-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .kg-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {

  .kg-chart-grid,
  .kg-bottom-grid {
    grid-template-columns: 1fr;
  }

  .kg-network-wrap {
    height: 480px;
  }
}

@media (max-width: 720px) {
  .kg-page {
    padding: 0 0 36px;
  }

  .kg-heading h1 {
    font-size: 24px;
  }

  .kg-actions,
  .kg-dataset-select,
  .kg-search {
    width: 100%;
  }

  .kg-control-band,
  .kg-summary-grid {
    grid-template-columns: 1fr;
  }

  .kg-panel-head,
  .kg-list-head {
    flex-direction: column;
  }

  .kg-chart-wrap {
    height: 260px;
  }

  .kg-network-wrap {
    height: 420px;
  }
}

/* Portal theme sync */
.kg-page {
  --kg-bg: #f8fafc;
  --kg-surface: #ffffff;
  --kg-border: #e2e8f0;
  --kg-border-soft: #edf2f7;
  --kg-text: #0f172a;
  --kg-muted: #64748b;
  --kg-subtle: #94a3b8;
  --kg-primary: #5eead4;
  --kg-primary-strong: #14b8a6;
  --kg-primary-text: #14b8a6;
  --kg-primary-soft: #f0fdfa;
  min-height: 100vh;
  padding: 0 0 48px !important;
  background: var(--kg-bg) !important;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif !important;
}

.kg-shell {
  gap: 18px !important;
}

.kg-header {
  position: relative;
  overflow: hidden;
  align-items: center !important;
  min-height: auto;
  padding: 22px 24px;
  border: 1px solid rgba(20, 184, 166, 0.16);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.24), rgba(255, 255, 255, 0.92) 46%, rgba(14, 165, 233, 0.16)),
    linear-gradient(rgba(94, 234, 212, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(94, 234, 212, 0.08) 1px, transparent 1px);
  background-size: auto, 22px 22px, 22px 22px;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
}

.kg-header::before,
.kg-header::after {
  display: none;
}

.kg-heading,
.kg-actions {
  position: relative;
  z-index: 1;
}

.kg-eyebrow {
  color: var(--kg-primary) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
}

.kg-heading h1 {
  color: var(--kg-text) !important;
  font-size: 30px !important;
  line-height: 1.18 !important;
}

.kg-heading p,
.kg-dataset-meta span,
.kg-control span,
.kg-panel-head p,
.kg-list-head p,
.kg-summary-label {
  color: var(--kg-muted) !important;
}

.kg-dataset-select :deep(.el-select__wrapper) {
  border-radius: 8px !important;
  border: 1px solid rgba(94, 234, 212, 0.34) !important;
  background: rgba(255, 255, 255, 0.78) !important;
  box-shadow: none !important;
}

.kg-control-band,
.kg-summary-grid,
.kg-chart-grid,
.kg-bottom-grid {
  gap: 14px !important;
}

.kg-dataset-meta,
.kg-control,
.kg-summary-card,
.kg-panel {
  border-radius: 8px !important;
  border: 1px solid var(--kg-border) !important;
  background: var(--kg-surface) !important;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.055) !important;
}

.kg-status {
  border-color: var(--kg-border) !important;
  background: rgba(255, 255, 255, 0.82) !important;
}

.kg-status--loading {
  color: var(--kg-primary-text) !important;
  background: var(--kg-primary-soft) !important;
  border-color: #99f6e4 !important;
}

.kg-summary-card {
  padding: 16px !important;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.kg-summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08) !important;
}

.kg-summary-icon {
  border-radius: 8px !important;
}

.kg-summary-icon--blue,
.kg-summary-icon--purple,
.kg-summary-icon--green,
.kg-summary-icon--orange {
  color: var(--kg-primary-text) !important;
  background: linear-gradient(135deg, #ccfbf1, #f0fdfa) !important;
  border: 1px solid #99f6e4 !important;
}

.kg-summary-value,
.kg-panel-head h2,
.kg-list-head h2,
.kg-dataset-meta strong,
.kg-control strong {
  color: var(--kg-text) !important;
}

.kg-panel {
  padding: 18px !important;
}

.kg-network-wrap {
  border-color: var(--kg-border) !important;
  border-radius: 8px !important;
  background:
    linear-gradient(rgba(94, 234, 212, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(94, 234, 212, 0.07) 1px, transparent 1px),
    #fbfdff !important;
  background-size: 26px 26px, 26px 26px, auto !important;
}

.kg-selected {
  color: var(--kg-primary-text) !important;
  background: var(--kg-primary-soft) !important;
  border-color: #99f6e4 !important;
}

.kg-selected button {
  color: var(--kg-primary-text) !important;
}

.kg-rank-row,
.kg-point-card,
.kg-network-node {
  border-radius: 8px !important;
  border-color: #ccfbf1 !important;
  background: linear-gradient(135deg, #ffffff, #f8fffd) !important;
}

.kg-rank-row:hover,
.kg-rank-row--active,
.kg-point-card:hover,
.kg-network-node.is-selected {
  border-color: #99f6e4 !important;
  background: linear-gradient(135deg, #ecfeff, #f0fdfa) !important;
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.08) !important;
}

.kg-network-edge {
  stroke: rgba(94, 234, 212, 0.42) !important;
}

.kg-network-node small {
  color: var(--kg-primary-text) !important;
}

.kg-network-node:hover,
.kg-network-node.is-selected {
  border-color: #5eead4 !important;
  box-shadow: 0 12px 24px rgba(94, 234, 212, 0.16) !important;
}

.kg-rank-no,
.kg-rank-count,
.kg-chapter-tag,
.kg-point-tags button.active {
  color: var(--kg-primary-text) !important;
}

.kg-rank-bar {
  background: linear-gradient(90deg, #99f6e4, #5eead4) !important;
}

.kg-search :deep(.el-input__wrapper) {
  border-radius: 8px !important;
  box-shadow: 0 0 0 1px var(--kg-border) inset !important;
}

.kg-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--kg-primary) inset, 0 0 0 3px rgba(20, 184, 166, 0.12) !important;
}

@media (max-width: 900px) {
  .kg-page {
    padding: 0 0 36px !important;
  }

  .kg-header {
    min-height: auto;
    align-items: stretch !important;
  }

  .kg-heading h1 {
    font-size: 26px !important;
  }
}
</style>
