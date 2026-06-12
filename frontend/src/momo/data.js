const clone = (value) => JSON.parse(JSON.stringify(value))

export const mockCourseInfo = {
  courseId: 'course-ai-001',
  courseName: '人工智能导论',
  courseDesc: '面向高校本科生的 AI 基础课程，包含模型基础、应用实践与案例分析。',
  teacherName: '李老师',
}

export const mockSections = [
  {
    sectionId: 'sec-1',
    title: '1. 课程导入与目标',
    relatedPages: [1, 2],
    keywords: ['课程目标', '学习路径', '评估方式'],
    explainScript:
      '本节介绍课程目标和整体学习路径。请重点关注知识体系如何从基础概念逐步过渡到实际应用。',
  },
  {
    sectionId: 'sec-2',
    title: '2. 机器学习基础',
    relatedPages: [3, 4, 5, 6],
    keywords: ['监督学习', '损失函数', '模型评估'],
    explainScript:
      '这里讲解机器学习的核心要素：数据、模型、损失函数与优化目标。建议结合示例理解训练与推理的差异。',
  },
  {
    sectionId: 'sec-3',
    title: '3. 深度学习与大模型',
    relatedPages: [7, 8, 9, 10, 11, 12],
    keywords: ['神经网络', 'Transformer', '参数规模'],
    explainScript:
      '本节聚焦深度学习发展脉络，并介绍 Transformer 在大模型中的关键作用，理解参数规模与泛化能力之间的关系。',
  },
  {
    sectionId: 'sec-4',
    title: '4. 高校场景应用',
    relatedPages: [13, 14, 15, 16, 17, 18],
    keywords: ['智能助教', '学习分析', '实时问答'],
    explainScript:
      '最后展示 AI 在高校在线学习中的应用，包括课件讲解、实时问答、学习画像与个性化节奏调整。',
  },
]

export const mockKnowledgeTree = [
  {
    id: 'k-1',
    label: 'AI 基础认知',
    children: [
      { id: 'k-1-1', label: '学习目标' },
      { id: 'k-1-2', label: '课程结构' },
    ],
  },
  {
    id: 'k-2',
    label: '机器学习核心',
    children: [
      { id: 'k-2-1', label: '训练流程' },
      { id: 'k-2-2', label: '模型评估指标' },
    ],
  },
  {
    id: 'k-3',
    label: '大模型实践',
    children: [
      { id: 'k-3-1', label: 'Transformer 结构' },
      { id: 'k-3-2', label: '教育场景部署' },
    ],
  },
]

export const mockPageContents = Array.from({ length: 18 }, (_, index) => {
  const page = index + 1
  return `第 ${page} 页课件示意内容：本页用于演示 PPT/PDF 预览区域，后续可替换为真实渲染结果。`
})

export const mockLessonMeta = {
  lessonId: 'lesson-ai-001',
  lessonTitle: '基于泛雅平台的 AI 互动智课',
  fileName: 'AI互动智课示例课件.pdf',
  totalPages: 18,
  sections: mockSections,
  pageContents: mockPageContents,
}

export const sleep = (data, delay = 500) =>
  new Promise((resolve) => {
    setTimeout(() => resolve(clone(data)), delay)
  })

export const createMockParseResult = (fileName = '上传课件.pdf') => ({
  fileName,
  totalPages: 18,
  knowledgeTree: mockKnowledgeTree,
  sections: mockSections,
  lessonTitle: 'AI 智课自动生成内容',
  pageContents: mockPageContents,
  parseStatus: 'success',
})

export const createMockScriptResult = () => ({
  scriptId: `script-${Date.now()}`,
  generatedAt: new Date().toISOString(),
  sections: mockSections.map((item) => ({
    ...item,
    explainScript: `${item.explainScript}（脚本已生成，可直接用于讲解播放）`,
  })),
})

const inferUnderstandingLevel = (question) => {
  if (!question) {
    return '中等'
  }
  if (question.includes('为什么') || question.includes('原理')) {
    return '深入'
  }
  if (question.includes('例子') || question.includes('举例')) {
    return '基础'
  }
  return '中等'
}

export const createMockQAResult = (question = '') => {
  const understandingLevel = inferUnderstandingLevel(question)
  return {
    answer:
      question.trim().length > 0
        ? `围绕你的问题“${question}”，系统建议先复习当前章节关键概念，再结合课件第 ${Math.ceil(
            Math.random() * 6,
          )} 页的示例理解。`
        : '请补充问题细节，我可以结合当前章节给出更准确的解答。',
    relatedKnowledge: ['当前章节核心概念', '跨章节关联知识'],
    understandingLevel,
    suggestions: ['能再给一个实际案例吗？', '这部分和上一章有什么联系？', '我需要补哪些前置知识？'],
    resumeHint: '问答完成后可回到原讲解节点继续学习。',
  }
}

export const createMockProgressResult = (action = '继续当前章节') => {
  const configMap = {
    继续当前章节: { pace: 'normal', delta: 5, understandingLevel: '中等' },
    补充讲解: { pace: 'slow', delta: 3, understandingLevel: '提升中' },
    加快节奏: { pace: 'fast', delta: 7, understandingLevel: '良好' },
  }
  const config = configMap[action] || configMap['继续当前章节']
  return {
    action,
    pace: config.pace,
    progressDelta: config.delta,
    understandingLevel: config.understandingLevel,
    recommendedActions: ['继续当前章节', '补充讲解', '加快节奏'],
  }
}
