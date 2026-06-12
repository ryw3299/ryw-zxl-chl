"""
SFT 数据准备脚本
将源数据转换为 SFT 训练格式

用法：
    python prepare_data.py
"""

import json
import os
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
SRC_DIR = Path("../../data/splits")
OUT_DIR = Path("./data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LEVEL2ID = {"novice": 0, "beginner": 1, "intermediate": 2, "advanced": 3}

SYSTEM_TEMPLATE = """你是一个教育问答系统的认知状态估计助手。

理解等级定义：
- novice（0-25分）：最基础定义，如"什么是XX？"
- beginner（26-50分）：追问原因、作用，如"为什么需要XX？"
- intermediate（51-75分）：对比应用，如"XX和YY的区别？"
- advanced（76-100分）：推导证明，如"推导XX的公式"

【当前检索内容】
{context}"""

USER_TEMPLATE = """【对话历史】
{history}

【当前问题】
{question}

请判断学生所属的理解等级："""

ASSISTANT_TEMPLATE = """理解等级：{label}
问题类型：{qtype}"""


def build_history_text(history: list) -> str:
    if not history:
        return "无历史对话"
    lines = []
    for i, turn in enumerate(history, 1):
        lvl = turn.get("understanding_level", "unknown")
        lines.append(f"第{i}轮提问：{turn['question']}")
        lines.append(f"理解等级：{lvl}")
    return "\n".join(lines)


def convert_item(item: dict) -> dict:
    """转换为 ChatML 格式"""
    ctx_key = "retrieval_context" if "retrieval_context" in item else "retrievel_context"
    context = item[ctx_key]
    if context.startswith("【检索结果】"):
        context = context.replace("【检索结果】", "").strip()

    history_text = build_history_text(item["history"])
    label = item["understanding_label"]
    qtype = item["question_type"]

    messages = [
        {"role": "system", "content": SYSTEM_TEMPLATE.format(context=context)},
        {"role": "user", "content": USER_TEMPLATE.format(history=history_text, question=item["current_question"])},
        {"role": "assistant", "content": ASSISTANT_TEMPLATE.format(label=label, qtype=qtype)},
    ]
    return {"messages": messages}


def convert_split(split: str):
    src_path = SRC_DIR / f"{split}.json"
    out_path = OUT_DIR / f"{split}_sft.jsonl"

    with open(src_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  [{split}] {len(data)} 条...", end=" ")

    with open(out_path, "w", encoding="utf-8") as f:
        for item in data:
            converted = convert_item(item)
            f.write(json.dumps(converted, ensure_ascii=False) + "\n")

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"保存到 {out_path} ({size_mb:.1f} MB)")


def main():
    print("=" * 50)
    print("SFT 数据准备")
    print("=" * 50)
    for split in ["train", "val", "test"]:
        convert_split(split)
    print("\n完成！")


if __name__ == "__main__":
    main()
