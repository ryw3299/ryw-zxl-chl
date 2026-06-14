"""AI 服务：通过 DeepSeek API 生成画像、路径、资源。"""

import json
import re

import httpx

from src.core.config import settings


LLM_API_URL = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {settings.LLM_API_KEY}",
    "Content-Type": "application/json",
}


async def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """调用 DeepSeek API，返回文本内容。"""
    import logging
    logger = logging.getLogger(__name__)

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }
    logger.info(f"[DeepSeek] 调用模型: {settings.LLM_MODEL}")
    logger.info(f"[DeepSeek] System prompt: {system_prompt[:100]}...")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(LLM_API_URL, json=payload, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Log token usage
        usage = data.get("usage", {})
        logger.info(f"[DeepSeek] 返回成功 | tokens: {usage.get('total_tokens', '?')} (prompt: {usage.get('prompt_tokens', '?')}, completion: {usage.get('completion_tokens', '?')})")
        logger.info(f"[DeepSeek] 返回内容: {content[:300]}...")

        return content


async def generate_profile(chat_history: list[dict]) -> dict:
    """根据对话历史生成六维学生画像。"""
    if settings.DIFY_MOCK_MODE:
        return _mock_profile()

    chat_text = "\n".join(
        f"{'学生' if m['role'] == 'user' else '系统'}: {m['content']}"
        for m in chat_history
    )

    system_prompt = """你是一位教育数据分析专家。根据学生与系统的对话内容，生成该学生的六维学习画像。

必须严格按照以下 JSON 格式输出，不要包含任何其他文字：

{
  "summary": "对该学生整体情况的自然语言总结（200字以内）",
  "dimensions": {
    "basic_knowledge": {
      "score": 0-100的整数,
      "level": "较弱/中等/较好/优秀",
      "strengths": ["优势1", "优势2"],
      "weaknesses": ["薄弱1", "薄弱2"],
      "evidence": ["依据1", "依据2"]
    },
    "engineering_ability": {
      "score": 整数,
      "level": "较弱/中等/较好/优秀",
      "strengths": [],
      "weaknesses": [],
      "evidence": []
    },
    "ai_data_ability": {
      "score": 整数,
      "level": "较弱/中等/较好/优秀",
      "strengths": [],
      "weaknesses": [],
      "evidence": []
    },
    "learning_goal": {
      "score": 整数,
      "level": "较模糊/较清晰/很清晰",
      "directions": ["方向1", "方向2"]
    },
    "resource_preference": {
      "score": 整数,
      "preferred_types": ["文档", "视频", "项目任务书"],
      "style": "案例驱动/理论系统/简洁步骤"
    },
    "learning_behavior": {
      "score": 整数,
      "level": "待观察/良好/优秀",
      "risk_flags": [],
      "mastery": {}
    }
  }
}

六维说明：
1. basic_knowledge：编程语言、数据结构、网络、数据库等基础掌握度
2. engineering_ability：Web开发、部署、Git、工程实践能力
3. ai_data_ability：机器学习、深度学习、大模型、RAG 等 AI 能力
4. learning_goal：学习目标清晰度与发展方向
5. resource_preference：学习风格偏好
6. learning_behavior：学习行为特征（初始可给中等分）
"""
    user_prompt = f"以下是学生与系统的对话记录，请分析并生成六维画像：\n\n{chat_text}"

    raw = await _call_llm(system_prompt, user_prompt)
    # 清理可能的 markdown 包裹
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw)


async def generate_path(profile: dict, preferences: dict) -> dict:
    """根据画像生成个性化学习路径。"""
    if settings.DIFY_MOCK_MODE:
        return _mock_path(profile)

    profile_str = json.dumps(profile, ensure_ascii=False, indent=2)
    pref_str = json.dumps(preferences, ensure_ascii=False, indent=2)

    system_prompt = """你是一位学习路径规划专家。根据学生画像和偏好，生成个性化学习路径。

必须严格按照以下 JSON 格式输出：

{
  "path_title": "路径标题",
  "natural_language_summary": "给学生看的自然语言说明（解释为什么这样规划）",
  "stages": [
    {
      "stage_index": 1,
      "title": "阶段标题",
      "duration": "第1-X天",
      "goal": "阶段目标描述",
      "knowledge_points": ["知识点1", "知识点2"],
      "platform_resources": ["推荐平台资源"],
      "generated_resources": ["推荐生成资源"],
      "assessment": "阶段验收标准"
    }
  ]
}

要求：
1. 阶段数量 3-5 个
2. 每个阶段有明确的学习目标
3. 知识体系由浅入深
4. 结合画像中的薄弱点重点安排
5. 路径总时长 30-90 天"""
    user_prompt = f"学生画像：\n{profile_str}\n\n偏好设置：\n{pref_str}"

    raw = await _call_llm(system_prompt, user_prompt)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw)


async def generate_resource(params: dict) -> dict:
    """根据参数生成个性化学习资源。"""
    if settings.DIFY_MOCK_MODE:
        return _mock_resource(params)

    params_str = json.dumps(params, ensure_ascii=False, indent=2)

    system_prompt = """你是一位教学资源设计师。根据参数生成个性化学习资源内容。

必须严格按照以下 JSON 格式输出：

{
  "title": "资源标题",
  "content": "完整的 Markdown 格式内容",
  "content_json": {"type": "资源类型", "knowledge_points": []},
  "related_knowledge_points": ["关联知识点1"]
}

要求：
- 内容详实、结构清晰
- 包含实际可用的示例
- 语言通俗易懂
- Markdown 格式完整"""
    user_prompt = f"生成参数：\n{params_str}"

    raw = await _call_llm(system_prompt, user_prompt)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw)


# ── Mock 降级 ──────────────────────────────────────────────

def _mock_profile() -> dict:
    return {
        "summary": "该学生具备一定的 Python 和 Web 基础，但在数据结构与算法、计算机网络和 AI 应用开发方面仍有提升空间。学习目标偏向就业和项目实践，适合项目驱动式学习路径。",
        "dimensions": {
            "basic_knowledge": {"score": 60, "level": "中等", "strengths": ["Python 基础", "数据库基础"], "weaknesses": ["数据结构与算法", "计算机网络"], "evidence": ["用户表示算法题训练较少"]},
            "engineering_ability": {"score": 65, "level": "中等", "strengths": ["Web 开发基础", "接口调用"], "weaknesses": ["项目部署", "Docker"], "evidence": ["用户有简单 Web 项目经验"]},
            "ai_data_ability": {"score": 40, "level": "较弱", "strengths": ["了解大模型基本概念"], "weaknesses": ["RAG", "向量数据库", "模型微调"], "evidence": ["用户希望学习 AI 应用开发"]},
            "learning_goal": {"score": 75, "level": "较清晰", "directions": ["AI 应用开发", "就业", "项目实践"]},
            "resource_preference": {"score": 80, "preferred_types": ["文档", "视频", "项目任务书"], "style": "案例驱动，步骤清晰"},
            "learning_behavior": {"score": 50, "level": "待观察", "risk_flags": [], "mastery": {}},
        },
    }


def _mock_path(profile: dict) -> dict:
    _dir = (profile.get("dimensions", {}).get("learning_goal", {}).get("directions", []) or ["AI 应用开发"])[0]
    return {
        "path_title": f"30 天 {_dir} 学习路径",
        "natural_language_summary": "根据你的学习画像，你目前具备一定的编程基础，但在 AI 应用开发方面仍然比较薄弱。建议你先补齐 Python 数据处理和 API 调用能力，再学习 RAG 与向量数据库，最后完成一个完整的 AI 应用项目。",
        "stages": [
            {"stage_index": 1, "title": "Python 数据处理基础", "duration": "第 1-5 天", "goal": "掌握 NumPy、Pandas 和基础数据清洗方法", "knowledge_points": ["NumPy", "Pandas", "数据清洗"], "platform_resources": ["Python 数据分析入门课程"], "generated_resources": ["Pandas 常用操作速查文档"], "assessment": "能够完成 CSV 数据清洗任务"},
            {"stage_index": 2, "title": "大模型 API 与 Prompt 工程", "duration": "第 6-12 天", "goal": "掌握大模型 API 调用和 Prompt 编写技巧", "knowledge_points": ["LLM API", "Prompt Engineering", "JSON 输出"], "platform_resources": ["大模型 API 入门课程", "Prompt 编写指南"], "generated_resources": ["API 调用速查文档", "Prompt 案例集"], "assessment": "完成一个智能对话助手 Demo"},
            {"stage_index": 3, "title": "RAG 与向量数据库", "duration": "第 13-22 天", "goal": "理解 RAG 原理并能搭建基础检索增强生成系统", "knowledge_points": ["RAG", "向量数据库", "Embedding", "文档分割"], "platform_resources": ["RAG 入门课程", "向量数据库文档"], "generated_resources": ["RAG 架构图解", "检索增强练习题"], "assessment": "搭建一个文档问答系统原型"},
            {"stage_index": 4, "title": "综合项目实战", "duration": "第 23-30 天", "goal": "综合运用所学完成一个完整的 AI 应用项目", "knowledge_points": ["项目架构", "前后端联调", "部署上线"], "platform_resources": ["项目实战课程"], "generated_resources": ["项目任务书", "代码模板"], "assessment": "完成项目的部署和演示"},
        ],
    }


def _mock_resource(params: dict) -> dict:
    rtype = params.get("resource_type", "document")
    kps = params.get("knowledge_points", ["Python"])
    kp_str = "、".join(kps)
    contents = {
        "document": f"# {kp_str} 学习笔记\n\n## 学习目标\n- 理解 {kp_str} 的核心概念\n- 掌握 {kp_str} 的基本使用方法\n\n## 核心概念\n\n### 1. 基本定义\n{kp_str} 是计算机科学中的重要概念。\n\n### 2. 代码示例\n```python\ndef hello():\n    print(\"Hello, {kp_str}!\")\n```\n\n## 练习\n1. 实现一个基于 {kp_str} 的小程序\n",
        "quiz": f"# {kp_str} 练习题\n\n## 单选题\n1. 关于 {kp_str}，以下哪个说法是正确的？\n   A. ...\n   B. ...\n\n## 简答题\n1. 请简述 {kp_str} 的核心原理。\n",
        "mindmap": "```mermaid\nmindmap\n  root((学习路线))\n    {kp_str}\n      基础概念\n      实践应用\n```",
    }
    content = contents.get(rtype, contents["document"])
    return {"title": f"{kp_str} {'笔记' if rtype == 'document' else '练习' if rtype == 'quiz' else '导图'}", "content": content, "content_json": {"type": rtype, "knowledge_points": kps}, "related_knowledge_points": kps}
