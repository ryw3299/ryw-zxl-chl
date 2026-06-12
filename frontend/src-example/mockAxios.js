import axios from 'axios'

const demoCourse = {
  id: 1,
  cid: 1,
  name: '人工智能通识课',
  description: '面向演示场景的智能教学课程。',
  image: '/favicon.png',
  background: '课程围绕人工智能基础概念、课堂应用与学习方法展开。',
  target: '帮助学生理解 AI 工具如何辅助学习，帮助教师快速组织课堂资源。',
  principle: '以问题驱动、案例演示和即时反馈为核心。',
}

const demoCourses = [
  demoCourse,
  {
    ...demoCourse,
    id: 2,
    cid: 2,
    name: 'Python 数据分析',
    description: '使用可视化和案例理解数据分析流程。',
  },
  {
    ...demoCourse,
    id: 3,
    cid: 3,
    name: '智慧课堂实践',
    description: '教师备课、课堂互动与学习反馈演示。',
  },
]

const demoProblem = {
  id: 1,
  cid: 1,
  type: '简答',
  title: '请说明人工智能在课堂中的一个应用场景。',
  description: '结合你的学习经历，说明 AI 可以如何提升学习效率。',
  positive: 78,
  negative: 22,
}

const demoStudent = {
  id: '123',
  sid: '123',
  name: '演示学生',
  school: '通慧智教大学',
  department: '计算机科学与技术学院',
  major: '计算机科学与技术',
  class: '计算机科学与技术1班',
  email: 'student@example.local',
  enrollment: '2026',
}

const demoTeacher = {
  id: '123',
  tid: '123',
  name: '演示教师',
  school: '通慧智教大学',
  email: 'teacher@example.local',
}

const demoResponse = (data, status = 200) => Promise.resolve({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {},
})

const llmText = '这是本地演示前端生成的模拟内容，不会连接外部 AI 或后端服务。'

const routeData = (url) => {
  const value = String(url)

  if (value.includes('face/analysis')) {
    return { img: '', analysis: { result: { face_list: [{ age: 20, gender: { type: 'male', probability: 0.99 }, emotion: { type: 'happy', probability: 0.92 }, eye_status: { left_eye: 1, right_eye: 1 } }] } } }
  }
  if (value.includes('chat/llm') || value.includes('question') && value.includes('generate')) {
    return { reply: llmText, message: llmText, data: llmText, content: llmText }
  }
  if (value.includes('teacher/statistics')) {
    return { course_number: 3, resource_number: 18, assignment_number: 6, student_number: 128, star_number: 520 }
  }
  if (value.includes('statistics')) {
    return { student_number: 128, resource_number: 18, assignment_number: 6, question_number: 12, star_number: 520 }
  }
  if (value.includes('teacher/course') || value.endsWith('/course') || value.endsWith('/course/')) {
    return demoCourses
  }
  if (value.includes('course/chapter')) {
    return [
      { id: 1, title: '第一章 AI 基础', name: '第一章 AI 基础', description: '基础概念与课堂案例。' },
      { id: 2, title: '第二章 智慧课堂', name: '第二章 智慧课堂', description: '课堂互动与反馈。' },
    ]
  }
  if (value.includes('course/announcement') || value.includes('/message/')) {
    return [
      { id: 1, title: '演示公告', content: '这是本地演示数据，所有信息均来自前端 mock。', time: '2026-05-20' },
    ]
  }
  if (value.includes('course/resource')) {
    return [
      { id: 1, title: '课程讲义.pdf', name: '课程讲义.pdf', type: 'PDF', size: '2.4MB', time: '2026-05-20', url: '#' },
      { id: 2, title: '课堂示例.zip', name: '课堂示例.zip', type: 'ZIP', size: '1.1MB', time: '2026-05-20', url: '#' },
    ]
  }
  if (value.includes('course/assignment')) {
    return [
      { id: 1, title: '课后思考题', type: '简答', description: '说明一个你熟悉的 AI 教学应用。', deadline: '2026-06-01', time: '2026-05-20' },
    ]
  }
  if (value.includes('course/question')) {
    return [
      { id: 1, question: 'AI 可以如何辅助老师备课？', answer: '可以帮助整理知识点、生成练习题和提供课堂反馈。' },
    ]
  }
  if (value.includes('student/course/progress')) {
    return [
      { name: '人工智能通识课', value: 82, progress: 82 },
      { name: 'Python 数据分析', value: 64, progress: 64 },
    ]
  }
  if (value.includes('student/course/activity')) {
    return [20, 35, 48, 62, 80, 76, 90]
  }
  if (value.includes('student/activity')) {
    return [
      { date: '2026-05-20', title: '完成课堂练习', type: '学习记录' },
      { date: '2026-05-19', title: '查看课程资料', type: '资源浏览' },
    ]
  }
  if (value.includes('student/emotion/status')) {
    return { message: '0.76' }
  }
  if (value.includes('student/problem/history')) {
    return [demoProblem]
  }
  if (value.includes('problem/key_concept')) {
    return [{ title: '智能教学', description: '使用算法与数据辅助教学决策。' }]
  }
  if (value.includes('problem/')) {
    return demoProblem
  }
  if (value.includes('student/info/family')) {
    return { parent: '演示家长', phone: '13800000000', address: '本地演示地址' }
  }
  if (value.includes('student/info/instructor')) {
    return { name: '演示导师', email: 'teacher@example.local', phone: '13800000001' }
  }
  if (value.includes('student/info/academy')) {
    return { school: demoStudent.school, department: demoStudent.department, major: demoStudent.major, class: demoStudent.class }
  }
  if (value.includes('student/info/basic') || value.includes('student/')) {
    return demoStudent
  }
  if (value.includes('teacher/') || value.includes('parent/')) {
    return demoTeacher
  }
  if (value.includes('description.json')) {
    return { title: '本地课程资源', chapters: [] }
  }
  if (value.includes('/course/')) {
    return demoCourse
  }

  return { message: 'ok', data: [] }
}

axios.get = (url) => demoResponse(routeData(url))
axios.post = (url) => demoResponse(routeData(url), String(url).includes('student/course') ? 201 : 200)
axios.put = (url) => demoResponse(routeData(url))
axios.delete = (url) => demoResponse(routeData(url))
