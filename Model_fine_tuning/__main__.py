"""
Model_fine_tuning 统一入口

用法：
    python -m Model_fine_tuning           # 显示帮助
    python -m Model_fine_tuning sft      # 运行 SFT 训练
    python -m Model_fine_tuning dpo      # 运行 DPO 训练
    python -m Model_fine_tuning infer     # 运行推理测试
"""

import sys
import subprocess

COMMANDS = {
    "sft-prepare": ["python", "SFT/prepare_data.py"],
    "sft-train":   ["python", "SFT/train.py"],
    "sft-infer":   ["python", "SFT/inference.py"],
    "dpo-prepare": ["python", "RL/prepare_data.py"],
    "dpo-train":   ["python", "RL/train.py"],
    "dpo-infer":   ["python", "RL/inference.py"],
    "all":         None,  # 依次运行全部
}

HELP_MSG = """
Model_fine_tuning - 认知状态估计 + 强化学习自适应问答

命令：
    sft-prepare   准备 SFT 训练数据
    sft-train     训练 SFT 模型
    sft-infer     SFT 推理测试
    dpo-prepare   生成 DPO 偏好数据
    dpo-train     DPO 强化学习训练
    dpo-infer     RL 策略推理测试
    all           运行完整流程（SFT + DPO）

示例：
    python -m Model_fine_tuning sft-prepare
    python -m Model_fine_tuning sft-train
    python -m Model_fine_tuning dpo-prepare
    python -m Model_fine_tuning dpo-train
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print(HELP_MSG)
        return

    cmd = sys.argv[1]

    if cmd not in COMMANDS:
        print(f"未知命令: {cmd}")
        print(HELP_MSG)
        return

    if cmd == "all":
        # 依次执行完整流程
        sequence = ["sft-prepare", "sft-train", "dpo-prepare", "dpo-train"]
        for c in sequence:
            print(f"\n{'='*50}")
            print(f">>> {c}")
            print(f"{'='*50}")
            result = subprocess.run(COMMANDS[c], cwd=".")
            if result.returncode != 0:
                print(f"命令 {c} 执行失败，退出")
                break
        print("\n✅ 完整流程执行完成！")
        return

    subprocess.run(COMMANDS[cmd], cwd=".")


if __name__ == "__main__":
    main()
