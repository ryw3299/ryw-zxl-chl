"""Shared question-type classification for the student agent pipeline.

This module is the single source of truth for keyword-based question
classification.  Both ``agent.py`` and ``response_builder.py`` should
delegate to ``classify_question_type`` instead of maintaining their own
copies.
"""

from __future__ import annotations

from typing import Literal

StudentQuestionType = Literal[
    "definition",
    "reasoning",
    "procedure",
    "example",
    "comparison",
    "summary",
    "chitchat",
    "unknown",
]

QUESTION_TYPE_KEYWORDS: dict[StudentQuestionType, tuple[str, ...]] = {
    "definition": ("什么是", "定义", "what is", "define", "什么叫", "概念"),
    "reasoning": ("为什么", "为何", "原因", "why", "reason", "什么原因"),
    "procedure": ("怎么", "如何", "步骤", "怎么做", "how", "steps", "如何做", "办法"),
    "example": ("例如", "举例", "例子", "for example", "example", "比如"),
    "comparison": ("区别", "不同", "比较", "对比", "compare", "difference", "差异"),
    "summary": ("总结", "概括", "归纳", "summary", "summarize", "小结"),
    "unknown": (),
}

CHITCHAT_PATTERNS: tuple[str, ...] = (
    "你好",
    "您好",
    "hi",
    "hello",
    "hey",
    "嗨",
    "哈喽",
    "你是谁",
    "你是什么",
    "你叫什么",
    "你能做什么",
    "who are you",
    "谢谢",
    "感谢",
    "thanks",
    "thank you",
    "thx",
    "好的",
    "明白了",
    "懂了",
    "了解",
    "知道了",
    "ok",
    "okay",
    "收到",
    "再见",
    "拜拜",
    "bye",
    "再见了",
    "嗯",
    "哦",
    "噢",
    "啊",
)


def classify_question_type(question: str) -> StudentQuestionType:
    """Classify a student question into a pedagogical category via keywords."""
    normalized = (question or "").strip().lower()
    if not normalized:
        return "unknown"

    if is_chitchat(normalized):
        return "chitchat"

    for qtype, keywords in QUESTION_TYPE_KEYWORDS.items():
        if any(kw.lower() in normalized for kw in keywords):
            return qtype
    return "unknown"


def is_chitchat(question: str) -> bool:
    """Return True if the question is casual chat rather than a course question."""
    normalized = (question or "").strip().lower()
    if not normalized:
        return False
    if len(normalized) <= 6 and any(p in normalized for p in CHITCHAT_PATTERNS):
        return True
    return normalized in set(CHITCHAT_PATTERNS)
