export function normalizeScriptSections(list = []) {
  return (Array.isArray(list) ? list : [])
    .map((item, index) => {
      const sectionId = item.sectionId || item.relatedChapterId || `section-${index + 1}`
      const relatedPages = Array.isArray(item.relatedPages) && item.relatedPages.length
        ? item.relatedPages.map(Number).filter(Number.isFinite)
        : [index + 1]
      const title = item.title || item.sectionName || `章节 ${index + 1}`

      return {
        sectionId,
        id: sectionId,
        title,
        sectionName: title,
        explainScript: item.explainScript || item.content || '',
        content: item.content || item.explainScript || '',
        keywords: [...(item.keywords || item.keyPoints || [])].filter(Boolean),
        keyPoints: [...(item.keyPoints || item.keywords || [])].filter(Boolean),
        relatedPages,
        page: relatedPages[0] || index + 1,
      }
    })
    .filter((item) => item.sectionId)
}
