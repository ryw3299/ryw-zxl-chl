const STORAGE_KEY = 'resource-library-items'

const seedResources = Object.freeze([
  {
    id: 'res-ai-001',
    title: '人工智能导论导学讲义',
    courseId: 'course-1',
    courseName: '人工智能导论',
    description: '覆盖课程目标、章节结构与课堂讨论引导，适合作为导学材料与课前预习资源。',
    tags: ['导学', 'PDF', '重点'],
    fileName: '人工智能导论导学讲义.pdf',
    fileSize: '4.8 MB',
    fileType: 'PDF',
    uploadedAt: '2026-04-10 14:20',
    uploader: '张老师',
    downloadCount: 58,
    accent: '#2563eb',
  },
  {
    id: 'res-ml-002',
    title: '机器学习基础实验模板',
    courseId: 'course-2',
    courseName: '机器学习基础',
    description: '包含 sklearn 实验骨架、数据说明与结果记录页，适合作为课堂实验起始模板。',
    tags: ['实验', '模板', '作业'],
    fileName: '机器学习基础实验模板.zip',
    fileSize: '12.1 MB',
    fileType: 'ZIP',
    uploadedAt: '2026-04-12 09:35',
    uploader: '张老师',
    downloadCount: 41,
    accent: '#0891b2',
  },
  {
    id: 'res-cs-003',
    title: '数据结构高频题型清单',
    courseId: 'course-3',
    courseName: '数据结构与算法',
    description: '整理了树、图、排序和动态规划的高频考点，适合复习和课堂随练。',
    tags: ['练习', '重点', '复习'],
    fileName: '数据结构高频题型清单.docx',
    fileSize: '1.3 MB',
    fileType: 'DOCX',
    uploadedAt: '2026-04-13 19:10',
    uploader: '张老师',
    downloadCount: 36,
    accent: '#7c3aed',
  },
  {
    id: 'res-py-004',
    title: 'Python 课堂案例素材包',
    courseId: 'course-4',
    courseName: 'Python 程序设计',
    description: '收录文件读写、函数封装和面向对象三个课堂案例，配套截图与运行说明。',
    tags: ['案例', '课堂', '素材'],
    fileName: 'Python课堂案例素材包.zip',
    fileSize: '8.6 MB',
    fileType: 'ZIP',
    uploadedAt: '2026-04-14 11:45',
    uploader: '张老师',
    downloadCount: 29,
    accent: '#059669',
  },
])

const normalizeResource = (item = {}) => ({
  id: String(item.id || `res-${Date.now()}`),
  title: String(item.title || '').trim(),
  courseId: String(item.courseId || '').trim(),
  courseName: String(item.courseName || '').trim(),
  description: String(item.description || '').trim(),
  tags: Array.isArray(item.tags) ? item.tags.map((tag) => String(tag).trim()).filter(Boolean) : [],
  fileName: String(item.fileName || '').trim(),
  fileSize: String(item.fileSize || '').trim(),
  fileType: String(item.fileType || 'FILE').trim().toUpperCase(),
  uploadedAt: String(item.uploadedAt || ''),
  uploader: String(item.uploader || ''),
  downloadCount: Number.isFinite(Number(item.downloadCount)) ? Number(item.downloadCount) : 0,
  accent: String(item.accent || '#2563eb'),
})

export const getSeedResources = () => seedResources.map((item) => ({ ...item, tags: [...item.tags] }))

export const loadResourceLibrary = () => {
  if (typeof window === 'undefined') {
    return getSeedResources()
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return getSeedResources()
    }
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return getSeedResources()
    }
    const resources = parsed.map(normalizeResource).filter((item) => item.title && item.courseName)
    return resources.length ? resources : getSeedResources()
  } catch {
    return getSeedResources()
  }
}

export const persistResourceLibrary = (items = []) => {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.map(normalizeResource)))
}

