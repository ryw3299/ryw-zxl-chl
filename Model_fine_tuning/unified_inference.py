"""
统一推理入口
展示 SFT + DPO 完整推理流程

流程：
    问题 → SFT推理(第1次) → 认知分数 → DPO推理(第2次) → 回答策略

用法：
    python unified_inference.py --question "什么是卷积神经网络？"
    python unified_inference.py --interactive
"""

import argparse
import sys
import os

# 确保能找到 SFT 和 RL 模块
sys.path.insert(0, os.path.dirname(__file__))

from SFT.inference import infer as sft_infer, load_model as load_sft_model
from RL.inference import decide_strategy as dpo_decide_strategy, load_model as load_dpo_model


def load_all_models():
    """加载 SFT 和 DPO 两个模型"""
    print("加载 SFT 模型...")
    sft_model, sft_tokenizer = load_sft_model()

    print("加载 DPO 模型...")
    dpo_model, dpo_tokenizer = load_dpo_model()

    return sft_model, sft_tokenizer, dpo_model, dpo_tokenizer


def unified_infer(question: str, context: str = "", history: list = None):
    """
    统一推理：SFT → 认知分数 → DPO → 回答策略

    参数：
        question: 学生问题
        context: RAG检索上下文
        history: 对话历史

    返回：
        sft_result: SFT模型的认知估计结果
        dpo_result: DPO模型的回答策略
    """
    # ========== 第1次推理：SFT 模型 ==========
    print("\n" + "=" * 50)
    print("第1次推理：SFT 模型（认知状态估计）")
    print("=" * 50)
    print(f"输入问题：{question}")
    print(f"输入上下文：{context[:50]}..." if len(context) > 50 else f"输入上下文：{context}")

    sft_result = sft_infer(question, context, history)

    print(f"\nSFT 输出：")
    print(f"  理解等级：{sft_result['level']}")
    print(f"  分数：{sft_result['expected_score']} / 100")
    print(f"  问题类型：{sft_result['question_type']}")

    # ========== 第2次推理：DPO 模型 ==========
    print("\n" + "=" * 50)
    print("第2次推理：DPO 模型（回答策略决策）")
    print("=" * 50)

    dpo_result = dpo_decide_strategy(sft_result['level'], sft_result['question_type'])

    print(f"\nDPO 输出（回答策略）：")
    for k, v in dpo_result.items():
        print(f"  {k}：{v}")

    # ========== 汇总 ==========
    print("\n" + "=" * 50)
    print("完整结果汇总")
    print("=" * 50)
    print(f"认知水平：{sft_result['level']}（{sft_result['expected_score']}分）")
    print(f"问题类型：{sft_result['question_type']}")
    print(f"回答策略：")
    print(f"  详细程度：{dpo_result.get('detail_level', 'N/A')}/5")
    print(f"  需要例子：{dpo_result.get('need_example', 'N/A')}")
    print(f"  需要推导：{dpo_result.get('need_derivation', 'N/A')}")
    print(f"  需要背景：{dpo_result.get('need_background', 'N/A')}")

    return {
        "sft": sft_result,
        "dpo": dpo_result,
    }


def main():
    parser = argparse.ArgumentParser(description="SFT + DPO 统一推理")
    parser.add_argument("--question", type=str, default=None,
                        help="学生问题")
    parser.add_argument("--context", type=str, default="",
                        help="RAG检索上下文")
    parser.add_argument("--interactive", action="store_true",
                        help="交互模式")
    args = parser.parse_args()

    # 加载模型
    load_all_models()

    if args.interactive:
        print("\n=== SFT + DPO 统一推理（输入 quit 退出）===\n")
        while True:
            q = input("问题: ").strip()
            if q.lower() in ["quit", "exit", "q"]:
                break
            c = input("检索上下文（可为空）: ").strip()
            unified_infer(q, c)

    elif args.question:
        unified_infer(args.question, args.context)

    else:
        # 默认测试
        test_q = "什么是卷积神经网络？"
        test_c = "卷积神经网络(CNN)是深度学习的一种架构，主要用于图像处理和模式识别任务。"
        unified_infer(test_q, test_c)


if __name__ == "__main__":
    main()
