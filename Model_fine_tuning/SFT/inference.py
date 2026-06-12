"""
SFT 推理脚本（分类头版本）
输出：4分类概率 + expected_score（0-100分）+ 问题类型

用法：
    python inference.py --question "什么是机器学习？"
    python inference.py --interactive
"""

import argparse
import json
import numpy as np
import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

# ── 配置 ──────────────────────────────────────────────
MODEL_PATH = "./outputs/sft_model/final"
BASE_MODEL = "Qwen/Qwen2.5-1.7B"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 等级中心分数
LEVEL_CENTERS = [12.5, 38.0, 63.0, 88.0]
ID2LEVEL = {0: "novice", 1: "beginner", 2: "intermediate", 3: "advanced"}
QTYPE_NAMES = ["definition", "procedure", "reasoning", "comparison", "derivation", "application", "example"]


# ── 复制训练时的模型结构 ────────────────────────────────
class QwenClassificationModel(nn.Module):
    def __init__(self, base_model_name: str, num_labels: int = 4, num_qtypes: int = 7):
        super().__init__()
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        self.base_model = AutoModel.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            output_hidden_states=True,
        )
        hidden_size = self.base_model.config.hidden_size
        self.level_head = nn.Linear(hidden_size, num_labels, bias=True)
        self.qtype_head = nn.Linear(hidden_size, num_qtypes, bias=True)

    def forward(self, input_ids, attention_mask, **kwargs):
        outputs = self.base_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        last_hidden = outputs.hidden_states[-1]
        mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
        sum_hidden = torch.sum(last_hidden * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        pooled = sum_hidden / sum_mask
        level_logits = self.level_head(pooled)
        qtype_logits = self.qtype_head(pooled)
        return {
            "level_logits": level_logits,
            "qtype_logits": qtype_logits,
            "pooled_hidden": pooled,
        }


def load_model():
    """加载模型"""
    print(f"加载模型 from: {MODEL_PATH}")

    # 加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 加载 LoRA 权重
    model = QwenClassificationModel(BASE_MODEL, num_labels=4, num_qtypes=7)

    # 尝试加载训练好的权重
    adapter_path = MODEL_PATH / "adapter_model.safetensors"
    if not adapter_path.exists():
        adapter_path = MODEL_PATH

    try:
        # 加载 base model 权重
        base_state = {}
        from safetensors.torch import load_file
        if (MODEL_PATH / "adapter_model.safetensors").exists():
            state_dict = load_file(str(MODEL_PATH / "adapter_model.safetensors"))
            model.load_state_dict(state_dict, strict=False)
            print("✅ LoRA 权重加载成功")
    except Exception as e:
        print(f"⚠️ 权重加载失败: {e}")
        print("⚠️ 使用未训练的模型（随机权重）")

    model = model.to(DEVICE)
    model.eval()
    return model, tokenizer


def infer(model, tokenizer, question: str, context: str = "", history: list = None):
    """
    推理认知状态

    返回：
    {
        "level": "novice",
        "level_probs": [0.70, 0.20, 0.08, 0.02],
        "expected_score": 23.15,
        "question_type": "definition",
        "qtype_probs": [...],
    }
    """
    history = history or []

    # 构建历史文本
    if history:
        history_parts = []
        for i, turn in enumerate(history, 1):
            history_parts.append(f"第{i}轮：{turn['question']} → {turn.get('level', 'unknown')}")
        history_text = "\n".join(history_parts)
    else:
        history_text = "无历史对话"

    # 构建 prompt
    system_prompt = f"""你是一个教育问答系统的认知状态估计助手。

理解等级定义：
- novice（0-25分）：最基础定义，如"什么是XX？"
- beginner（26-50分）：追问原因、作用，如"为什么需要XX？"
- intermediate（51-75分）：对比应用，如"XX和YY的区别？"
- advanced（76-100分）：推导证明，如"推导XX的公式"

【当前检索内容】
{context or "无"}"""

    user_prompt = f"""【对话历史】
{history_text}

【当前问题】
{question}

请分析学生所属的理解等级。"""

    text = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    # Tokenize
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    # 推理
    with torch.no_grad():
        outputs = model(**inputs)

    # 处理理解等级
    level_logits = outputs["level_logits"].cpu().numpy()[0]
    level_probs = np.exp(level_logits) / np.exp(level_logits).sum()
    expected_score = np.dot(level_probs, LEVEL_CENTERS)
    level_id = level_probs.argmax()
    level = ID2LEVEL[level_id]

    # 处理问题类型
    qtype_logits = outputs["qtype_logits"].cpu().numpy()[0]
    qtype_probs = np.exp(qtype_logits) / np.exp(qtype_logits).sum()
    qtype_id = qtype_probs.argmax()
    qtype = QTYPE_NAMES[qtype_id]

    return {
        "level": level,
        "level_probs": level_probs.tolist(),
        "expected_score": round(float(expected_score), 2),
        "question_type": qtype,
        "qtype_probs": qtype_probs.tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", type=str, default=None)
    parser.add_argument("--context", type=str, default="")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    model, tokenizer = load_model()

    if args.interactive:
        print("\n=== 认知状态估计（分类头版）===\n")
        while True:
            q = input("问题: ").strip()
            if q.lower() in ["quit", "exit", "q"]:
                break
            c = input("检索上下文（可为空）: ").strip()
            result = infer(model, tokenizer, q, c)
            print(f"\n  理解等级: {result['level']}")
            print(f"  分数: {result['expected_score']} / 100")
            print(f"  等级概率: { {ID2LEVEL[i]: round(p,3) for i,p in enumerate(result['level_probs'])} }")
            print(f"  问题类型: {result['question_type']}")
            print(f"  类型概率: { {QTYPE_NAMES[i]: round(p,3) for i,p in enumerate(result['qtype_probs'])} }")
            print()

    elif args.question:
        result = infer(model, tokenizer, args.question, args.context)
        print(f"\n问题: {args.question}")
        print(f"理解等级: {result['level']} (分数: {result['expected_score']})")
        print(f"等级概率: {result['level_probs']}")
        print(f"问题类型: {result['question_type']}")
        print(f"类型概率: {result['qtype_probs']}")

    else:
        # 默认测试
        test_q = "什么是机器学习？"
        result = infer(model, tokenizer, test_q, "机器学习是人工智能的一个分支...")
        print(f"\n测试: {test_q}")
        print(f"理解等级: {result['level']} (分数: {result['expected_score']})")
        print(f"等级概率: {[round(p,3) for p in result['level_probs']]}")
        print(f"问题类型: {result['question_type']}")
        print(f"\n分数量化示意：")
        for i, (lvl, center) in enumerate(zip(ID2LEVEL.values(), LEVEL_CENTERS)):
            bar = "█" * int(result['level_probs'][i] * 30)
            print(f"  {lvl:12s} (center={center:5.1f}): {bar} {result['level_probs'][i]:.3f}")
        print(f"  {'expected_score':12s} = {result['expected_score']}")


if __name__ == "__main__":
    main()
