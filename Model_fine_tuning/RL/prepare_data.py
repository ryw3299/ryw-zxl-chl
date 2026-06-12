"""
RL DPO 偏好数据准备脚本
从 SFT 数据和用户反馈日志生成 DPO 训练数据

DPO 数据格式（JSONL）：
{
  "prompt": "问题文本",
  "chosen": "好回答",
  "rejected": "差回答"
}

用户反馈信号（生成偏好对）：
- 追问减少 → 正向偏好
- 回答被收藏 → 正向偏好
- 跳过回答 → 负向偏好
- 差评 → 负向偏好

用法：
    python prepare_data.py
"""

import json
import random
import os
from pathlib import Path
from collections import defaultdict

# ── 配置 ──────────────────────────────────────────────
SFT_DATA_DIR = Path("../SFT/data")
OUT_DIR = Path("./data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

# 回答策略选项（用于构造正负例）
DETAIL_LEVELS = ["极简", "简洁", "中等", "详细", "非常详细"]
RESPONSE_STYLES = ["纯概念", "带例子", "带推导", "带应用"]


def load_sft_data():
    """加载 SFT 数据"""
    data = []
    for split in ["train", "val"]:
        path = SFT_DATA_DIR / f"{split}_sft.jsonl"
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    return data


def parse_sft_item(item: dict):
    """解析 SFT item，提取问题和回答"""
    messages = item["messages"]
    # 找到 user 和 assistant 的内容
    user_content = ""
    assistant_content = ""
    for msg in messages:
        if msg["role"] == "user":
            user_content = msg["content"]
        elif msg["role"] == "assistant":
            assistant_content = msg["content"]
    return user_content, assistant_content


def build_detail_variant(base_answer: str, level: str, style: str) -> str:
    """根据详细程度和风格构造不同版本"""
    # 这是一个简化的版本，实际项目中会根据真实用户反馈生成
    detail_map = {
        "极简": f"答：{base_answer.split(chr(10))[0] if chr(10) in base_answer else base_answer[:50]}",
        "简洁": base_answer[:100] if len(base_answer) > 100 else base_answer,
        "中等": base_answer,
        "详细": base_answer + "\n\n【补充说明】以上内容如有疑问可继续提问。",
        "非常详细": base_answer + "\n\n【深入扩展】" + "相关知识点参考：详见教材对应章节。",
    }
    return detail_map.get(level, base_answer)


def generate_preference_pairs(data: list) -> list:
    """
    生成 DPO 偏好数据

    模拟用户反馈逻辑：
    - 认知等级高 + 回答简洁 → 用户满意（正例）
    - 认知等级低 + 回答太简 → 用户不满意（负例）
    - 认知等级低 + 回答详细 → 用户满意（正例）
    - 认知等级高 + 回答太详 → 用户不满意（负例）
    """
    pairs = []
    for item in data:
        # 从 assistant 消息中提取认知等级
        messages = item["messages"]
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        assistant_msg = next((m["content"] for m in messages if m["role"] == "assistant"), "")

        # 解析等级
        level = None
        for lvl in ["novice", "beginner", "intermediate", "advanced"]:
            if lvl in assistant_msg:
                level = lvl
                break

        if not level:
            continue

        # 根据等级决定什么是"好回答"和"坏回答"
        # novice/beginner：喜欢详细、带例子的回答
        # advanced：喜欢简洁、直接给要点的回答
        if level in ["novice", "beginner"]:
            chosen = build_detail_variant(assistant_msg, "详细", "带例子")
            rejected = build_detail_variant(assistant_msg, "极简", "纯概念")
        else:  # intermediate, advanced
            chosen = build_detail_variant(assistant_msg, "简洁", "带推导")
            rejected = build_detail_variant(assistant_msg, "非常详细", "带扩展")

        pairs.append({
            "prompt": user_msg,
            "chosen": chosen,
            "rejected": rejected,
            "cognitive_level": level,
        })

    return pairs


def main():
    print("=" * 50)
    print("DPO 偏好数据生成")
    print("=" * 50)

    print("\n[1/3] 加载 SFT 数据...")
    sft_data = load_sft_data()
    print(f"  加载 {len(sft_data)} 条 SFT 数据")

    print("\n[2/3] 生成偏好数据...")
    pairs = generate_preference_pairs(sft_data)
    print(f"  生成 {len(pairs)} 个偏好对")

    print("\n[3/3] 保存数据...")
    # 分割
    random.shuffle(pairs)
    train_end = int(len(pairs) * 0.9)
    train_pairs = pairs[:train_end]
    val_pairs = pairs[train_end:]

    for split, data in [("train", train_pairs), ("val", val_pairs)]:
        out_path = OUT_DIR / f"dpo_{split}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  {split}: {len(data)} 对 -> {out_path} ({size_mb:.1f} MB)")

    # 展示样例
    print("\n样例：")
    sample = pairs[0]
    print(f"  Prompt: {sample['prompt'][:80]}...")
    print(f"  Chosen: {sample['chosen'][:60]}...")
    print(f"  Rejected: {sample['rejected'][:60]}...")
    print(f"  Level: {sample['cognitive_level']}")

    print("\n✅ DPO 数据准备完成！")


if __name__ == "__main__":
    main()
