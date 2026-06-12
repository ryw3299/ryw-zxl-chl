/**
 * 精心策划的章节关键词映射（演示数据）
 * Key: `${datasetId}:${chapterId}`
 * Value: 本章核心关键词列表（按重要性排序）
 *
 * 跨章节共享的关键词会自动形成网络图中的跨章联结。
 */

export const CHAPTER_KEYWORDS = {
  // ── 人工智能导论 ───────────────────────────────────────────
  'ai-intro:ch1': [
    '人工智能', '图灵测试', '符号主义', '连接主义', '行为主义',
    '感知智能', '认知智能', '决策智能', '神经网络', '深度学习', '机器学习',
  ],
  'ai-intro:ch2': [
    '启发式搜索', '状态空间', '广度优先搜索', '深度优先搜索',
    'A*算法', '博弈树', 'α-β剪枝', '蒙特卡洛', '迭代加深', '最短路径',
  ],
  'ai-intro:ch3': [
    '机器学习', '监督学习', '无监督学习', '强化学习',
    '过拟合', '欠拟合', '交叉验证', '梯度下降', '特征工程', '损失函数',
  ],
  'ai-intro:ch4': [
    '深度学习', '神经网络', '反向传播', '激活函数',
    '卷积神经网络', '循环神经网络', 'LSTM', '注意力机制',
    'Transformer', '迁移学习', '梯度下降',
  ],
  'ai-intro:ch5': [
    '知识表示', '谓词逻辑', '语义网络', '框架表示',
    '产生式规则', '本体', '知识图谱', '推理机', '前向链接', '后向链接',
  ],
  'ai-intro:ch6': [
    '自然语言处理', '分词', '词向量', 'Word2Vec', 'BERT',
    '命名实体识别', '情感分析', '机器翻译', '问答系统', '大语言模型', 'Transformer',
  ],
  'ai-intro:ch7': [
    'AI伦理', '算法偏见', '可解释AI', '数据隐私', '对抗样本',
    'AI安全', '公平性', '人机协同', '透明度', '问责制',
  ],

  // ── 数据结构与算法 ───────────────────────────────────────────
  'data-structures:ch1': [
    '数据结构', '算法', '时间复杂度', '空间复杂度',
    '大O记法', '抽象数据类型', '递归', '递推关系',
  ],
  'data-structures:ch2': [
    '数组', '链表', '栈', '队列',
    '双端队列', '优先队列', '循环队列', 'KMP算法',
  ],
  'data-structures:ch3': [
    '二叉树', '二叉搜索树', 'AVL树', '红黑树',
    'B树', '堆', '字典树', '哈夫曼树', '优先队列',
  ],
  'data-structures:ch4': [
    '图', '邻接矩阵', '邻接表', '广度优先搜索', '深度优先搜索',
    'Dijkstra', 'Bellman-Ford', 'Floyd', '最小生成树', '拓扑排序',
  ],
  'data-structures:ch5': [
    '冒泡排序', '插入排序', '归并排序', '快速排序',
    '堆排序', '二分查找', '哈希表', '布隆过滤器',
  ],
  'data-structures:ch6': [
    '分治', '动态规划', '贪心算法', '回溯法',
    '分支限界', 'NP问题', '近似算法', '随机算法',
  ],

  // ── Python 程序设计 ───────────────────────────────────────────
  'python-programming:ch1': [
    'Python', '基本数据类型', '字符串', '列表',
    '元组', '字典', '集合', '列表推导式',
  ],
  'python-programming:ch2': [
    '条件分支', '循环', '函数', 'lambda',
    '闭包', '装饰器', '生成器', '迭代器',
  ],
  'python-programming:ch3': [
    '类', '对象', '继承', '多继承',
    'MRO', '封装', '多态', '特殊方法', '抽象基类',
  ],
  'python-programming:ch4': [
    '文件操作', 'JSON', 'CSV', 'pickle',
    'pathlib', '异常处理', 'try-except', '自定义异常',
  ],
  'python-programming:ch5': [
    'itertools', 'functools', 'collections', 'datetime',
    '正则表达式', 'threading', 'asyncio', '单元测试', '虚拟环境', '类型注解',
  ],

  // ── 机器学习基础 ───────────────────────────────────────────
  'machine-learning:ch1': [
    '机器学习', '监督学习', '无监督学习', '强化学习',
    '训练集', '验证集', '测试集', '特征', '归纳偏置',
  ],
  'machine-learning:ch2': [
    '线性回归', '梯度下降', '学习率', 'L1正则化', 'L2正则化',
    'Logistic回归', '决策边界', '支持向量机', '核技巧',
  ],
  'machine-learning:ch3': [
    '决策树', '信息增益', '基尼系数', '集成学习',
    'Bagging', '随机森林', 'Boosting', 'AdaBoost', 'GBDT', 'XGBoost',
  ],
  'machine-learning:ch4': [
    'K-Means', '层次聚类', 'DBSCAN', 'PCA',
    't-SNE', 'UMAP', '自编码器', '变分自编码器', '异常检测',
  ],
  'machine-learning:ch5': [
    '混淆矩阵', '精确率', '召回率', 'F1值',
    'AUC-ROC', '均方误差', 'k折交叉验证', '网格搜索', '贝叶斯优化',
  ],
}

/**
 * 为一条知识点匹配其中包含的关键词（大小写不敏感）
 */
export function matchKeywordsInText(text, keywords) {
  const matched = new Set()
  const lower = String(text).toLowerCase()
  for (const kw of keywords) {
    if (lower.includes(kw.toLowerCase())) matched.add(kw)
  }
  return matched
}

/**
 * 为章节计算关键词的出现次数（按知识点条数统计）
 */
export function computeKeywordFreq(chapter, keywords) {
  const freqMap = new Map()
  for (const kw of keywords) freqMap.set(kw, 0)
  const kwLower = keywords.map((k) => ({ raw: k, lower: k.toLowerCase() }))
  for (const kp of chapter.knowledge_points) {
    const kpLower = String(kp).toLowerCase()
    for (const { raw, lower } of kwLower) {
      if (kpLower.includes(lower)) freqMap.set(raw, freqMap.get(raw) + 1)
    }
  }
  return [...freqMap.entries()]
    .map(([word, count]) => ({ word, count: Math.max(1, count) }))
    .sort((a, b) => b.count - a.count)
}
