const readText = (value, fallback = '') => {
  if (Array.isArray(value)) {
    return readText(value[0], fallback)
  }
  if (typeof value !== 'string') {
    return fallback
  }
  const normalized = value.trim()
  return normalized || fallback
}

const readPositiveNumber = (value, fallback = 1) => {
  const normalized = Number(Array.isArray(value) ? value[0] : value)
  if (!Number.isFinite(normalized) || normalized <= 0) {
    return fallback
  }
  return Math.round(normalized)
}

const slugify = (value) => {
  const source = readText(value, 'practice-quiz')
  const slug = source
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)

  return slug || 'practice-quiz'
}

const buildOption = (questionId, index, text, isCorrect = false) => ({
  id: `${questionId}_option_${index + 1}`,
  text,
  isCorrect,
})

const buildQuestion = ({ quizId, index, question, subject, knowledgePoint, hint, score, options }) => ({
  id: `${quizId}_question_${index + 1}`,
  question,
  subject,
  knowledgePoint,
  hint,
  score,
  options: options.map((option, optionIndex) => buildOption(`${quizId}_question_${index + 1}`, optionIndex, option.text, option.isCorrect)),
})

export const buildGameLevels = (context = {}) => {
  return [
    {
      id: 'level-1',
      name: '基础概念',
      desc: '掌握双星模型的核心定义',
      icon: '📖',
      questions: [
        {
          id: 'l1q1',
          question: '双星系统中，两颗星绕公共质心运动，它们的哪个物理量必然相同？',
          knowledgePoint: '双星运动基本特征',
          hint: '两星始终保持连线通过质心，周期是否一致？',
          baseScore: 20,
          correctIndex: 1,
          options: ['线速度大小', '角速度（公转周期）', '向心加速度大小', '轨道半径'],
        },
        {
          id: 'l1q2',
          question: '双星系统中，两星之间的万有引力充当各自的什么力？',
          knowledgePoint: '向心力来源',
          hint: '双星做圆周运动，维持圆周运动需要哪种力？',
          baseScore: 20,
          correctIndex: 2,
          options: ['重力', '弹力', '向心力', '摩擦力'],
        },
        {
          id: 'l1q3',
          question: '设双星质量分别为 m₁、m₂，两星间距为 r，则质心到质量 m₁ 的距离 r₁ 满足？',
          knowledgePoint: '质心位置',
          hint: '质心定义：m₁r₁ = m₂r₂，且 r₁ + r₂ = r。',
          baseScore: 20,
          correctIndex: 0,
          options: ['r₁ = m₂r / (m₁ + m₂)', 'r₁ = m₁r / (m₁ + m₂)', 'r₁ = r / 2', 'r₁ = (m₁ - m₂)r / (m₁ + m₂)'],
        },
      ],
    },
    {
      id: 'level-2',
      name: '公式推导',
      desc: '运用万有引力和圆周运动公式',
      icon: '🔬',
      questions: [
        {
          id: 'l2q1',
          question: '双星系统中两星质量均为 m，间距为 r，则公转周期 T 的表达式为？（G 为引力常量）',
          knowledgePoint: '双星周期公式',
          hint: '引力 = 向心力：Gm²/r² = m·(2π/T)²·(r/2)，解出 T。',
          baseScore: 25,
          correctIndex: 3,
          options: [
            'T = 2π√(r³ / Gm)',
            'T = π√(r³ / Gm)',
            'T = 2π√(r³ / 2Gm)',
            'T = 2π√(r³ / 4Gm) · √2',
          ],
        },
        {
          id: 'l2q2',
          question: '双星中质量较大的星，其轨道半径与质量较小的星相比？',
          knowledgePoint: '轨道半径与质量关系',
          hint: '质心条件 m₁r₁ = m₂r₂，m₁ > m₂ 时 r₁ 与 r₂ 大小如何？',
          baseScore: 25,
          correctIndex: 1,
          options: ['轨道半径更大', '轨道半径更小', '轨道半径相等', '无法确定'],
        },
        {
          id: 'l2q3',
          question: '双星系统中，两星的线速度之比 v₁ : v₂ 等于？',
          knowledgePoint: '线速度比',
          hint: 'v = ωr，两星 ω 相同，线速度之比即轨道半径之比。',
          baseScore: 25,
          correctIndex: 0,
          options: ['r₁ : r₂', 'r₂ : r₁', 'm₁ : m₂', 'm₂ : m₁'],
        },
      ],
    },
    {
      id: 'level-3',
      name: '综合挑战',
      desc: '解决双星问题的综合计算',
      icon: '🏆',
      questions: [
        {
          id: 'l3q1',
          question: '双星 A、B 质量之比 mA : mB = 1 : 3，则两星向心加速度之比 aA : aB 为？',
          knowledgePoint: '向心加速度比较',
          hint: '两星所受引力大小相等，a = F/m，质量不同则加速度不同。',
          baseScore: 30,
          correctIndex: 2,
          options: ['1 : 3', '3 : 1', '3 : 1（aA > aB）', '1 : 1'],
        },
        {
          id: 'l3q2',
          question: '若已知双星系统的公转周期 T 和两星间距 r，可以求出什么物理量？',
          knowledgePoint: '双星系统总质量',
          hint: '由 G(m₁+m₂)/r² = (2π/T)²·r，可解出 m₁+m₂。',
          baseScore: 30,
          correctIndex: 1,
          options: ['各星单独质量', '两星质量之和', '两星质量之差', '两星的密度'],
        },
        {
          id: 'l3q3',
          question: '双星系统中，若其中一颗星质量突然增大，在两星间距不变的前提下，系统公转周期将如何变化？',
          knowledgePoint: '参数变化分析',
          hint: '总质量增大，由 T² ∝ r³/(m₁+m₂) 判断 T 的变化趋势。',
          baseScore: 30,
          correctIndex: 0,
          options: ['周期变短', '周期变长', '周期不变', '无法判断'],
        },
      ],
    },
  ]
}

export const parseMockGameContext = (query = {}) => {
  const courseName = readText(query.courseName, '课程学习')
  const lessonTitle = readText(query.lessonTitle, '当前课时')
  const sectionTitle = readText(query.sectionTitle, '核心知识点')
  const currentPage = readPositiveNumber(query.currentPage, 1)

  return {
    courseName,
    lessonTitle,
    sectionTitle,
    currentPage,
  }
}

export const buildMockGameQuiz = (context = {}) => {
  const { courseName, lessonTitle, sectionTitle, currentPage } = parseMockGameContext(context)
  const quizId = `lesson-${slugify(`${courseName}-${lessonTitle}-${sectionTitle}`)}`
  const scorePerQuestion = 25

  return {
    id: quizId,
    name: `双星问题 练习闯关`,
    totalScore: scorePerQuestion * 4,
    questions: [
      buildQuestion({
        quizId,
        index: 0,
        question: '双星系统中，两颗星绕公共质心做匀速圆周运动，以下说法正确的是？',
        subject: '双星问题',
        knowledgePoint: '双星运动基本规律',
        hint: '两星始终保持两心连线，思考角速度与周期的关系。',
        score: scorePerQuestion,
        options: [
          { text: '两星角速度相同，线速度也相同', isCorrect: false },
          { text: '两星角速度相同，线速度不同', isCorrect: true },
          { text: '两星线速度相同，角速度不同', isCorrect: false },
          { text: '两星向心力大小不同', isCorrect: false },
        ],
      }),
      buildQuestion({
        quizId,
        index: 1,
        question: '双星 A、B 质量分别为 2m 和 m，两星间距为 L，则 A 的轨道半径为？',
        subject: '双星问题',
        knowledgePoint: '质心与轨道半径',
        hint: '质心条件：m_A · r_A = m_B · r_B，且 r_A + r_B = L。',
        score: scorePerQuestion,
        options: [
          { text: 'L/3', isCorrect: true },
          { text: '2L/3', isCorrect: false },
          { text: 'L/2', isCorrect: false },
          { text: '3L/4', isCorrect: false },
        ],
      }),
      buildQuestion({
        quizId,
        index: 2,
        question: '两颗质量均为 M 的星体组成双星系统，间距为 d，引力常量为 G，则公转周期 T 为？',
        subject: '双星问题',
        knowledgePoint: '双星周期公式推导',
        hint: '每星轨道半径为 d/2，令引力 = 向心力：GM²/d² = M·ω²·(d/2)。',
        score: scorePerQuestion,
        options: [
          { text: 'T = 2π√(d³/GM)', isCorrect: false },
          { text: 'T = π√(2d³/GM)', isCorrect: true },
          { text: 'T = 2π√(d³/2GM)', isCorrect: false },
          { text: 'T = 2π√(d/GM)', isCorrect: false },
        ],
      }),
      buildQuestion({
        quizId,
        index: 3,
        question: '已知双星系统公转周期为 T，两星间距为 r，引力常量为 G，则两星质量之和为？',
        subject: '双星问题',
        knowledgePoint: '由周期求总质量',
        hint: '由 G(m₁+m₂)/r² = (2π/T)²·r 整理可得。',
        score: scorePerQuestion,
        options: [
          { text: 'GT²/(4π²r³)', isCorrect: false },
          { text: '4π²r³/(GT²)', isCorrect: true },
          { text: '2π²r³/(GT²)', isCorrect: false },
          { text: 'Gπ²r³/T²', isCorrect: false },
        ],
      }),
    ],
  }
}
