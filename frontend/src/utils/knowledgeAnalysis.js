/**
 * 知识点关键词分析工具
 * - 从短句集合中提取领域术语 + 基于标点的完整短语
 * - 按关键词出现次数过滤得到词表
 * - 统计同一条知识点内关键词两两共现次数（用于构建无向图边权）
 *
 * 输入：string[]（每条是一句知识点描述）
 * 输出：{ vocabulary, freqForCharts, edgeWeights, pointKeywords }
 */

const STOP = new Set(
  '的 了 和 与 在 是 为 及 或 等 中 对 从 将 之 能 可 有 要 需 应 会 由 通过 基于 进行 方法 方式 包括 以及 不同 相同 本章 本节 例子 例如 一个 一种 一些 可以 能够 需要 必须 如果 由于 因此 所以 但是 然而 其中 其 各 每 当 时 后 前 上 下 内 外 所 以 于 即 也 又 还 都 而 则 且 但 并 被 把 让 使 得 着 过 地 很 更 最 较 再 已 未 无 非 是否 如何 什么 哪些 该 此 这 那 它 它们 我们 你们 他们 之间 情况 部分 内容 过程 结果 作用 意义 目的 特点 优点 缺点 问题 原因 影响 因素 条件 要求 原则 步骤 第一 第二 第三 一步 二步 总结 分析 计算 确定 得到 得出 应用 使用 采用 选择 根据 按照 有关 相关 关于 对于 来说 而言 方面 领域 类型 形式 结构 系统 设备 装置 具体 实际 理想 正常 故障 状态 变化 增加 减少 升高 降低'.split(
    /\s+/,
  ),
)

const onlyCjk = (s) => s.replace(/[^\u4e00-\u9fff]/g, '')
const isStopGram = (sub) => STOP.has(sub) || sub.length <= 1
const BAD_BOUNDARY_RE = /^[的了和与及或是在为由将把被使让则并且但而用得]/u
const BAD_TRAILING_RE = /[的了和与及或是在为由将把被使让则并且但而中上下前后时]$/u

const DOMAIN_SUFFIXES = [
  '功率因数',
  '表示方法',
  '表示方式',
  '计算方法',
  '连接方式',
  '联结方式',
  '联接方法',
  '联结方法',
  '运动规律',
  '万有引力定律',
  '牛顿运动定律',
  '匀速圆周运动',
  '圆周运动',
  '轨道半径',
  '旋转半径',
  '旋转中心',
  '向心加速度',
  '表示式',
  '表示法',
  '联结',
  '联接',
  '连接',
  '电压',
  '电流',
  '功率',
  '负载',
  '电路',
  '电源',
  '系统',
  '绕组',
  '相序',
  '相量',
  '中性线',
  '中线',
  '零线',
  '发电机',
  '电动机',
  '变压器',
  '万有引力',
  '向心力',
  '角速度',
  '线速度',
  '加速度',
  '周期',
  '半径',
  '恒星',
  '天体',
  '星体',
  '双星',
  '三星',
  '多星',
  '三体问题',
  '等边三角形',
  '阻抗',
  '电阻',
  '感抗',
  '短路',
  '断路',
  '故障',
  '算法',
  '模型',
  '网络',
  '学习',
  '搜索',
  '排序',
  '队列',
  '链表',
  '二叉树',
  '概念',
  '原则',
  '方法',
  '结构',
]

const TERM_PATTERNS = [
  /(?:双星|三星|多星)(?:系统|模型|问题)/gu,
  /(?:不规则|特殊)?三星问题/gu,
  /(?:特殊)?三体问题/gu,
  /(?:万有引力定律|牛顿运动定律|万有引力|向心力|匀速圆周运动|圆周运动)/gu,
  /(?:轨道半径|旋转半径|运行角速度|角速度|线速度|向心速度|向心加速度|周期|旋转中心|共同中心|固定点|等边三角形)/gu,
  /(?:三角形中心|等边三角形中心)/gu,
  /相位互差(?:\d+)?度/gu,
  /(?:欧姆定律|基尔霍夫定律)/gu,
  /(?:线电压|相电压|线电流|相电流)(?:等于|是)(?:相电压|线电压|相电流|线电流)(?:的)?(?:√?3)?(?:倍)?/gu,
  /(?:两颗恒星|两恒星|恒星|星体|天体)/gu,
  /(?:对称|不对称)?三相(?:制|电路|电压|电流|电源|负载|功率|系统|发电机|电动机)/gu,
  /(?:单相|三相)(?:制|负载|设备|电源|电动机|发电机)/gu,
  /(?:星形|三角形|Y|Δ|△)(?:联结|联接|连接|接法)/gu,
  /(?:相|线)(?:电压|电流)/gu,
  /(?:中性线|中线|零线)(?:电压|电流)?/gu,
  /(?:有功|无功|视在|输入|输出|总有功)?功率(?:因数|公式)?/gu,
  /(?:额定|对称|不对称)?(?:电压|电流|负载|电路|电源|功率|阻抗)/gu,
  /(?:瞬时表示式|相量表示法|相量图|电磁感应|动磁生电|短路故障|断路故障)/gu,
  /(?:状态空间|启发式搜索|广度优先搜索|深度优先搜索|博弈树搜索|极小极大算法|蒙特卡洛树搜索)/gu,
  /(?:机器学习|监督学习|无监督学习|强化学习|深度学习|迁移学习|特征工程|梯度下降|交叉验证)/gu,
  /(?:卷积神经网络|循环神经网络|神经网络|注意力机制|自然语言处理|知识图谱|语义网络|谓词逻辑)/gu,
  /(?:时间复杂度|空间复杂度|抽象数据类型|二叉搜索树|优先队列|最小生成树|拓扑排序|动态规划|贪心算法|回溯法)/gu,
]

const LATIN_TERM_RE =
  /\b(?:AI|NLP|BFS|DFS|A\*|MCTS|SGD|CNN|RNN|LSTM|GRU|Transformer|BERT|Word2Vec|GloVe|LLM|KMP|AVL|BST|Dijkstra|Bellman-Ford|Floyd-Warshall|Prim|Kruskal|Tarjan|Kosaraju|PCA|t-SNE|UMAP|DBSCAN|K-Means|SVM|XGBoost|LightGBM|AdaBoost|GBDT|Logistic|Python|JSON|CSV|pickle|pathlib|asyncio|threading|collections|itertools|functools|datetime|PEP\s*8|mypy)\b/g

const LEADING_CLEAN_RE =
  /^(?:本章|本节|掌握|理解|学会|能够|通过|基于|根据|利用|采用|介绍|讲解|展示|比较|讨论|总结|验证|确定|要求|包括|包含|涉及|影响|用于|适用于|有助于|常见于|第一步|第二步|第三步|第四步|第五步|这种|这一|这些|此例|此计算|主要|基本|核心|重要|常见|典型|实际|具体|两种|三种|一种|一个|多个|各类|各相|每相)+/u
const LEADING_CHAR_RE = /^[的了和与及或是在为由将把被使让需可用得]/u
const ALLOW_SHORT_TERMS = new Set(
  '双星 三星 多星 恒星 天体 星体 周期 质量 半径 速度 引力 中心 系统 模型 规律 比值 合力'.split(' '),
)
const NOISE_TERMS = new Set(
  '满足 旋转 两颗 颗恒 星系 星系统 万有 有引 向心 心力 角速 三角 运动特点'.split(' '),
)
const ALWAYS_KEEP_TERMS = new Set(
  [
    '双星系统',
    '双星模型',
    '双星问题',
    '三星系统',
    '三星问题',
    '三星模型',
    '多星模型',
    '三体问题',
    '特殊三星系统',
    '万有引力',
    '向心力',
    '角速度',
    '线速度',
    '向心加速度',
    '轨道半径',
    '旋转半径',
    '旋转中心',
    '匀速圆周运动',
    '圆周运动',
    '万有引力定律',
    '牛顿运动定律',
    '等边三角形',
    '三角形中心',
  ],
)
const BAD_FRAGMENT_RE = /(?:满足|位于|受到|因此|根据|求解|明确|结合|联立|消去|分别|具有|包括|能够|需要|要求|第[一二三四五]步|这种|接于|用表示|得三相)/u
const BAD_TAIL_CHAR_RE = /[满因受作位]$/u

function hasBadBoundary(term) {
  if (!term || term.length <= 1) return true
  return BAD_BOUNDARY_RE.test(term) || BAD_TRAILING_RE.test(term)
}

function isLikelyFragmentTerm(term, count, freqMap) {
  if (NOISE_TERMS.has(term)) return true
  if (BAD_FRAGMENT_RE.test(term)) return true
  if (!term.endsWith('作用') && BAD_TAIL_CHAR_RE.test(term)) return true
  if (ALWAYS_KEEP_TERMS.has(term)) return false
  if (term.length > 6 && term.includes('中')) return true
  if (term.length <= 2 && ALLOW_SHORT_TERMS.has(term)) return false

  let containingCount = 0
  freqMap.forEach((otherCount, other) => {
    if (other === term || other.length <= term.length || !other.includes(term)) return
    containingCount += Math.min(otherCount, count)
  })

  if (term.length <= 2) return containingCount >= count * 0.5
  return containingCount >= count * 0.75
}

const ngramsForText = (text) => {
  const s = onlyCjk(text)
  const set = new Set()
  for (let L = 4; L >= 2; L--) {
    for (let i = 0; i + L <= s.length; i++) {
      const sub = s.slice(i, i + L)
      if (isStopGram(sub)) continue
      if (hasBadBoundary(sub)) continue
      set.add(sub)
    }
  }
  return set
}

const phraseChunks = (text) => {
  const set = new Set()
  const parts = text.split(/[，。；、：？!！\s,.;:]+/).filter(Boolean)
  for (const p of parts) {
    const t = p.trim()
    if (t.length >= 2 && t.length <= 14 && !/^[\d.、\s]+$/.test(t)) {
      if (/[0-9A-Za-z√=]/.test(t)) continue
      const cjk = onlyCjk(t)
      if (/^第[一二三四五六七八九十]+步$/.test(cjk)) continue
      if (cjk.length >= 2 && cjk.length <= 14 && !isStopGram(cjk)) set.add(cjk)
    }
  }
  return set
}

function trimTermCandidate(candidate) {
  let s = String(candidate || '')
  if (!s) return ''

  const boundaryWords = [
    '以及',
    '包括',
    '包含',
    '通过',
    '根据',
    '利用',
    '采用',
    '进行',
    '掌握',
    '理解',
    '学会',
    '能够',
    '需要',
    '要求',
    '介绍',
    '讲解',
    '展示',
    '比较',
    '分析',
    '计算',
    '确定',
    '用于',
    '适用于',
    '有助于',
    '常见于',
    '例如',
    '和',
    '与',
    '及',
    '或',
    '是',
    '为',
    '在',
    '当',
    '将',
    '把',
    '被',
    '使',
    '由',
    '得',
    '用',
    '接于',
  ]

  for (const word of boundaryWords) {
    const index = s.lastIndexOf(word)
    if (index >= 0 && index + word.length < s.length - 1) {
      s = s.slice(index + word.length)
    }
  }

  let previous = ''
  while (previous !== s) {
    previous = s
    s = s.replace(LEADING_CLEAN_RE, '').replace(LEADING_CHAR_RE, '')
  }

  return s
}

function countTermOccurrences(text, term) {
  const source = String(text || '')
  const needle = String(term || '')
  if (!source || !needle) return 0

  let count = 0
  let fromIndex = 0
  while (fromIndex < source.length) {
    const foundAt = source.indexOf(needle, fromIndex)
    if (foundAt === -1) break
    count += 1
    fromIndex = foundAt + Math.max(needle.length, 1)
  }
  return count || 1
}

function termLikePhrasesForText(text) {
  const set = new Set()

  for (const pattern of TERM_PATTERNS) {
    for (const match of String(text).matchAll(pattern)) {
      const term = String(match[0] || '').trim()
      if (term.length >= 2 && term.length <= 16 && !hasBadBoundary(term)) set.add(term)
    }
  }

  for (const match of String(text).matchAll(LATIN_TERM_RE)) {
    const term = String(match[0] || '').replace(/\s+/g, ' ').trim()
    if (term) set.add(term)
  }

  const cjkRuns = String(text).match(/[\u4e00-\u9fff]+/gu) || []
  for (const run of cjkRuns) {
    for (const suffix of DOMAIN_SUFFIXES) {
      let index = run.indexOf(suffix)
      while (index >= 0) {
        const end = index + suffix.length
        const start = Math.max(0, index - 8)
        const candidate = trimTermCandidate(run.slice(start, end))
        if (
          candidate.includes(suffix) &&
          candidate.length >= suffix.length &&
          candidate.length >= 2 &&
          candidate.length <= 14 &&
          !STOP.has(candidate) &&
          !hasBadBoundary(candidate)
        ) {
          set.add(candidate)
        }
        index = run.indexOf(suffix, end)
      }
    }
  }

  return set
}

/**
 * @param {string[]} knowledgePoints
 * @param {{ minCount?: number, useNgrams?: boolean }} opts
 */
export function analyzeKnowledgePoints(knowledgePoints, opts = {}) {
  const minCount = opts.minCount ?? 1
  const useNgrams = opts.useNgrams ?? false

  const keywordCounts = new Map()
  const pointKeywords = new Map()
  const edgeWeights = new Map()

  const perPointTerms = knowledgePoints.map((raw, idx) => {
    const a = useNgrams ? ngramsForText(raw) : new Set()
    const b = phraseChunks(raw)
    const c = termLikePhrasesForText(raw)
    const merged = new Set([...a, ...b, ...c])
    for (const term of merged) {
      keywordCounts.set(term, (keywordCounts.get(term) || 0) + countTermOccurrences(raw, term))
    }
    return { idx, raw, merged }
  })

  const candidates = [...keywordCounts.entries()]
    .filter(([, count]) => count >= minCount)
    .filter(([w]) => !hasBadBoundary(w))
    .filter(([w, count]) => !isLikelyFragmentTerm(w, count, keywordCounts))
    .map(([w, count]) => ({ w, count, len: w.length }))
    .sort((x, y) => y.count - x.count || y.len - x.len || y.w.localeCompare(x.w))

  const vocabSet = new Set()
  for (const { w } of candidates) {
    const isContainedBySelected = [...vocabSet].some((existing) => {
      if (w.length < 3 || !existing.includes(w) || existing === w) return false
      const existingCount = keywordCounts.get(existing) || 0
      const currentCount = keywordCounts.get(w) || 0
      return existingCount >= currentCount * 0.75
    })
    if (w.length >= 2 && !isContainedBySelected) vocabSet.add(w)
  }
  const vocabulary = [...vocabSet]

  for (const { idx, raw, merged } of perPointTerms) {
    const hits = vocabulary
      .filter((k) => raw.includes(k) && merged.has(k))
      .sort(
        (a, b) =>
          b.length - a.length ||
          (keywordCounts.get(b) || 0) - (keywordCounts.get(a) || 0),
      )
    const picked = []
    const used = new Set()
    for (const k of hits) {
      let overlap = false
      for (const u of used) {
        if (u.includes(k) || k.includes(u)) {
          overlap = true
          break
        }
      }
      if (overlap && picked.length > 0) continue
      picked.push(k)
      used.add(k)
    }
    pointKeywords.set(String(idx), picked)

    for (let i = 0; i < picked.length; i++) {
      for (let j = i + 1; j < picked.length; j++) {
        const a = picked[i]
        const b = picked[j]
        const x = a < b ? a : b
        const y = a < b ? b : a
        if (!edgeWeights.has(x)) edgeWeights.set(x, new Map())
        const m = edgeWeights.get(x)
        m.set(y, (m.get(y) || 0) + 1)
      }
    }
  }

  const freqForCharts = vocabulary
    .map((k) => ({ k, c: keywordCounts.get(k) || 0 }))
    .filter((x) => x.c > 0)
    .sort((a, b) => b.c - a.c)

  const total = freqForCharts.reduce((s, x) => s + x.c, 0) || 1

  let edgeCount = 0
  edgeWeights.forEach((inner) => {
    edgeCount += inner.size
  })

  return {
    vocabulary,
    freqForCharts,
    total,
    edgeCount,
    edgeWeights,
    pointKeywords,
    pointCount: knowledgePoints.length,
  }
}

/**
 * 动态加载 CDN 脚本。重复调用会复用同一个 Promise。
 * @param {string} src
 * @param {string} globalName
 */
const _scriptPromises = new Map()
export function loadExternalScript(src, globalName) {
  if (typeof window !== 'undefined' && globalName && window[globalName]) {
    return Promise.resolve(window[globalName])
  }
  if (_scriptPromises.has(src)) return _scriptPromises.get(src)

  const promise = new Promise((resolve, reject) => {
    const el = document.createElement('script')
    el.src = src
    el.async = true
    el.onload = () => resolve(globalName ? window[globalName] : null)
    el.onerror = () => reject(new Error(`加载脚本失败：${src}`))
    document.head.appendChild(el)
  })
  _scriptPromises.set(src, promise)
  return promise
}
