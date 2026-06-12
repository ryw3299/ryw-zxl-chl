"""
RL DPO 推理脚本
基于偏好优化后的策略，决定回答详细程度

用法：
    python inference.py --sft-output '{"level":"novice","expected_score":23.15,"question_type":"definition"}'
    python inference.py --interactive

注意：DPO 模型的输入是 SFT 模型的输出，
      所以实际使用时需要先调用 SFT 推理，再用 DPO 推理。
      两次推理串联，形成完整流程。
"""

import argparse
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ── 配置 ──────────────────────────────────────────────
DPO_MODEL_PATH = "./outputs/dpo_model/final"
SFT_MODEL_PATH = "../SFT/outputs/sft_model/final"
BASE_MODEL = "Qwen/Qwen2.5-1.7B"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

LEVEL_DESC = {
    "novice": "novice（初学者，完全基础的问题）",
    "beginner": "beginner（入门水平，追问原因和作用）",
    "intermediate": "intermediate（中级水平，能问对比和应用）",
    "advanced": "advanced（高级水平，追问推导和证明）",
}

# DPO 策略决策 prompt
STRATEGY_PROMPT = """你是一个教育问答系统的策略决策助手。

根据学生的认知等级，决定最优的回答策略。

认知等级：
- novice（0-25分）：最基础，需要详细解释 + 生活例子
- beginner（26-50分）：入门，需要带原因说明 + 应用场景
- intermediate（51-75分）：中级，聚焦对比 + 步骤说明
- advanced（76-100分）：高级，只需核心要点 + 推导

学生认知等级：{level}

请决定回答策略（直接输出 JSON）：
{{"detail_level": 1-5, "need_example": true/false, "need_derivation": true/false, "need_background": true/false, "response_length": "极简/中等/详细"}}"""


def load_model():
    """加载模型"""
    tokenizer = AutoTokenizer.from_pretrained(SFT_MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    # 尝试加载 DPO 模型
    if DPO_MODEL_PATH.exists():
        try:
            model = PeftModel.from_pretrained(base_model, DPO_MODEL_PATH)
            print("✅ 加载 DPO 微调模型")
        except Exception:
            print("⚠️ DPO 模型加载失败，使用 SFT 模型")
            model = base_model
    else:
        print("⚠️ 未找到 DPO 模型，使用 SFT 模型")
        model = base_model

    return model, tokenizer


def decide_strategy(model, tokenizer, cognitive_level: str) -> dict:
    """用 DPO 模型决定回答策略"""
    prompt = STRATEGY_PROMPT.format(level=LEVEL_DESC.get(cognitive_level, cognitive_level))

    messages = [{"role": "user", "content": prompt}]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=128,
            temperature=0.2,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    )

    # 解析策略
    try:
        strategy = json.loads(response.strip())
    except json.JSONDecodeError:
        # 如果不是 JSON，尝试提取
        strategy = {
            "raw_response": response.strip(),
            "detail_level": 3,
            "need_example": True,
            "need_derivation": False,
        }

    return strategy


def generate_adaptive_response(
    model, tokenizer, question: str, cognitive_level: str, context: str = ""
) -> str:
    """根据认知等级和策略生成自适应回答"""
    # 先决定策略
    strategy = decide_strategy(model, tokenizer, cognitive_level)

    # 构建回答 prompt
    detail_instruct = {
        1: "极简回答，不超过3句话，只给核心定义。",
        2: "简洁回答，约100字，给出要点。",
        3: "中等长度回答，约200字，包含定义和要点。",
        4: "详细回答，约400字，包含定义、例子、应用场景。",
        5: "非常详细回答，500字以上，包含定义、例子、推导、应用和延伸。",
    }

    level_desc = LEVEL_DESC.get(cognitive_level, cognitive_level)
    detail_instr = detail_instruct.get(strategy.get("detail_level", 3), detail_instruct[3])

    if strategy.get("need_example"):
        detail_instr += "必须包含生活类比例子。"
    if strategy.get("need_derivation"):
        detail_instr += "需要包含推导过程。"
    if strategy.get("need_background"):
        detail_instr += "需要补充背景知识。"

    system_msg = f"""你是一个教育问答助手。

学生当前认知等级：{level_desc}

回答要求：{detail_instr}

检索上下文：{context or '无'}"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": question},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    )

    return response, strategy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", type=str, default=None)
    parser.add_argument("--level", type=str, default="novice", choices=list(LEVEL_DESC.keys()))
    parser.add_argument("--context", type=str, default="")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    model, tokenizer = load_model()

    if args.interactive:
        print("\n=== RL 自适应问答（输入 quit 退出）===\n")
        while True:
            q = input("问题: ").strip()
            if q.lower() in ["quit", "exit", "q"]:
                break
            lvl = input("认知等级 (novice/beginner/intermediate/advanced): ").strip() or "novice"
            c = input("检索上下文（可为空）: ").strip()

            response, strategy = generate_adaptive_response(
                model, tokenizer, q, lvl, c
            )
            print(f"\n策略决策: {json.dumps(strategy, ensure_ascii=False)}")
            print(f"\n回答:\n{response}\n")

    elif args.question:
        response, strategy = generate_adaptive_response(
            model, tokenizer, args.question, args.level, args.context
        )
        print(f"\n问题: {args.question}")
        print(f"认知等级: {args.level}")
        print(f"策略: {json.dumps(strategy, ensure_ascii=False)}")
        print(f"\n回答:\n{response}")

    else:
        # 默认测试
        test_q = "什么是机器学习？"
        response, strategy = generate_adaptive_response(
            model, tokenizer, test_q, "novice",
            "机器学习是人工智能的一个分支，研究如何让计算机从数据中学习。"
        )
        print(f"\n测试问题: {test_q}")
        print(f"认知等级: novice")
        print(f"策略: {json.dumps(strategy, ensure_ascii=False)}")
        print(f"\n回答:\n{response}")


if __name__ == "__main__":
    main()
