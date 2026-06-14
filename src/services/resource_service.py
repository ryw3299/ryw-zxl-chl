"""资源服务（含种子数据）。"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.resource import GeneratedResource, PlatformResource
from src.services.dify_service import generate_resource as ai_generate_resource


class ResourceNotFound(Exception):
    pass


SEED_RESOURCES = [

    # =============================================================================
    #  课程
    # =============================================================================

    {"title": "Python 零基础入门", "resource_type": "course", "direction": "后端开发", "difficulty": "beginner", "knowledge_points": ["Python", "编程基础"], "description": "从零开始学习 Python 编程语言，涵盖变量、数据类型、控制流、函数等基础知识。"},
    {"title": "数据结构与算法", "resource_type": "course", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["数据结构", "算法"], "description": "系统学习常见数据结构和经典算法，包含大量 LeetCode 实战练习。"},
    {"title": "Web 全栈开发实战", "resource_type": "course", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["Vue", "FastAPI", "MySQL"], "description": "从零搭建一个完整的 Web 应用，覆盖前端、后端、数据库全链路。"},
    {"title": "深度学习入门", "resource_type": "course", "direction": "AI", "difficulty": "intermediate", "knowledge_points": ["深度学习", "PyTorch", "神经网络"], "description": "系统学习深度学习基础理论，使用 PyTorch 完成图像分类、文本分类等实战项目。"},
    {"title": "大模型应用开发", "resource_type": "course", "direction": "AI", "difficulty": "advanced", "knowledge_points": ["LLM", "RAG", "Agent", "Prompt"], "description": "从 API 调用到 RAG 系统搭建，再到多 Agent 协作，全面掌握大模型应用开发。"},
    {"title": "React 18 实战入门", "resource_type": "course", "direction": "前端开发", "difficulty": "beginner", "knowledge_points": ["React", "Hooks", "JSX"], "description": "从零学习 React 18，掌握组件化开发思想、Hooks 用法以及前端工程化最佳实践。"},
    {"title": "Spark 大数据分析", "resource_type": "course", "direction": "大数据", "difficulty": "advanced", "knowledge_points": ["Spark", "Scala", "数据仓库"], "description": "深入讲解 Apache Spark 核心原理与大数据分析实战，涵盖 RDD、DataFrame、Streaming 等内容。"},
    {"title": "NLP 自然语言处理", "resource_type": "course", "direction": "AI", "difficulty": "advanced", "knowledge_points": ["NLP", "Transformer", "BERT"], "description": "系统学习自然语言处理核心技术，从文本预处理到预训练模型微调，覆盖分类、序列标注、生成等任务。"},
    {"title": "鸿蒙应用开发入门", "resource_type": "course", "direction": "前端开发", "difficulty": "beginner", "knowledge_points": ["鸿蒙", "ArkTS", "鸿蒙架构"], "description": "从零开始学习鸿蒙应用开发，掌握 ArkTS 语言、组件化开发和鸿蒙生态集成能力。"},

    # =============================================================================
    #  文档
    # =============================================================================

    {"title": "FastAPI 官方文档中文版", "resource_type": "document", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["FastAPI", "RESTful", "API"], "description": "FastAPI 框架的官方文档中文翻译，涵盖路由、依赖注入、数据库集成等内容。", "content_text": "# FastAPI 入门\n\n## 路由定义\nFastAPI 使用装饰器定义路由：\n\n```python\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/\")\ndef read_root():\n    return {\"Hello\": \"World\"}\n```"},
    {"title": "RAG 系统搭建指南", "resource_type": "document", "direction": "AI", "difficulty": "advanced", "knowledge_points": ["RAG", "向量数据库", "Embedding"], "description": "详细的 RAG 系统搭建教程，从文档分割到向量检索再到 LLM 生成，完整覆盖每个环节。", "content_text": "# RAG 系统搭建指南\n\n## 什么是 RAG\n\nRAG（Retrieval-Augmented Generation）是一种将信息检索与文本生成相结合的技术范式。\n\n## 核心流程\n1. 文档分割（Chunking）\n2. 向量化（Embedding）\n3. 向量存储（Vector Store）\n4. 检索（Retrieval）\n5. 生成（Generation）"},
    {"title": "Git 协作最佳实践", "resource_type": "document", "direction": "后端开发", "difficulty": "beginner", "knowledge_points": ["Git", "协作", "版本控制"], "description": "团队协作中使用 Git 的规范流程和常见问题解决方案。", "content_text": "# Git 协作最佳实践\n\n## 分支策略\n- main: 生产分支\n- dev: 开发分支\n- feature/*: 功能分支\n\n## 提交规范\n使用 Conventional Commits 规范：\n- feat: 新功能\n- fix: 修复\n- docs: 文档"},
    {"title": "机器学习数学基础", "resource_type": "document", "direction": "AI", "difficulty": "intermediate", "knowledge_points": ["线性代数", "概率论", "微积分"], "description": "机器学习中常用的数学知识总结，线性代数、概率论、微积分核心概念梳理。", "content_text": "# 机器学习数学基础\n\n## 线性代数\n- 向量与矩阵运算\n- 特征值与特征向量\n- SVD 分解\n\n## 概率论\n- 概率分布\n- 贝叶斯定理\n- 最大似然估计"},
    {"title": "MySQL 性能优化手册", "resource_type": "document", "direction": "后端开发", "difficulty": "advanced", "knowledge_points": ["MySQL", "索引优化", "SQL调优"], "description": "MySQL 数据库性能调优实战手册，涵盖索引设计、查询优化、锁机制、主从架构等核心内容。", "content_text": "# MySQL 性能优化手册\n\n## 索引优化\n- 最左前缀原则\n- 覆盖索引\n- 索引下推\n\n## 慢查询优化\n使用 EXPLAIN 分析执行计划，重点关注 type、rows、Extra 等字段。"},
    {"title": "Hadoop 生态入门指南", "resource_type": "document", "direction": "大数据", "difficulty": "beginner", "knowledge_points": ["Hadoop", "HDFS", "MapReduce"], "description": "大数据技术栈入门文档，介绍 Hadoop 分布式文件系统和 MapReduce 计算框架的核心概念。", "content_text": "# Hadoop 生态入门指南\n\n## HDFS 架构\n- NameNode / DataNode\n- 副本机制\n- 读写流程\n\n## MapReduce\n- Map 阶段\n- Shuffle 阶段\n- Reduce 阶段"},
    {"title": "前端工程化实践指南", "resource_type": "document", "direction": "前端开发", "difficulty": "intermediate", "knowledge_points": ["Webpack", "Vite", "前端工程化"], "description": "现代化前端工程化最佳实践，涵盖构建工具选型、模块化、代码规范、CI/CD 集成等。", "content_text": "# 前端工程化实践指南\n\n## 构建工具\n- Vite: 快速开发服务器\n- Webpack: 成熟的生产构建\n\n## 代码规范\n- ESLint + Prettier\n- Husky + lint-staged"},

    # =============================================================================
    #  视频
    # =============================================================================

    {"title": "Vue 3 组合式 API 详解", "resource_type": "video", "direction": "前端开发", "difficulty": "intermediate", "knowledge_points": ["Vue 3", "Composition API", "响应式"], "description": "深入讲解 Vue 3 组合式 API 的核心概念和使用技巧，适合有 Vue 2 基础的开发者。", "duration_seconds": 5400},
    {"title": "Docker 容器化部署", "resource_type": "video", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["Docker", "容器化", "部署"], "description": "从 Docker 基础命令到 Docker Compose 多容器编排，再到生产环境部署的最佳实践。", "duration_seconds": 7200},
    {"title": "PyTorch 入门到实战", "resource_type": "video", "direction": "AI", "difficulty": "beginner", "knowledge_points": ["PyTorch", "张量", "模型训练"], "description": "从张量基础操作开始，逐步讲解如何用 PyTorch 搭建、训练和部署深度学习模型。", "duration_seconds": 8100},
    {"title": "Transformer 架构精讲", "resource_type": "video", "direction": "AI", "difficulty": "advanced", "knowledge_points": ["Transformer", "自注意力", "BERT"], "description": "深入剖析 Transformer 架构的每一层设计，从 Self-Attention 到 Multi-Head Attention，手写实现核心代码。", "duration_seconds": 10800},
    {"title": "Flutter 跨平台开发实战", "resource_type": "video", "direction": "前端开发", "difficulty": "intermediate", "knowledge_points": ["Flutter", "Dart", "跨平台"], "description": "使用 Flutter 框架开发跨平台移动应用，从 Widget 基础到状态管理再到原生平台集成。", "duration_seconds": 9600},
    {"title": "Flink 实时流处理", "resource_type": "video", "direction": "大数据", "difficulty": "advanced", "knowledge_points": ["Flink", "流处理", "实时计算"], "description": "深入讲解 Apache Flink 实时流处理框架，涵盖时间语义、状态管理、Checkpoint 机制及生产部署。", "duration_seconds": 6600},
    {"title": "Python 数据分析与可视化", "resource_type": "video", "direction": "大数据", "difficulty": "beginner", "knowledge_points": ["Pandas", "NumPy", "Matplotlib"], "description": "使用 Python 生态进行数据清洗、分析和可视化，包含真实数据集分析案例。", "duration_seconds": 4800},

    # =============================================================================
    #  PPT
    # =============================================================================

    {"title": "机器学习基础概念", "resource_type": "ppt", "direction": "AI", "difficulty": "beginner", "knowledge_points": ["机器学习", "监督学习", "无监督学习"], "description": "介绍机器学习基本概念、分类、常见算法及评估方法，适合入门学习者。"},
    {"title": "Web 安全防护体系", "resource_type": "ppt", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["Web安全", "XSS", "CSRF", "SQL注入"], "description": "全面讲解 Web 应用中常见的安全威胁及防护策略，包含 OWASP Top 10 解读。"},
    {"title": "React Native 移动端架构设计", "resource_type": "ppt", "direction": "前端开发", "difficulty": "advanced", "knowledge_points": ["React Native", "架构设计", "性能优化"], "description": "React Native 大型应用的架构设计模式、性能优化方案和原生模块开发经验分享。"},
    {"title": "数据仓库与 ETL 实践", "resource_type": "ppt", "direction": "大数据", "difficulty": "intermediate", "knowledge_points": ["数据仓库", "ETL", "数仓建模"], "description": "企业级数据仓库建设方法论，涵盖维度建模、ETL 流程设计及调度系统搭建。"},

    # =============================================================================
    #  思维导图
    # =============================================================================

    {"title": "Java 知识体系全景图", "resource_type": "mindmap", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["Java", "JVM", "Spring", "微服务"], "description": "Java 后端开发完整知识体系思维导图，从基础语法到 JVM 调优再到微服务架构。"},
    {"title": "AI 学习路线图", "resource_type": "mindmap", "direction": "AI", "difficulty": "beginner", "knowledge_points": ["AI", "机器学习", "深度学习", "学习路径"], "description": "人工智能学习路径思维导图，从数学基础到经典算法到前沿大模型，规划清晰的学习路线。"},
    {"title": "大数据技术栈一览", "resource_type": "mindmap", "direction": "大数据", "difficulty": "intermediate", "knowledge_points": ["大数据", "Hadoop", "Spark", "Flink"], "description": "大数据生态技术栈全景思维导图，涵盖数据采集、存储、计算、调度、可视化全链路。"},

    # =============================================================================
    #  题库
    # =============================================================================

    {"title": "Python 基础 100 题", "resource_type": "quiz", "direction": "后端开发", "difficulty": "beginner", "knowledge_points": ["Python", "编程基础"], "description": "涵盖 Python 基础的 100 道练习题，从变量到面向对象编程。"},
    {"title": "数据结构专项练习", "resource_type": "quiz", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["数据结构", "算法"], "description": "数组、链表、树、图、哈希表等数据结构的专项练习题。"},
    {"title": "SQL 查询挑战", "resource_type": "quiz", "direction": "后端开发", "difficulty": "intermediate", "knowledge_points": ["SQL", "数据库"], "description": "从简单查询到复杂多表联查的 SQL 练习题。"},
    {"title": "机器学习模型评估", "resource_type": "quiz", "direction": "AI", "difficulty": "intermediate", "knowledge_points": ["机器学习", "模型评估", "交叉验证"], "description": "关于机器学习模型评估指标的练习题，涵盖准确率、精确率、召回率、F1 分数、ROC 曲线等。"},
    {"title": "前端基础八股文", "resource_type": "quiz", "direction": "前端开发", "difficulty": "beginner", "knowledge_points": ["HTML", "CSS", "JavaScript"], "description": "前端开发基础面试题库，涵盖 HTML/CSS/JavaScript 核心知识点。"},

    # =============================================================================
    #  项目案例
    # =============================================================================

    {"title": "在线考试系统", "resource_type": "project", "direction": "后端开发", "difficulty": "advanced", "knowledge_points": ["FastAPI", "Vue", "MySQL"], "description": "一个完整的在线考试系统，支持题库管理、在线考试、自动评分等功能。"},
    {"title": "智能问答机器人", "resource_type": "project", "direction": "AI", "difficulty": "advanced", "knowledge_points": ["LLM", "RAG", "Prompt"], "description": "基于大模型 API 和 RAG 技术的智能问答机器人，支持文档上传和知识库问答。"},
    {"title": "电商数据实时大屏", "resource_type": "project", "direction": "大数据", "difficulty": "intermediate", "knowledge_points": ["Flink", "Kafka", "数据可视化"], "description": "基于 Flink + Kafka 的电商实时数据大屏项目，涵盖实时 ETL、指标计算和可视化展示。"},
    {"title": "低代码可视化搭建平台", "resource_type": "project", "direction": "前端开发", "difficulty": "advanced", "knowledge_points": ["React", "拖拽", "可视化"], "description": "一个低代码可视化页面搭建平台，支持组件拖拽、属性配置、实时预览和代码导出。"},
    {"title": "微服务电商平台", "resource_type": "project", "direction": "后端开发", "difficulty": "advanced", "knowledge_points": ["微服务", "Spring Cloud", "分布式"], "description": "基于微服务架构的电商平台，涵盖服务注册发现、配置中心、网关、分布式事务等核心技术。"},
]


def seed_resources(db: Session) -> None:
    """初始化种子数据。"""
    if db.query(PlatformResource).count() > 0:
        return
    for item in SEED_RESOURCES:
        resource = PlatformResource(**item)
        db.add(resource)
    db.commit()


def get_resource_list(db: Session, filters: dict) -> tuple[list[dict], int]:
    query = db.query(PlatformResource)

    if filters.get("resource_type"):
        query = query.filter(PlatformResource.resource_type == filters["resource_type"])
    if filters.get("direction"):
        query = query.filter(PlatformResource.direction == filters["direction"])
    if filters.get("difficulty"):
        query = query.filter(PlatformResource.difficulty == filters["difficulty"])
    if filters.get("keyword"):
        kw = f"%{filters['keyword']}%"
        query = query.filter(
            or_(PlatformResource.title.ilike(kw), PlatformResource.description.ilike(kw))
        )

    total = query.count()
    page = int(filters.get("page", 1))
    page_size = int(filters.get("page_size", 20))
    resources = query.order_by(PlatformResource.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [
        {
            "id": r.id,
            "title": r.title,
            "resource_type": r.resource_type,
            "direction": r.direction,
            "difficulty": r.difficulty,
            "description": r.description,
            "knowledge_points": r.knowledge_points,
            "created_at": str(r.created_at),
        }
        for r in resources
    ]
    return items, total


def get_resource_detail(db: Session, resource_id: int) -> dict:
    resource = db.query(PlatformResource).filter(PlatformResource.id == resource_id).first()
    if not resource:
        raise ResourceNotFound("资源不存在")
    return {
        "id": resource.id,
        "title": resource.title,
        "resource_type": resource.resource_type,
        "direction": resource.direction,
        "difficulty": resource.difficulty,
        "description": resource.description,
        "knowledge_points": resource.knowledge_points,
        "content_url": resource.content_url,
        "content_text": resource.content_text,
        "duration_seconds": resource.duration_seconds,
        "created_at": str(resource.created_at),
    }


async def generate_resource_core(
    db: Session, user_id: int, params: dict
) -> dict:
    result = await ai_generate_resource(params)
    resource = GeneratedResource(
        user_id=user_id,
        path_id=params.get("path_id"),
        resource_type=params.get("resource_type", "document"),
        title=result.get("title", ""),
        content=result.get("content", ""),
        content_json=result.get("content_json"),
        related_knowledge_points=result.get("related_knowledge_points"),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {
        "id": resource.id,
        "resource_type": resource.resource_type,
        "title": resource.title,
        "content": resource.content,
        "content_json": resource.content_json,
        "related_knowledge_points": resource.related_knowledge_points,
        "created_at": str(resource.created_at),
    }


def get_generated_resources(db: Session, user_id: int) -> list[dict]:
    resources = (
        db.query(GeneratedResource)
        .filter(GeneratedResource.user_id == user_id)
        .order_by(GeneratedResource.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "resource_type": r.resource_type,
            "title": r.title,
            "created_at": str(r.created_at),
        }
        for r in resources
    ]


def get_generated_resource_detail(db: Session, resource_id: int, user_id: int) -> dict:
    resource = db.query(GeneratedResource).filter(
        GeneratedResource.id == resource_id,
        GeneratedResource.user_id == user_id,
    ).first()
    if not resource:
        raise ResourceNotFound("生成资源不存在")
    return {
        "id": resource.id,
        "resource_type": resource.resource_type,
        "title": resource.title,
        "content": resource.content,
        "content_json": resource.content_json,
        "related_knowledge_points": resource.related_knowledge_points,
        "created_at": str(resource.created_at),
    }
