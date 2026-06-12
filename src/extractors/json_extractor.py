"""
JSON extractor: 从 artifact JSON 中按字段路径提取子集。

用法示例：
    from src.utils.json_extractor import extract_fields

    data = extract_fields(
        artifact_json={"parser_output": {...}, "generate_output": {...}},
        fields=["parser_output.structured_content", "generate_output.lesson_script"]
    )

    # 或从文件读取：
    data = extract_fields(
        input_path="artifact.json",
        fields=["parser_output.structured_content", "generate_output.lesson_script"],
        output_path="student_data.json"
    )
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def extract_fields(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    fields: Optional[list[str]] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    从 artifact JSON 中提取指定字段。

    Args:
        data: 直接传入的 JSON dict（与 input_path 二选一）
        input_path: JSON 文件路径（与 data 二选一）
        fields: 要提取的字段路径列表，支持 dot notation，如 "parser_output.structured_content"
        output_path: 可选，写入输出文件路径

    Returns:
        只包含所选字段的 dict

    Raises:
        ValueError: 未提供 data 或 input_path
        KeyError: 字段路径不存在
    """
    if data is None and input_path is None:
        raise ValueError("必须提供 data dict 或 input_path 文件路径")

    if data is None:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))

    if fields is None:
        fields = []

    result = {}
    for field_path in fields:
        value = _get_by_dot_path(data, field_path)
        if value is not None or _path_exists(data, field_path):
            _set_by_dot_path(result, field_path, value)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return result


def _get_by_dot_path(data: dict[str, Any], path: str) -> Any:
    """
    按 dot notation 获取嵌套值。

    示例：_get_by_dot_path(data, "parser_output.structured_content.pages")
    """
    keys = path.split(".")
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            current = current[int(key)]
        else:
            return None
        if current is None:
            return None
    return current


def _set_by_dot_path(data: dict[str, Any], path: str, value: Any) -> None:
    """
    按 dot notation 设置嵌套值，自动创建中间 dict。

    示例：_set_by_dot_path(result, "parser_output.structured_content", {...})
    """
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _path_exists(data: dict[str, Any], path: str) -> bool:
    """检查字段路径是否存在（即使值为 None 也返回 True）。"""
    keys = path.split(".")
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                return False
            current = current[key]
        elif isinstance(current, list) and key.isdigit():
            idx = int(key)
            if idx < 0 or idx >= len(current):
                return False
            current = current[idx]
        else:
            return False
    return True


# ─── 单一字段快捷提取 ────────────────────────────────────────────────────────


def extract_presentation_outline(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取 presentation_outline（展示大纲 + 卡片结构）。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=["generate_output.presentation_outline"],
        output_path=output_path,
    )


def extract_lesson_script(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取 lesson_script（讲稿脚本）。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=["generate_output.lesson_script"],
        output_path=output_path,
    )


def extract_ppt_outline(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取 ppt_outline（PPT幻灯片大纲）。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=["generate_output.ppt_outline"],
        output_path=output_path,
    )


def extract_structured_content(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取 structured_content（解析后的结构化内容）。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=["parser_output.structured_content"],
        output_path=output_path,
    )


def extract_teacher_feedback(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取 teacher_feedback_text（教师反馈文本）。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=["generate_output.teacher_feedback_text"],
        output_path=output_path,
    )


# ─── 组合预设 ────────────────────────────────────────────────────────────────

# 学生端必需的核心字段
STUDENT_CORE_FIELDS = [
    "parser_output.structured_content.pages",
    "parser_output.structured_content.sections",
    "parser_output.structured_content.knowledge_points",
    "parser_output.structured_content.lesson_summary",
    "generate_output.lesson_script",
    "generate_output.presentation_outline",
]

# 仅展示用的字段（不含讲稿）
PRESENTATION_ONLY_FIELDS = [
    "parser_output.structured_content.pages",
    "parser_output.structured_content.sections",
    "parser_output.structured_content.knowledge_points",
    "generate_output.presentation_outline",
    "generate_output.ppt_outline",
]

# 完整解析结果
PARSER_ALL_FIELDS = [
    "parser_output.structured_content",
    "parser_output.pages",
    "parser_output.sections",
    "parser_output.knowledge_points",
    "parser_output.lesson_summary",
]

# 生成阶段完整输出
GENERATE_ALL_FIELDS = [
    "generate_output.presentation_outline",
    "generate_output.lesson_script",
    "generate_output.ppt_outline",
    "generate_output.teacher_feedback_text",
]


def extract_student_core(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取学生端核心必需字段。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=STUDENT_CORE_FIELDS,
        output_path=output_path,
    )


def extract_presentation(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取仅用于展示的字段（不含讲稿）。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=PRESENTATION_ONLY_FIELDS,
        output_path=output_path,
    )


def extract_parser_all(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取解析阶段的完整输出。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=PARSER_ALL_FIELDS,
        output_path=output_path,
    )


def extract_generate_all(
    data: Optional[dict[str, Any]] = None,
    *,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """提取生成阶段的完整输出。"""
    return extract_fields(
        data=data,
        input_path=input_path,
        fields=GENERATE_ALL_FIELDS,
        output_path=output_path,
    )
