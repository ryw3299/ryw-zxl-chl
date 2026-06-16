# 基于大模型的个性化资源生成与学习多智能体系统开发计划

## 1. 项目背景与定位

本项目拟以已有项目 `ryw-zxl-chl` 为工程模板，开发一个面向计算机、软件工程、人工智能等信息类工科学生的个性化学习资源生成与多智能体学习辅助系统。

系统不是单纯的聊天机器人，也不是单纯的资源生成工具，而是一个完整的学习平台。平台以“动态学生画像”为核心，以“个性化学习路径”为主线，以“资源生成、智能助手、学习行为感知”为支撑，形成持续更新的个性化学习闭环。

整体目标：

1. 为学生建立动态学习画像；
2. 根据画像生成自然语言化、结构化的个性化学习路径；
3. 基于平台已有资源和大模型生成资源，为学生推荐或生成学习材料；
4. 在网页中提供右侧智能助手，支持选中文字、页面截图、图片上传等上下文问答；
5. 根据阅读、视频、答题、提问等学习行为持续更新学生画像；
6. 形成“画像生成—路径规划—资源推荐—学习行为—画像更新—路径调整”的完整闭环。

---

## 2. 参考模板项目说明

已有模板项目 `ryw-zxl-chl` 可作为本项目的工程基础。该项目包含 FastAPI 后端、Vue 3 + Vite 前端、Agent 链路、工具调用、课程内容处理、学习状态记录等基础能力。

本项目可以复用或参考以下内容：

1. 前后端分离结构；
2. Vue 3 + Vite 前端工程；
3. FastAPI 后端服务结构；
4. Agent 请求与响应封装方式；
5. 学习状态、学习进度、问答记录等设计思路；
6. 首页、课程页、学习页、智能体交互页等页面组织方式；
7. `.env.example`、启动脚本、部署文档、测试目录等工程规范。

但本项目的业务重点需要从原来的“课程 Agent / 教师侧课件链路”转向“学生画像驱动的个性化学习平台”。

---

## 3. 系统整体定位

项目名称建议：

> 智学工坊：面向工科生的个性化学习资源生成与多智能体学习平台

也可以使用更正式的名称：

> 基于大模型的工科生个性化学习资源生成与多智能体学习辅助系统

系统核心理念：

> 以动态学生画像为核心，以个性化学习路径为主线，以平台资源与生成式资源为内容支撑，以智能助手和行为感知实现学习过程中的持续反馈与动态优化。

---

## 4. 系统核心闭环

系统整体闭环如下：

```text
用户注册 / 登录
  ↓
检测是否已有学生画像
  ↓
无画像：进入初始化个人信息对话
  ↓
Dify 工作流生成六维动态学生画像
  ↓
系统生成个性化学习路径
  ↓
优先推荐平台已有课程、文档、视频、题库等资源
  ↓
根据路径阶段和用户画像生成个性化资源
  ↓
用户阅读文档、观看视频、完成测验、向助手提问
  ↓
系统记录学习行为事件
  ↓
智能助手主动干预或答疑
  ↓
画像更新工作流或后端规则更新学生画像
  ↓
系统动态调整学习路径、推荐资源和生成资源
```

系统不是五个功能的简单堆叠，而是一个持续运行的学习反馈系统。

---

## 5. 用户角色设计

### 5.1 学生用户

学生是系统的主要使用者，拥有以下能力：

1. 注册、登录、维护个人信息；
2. 初始化个人学习画像；
3. 查看自己的学生画像；
4. 生成个性化学习路径；
5. 查看平台已有学习资源；
6. 阅读文档、观看视频、完成练习题；
7. 生成个性化学习资源；
8. 使用右侧智能助手进行学习答疑；
9. 查看学习记录、掌握度、薄弱知识点和推荐任务。

### 5.2 管理员用户

管理员主要负责平台基础数据维护，拥有以下能力：

1. 管理用户；
2. 管理课程资源；
3. 管理文档资源；
4. 管理视频资源；
5. 管理知识点标签；
6. 查看系统使用数据；
7. 配置 Dify 工作流地址和 API Key。

### 5.3 可选教师用户

如开发时间充足，可以加入教师角色：

1. 上传课程资源；
2. 创建课程章节；
3. 查看学生学习情况；
4. 查看学生共性薄弱点；
5. 生成班级学习分析报告。

MVP 阶段可以先不做教师端，优先完成学生端和管理员端。

---

## 6. 功能模块总览

系统功能分为基础平台功能和智能化功能两大类。

### 6.1 基础平台功能

这些功能虽然不是赛题基本需求中重点强调的 AI 功能，但作为完整系统必须具备：

1. 首页；
2. 用户注册；
3. 用户登录；
4. 个人中心；
5. 学生画像页；
6. 学习路径页；
7. 资源中心；
8. 资源详情页；
9. 文档阅读页；
10. 视频学习页；
11. 题目练习页；
12. 学习记录页；
13. 资源生成历史页；
14. 管理后台；
15. 课程资源管理；
16. 知识点管理；
17. 智能助手悬浮组件。

### 6.2 智能化核心功能

1. 初始化个人信息对话；
2. 动态学生画像生成；
3. 个性化学习路径规划；
4. 平台已有资源推荐；
5. 个性化资源生成；
6. 多智能体协同生成；
7. 右侧智能学习助手；
8. 页面选中文字添加到会话；
9. 页内截图添加到会话；
10. 图片上传提问；
11. 阅读行为感知；
12. 视频学习行为感知；
13. 主动弹窗式学习检测；
14. 学生画像动态更新；
15. 学习路径动态调整。

---

## 7. 页面规划

### 7.1 首页

首页不是简单展示入口，而应该体现系统完整性。

首页内容建议包括：

1. 系统名称与简介；
2. 核心能力展示；
3. 使用流程说明；
4. 学生画像、路径规划、资源生成、智能助手四个核心入口；
5. 推荐学习方向；
6. 热门课程资源；
7. 平台优势说明；
8. 登录 / 注册入口。

首页核心文案示例：

```text
让学习资源不再千篇一律。
系统将根据你的专业基础、学习目标、能力短板和学习行为，动态生成学习画像，规划个性化学习路径，并为你推荐或生成专属学习资源。
```

### 7.2 工作台 Dashboard

登录后进入学生工作台。

工作台显示：

1. 今日学习任务；
2. 当前学习路径进度；
3. 最近薄弱知识点；
4. 推荐资源；
5. 最近生成资源；
6. 学习掌握度概览；
7. 画像完成度；
8. 快捷入口。

快捷入口包括：

1. 初始化 / 更新画像；
2. 生成学习路径；
3. 进入资源中心；
4. 生成个性化资源；
5. 查看学习记录。

### 7.3 初始化个人信息页

页面形式：类 ChatGPT 对话页。

功能：

1. 大模型逐步询问学生基础信息；
2. 用户以自然语言回答；
3. 系统自动总结关键信息；
4. 调用 Dify 画像生成工作流；
5. 生成六维学生画像；
6. 保存画像；
7. 引导生成学习路径。

### 7.4 学生画像页

显示六维画像：

1. 基础知识掌握度；
2. 工程实践能力；
3. AI 与数据能力；
4. 学习目标与发展方向；
5. 学习偏好与资源偏好；
6. 学习行为与掌握状态。

页面展示方式：

1. 雷达图；
2. 维度评分；
3. 优势能力；
4. 薄弱能力；
5. 系统依据；
6. 最近画像变化；
7. 推荐下一步行动。

### 7.5 个性化学习路径页

学习路径既要结构化，也要支持自然语言描述。

页面内容：

1. 路径标题；
2. 路径自然语言总述；
3. 阶段列表；
4. 每阶段目标；
5. 每阶段知识点；
6. 推荐平台资源；
7. 推荐生成资源；
8. 阶段检测任务；
9. 路径调整记录。

自然语言路径示例：

```text
根据你的画像，你目前具备一定的 Python 基础，但在机器学习数学基础、深度学习框架使用和项目实践方面仍有明显提升空间。因此，系统建议你先用 5 天补齐 Numpy、Pandas 和基础数据处理能力，再进入机器学习核心算法学习。完成基础算法后，再进入 PyTorch 实践阶段，最后通过一个图像分类或文本分类项目完成综合训练。
```

结构化阶段示例：

```text
阶段一：Python 数据处理基础
时间：第 1-5 天
目标：掌握 Numpy、Pandas 和基础数据清洗方法
平台资源：Python 数据分析入门课程、Pandas 文档资源
生成资源：Pandas 常用操作速查文档、数据清洗练习题
验收标准：能够独立完成一份 CSV 数据清洗任务
```

### 7.6 资源中心页

资源中心用于展示平台已有资源。

资源类型包括：

1. 课程；
2. 文档；
3. 视频；
4. 题库；
5. 项目案例；
6. PPT；
7. 思维导图；
8. 实验任务。

基础功能：

1. 资源列表；
2. 分类筛选；
3. 关键词搜索；
4. 按方向筛选；
5. 按难度筛选；
6. 按知识点筛选；
7. 点击进入详情；
8. 收藏资源；
9. 标记学习状态；
10. 记录阅读 / 观看行为。

### 7.7 资源详情页

展示资源基本信息：

1. 标题；
2. 简介；
3. 类型；
4. 所属方向；
5. 难度；
6. 关联知识点；
7. 推荐理由；
8. 开始学习按钮。

### 7.8 文档阅读页

基础功能：

1. 文档内容展示；
2. 目录导航；
3. 阅读进度记录；
4. 行号统计；
5. 滚动位置记录；
6. 选中文字；
7. 右键“添加到会话”；
8. 页内截图；
9. 智能助手联动；
10. 阅读行为事件上报。

### 7.9 视频学习页

基础功能：

1. 视频播放；
2. 播放进度记录；
3. 倍速播放；
4. 暂停 / 拖动记录；
5. 章节目录；
6. 当前知识点显示；
7. 反复观看检测；
8. 高倍速学习检测；
9. 智能助手联动；
10. 视频行为事件上报。

### 7.10 练习题页

功能：

1. 按知识点练习；
2. 按路径阶段练习；
3. 单选题；
4. 多选题；
5. 判断题；
6. 简答题；
7. 编程题；
8. 自动判题；
9. 答案解析；
10. 错题记录；
11. 掌握度更新。

### 7.11 个性化资源生成页

用户可以选择：

1. 资源类型；
2. 关联学习路径阶段；
3. 关联知识点；
4. 生成难度；
5. 输出风格；
6. 是否结合学生画像；
7. 是否结合平台资源。

可生成资源包括：

1. 个性化学习文档；
2. PPT 课件内容；
3. 思维导图；
4. 练习题 / 测验题；
5. 项目实战任务书；
6. 短视频讲解脚本。

### 7.12 右侧智能助手

所有主要学习页面右侧都有智能助手。

默认状态：

1. 页面右侧悬浮圆球；
2. 支持拖动；
3. 点击展开对话框；
4. 可最小化；
5. 可读取当前页面上下文。

核心能力：

1. 输入问题；
2. 添加选中文字到会话；
3. 添加页内截图到会话；
4. 上传图片；
5. 根据当前页面内容回答；
6. 根据学生画像调整解释难度；
7. 输出文字解释、图解、题目、学习建议或短视频讲解脚本。

右键菜单只保留一个选项：

```text
添加到会话
```

不再单独提供“解释这段内容”“根据这段内容出题”“生成思维导图”等重复入口。用户将内容添加到会话后，可以自然语言要求助手解释、出题、生成导图等。

---

## 8. 学生画像设计

### 8.1 六维学生画像

学生画像包括 6 个维度。

#### 维度一：基础知识掌握度

关注学生对计算机基础课程的掌握情况。

包括：

1. 程序设计基础；
2. 数据结构与算法；
3. 操作系统；
4. 计算机网络；
5. 数据库；
6. 软件工程；
7. 离散数学；
8. 概率统计；
9. 线性代数。

#### 维度二：工程实践能力

关注学生将知识转化为项目的能力。

包括：

1. 前端开发；
2. 后端开发；
3. 数据库设计；
4. 接口开发；
5. 项目部署；
6. Git 协作；
7. Linux 使用；
8. Docker 使用；
9. 调试与排错能力；
10. 文档编写能力。

#### 维度三：AI 与数据能力

关注学生在人工智能与数据方向的能力。

包括：

1. 机器学习基础；
2. 深度学习基础；
3. Python 数据处理；
4. 大模型使用；
5. Prompt 编写；
6. RAG；
7. Agent；
8. Workflow；
9. 向量数据库；
10. 多模态模型使用。

#### 维度四：学习目标与发展方向

关注学生为什么学习、希望达到什么目标。

包括：

1. 考研方向；
2. 就业方向；
3. 竞赛方向；
4. 科研方向；
5. 项目实践方向；
6. 后端方向；
7. 前端方向；
8. AI 应用开发方向；
9. 数据分析方向；
10. 网络安全方向。

#### 维度五：学习偏好与资源偏好

关注学生适合什么样的资源和讲解方式。

包括：

1. 文档偏好；
2. PPT 偏好；
3. 视频偏好；
4. 图解偏好；
5. 题目练习偏好；
6. 项目实践偏好；
7. 详细讲解偏好；
8. 简洁步骤偏好；
9. 案例驱动偏好；
10. 理论系统学习偏好。

#### 维度六：学习行为与掌握状态

关注学生真实学习过程中的表现。

包括：

1. 阅读速度；
2. 阅读停留时间；
3. 视频观看速度；
4. 视频反复观看片段；
5. 跳过内容情况；
6. 提问频率；
7. 答题正确率；
8. 错题知识点；
9. 卡顿知识点；
10. 掌握度变化。

### 8.2 画像生成方式

画像来源包括两类。

第一类：初始化对话生成。

学生通过自然语言回答系统问题，Dify 画像生成工作流根据对话内容生成初始画像。

第二类：学习行为动态更新。

系统根据阅读、视频、练习、提问等行为生成学习事件，再通过规则或 Dify 画像更新工作流持续更新画像。

### 8.3 画像数据格式

建议后端保存 JSON 格式画像。

示例：

```json
{
  "summary": "该学生具备一定 Java 和 Web 基础，但算法、计算机网络和 AI 应用开发能力仍需提升。学习目标偏向就业和项目实践，适合项目驱动式学习路径。",
  "dimensions": {
    "basic_knowledge": {
      "score": 62,
      "level": "中等",
      "strengths": ["Java 基础", "数据库基础"],
      "weaknesses": ["计算机网络", "算法训练"],
      "evidence": ["用户表示 TCP/IP 不熟悉", "缺少算法题训练经历"]
    },
    "engineering_ability": {
      "score": 70,
      "level": "较好",
      "strengths": ["Spring Boot", "接口开发"],
      "weaknesses": ["部署经验不足", "Docker 使用较少"],
      "evidence": ["用户有 Web 项目经验"]
    },
    "ai_data_ability": {
      "score": 45,
      "level": "较弱",
      "strengths": ["了解大模型调用"],
      "weaknesses": ["RAG", "向量数据库", "模型评估"],
      "evidence": ["用户希望学习 AI 项目开发"]
    },
    "learning_goal": {
      "score": 78,
      "level": "较清晰",
      "directions": ["AI 应用开发", "就业", "项目实践"]
    },
    "resource_preference": {
      "score": 80,
      "preferred_types": ["文档", "PPT", "思维导图", "项目任务书"],
      "style": "案例驱动，步骤清晰"
    },
    "learning_behavior": {
      "score": 50,
      "level": "待观察",
      "risk_flags": [],
      "mastery": {}
    }
  }
}
```

---

## 9. 初始化个人信息对话设计

### 9.1 对话目标

初始化对话不是普通闲聊，而是用于收集画像生成所需信息。

目标包括：

1. 确认学生基本背景；
2. 确认专业方向；
3. 确认当前能力；
4. 确认学习目标；
5. 确认学习困难；
6. 确认资源偏好；
7. 确认学习时间；
8. 确认期望产出。

### 9.2 问题设计

大模型可以逐步询问：

1. 你目前是大几，专业方向是什么？
2. 你现在主要想提升哪方面能力？
3. 你目前掌握哪些编程语言或技术栈？
4. 你觉得自己在哪些课程或知识点上比较薄弱？
5. 你最近的学习目标是什么？例如考研、就业、竞赛、项目开发或课程补弱。
6. 你更喜欢哪类学习资源？例如文档、PPT、视频、思维导图、题目或项目任务。
7. 你每天大概能投入多少学习时间？
8. 你希望最后获得什么成果？例如完成一个项目、通过一门课程、准备一次面试或参加竞赛。

### 9.3 初始化完成后的引导

画像生成完成后，系统自动提示：

```text
你的初始学生画像已经生成。根据当前画像，系统建议你继续生成一条个性化学习路径，这样后续可以为你推荐更合适的平台资源，并生成专属学习材料。
```

提供按钮：

1. 生成学习路径；
2. 查看我的画像；
3. 稍后再说。

---

## 10. 个性化学习路径设计

### 10.1 路径生成方式

个性化学习路径由 Dify 工作流生成。

输入包括：

1. 学生画像；
2. 学习目标；
3. 学习方向；
4. 每日学习时间；
5. 学习周期；
6. 平台已有资源；
7. 最近学习行为；
8. 最近薄弱知识点。

输出包括两种形式：

1. 自然语言描述；
2. 结构化阶段数据。

### 10.2 自然语言路径描述

自然语言描述用于让学生看懂为什么这样规划。

示例：

```text
根据你的学习画像，你目前具备一定的 Java 基础和 Web 开发经验，但在 AI 应用开发、向量数据库和 RAG 系统设计方面仍然比较薄弱。由于你的目标是完成一个可以展示在简历中的 AI 应用项目，系统建议你先补齐大模型 API 调用和 Prompt 编写能力，再学习 RAG 的基本流程，随后进入向量数据库和文档检索模块，最后完成一个基于课程资料的智能问答系统项目。

这条路径会优先使用平台中已有的 Java 后端、Vue 前端、RAG 入门和向量数据库课程资源。对于你薄弱的部分，系统会额外生成个性化文档、思维导图和练习题，帮助你降低学习难度。
```

### 10.3 结构化路径数据

结构化路径用于前端展示和后续任务推荐。

示例：

```json
{
  "path_title": "30 天 AI 应用开发学习路径",
  "natural_language_summary": "根据你的画像，系统建议你先补齐大模型 API 调用和 Prompt 编写能力，再学习 RAG 与向量数据库，最后完成一个课程资料智能问答项目。",
  "stages": [
    {
      "stage_index": 1,
      "title": "大模型 API 与 Prompt 基础",
      "duration": "第 1-5 天",
      "goal": "掌握大模型 API 调用、Prompt 编写和基础对话功能开发。",
      "knowledge_points": ["LLM API", "Prompt", "JSON 输出", "前后端接口调用"],
      "platform_resources": ["大模型 API 入门课程", "Prompt 编写基础文档"],
      "generated_resources": ["API 调用速查文档", "Prompt 案例练习题"],
      "assessment": "完成一个网页聊天助手 Demo"
    }
  ]
}
```

### 10.4 路径动态调整

当系统发现学生在某知识点上掌握不足时，可以调整路径。

触发条件：

1. 某知识点连续答错；
2. 某视频片段反复观看；
3. 某文档段落停留过久；
4. 对同一知识点多次向助手提问；
5. 阶段测验低于设定分数。

调整方式：

1. 插入补弱任务；
2. 延长当前阶段；
3. 降低资源难度；
4. 推荐更多图解资源；
5. 生成专项练习题；
6. 重新排序后续阶段。

---

## 11. 个性化资源生成设计

### 11.1 资源类型

系统至少支持 5 种个性化资源生成，建议设计 6 种：

1. 个性化学习文档；
2. PPT 课件内容；
3. 思维导图；
4. 练习题 / 测验题；
5. 项目实战任务书；
6. 短视频讲解脚本。

### 11.2 资源生成逻辑

资源生成不是只输入一个主题，而是综合以下信息：

1. 用户画像；
2. 当前学习路径；
3. 当前阶段；
4. 关联知识点；
5. 平台已有资源；
6. 用户资源偏好；
7. 最近薄弱知识点；
8. 期望输出类型。

### 11.3 资源类型说明

#### 11.3.1 个性化学习文档

用于知识点讲解和复习。

内容包括：

1. 学习目标；
2. 前置知识；
3. 核心概念；
4. 示例代码；
5. 常见误区；
6. 练习任务；
7. 总结。

#### 11.3.2 PPT 课件内容

用于课堂展示、复习汇报或自学梳理。

内容包括：

1. PPT 标题；
2. 页面大纲；
3. 每页标题；
4. 每页要点；
5. 讲解备注；
6. 图示建议；
7. 课堂提问。

MVP 阶段可以先生成 PPT 内容结构，不一定直接生成 `.pptx` 文件。

#### 11.3.3 思维导图

用于知识结构化整理。

建议输出 Mermaid mindmap 或 Markmap Markdown。

#### 11.3.4 练习题 / 测验题

用于掌握度检测。

题型包括：

1. 单选题；
2. 多选题；
3. 判断题；
4. 简答题；
5. 编程题；
6. 场景分析题。

每道题包含：

1. 题目；
2. 选项；
3. 答案；
4. 解析；
5. 难度；
6. 关联知识点；
7. 对画像的影响规则。

#### 11.3.5 项目实战任务书

用于工科学生项目实践。

内容包括：

1. 项目背景；
2. 功能需求；
3. 技术栈；
4. 数据库设计；
5. 接口设计；
6. 开发步骤；
7. 验收标准；
8. 扩展方向。

#### 11.3.6 短视频讲解脚本

MVP 阶段生成短视频讲解脚本，不直接生成视频。

内容包括：

1. 视频标题；
2. 目标受众；
3. 讲解时长；
4. 分镜设计；
5. 画面说明；
6. 配音文案；
7. 屏幕演示建议；
8. 结尾检测题。

后续可扩展为 TTS + 图片生成 + FFmpeg 自动合成视频。

---

## 12. 多智能体与 Dify 工作流设计

### 12.1 Dify 工作流总览

建议至少配置 5 个 Dify 工作流：

1. 画像生成工作流；
2. 路径规划工作流；
3. 资源生成工作流；
4. 智能答疑工作流；
5. 画像更新工作流。

### 12.2 并发 LLM 设计原则

Dify 工作流中可以使用并发 LLM 提升效率和体现多智能体协作。

适合并发的场景：

1. 学生画像六维度可以并发分析；
2. 路径规划中可以并发生成“知识点路径”“资源推荐”“阶段测评”；
3. 资源生成中可以并发生成“正文内容”“练习题”“图解结构”“质量检查”；
4. 智能答疑中可以并发生成“直接答案”“图解方案”“延伸练习”；
5. 画像更新中可以并发分析“阅读行为”“视频行为”“答题行为”“提问行为”。

不适合并发的场景：

1. 需要依赖前一步结论的最终汇总；
2. 需要统一格式输出的最终 JSON；
3. 需要严格按阶段排序的路径最终生成。

因此建议采用：

```text
并发分析 → 汇总整理 → 质量检查 → 最终输出
```

### 12.3 画像生成工作流

建议结构：

```text
开始节点
  ↓
输入用户初始化对话
  ↓
并发 LLM 1：分析基础知识掌握度
并发 LLM 2：分析工程实践能力
并发 LLM 3：分析 AI 与数据能力
并发 LLM 4：分析学习目标与发展方向
并发 LLM 5：分析学习偏好与资源偏好
并发 LLM 6：分析学习行为与掌握状态
  ↓
汇总 LLM：整合六维画像
  ↓
质量检查 LLM：检查是否过度推断、是否缺少依据
  ↓
输出结构化画像 JSON + 自然语言总结
```

### 12.4 路径规划工作流

建议结构：

```text
开始节点
  ↓
输入学生画像、学习目标、学习周期、平台资源列表
  ↓
并发 LLM 1：生成知识点学习顺序
并发 LLM 2：匹配平台已有资源
并发 LLM 3：设计阶段测评任务
并发 LLM 4：生成自然语言路径说明
  ↓
汇总 LLM：整合为完整路径
  ↓
质量检查 LLM：检查路径是否可执行、是否符合画像
  ↓
输出自然语言说明 + 结构化路径 JSON
```

### 12.5 资源生成工作流

建议结构：

```text
开始节点
  ↓
输入画像、路径阶段、知识点、资源类型、平台资源摘要
  ↓
学情分析 LLM：判断资源难度和讲解风格
  ↓
根据资源类型分支
  ├─ 文档生成分支
  ├─ PPT 内容生成分支
  ├─ 思维导图生成分支
  ├─ 题目生成分支
  ├─ 项目任务书生成分支
  └─ 短视频脚本生成分支
  ↓
质量检查 LLM：检查内容准确性、难度适配性、格式完整性
  ↓
输出资源内容
```

对于一次性生成多个资源的情况，可以并发：

```text
文档 LLM、题目 LLM、思维导图 LLM、PPT LLM 并发执行
  ↓
统一汇总
```

### 12.6 智能答疑工作流

建议结构：

```text
开始节点
  ↓
输入用户问题、选中文字、截图、图片、当前页面上下文、学生画像
  ↓
上下文整理 LLM：判断用户真实问题和当前知识点
  ↓
并发 LLM 1：生成文字解释
并发 LLM 2：生成图解结构
并发 LLM 3：生成检测题或追问
  ↓
回答选择 LLM：根据用户请求选择最合适的输出形式
  ↓
输出回答、图解、题目或短视频脚本
```

### 12.7 画像更新工作流

建议结构：

```text
开始节点
  ↓
输入旧画像、学习行为事件、答题结果、提问记录
  ↓
并发 LLM 1：分析阅读行为
并发 LLM 2：分析视频行为
并发 LLM 3：分析答题行为
并发 LLM 4：分析提问行为
  ↓
汇总 LLM：生成画像更新建议
  ↓
规则校验节点：限制每次分数变化幅度
  ↓
输出更新后的画像和调整说明
```

### 12.8 后端与 Dify 的调用关系

后端不把所有逻辑都交给 Dify。

建议分工：

后端负责：

1. 用户管理；
2. 数据库读写；
3. 行为事件记录；
4. 平台资源检索；
5. 文件上传；
6. Dify API 调用；
7. 权限校验；
8. 前端接口封装。

Dify 负责：

1. 学生画像生成；
2. 学习路径规划；
3. 个性化资源生成；
4. 智能助手回答；
5. 学习行为分析与画像更新建议。

---

## 13. 智能助手设计

### 13.1 悬浮球设计

在学习相关页面右侧放置悬浮球。

要求：

1. 默认显示为圆形按钮；
2. 支持拖动；
3. 点击后展开为对话窗口；
4. 支持最小化；
5. 支持读取当前页面上下文；
6. 支持与当前资源、当前知识点关联。

### 13.2 添加选中文字到会话

用户选中页面文字后，右键菜单显示：

```text
添加到会话
```

点击后，将选中文字添加到智能助手输入区或会话上下文中。

数据格式：

```json
{
  "type": "selected_text",
  "content": "用户选中的文字",
  "page_id": "doc_001",
  "resource_id": "res_001",
  "knowledge_point": "数据库索引"
}
```

不需要单独提供“解释这段内容”“根据这段内容出题”“生成思维导图”等菜单项。因为添加到会话后，用户可以直接输入：

```text
解释一下这段内容
```

或：

```text
根据这段内容出 3 道题
```

或：

```text
把这段内容整理成思维导图
```

### 13.3 页内截图添加到会话

功能流程：

```text
用户点击截图按钮
  ↓
页面进入截图选择模式
  ↓
用户拖拽选择区域
  ↓
前端生成截图图片
  ↓
上传后端
  ↓
后端保存图片并传给多模态模型或 Dify 工作流
  ↓
智能助手基于截图内容回答
```

前端可选技术：

1. html2canvas；
2. cropperjs；
3. 原生 canvas；
4. 浏览器 Selection API。

### 13.4 图片上传

支持上传：

1. 题目截图；
2. 代码报错截图；
3. 课程 PPT 截图；
4. 思维导图截图；
5. 流程图；
6. 表格；
7. 公式图片。

### 13.5 输出形式

智能助手支持：

1. 文字解释；
2. 分步骤说明；
3. Mermaid 图解；
4. 练习题；
5. 学习建议；
6. 短视频讲解脚本。

---

## 14. 学习行为感知设计

### 14.1 行为采集边界

系统只采集平台内学习行为，不进行无边界屏幕监听。

可采集行为包括：

1. 文档阅读行为；
2. 视频观看行为；
3. 题目练习行为；
4. 智能助手提问行为；
5. 资源生成行为；
6. 收藏、点击、打开、完成等基础行为。

### 14.2 文档阅读行为

采集指标：

1. 打开文档时间；
2. 关闭文档时间；
3. 阅读总时长；
4. 当前阅读行号；
5. 滚动速度；
6. 单次滚动跨越行数；
7. 是否快速跳过多个知识块；
8. 是否在某个段落停留过久；
9. 是否选中文字；
10. 是否截图提问。

### 14.3 阅读过快规则

不使用“30 秒阅读 80% 文档”的规则，因为长文档或上百页文档不适合按百分比判断。

改为按阅读行数和知识块判断。

建议规则：

```text
如果用户在 30 秒内连续滚动超过 120 行，且中间没有明显停留、选中、提问或截图行为，则判断为疑似快速浏览。
```

也可以按知识块判断：

```text
如果用户在 60 秒内跳过 5 个以上知识块，且没有任何交互行为，则判断为疑似快速浏览。
```

触发弹窗示例：

```text
留意到你刚刚快速浏览了“B+ 树索引结构”和“索引失效场景”相关内容。这个部分在数据库优化中比较重要，要不要我出一道题帮你确认是否掌握？
```

### 14.4 阅读过慢或停留过久规则

建议规则：

```text
如果用户在同一知识块停留时间超过该知识块建议阅读时间的 2.5 倍，且没有继续滚动，则判断为疑似理解困难。
```

弹窗示例：

```text
我注意到你在“反向传播算法”这一部分停留较久。这个知识点确实比较抽象，需要我用图解方式重新讲一遍吗？
```

### 14.5 视频学习行为

采集指标：

1. 播放时间；
2. 暂停时间；
3. 倍速设置；
4. 拖动进度条次数；
5. 跳过片段；
6. 反复观看片段；
7. 当前视频知识点；
8. 视频完成率；
9. 高倍速持续时长。

### 14.6 视频高倍速规则

建议规则：

```text
如果用户连续 5 分钟使用 2 倍速或更高倍速，并且跳过至少 2 个关键知识点片段，则触发掌握检测。
```

弹窗示例：

```text
你刚刚高倍速看完了“HTTP 请求流程”和“状态码分类”两个知识点。我可以用 2 道题帮你快速检测一下是否掌握。
```

### 14.7 视频反复观看规则

建议规则：

```text
如果用户在同一视频时间段内反复拖动或回看 3 次以上，则判断该片段对应知识点可能存在理解困难。
```

弹窗示例：

```text
你似乎反复查看了“三次握手”这一段。需要我用图解方式重新解释一下吗？
```

### 14.8 答题行为

采集指标：

1. 题目知识点；
2. 答题结果；
3. 答题耗时；
4. 查看解析情况；
5. 重做情况；
6. 连续答错情况；
7. 知识点掌握度变化。

### 14.9 行为对画像的影响

行为事件影响画像。

示例：

| 行为 | 画像影响 |
|---|---|
| 阅读速度过快且测验答错 | 对应知识点掌握度下降 |
| 阅读速度过快但测验答对 | 学习效率评价提高 |
| 某知识块停留过久 | 标记为疑似薄弱知识点 |
| 视频片段反复观看 | 对应知识点加入重点复习 |
| 同一知识点多次提问 | 标记为高关注或疑似困难知识点 |
| 上传代码报错截图 | 工程实践问题记录增加 |
| 测验连续答对 | 对应知识点掌握度提高 |
| 阶段任务完成 | 路径阶段进度提高 |

---

## 15. 数据库设计

### 15.1 user 用户表

```sql
CREATE TABLE user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(100) NOT NULL,
  email VARCHAR(255),
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) DEFAULT 'student',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 15.2 student_profile 学生画像表

```sql
CREATE TABLE student_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  profile_json JSON NOT NULL,
  summary TEXT,
  version INT DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 15.3 learning_path 学习路径表

```sql
CREATE TABLE learning_path (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  profile_id BIGINT,
  title VARCHAR(255) NOT NULL,
  natural_language_summary TEXT,
  path_json JSON NOT NULL,
  status VARCHAR(50) DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 15.4 platform_resource 平台资源表

```sql
CREATE TABLE platform_resource (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL,
  resource_type VARCHAR(50) NOT NULL,
  direction VARCHAR(100),
  difficulty VARCHAR(50),
  knowledge_points JSON,
  description TEXT,
  content_url VARCHAR(500),
  content_text LONGTEXT,
  duration_seconds INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 15.5 generated_resource 生成资源表

```sql
CREATE TABLE generated_resource (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  path_id BIGINT,
  resource_type VARCHAR(50) NOT NULL,
  title VARCHAR(255) NOT NULL,
  content LONGTEXT NOT NULL,
  content_json JSON,
  related_knowledge_points JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 15.6 learning_event 学习行为事件表

```sql
CREATE TABLE learning_event (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  resource_id BIGINT,
  page_id VARCHAR(100),
  knowledge_point VARCHAR(255),
  event_data JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 15.7 knowledge_mastery 知识点掌握度表

```sql
CREATE TABLE knowledge_mastery (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  knowledge_point VARCHAR(255) NOT NULL,
  mastery_score DECIMAL(5,2) DEFAULT 0,
  confidence DECIMAL(5,2) DEFAULT 0,
  evidence JSON,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 15.8 assistant_conversation 智能助手会话表

```sql
CREATE TABLE assistant_conversation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  title VARCHAR(255),
  context_type VARCHAR(50),
  context_id VARCHAR(100),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 15.9 assistant_message 智能助手消息表

```sql
CREATE TABLE assistant_message (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  conversation_id BIGINT NOT NULL,
  role VARCHAR(50) NOT NULL,
  content LONGTEXT,
  attachment_url VARCHAR(500),
  message_type VARCHAR(50) DEFAULT 'text',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 15.10 quiz_record 答题记录表

```sql
CREATE TABLE quiz_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  question_id BIGINT,
  knowledge_point VARCHAR(255),
  user_answer TEXT,
  correct_answer TEXT,
  is_correct BOOLEAN,
  time_spent_seconds INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 16. 后端接口规划

### 16.1 用户接口

```text
POST /api/auth/register          用户注册
POST /api/auth/login             用户登录
GET  /api/user/me                获取当前用户信息
PUT  /api/user/me                更新用户信息
```

### 16.2 学生画像接口

```text
GET  /api/profile/me             获取当前学生画像
POST /api/profile/init-chat      初始化画像对话
POST /api/profile/generate       调用 Dify 生成画像
POST /api/profile/update         根据学习行为更新画像
GET  /api/profile/history        获取画像历史版本
```

### 16.3 学习路径接口

```text
GET  /api/paths                  获取学习路径列表
POST /api/paths/generate         生成学习路径
GET  /api/paths/{id}             获取路径详情
POST /api/paths/{id}/adjust      调整学习路径
PUT  /api/paths/{id}/status      更新路径状态
```

### 16.4 平台资源接口

```text
GET  /api/resources              获取资源列表
GET  /api/resources/{id}         获取资源详情
POST /api/resources              新增资源
PUT  /api/resources/{id}         更新资源
DELETE /api/resources/{id}       删除资源
POST /api/resources/{id}/view    记录资源点击 / 阅读
```

### 16.5 资源生成接口

```text
POST /api/generated-resources/generate     生成个性化资源
GET  /api/generated-resources              获取生成资源列表
GET  /api/generated-resources/{id}         获取生成资源详情
DELETE /api/generated-resources/{id}       删除生成资源
```

### 16.6 智能助手接口

```text
POST /api/assistant/conversations          创建会话
GET  /api/assistant/conversations          获取会话列表
GET  /api/assistant/conversations/{id}     获取会话详情
POST /api/assistant/chat                   发送消息
POST /api/assistant/upload-image           上传图片
POST /api/assistant/upload-screenshot      上传截图
POST /api/assistant/add-context            添加选中文字或页面上下文
```

### 16.7 学习行为接口

```text
POST /api/events                           上报学习行为事件
POST /api/events/batch                     批量上报行为事件
GET  /api/events/me                        获取个人学习行为记录
GET  /api/mastery/me                       获取知识点掌握度
```

### 16.8 练习题接口

```text
POST /api/quiz/generate                    生成练习题
POST /api/quiz/submit                      提交答案
GET  /api/quiz/records                     获取答题记录
GET  /api/quiz/wrong                       获取错题列表
```

---

## 17. 前端组件规划

### 17.1 页面级组件

```text
HomePage.vue                 首页
DashboardPage.vue            学生工作台
LoginPage.vue                登录页
RegisterPage.vue             注册页
ProfileInitPage.vue          画像初始化页
ProfilePage.vue              学生画像页
LearningPathPage.vue         学习路径页
ResourceCenterPage.vue       资源中心页
ResourceDetailPage.vue       资源详情页
DocumentReaderPage.vue       文档阅读页
VideoStudyPage.vue           视频学习页
QuizPage.vue                 练习题页
GeneratedResourcePage.vue    生成资源页
AdminResourcePage.vue        管理后台资源页
```

### 17.2 通用组件

```text
AppHeader.vue                顶部导航
AppSidebar.vue               侧边栏
ResourceCard.vue             资源卡片
PathTimeline.vue             学习路径时间轴
ProfileRadar.vue             画像雷达图
KnowledgeHeatmap.vue         知识点热力图
AssistantFloatingButton.vue  智能助手悬浮球
AssistantPanel.vue           智能助手面板
SelectionContextMenu.vue     选中文字右键菜单
ScreenshotSelector.vue       截图选择组件
MarkdownRenderer.vue         Markdown 渲染组件
MermaidRenderer.vue          Mermaid 渲染组件
VideoPlayer.vue              视频播放器
DocumentReader.vue           文档阅读器
```

### 17.3 状态管理

建议使用 Pinia。

Store 设计：

```text
userStore             用户状态
profileStore          学生画像状态
pathStore             学习路径状态
resourceStore         资源状态
assistantStore        智能助手状态
eventStore            学习行为状态
```

---

## 18. 技术栈说明

### 18.1 前端技术栈

建议：

1. Vue 3；
2. Vite；
3. TypeScript；
4. Pinia；
5. Vue Router；
6. Element Plus 或 Ant Design Vue；
7. Axios；
8. Markdown-it；
9. Mermaid；
10. ECharts；
11. html2canvas；
12. cropperjs；
13. Plyr 或 video.js。

用途说明：

| 技术 | 用途 |
|---|---|
| Vue 3 | 前端页面开发 |
| Vite | 前端构建 |
| TypeScript | 类型约束 |
| Pinia | 全局状态管理 |
| Vue Router | 页面路由 |
| Element Plus | UI 组件 |
| Axios | HTTP 请求 |
| Markdown-it | 文档渲染 |
| Mermaid | 思维导图、流程图渲染 |
| ECharts | 雷达图、热力图、统计图 |
| html2canvas | 页内截图 |
| cropperjs | 图片裁剪 |
| video.js | 视频播放与事件监听 |

### 18.2 后端技术栈

建议：

1. Python 3.11 或 3.12；
2. FastAPI；
3. Uvicorn；
4. SQLAlchemy；
5. Pydantic；
6. MySQL；
7. Redis；
8. httpx；
9. python-jose；
10. passlib；
11. python-multipart；
12. Loguru。

用途说明：

| 技术 | 用途 |
|---|---|
| FastAPI | 后端 API 服务 |
| Uvicorn | ASGI 服务启动 |
| SQLAlchemy | ORM 数据库操作 |
| Pydantic | 请求响应数据校验 |
| MySQL | 业务数据存储 |
| Redis | 缓存、会话、限流、任务状态 |
| httpx | 调用 Dify API 和外部模型接口 |
| python-jose | JWT 认证 |
| passlib | 密码哈希 |
| python-multipart | 文件上传 |
| Loguru | 日志记录 |

### 18.3 AI 与工作流技术

1. Dify Workflow；
2. Dify Chatflow；
3. LLM 节点；
4. 知识检索节点；
5. HTTP 请求节点；
6. 并发 LLM 分支；
7. 多模态模型接口；
8. 可选向量数据库。

### 18.4 可选技术

如果后续需要增强：

1. Celery：异步任务；
2. MinIO：文件对象存储；
3. Elasticsearch：资源全文搜索；
4. Milvus / Qdrant：向量检索；
5. FFmpeg：视频合成；
6. TTS 服务：语音讲解生成；
7. Docker Compose：统一部署。

---

## 19. 环境与配置说明

### 19.1 本地开发环境

建议环境：

```text
操作系统：Windows 10 / Windows 11 / Linux
Node.js：20.x 或 22.x
Python：3.11 或 3.12
MySQL：8.0+
Redis：7.x+
Git：最新版
包管理：npm / pnpm，pip / uv
```

### 19.2 后端环境变量

建议 `.env`：

```env
APP_NAME=AI_STUDY_PLATFORM
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8001

DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/ai_study_platform
REDIS_URL=redis://127.0.0.1:6379/0

JWT_SECRET_KEY=change-this-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

DIFY_PROFILE_WORKFLOW_URL=https://api.dify.ai/v1/workflows/run
DIFY_PROFILE_API_KEY=your-profile-workflow-key

DIFY_PATH_WORKFLOW_URL=https://api.dify.ai/v1/workflows/run
DIFY_PATH_API_KEY=your-path-workflow-key

DIFY_RESOURCE_WORKFLOW_URL=https://api.dify.ai/v1/workflows/run
DIFY_RESOURCE_API_KEY=your-resource-workflow-key

DIFY_ASSISTANT_WORKFLOW_URL=https://api.dify.ai/v1/chat-messages
DIFY_ASSISTANT_API_KEY=your-assistant-key

UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=20
```

### 19.3 前端环境变量

建议 `.env.development`：

```env
VITE_APP_TITLE=智学工坊
VITE_API_BASE_URL=http://127.0.0.1:8001/api
VITE_ENABLE_ASSISTANT=true
VITE_ENABLE_SCREENSHOT=true
```

### 19.4 启动方式

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 127.0.0.1 --port 8001 --reload
```

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --host 127.0.0.1 --port 8001 --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
前端：http://127.0.0.1:3000
后端：http://127.0.0.1:8001
API 文档：http://127.0.0.1:8001/docs
```

---

## 20. 项目目录结构建议

```text
ai-study-platform/
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── profile.py
│   │   │   ├── path.py
│   │   │   ├── resource.py
│   │   │   ├── generated_resource.py
│   │   │   ├── assistant.py
│   │   │   ├── event.py
│   │   │   └── quiz.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── profile.py
│   │   │   ├── learning_path.py
│   │   │   ├── resource.py
│   │   │   ├── event.py
│   │   │   └── assistant.py
│   │   ├── schemas/
│   │   │   ├── user_schema.py
│   │   │   ├── profile_schema.py
│   │   │   ├── path_schema.py
│   │   │   ├── resource_schema.py
│   │   │   ├── assistant_schema.py
│   │   │   └── event_schema.py
│   │   ├── services/
│   │   │   ├── dify_service.py
│   │   │   ├── profile_service.py
│   │   │   ├── path_service.py
│   │   │   ├── resource_service.py
│   │   │   ├── assistant_service.py
│   │   │   └── event_service.py
│   │   └── utils/
│   │       ├── file_utils.py
│   │       └── response.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/
│   │   ├── api/
│   │   ├── views/
│   │   ├── components/
│   │   ├── components/assistant/
│   │   ├── components/resource/
│   │   ├── components/profile/
│   │   ├── components/path/
│   │   └── utils/
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.development
│
├── docs/
│   ├── API.md
│   ├── DATABASE.md
│   ├── DIFY_WORKFLOWS.md
│   ├── DEPLOYMENT.md
│   └── PLAN.md
│
├── scripts/
│   ├── init_db.sql
│   └── seed_resources.py
│
├── uploads/
├── tests/
├── start.bat
├── stop.bat
└── README.md
```

---

## 21. 开发阶段规划

### 21.1 阶段一：基础系统与核心闭环 MVP

目标：完成系统基本页面和“画像—路径—资源”的主流程。

任务：

1. 搭建前后端项目；
2. 完成用户注册登录；
3. 完成首页和学生工作台；
4. 完成资源中心基础功能；
5. 完成文档阅读页；
6. 完成学生画像初始化页面；
7. 接入 Dify 画像生成工作流；
8. 保存学生画像；
9. 完成学习路径生成页面；
10. 接入 Dify 路径规划工作流；
11. 展示自然语言路径和结构化路径；
12. 完成资源生成入口；
13. 支持生成文档、PPT 内容、思维导图、题目、项目任务书。

验收标准：

1. 新用户可以完成画像初始化；
2. 系统可以生成六维学生画像；
3. 系统可以生成自然语言化学习路径；
4. 系统可以推荐平台已有资源；
5. 系统可以生成至少 5 种个性化资源。

### 21.2 阶段二：智能助手与上下文交互

目标：完成页面级智能助手。

任务：

1. 实现右侧悬浮球；
2. 实现助手对话窗口；
3. 支持当前页面上下文传入；
4. 支持选中文字“添加到会话”；
5. 支持页内截图；
6. 支持图片上传；
7. 接入 Dify 智能答疑工作流；
8. 支持文字、图解、题目、短视频脚本等回答形式。

验收标准：

1. 用户可以在文档页选中文字并添加到助手会话；
2. 用户可以截图提问；
3. 用户可以上传图片提问；
4. 助手回答能够结合当前资源和用户画像。

### 21.3 阶段三：学习行为感知与主动干预

目标：让系统具备动态学习反馈能力。

任务：

1. 实现文档阅读行数统计；
2. 实现滚动速度检测；
3. 实现阅读过快规则；
4. 实现阅读停留过久规则；
5. 实现视频倍速检测；
6. 实现视频反复观看检测；
7. 实现主动弹窗提醒；
8. 实现弹窗出题；
9. 实现答题结果记录；
10. 实现行为事件写入数据库；
11. 实现画像更新规则或 Dify 画像更新工作流。

验收标准：

1. 阅读超过指定行数且速度过快时可以触发提醒；
2. 视频高倍速或反复观看时可以触发提醒；
3. 答题结果可以影响知识点掌握度；
4. 学生画像可以随着学习行为更新。

### 21.4 阶段四：可视化与高级展示

目标：增强答辩展示效果。

任务：

1. 画像雷达图；
2. 知识点掌握热力图；
3. 学习路径时间轴；
4. 学习行为统计图；
5. 画像变化记录；
6. 路径动态调整记录；
7. 资源生成历史；
8. 管理后台优化。

验收标准：

1. 可以清晰展示学生六维画像；
2. 可以展示知识点掌握度；
3. 可以展示学习路径进度；
4. 可以展示画像如何因学习行为变化。

---

## 22. MVP 优先级

必须做：

1. 首页；
2. 登录注册；
3. 学生工作台；
4. 初始化画像；
5. 六维画像生成；
6. 学习路径生成；
7. 自然语言路径描述；
8. 平台资源中心；
9. 文档阅读；
10. 资源生成；
11. 智能助手基础对话；
12. 选中文字添加到会话；
13. 学习行为事件记录。

强烈建议做：

1. 页内截图提问；
2. 图片上传提问；
3. 视频学习页；
4. 阅读过快提醒；
5. 视频高倍速提醒；
6. 画像雷达图；
7. 知识点掌握度表。

可以后做：

1. 真正的视频自动生成；
2. TTS 语音讲解；
3. 教师端；
4. 班级分析；
5. 向量数据库深度检索；
6. 自动生成 `.pptx` 文件；
7. 复杂权限管理。

---

## 23. 关键实现细节

### 23.1 平台已有资源优先原则

学习路径规划时，系统应优先推荐平台已有资源，而不是全部由大模型生成。

原因：

1. 已有资源更稳定；
2. 便于系统管理；
3. 可以记录真实学习行为；
4. 避免大模型生成内容不可控；
5. 更像完整学习平台。

生成式资源用于补充个性化需求。

### 23.2 路径规划输出原则

路径规划必须同时有：

1. 给学生看的自然语言说明；
2. 给系统用的结构化 JSON。

自然语言说明解决“为什么这么学”。

结构化 JSON 解决“系统怎么展示和调度”。

### 23.3 右键菜单简化原则

右键菜单只保留：

```text
添加到会话
```

避免重复功能入口。

用户添加内容后，可以在助手里自然语言表达后续需求。

### 23.4 阅读速度判断原则

不按文档百分比判断，而按行数、知识块和时间判断。

推荐规则：

```text
30 秒内连续滚动超过 120 行，并且没有停留、选中、提问或截图行为，判断为疑似快速浏览。
```

对于短文档可以降低阈值，对于长文档可以提高阈值。

### 23.5 隐私边界原则

系统只采集平台内学习行为，不做无感全屏监听。

文档中统一表述为：

```text
平台内学习行为感知
```

不要表述为：

```text
监听用户屏幕
```

---

## 24. 风险与解决方案

### 24.1 Dify 工作流输出不稳定

风险：LLM 输出格式不稳定，前端难以解析。

解决方案：

1. 要求 Dify 最终节点输出严格 JSON；
2. 后端增加 JSON 校验；
3. 解析失败时回退为 Markdown 展示；
4. 增加质量检查 LLM 节点。

### 24.2 功能范围过大

风险：功能太多，开发周期不够。

解决方案：

1. 先完成画像、路径、资源三个核心闭环；
2. 智能助手先做文字和选中文字；
3. 行为感知先做阅读过快和视频倍速；
4. 视频生成先做脚本，不做真实视频。

### 24.3 学习行为判断不准确

风险：阅读快不一定代表没掌握。

解决方案：

1. 行为只作为疑似信号；
2. 通过弹窗测验确认掌握度；
3. 不直接大幅降低画像分数；
4. 每次画像变化保存证据。

### 24.4 大模型生成资源准确性问题

风险：生成内容可能出错。

解决方案：

1. 优先结合平台已有资源；
2. 增加质量检查 LLM；
3. 输出关联知识点和依据；
4. 对关键知识点增加管理员审核机制。

### 24.5 多模态能力接入复杂

风险：截图和图片理解依赖多模态模型。

解决方案：

1. MVP 阶段先上传图片并保存；
2. 可先用支持图片的大模型接口；
3. 如果暂时没有多模态模型，则让用户补充文字说明；
4. 后续再接更完整的多模态分析。

---

## 25. 答辩展示建议

答辩时不要只展示单个功能，而要展示闭环。

推荐演示流程：

1. 新用户登录系统；
2. 首页介绍平台能力；
3. 进入初始化画像对话；
4. 生成六维学生画像；
5. 展示画像雷达图；
6. 点击生成学习路径；
7. 展示自然语言路径说明；
8. 展示阶段化路径；
9. 点击某阶段推荐资源；
10. 进入文档阅读页；
11. 选中文字添加到智能助手会话；
12. 智能助手解释内容；
13. 快速滚动文档触发提醒；
14. 系统生成一道检测题；
15. 用户答错；
16. 画像中对应知识点掌握度下降；
17. 系统推荐补弱资源或调整路径。

最终强调：

```text
本系统不是简单调用大模型生成资料，而是以动态学生画像为核心，通过学习路径、平台资源、生成资源、智能助手和行为感知形成个性化学习闭环。
```

---

## 26. 最终结论

本项目应按照“完整学习平台 + AI 个性化能力”的思路开发。

基础平台功能保证系统完整性，包括首页、登录注册、资源中心、文档阅读、视频学习、练习题、个人中心等。

AI 核心功能体现竞赛主题，包括动态学生画像、个性化学习路径、多智能体资源生成、智能助手、学习行为感知和画像更新。

Dify 工作流中应合理使用并发 LLM，将多个维度的分析、多个资源分支的生成、多个行为来源的判断并行处理，再通过汇总节点形成统一结果。

学习路径既要有自然语言描述，方便学生理解，也要有结构化数据，方便系统展示、推荐、调度和动态调整。

右侧智能助手应减少重复入口，保留“添加到会话”作为统一上下文入口，再由用户通过自然语言指定解释、出题、生成导图等操作。

学习行为感知应基于平台内行为，不做无边界屏幕监听。阅读速度判断应从“百分比”改为“行数、知识块、停留时间”等更合理的规则。

最终系统应形成一个可演示、可落地、可扩展的个性化学习闭环。
