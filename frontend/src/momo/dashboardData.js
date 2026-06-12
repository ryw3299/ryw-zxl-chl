export const learningPathOverview = {
  completionRate: 68,
  streakDays: 12,
  weeklyHours: 9.5,
  nextMilestone: '完成“神经网络基础”阶段测验',
}

export const learningPathStages = [
  {
    id: 'stage-1',
    phase: '阶段 01',
    title: 'AI 基础认知',
    progress: 100,
    status: 'completed',
    duration: '第 1-2 周',
    focus: '建立概念框架，理解 AI、机器学习与深度学习之间的关系。',
    modules: ['人工智能概览', '机器学习范式', '典型应用场景'],
    outcome: '已完成 3/3 个模块',
  },
  {
    id: 'stage-2',
    phase: '阶段 02',
    title: '数学与建模基础',
    progress: 76,
    status: 'active',
    duration: '第 3-5 周',
    focus: '补足线性代数、概率统计与优化的关键直觉，支撑后续模型理解。',
    modules: ['向量与矩阵', '概率分布', '梯度下降'],
    outcome: '推荐优先复习“梯度下降”与“损失函数”',
  },
  {
    id: 'stage-3',
    phase: '阶段 03',
    title: '神经网络基础',
    progress: 42,
    status: 'upcoming',
    duration: '第 6-8 周',
    focus: '从单层感知机过渡到多层网络，理解前向传播与反向传播。',
    modules: ['感知机', '多层网络', '反向传播'],
    outcome: '解锁条件：完成数学基础阶段',
  },
  {
    id: 'stage-4',
    phase: '阶段 04',
    title: '项目实战与复盘',
    progress: 8,
    status: 'planned',
    duration: '第 9-12 周',
    focus: '围绕真实案例完成一次完整建模流程，形成可复用的方法论。',
    modules: ['数据清洗', '模型训练', '实验复盘'],
    outcome: '结项输出：项目报告 + 讲解视频',
  },
]

export const learningPathMilestones = [
  {
    id: 'm-1',
    title: '下一次测验',
    detail: '周四 19:30 · 神经网络基础随堂测',
    accent: '#2563eb',
  },
  {
    id: 'm-2',
    title: '目标证书',
    detail: 'AI 导论阶段认证 · 还差 18 学习积分',
    accent: '#0891b2',
  },
  {
    id: 'm-3',
    title: '复习提醒',
    detail: '建议本周回看 2 次“梯度下降”讲解',
    accent: '#059669',
  },
]

export const weeklyLearningPlan = [
  {
    id: 'w-1',
    day: '周一',
    title: '线性代数回顾',
    minutes: 45,
    tag: '基础巩固',
    done: true,
  },
  {
    id: 'w-2',
    day: '周二',
    title: '梯度下降专题课',
    minutes: 60,
    tag: '重点突破',
    done: true,
  },
  {
    id: 'w-3',
    day: '周三',
    title: '知识点自测',
    minutes: 25,
    tag: '测验',
    done: false,
  },
  {
    id: 'w-4',
    day: '周四',
    title: '课堂讨论与问答',
    minutes: 40,
    tag: '互动',
    done: false,
  },
  {
    id: 'w-5',
    day: '周五',
    title: '案例代码跟练',
    minutes: 70,
    tag: '实战',
    done: false,
  },
]

export const skillProgress = [
  { id: 's-1', label: '数学基础', value: 82, color: '#2563eb' },
  { id: 's-2', label: '建模思维', value: 71, color: '#0891b2' },
  { id: 's-3', label: '代码实现', value: 64, color: '#0f766e' },
  { id: 's-4', label: '结果表达', value: 58, color: '#d97706' },
]

export const leaderboardTopThree = [
  {
    id: 'u-1',
    name: '陈思远',
    score: 1560,
    rank: 2,
    streak: 15,
    courses: 7,
    badge: '稳定推进',
  },
  {
    id: 'u-2',
    name: '林知夏',
    score: 1688,
    rank: 1,
    streak: 21,
    courses: 8,
    badge: '本周领先',
  },
  {
    id: 'u-3',
    name: '周靖',
    score: 1482,
    rank: 3,
    streak: 13,
    courses: 6,
    badge: '持续跟进',
  },
]

export const leaderboardEntries = [
  { id: 'u-4', rank: 4, name: '赵闻笙', score: 1396, growth: '+11%', focus: '机器学习基础', minutes: 640 },
  { id: 'u-5', rank: 5, name: '许安', score: 1318, growth: '+9%', focus: 'Python 程序设计', minutes: 598 },
  { id: 'u-6', rank: 6, name: '沈清禾', score: 1262, growth: '+14%', focus: '数据结构与算法', minutes: 576 },
  { id: 'u-7', rank: 7, name: '你', score: 1216, growth: '+18%', focus: '人工智能导论', minutes: 552, isCurrentUser: true },
  { id: 'u-8', rank: 8, name: '蒋舟', score: 1184, growth: '+7%', focus: '人工智能导论', minutes: 531 },
  { id: 'u-9', rank: 9, name: '吴昀', score: 1138, growth: '+5%', focus: '机器学习基础', minutes: 516 },
  { id: 'u-10', rank: 10, name: '冯恬', score: 1096, growth: '+4%', focus: 'Python 程序设计', minutes: 493 },
]

export const leaderboardInsights = [
  {
    id: 'i-1',
    title: '进入前五还差',
    value: '102 分',
    detail: '完成 2 次专题练习和 1 次课堂测验，基本可以追平。',
  },
  {
    id: 'i-2',
    title: '本周成长率',
    value: '+18%',
    detail: '当前增速在前十里排第 2，保持节奏还有上升空间。',
  },
  {
    id: 'i-3',
    title: '建议优先课程',
    value: '人工智能导论',
    detail: '这门课的问答得分还有提升空间，适合用来快速补分。',
  },
]

const seededRandom = (seed) => {
  let s = seed
  return () => {
    s = (s * 16807 + 0) % 2147483647
    return (s - 1) / 2147483646
  }
}

const hashCode = (str) => {
  let hash = 0
  for (let i = 0; i < str.length; i += 1) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

const COURSE_PROFILES = {
  'course-1': {
    name: '人工智能导论',
    unit: 'AI 核心原理与感知机模型',
    audience: '大一(2)班',
    studentCount: 45,
    totalPages: 18,
    queries: [
      '老师，为什么 sigmoid 函数要取指数？',
      '反向传播里的链式法则怎么理解？',
      '损失函数最小化和梯度下降是什么关系？',
    ],
    clusters: [
      { label: '错因 1：激活函数理解偏差', desc: '将 sigmoid 与 ReLU 的适用场景混淆', pct: 38, count: 17 },
      { label: '错因 2：反向传播链路不清', desc: '不理解梯度如何从输出层逐层回传', pct: 36, count: 16 },
      { label: '错因 3：数学基础薄弱', desc: '偏导数与链式求导运算存在困难', pct: 26, count: 12 },
    ],
    advices: [
      { tag: '可视化增强', tagClass: 'tag-visual', title: '增加计算图动画', content: '建议插入反向传播计算图动画，用|红色箭头高亮梯度流向|，用|蓝色节点展示层间输出|。' },
      { tag: '分支降级', tagClass: 'tag-branch', title: '补充数学前置分支', content: '针对基础薄弱学生，插入“偏导数与链式法则速查”分支内容。' },
    ],
  },
  'course-2': {
    name: '机器学习基础',
    unit: '模型评估与交叉验证',
    audience: '大二(1)班',
    studentCount: 52,
    totalPages: 15,
    queries: [
      'K-fold 的 K 越大越好吗？',
      '为什么训练集准确率高但测试集很低？',
      '正则化参数 λ 怎么选？',
    ],
    clusters: [
      { label: '错因 1：过拟合判断失误', desc: '无法区分过拟合与欠拟合的表现差异', pct: 42, count: 22 },
      { label: '错因 2：验证策略混淆', desc: '验证集与测试集用途边界不清', pct: 35, count: 18 },
      { label: '错因 3：正则化原理不明', desc: '对 L1/L2 如何约束模型复杂度理解不足', pct: 23, count: 12 },
    ],
    advices: [
      { tag: '交互实验', tagClass: 'tag-visual', title: '增加学习曲线面板', content: '建议增加训练/验证误差曲线交互图，让学生拖动模型复杂度观察过拟合变化。' },
      { tag: '动态路由', tagClass: 'tag-branch', title: '补充正则化推导路径', content: '对正则化理解困难的学生自动切入低阶解释路径。' },
    ],
  },
  'course-3': {
    name: '数据结构与算法',
    unit: '动态规划入门与状态转移',
    audience: '大一(5)班',
    studentCount: 48,
    totalPages: 20,
    queries: [
      '状态转移方程怎么列？',
      '记忆化搜索和动态规划有什么区别？',
      '为什么要从子问题开始推？',
    ],
    clusters: [
      { label: '错因 1：状态定义困难', desc: '无法抽象出稳定的子问题结构', pct: 45, count: 22 },
      { label: '错因 2：递推方向混淆', desc: '自顶向下与自底向上的适用场景不清', pct: 32, count: 15 },
      { label: '错因 3：边界条件遗漏', desc: '基础情况处理不完整导致结果错误', pct: 23, count: 11 },
    ],
    advices: [
      { tag: '可视化增强', tagClass: 'tag-visual', title: '增加状态转移动画', content: '建议插入 DP 表格逐步填充动画，用|红色高亮当前状态|，用|蓝色标记依赖状态|。' },
      { tag: '分支降级', tagClass: 'tag-branch', title: '补充递归到 DP 的过渡讲解', content: '对方向混淆的学生，补充“暴力递归 → 记忆化 → 递推”的渐进式讲解。' },
    ],
  },
  'course-4': {
    name: 'Python 程序设计',
    unit: '面向对象编程与类继承',
    audience: '大一(3)班',
    studentCount: 55,
    totalPages: 16,
    queries: [
      'self 参数到底是什么？',
      '子类调用父类方法应该用 super() 吗？',
      '什么时候该用继承，什么时候该用组合？',
    ],
    clusters: [
      { label: '错因 1：self 理解偏差', desc: '不理解实例方法中 self 的绑定机制', pct: 40, count: 22 },
      { label: '错因 2：继承链混乱', desc: '多继承场景下 MRO 解析顺序不清', pct: 35, count: 19 },
      { label: '错因 3：封装意识缺失', desc: '直接访问内部属性而非通过方法接口', pct: 25, count: 14 },
    ],
    advices: [
      { tag: '交互实验', tagClass: 'tag-visual', title: '增加对象模型图', content: '建议插入对象与类关系图，用|红色标注实例属性|，用|蓝色标注类属性|。' },
      { tag: '动态路由', tagClass: 'tag-branch', title: '补充继承实战分支', content: '对继承链理解混乱的学生，补充从单继承到多继承的渐进示例。' },
    ],
  },
}

const CLUSTER_COLORS = ['#ef4444', '#f59e0b', '#3b82f6']

export const generateDashboardData = (courseId) => {
  const profile = COURSE_PROFILES[courseId]
  const rand = seededRandom(hashCode(courseId || 'default'))

  const courseName = profile?.name || '综合能力训练'
  const courseUnit = profile?.unit || '课程关键知识梳理'
  const audience = profile?.audience || '默认班级'
  const studentCount = profile?.studentCount || 40
  const totalPages = profile?.totalPages || 12

  const barData = []
  let totalInteractions = 0
  let maxVal = 0
  let maxPage = 1

  for (let i = 1; i <= totalPages; i += 1) {
    const wave = Math.sin(i / 2) * 6
    const noise = Math.floor(rand() * 8)
    const val = Math.max(3, Math.round(8 + wave + noise))
    totalInteractions += val
    if (val > maxVal) {
      maxVal = val
      maxPage = i
    }
    barData.push({ page: `页${i}`, val, pct: 0, danger: false })
  }

  barData.forEach((item) => {
    item.pct = Math.round((item.val / maxVal) * 100)
  })

  const dangerIndex = barData.findIndex((item) => item.val === maxVal)
  if (dangerIndex >= 0) {
    barData[dangerIndex].danger = true
  }

  const clusters = (profile?.clusters || [
    { label: '错因 1：核心概念混淆', desc: '基础定义理解存在偏差', pct: 44, count: Math.round(studentCount * 0.44) },
    { label: '错因 2：知识迁移受阻', desc: '无法将理论映射到具体题型', pct: 33, count: Math.round(studentCount * 0.33) },
    { label: '错因 3：计算过程不稳', desc: '推导和中间步骤容易出错', pct: 23, count: Math.round(studentCount * 0.23) },
  ]).map((cluster, index) => ({
    ...cluster,
    color: CLUSTER_COLORS[index] || '#6b7280',
  }))

  const nlpConfidence = (85 + rand() * 12).toFixed(1)

  return {
    courseName,
    courseUnit,
    audience,
    studentCount,
    totalPages,
    totalInteractions,
    dangerNode: `Node_${maxPage}`,
    dangerPage: maxPage,
    nlpConfidence: `${nlpConfidence}%`,
    adviceCount: profile?.advices?.length || 2,
    barData,
    rawQueries: profile?.queries || [
      '这个概念和之前学的有什么区别？',
      '公式推导过程能再讲一遍吗？',
      '实际应用场景里应该怎么用？',
    ],
    clusters,
    advices: profile?.advices || [
      { tag: '可视化增强', tagClass: 'tag-visual', title: '增加概念对比图', content: '建议插入概念对比图，用|红色标注易混淆点|，用|蓝色标注正确理解|。' },
      { tag: '分支降级', tagClass: 'tag-branch', title: '补充前置知识分支', content: '针对基础薄弱的学生，在卡壳节点自动切入前置知识讲解。' },
    ],
  }
}
