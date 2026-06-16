"""AI 服务：通过 Dify 和 DeepSeek 生成画像、路径、资源。"""

import json
import re

import httpx

from src.core.config import settings


LLM_API_URL = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {settings.LLM_API_KEY}",
    "Content-Type": "application/json",
}
DIFY_CHAT_MESSAGES_URL = f"{settings.DIFY_BASE_URL.rstrip('/')}/chat-messages"
DIFY_HEADERS = {
    "Authorization": f"Bearer {settings.DIFY_API_KEY}",
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


async def generate_profile(
    chat_history: list[dict], user_id: int, conversation_id: str = ""
) -> dict:
    """调用 Dify Chatflow 生成或追问学生画像。"""
    if settings.DIFY_MOCK_MODE:
        payload = _wrap_mock_profile(chat_history, user_id, conversation_id)
        return payload

    latest_user_query = _get_latest_user_query(chat_history)
    query = latest_user_query or _build_profile_query(chat_history, conversation_id)
    payload = {
        "inputs": {
            "user_id": str(user_id),
            "userinput": {
                "query": query,
                "files": [],
            },
        },
        "query": query,
        "response_mode": "streaming",
        "conversation_id": conversation_id,
        "user": str(user_id),
    }
    dify_response = await _call_dify_chat_streaming(payload)

    profile_payload = _extract_profile_payload(dify_response)
    return {
        "provider": "dify_chatflow",
        "request_payload": payload,
        "http_response": dify_response,
        "profile_payload": profile_payload,
        "conversation_id": dify_response.get("conversation_id", conversation_id or ""),
        "message_id": dify_response.get("message_id") or dify_response.get("id", ""),
        "answer_text": dify_response.get("answer", ""),
    }


async def _call_dify_chat_streaming(payload: dict) -> dict:
    timeout = httpx.Timeout(
        connect=30.0,
        read=settings.DIFY_TIMEOUT_SECONDS,
        write=30.0,
        pool=30.0,
    )
    answer_parts: list[str] = []
    events: list[dict] = []
    conversation_id = payload.get("conversation_id", "")
    message_id = ""
    task_id = ""
    created_at = None
    metadata = {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            DIFY_CHAT_MESSAGES_URL,
            json=payload,
            headers={**DIFY_HEADERS, "Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    event_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                events.append(event_data)
                event_type = event_data.get("event", "")
                conversation_id = event_data.get("conversation_id", conversation_id)
                message_id = (
                    event_data.get("message_id")
                    or event_data.get("id")
                    or message_id
                )
                task_id = event_data.get("task_id", task_id)
                created_at = event_data.get("created_at", created_at)

                if event_type == "message":
                    answer_parts.append(event_data.get("answer", ""))
                elif event_type == "message_end":
                    metadata = event_data.get("metadata", metadata)

    return {
        "event": "message",
        "task_id": task_id,
        "id": message_id,
        "message_id": message_id,
        "conversation_id": conversation_id,
        "mode": "advanced-chat",
        "answer": "".join(answer_parts),
        "metadata": metadata,
        "created_at": created_at,
        "stream_events": events,
    }


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
        "profile_ready": True,
        "profile_type": "initial_student_profile",
        "user_id": "",
        "profile_summary": "该学生具备一定的 Python 和 Web 基础，但在数据结构与算法、计算机网络和 AI 应用开发方面仍有提升空间。学习目标偏向就业和项目实践，适合项目驱动式学习路径。",
        "dialogue_summary": "用户具备 Python 和 Web 基础，希望提升 AI 应用开发能力，偏好项目驱动学习。",
        "collected_info": {
            "user_id": "",
            "name": "",
            "grade": "",
            "major": "",
            "current_courses": [],
            "learning_goal": "提升 AI 应用开发能力",
            "target_direction": "AI 应用开发",
            "expected_output": "完成一个项目并用于求职展示",
            "learning_situation": "",
            "weak_points": ["数据结构与算法", "计算机网络"],
            "technical_foundation": ["Python", "数据库基础", "Web 开发基础"],
            "daily_study_time": "",
            "planning_preference": "项目驱动",
            "resource_preference": ["文档", "视频", "项目任务书"],
            "learning_style": "案例驱动",
            "project_experience": "有简单 Web 项目经验",
            "exam_or_competition": "",
            "deadline": "",
            "preferred_difficulty": "",
            "learning_constraints": [],
            "motivation": "",
            "device_or_tools": [],
            "evidence": ["用户表示算法题训练较少", "用户有简单 Web 项目经验"],
        },
        "frontend_message": "你的初始学生画像已生成。接下来可以查看画像，或继续生成个性化学习路径。",
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


def _wrap_mock_profile(
    chat_history: list[dict], user_id: int, conversation_id: str = ""
) -> dict:
    payload = _normalize_profile_payload(_mock_profile())
    return {
        "provider": "mock_dify_chatflow",
        "request_payload": {
            "inputs": {
                "user_id": str(user_id),
                "userinput": {
                    "query": _get_latest_user_query(chat_history)
                    or _build_profile_query(chat_history, conversation_id),
                    "files": [],
                },
            },
            "query": _get_latest_user_query(chat_history)
            or _build_profile_query(chat_history, conversation_id),
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": str(user_id),
        },
        "http_response": {"answer": json.dumps(payload, ensure_ascii=False)},
        "profile_payload": payload,
        "conversation_id": conversation_id,
        "message_id": "",
        "answer_text": json.dumps(payload, ensure_ascii=False),
    }


def _build_profile_query(chat_history: list[dict], conversation_id: str = "") -> str:
    user_messages = _get_user_messages(chat_history)
    if conversation_id and user_messages:
        return user_messages[-1]

    lines = []
    for item in chat_history:
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        role = "学生" if item.get("role") == "user" else "助手"
        lines.append(f"{role}: {content}")

    transcript = "\n".join(lines) if lines else (user_messages[-1] if user_messages else "")
    return (
        "以下是围绕学生学习画像收集的完整对话，请基于全部上下文继续进行信息抽取。"
        "如果信息不足，请明确指出下一轮最需要补充的内容；如果信息足够，请输出完整画像结果。\n\n"
        f"{transcript}"
    )


def _get_user_messages(chat_history: list[dict]) -> list[str]:
    return [
        str(item.get("content", "")).strip()
        for item in chat_history
        if item.get("role") == "user" and str(item.get("content", "")).strip()
    ]


def _get_latest_user_query(chat_history: list[dict]) -> str:
    user_messages = _get_user_messages(chat_history)
    return user_messages[-1] if user_messages else ""


def _extract_profile_payload(dify_response: dict) -> dict:
    candidates = [
        dify_response,
        dify_response.get("answer"),
        dify_response.get("outputs"),
        dify_response.get("data"),
        (dify_response.get("metadata") or {}).get("outputs"),
        (dify_response.get("metadata") or {}).get("workflow_run", {}).get("outputs"),
        (dify_response.get("workflow_run") or {}).get("outputs"),
    ]

    for candidate in candidates:
        parsed = _parse_profile_candidate(candidate)
        if _looks_like_profile_payload(parsed):
            return _normalize_profile_payload(parsed)

    answer_text = _strip_think_text(str(dify_response.get("answer", "")).strip())
    if answer_text:
        return {
            "profile_ready": False,
            "profile_type": "incomplete_student_profile",
            "user_id": "",
            "profile_summary": "",
            "dialogue_summary": "",
            "collected_info": {},
            "student_profile": None,
            "missing_information": [],
            "frontend_message": answer_text,
            "raw_answer": answer_text,
        }

    raise ValueError("Dify 返回中未找到可解析的画像结果")


def _parse_profile_candidate(candidate) -> dict | None:
    if not candidate:
        return None
    if isinstance(candidate, dict):
        return candidate
    if not isinstance(candidate, str):
        return None

    text = _clean_json_text(candidate)
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _clean_json_text(text: str) -> str:
    text = text.strip()
    text = _strip_think_text(text)
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _strip_think_text(text: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", text or "", flags=re.IGNORECASE).strip()


def _looks_like_profile_payload(payload: dict | None) -> bool:
    if not isinstance(payload, dict):
        return False
    return any(
        key in payload
        for key in ("profile_ready", "profile_type", "collected_info", "student_profile")
    )


def _normalize_profile_payload(payload: dict) -> dict:
    normalized = dict(payload)
    student_profile = normalized.get("student_profile")

    if not student_profile and "dimensions" in normalized:
        student_profile = {
            "summary": normalized.get("summary", ""),
            "dimensions": normalized.get("dimensions", {}),
            "strengths_summary": normalized.get("strengths_summary", []),
            "weaknesses_summary": normalized.get("weaknesses_summary", []),
            "recommended_next_actions": normalized.get("recommended_next_actions", []),
            "missing_information": normalized.get("missing_information", []),
            "profile_confidence": normalized.get("profile_confidence", {}),
        }
        normalized["student_profile"] = student_profile

    normalized["profile_ready"] = _to_bool(
        normalized.get("profile_ready", bool(student_profile))
    )
    normalized.setdefault("profile_type", "initial_student_profile")
    normalized.setdefault("user_id", normalized.get("collected_info", {}).get("user_id", ""))
    normalized.setdefault("collected_info", {})
    normalized.setdefault("dialogue_summary", "")
    normalized.setdefault("frontend_message", "")
    normalized.setdefault("missing_information", [])
    normalized["profile_summary"] = (
        normalized.get("profile_summary")
        or (student_profile or {}).get("summary", "")
        or normalized.get("summary", "")
    )
    return normalized


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)
