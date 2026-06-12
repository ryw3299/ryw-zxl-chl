"""
DPO 强化学习训练脚本
Direct Preference Optimization - 直接偏好优化

在 SFT 模型基础上，用偏好数据进一步优化回答策略
使得模型学习：什么认知等级应该配什么详细程度的回答

用法：
    python train.py
"""

import os
import json
from pathlib import Path
from datetime import datetime

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    set_seed,
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datasets import Dataset

# ── 配置 ──────────────────────────────────────────────
set_seed(42)

SFT_MODEL_PATH = Path("../SFT/outputs/sft_model/final")
DPO_DATA_DIR = Path("./data")
OUTPUT_DIR = Path("./outputs/dpo_model")
BASE_MODEL = "Qwen/Qwen2.5-1.7B"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[设备] {device}")


def load_jsonl(path: Path):
    """加载 JSONL 文件"""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def build_dpo_prompt(item: dict) -> dict:
    """构建 DPO 训练样本"""
    return {
        "prompt": item["prompt"],
        "chosen": item["chosen"],
        "rejected": item["rejected"],
    }


def tokenize(tokenizer, texts, max_length=512):
    return tokenizer(
        texts,
        truncation=True,
        max_length=max_length,
        padding=False,
    )


def main():
    print("=" * 60)
    print("DPO 强化学习训练 - 直接偏好优化")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/5] 加载偏好数据...")
    train_data = load_jsonl(DPO_DATA_DIR / "dpo_train.jsonl")
    val_data = load_jsonl(DPO_DATA_DIR / "dpo_val.jsonl")
    print(f"  Train: {len(train_data)} | Val: {len(val_data)}")

    # 2. Tokenizer
    print("\n[2/5] 加载 Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(SFT_MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 3. 准备 DPO 数据集
    print("\n[3/5] 准备 DPO 训练数据...")

    # DPO 格式：prompt, chosen, rejected
    # 构建方法：直接用trl库的DPO Trainer
    train_formatted = [build_dpo_prompt(item) for item in train_data]
    val_formatted = [build_dpo_prompt(item) for item in val_data]

    # 4. 加载 SFT 模型作为 ref
    print("\n[4/5] 加载 SFT 模型...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        SFT_MODEL_PATH,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    ref_model = AutoModelForCausalLM.from_pretrained(
        SFT_MODEL_PATH,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    # 5. DPO 训练（使用 HuggingFace TRL 库的 DPOTrainer）
    print("\n[5/5] 开始 DPO 训练...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=1e-5,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=50,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        fp16=True,
        report_to="none",
        remove_unused_columns=False,
    )

    # 使用 HFU TRL 的 DPO Trainer（如果安装了trl库）
    try:
        from trl import DPOTrainer

        dpo_trainer = DPOTrainer(
            model=model,
            ref_model=ref_model,
            args=training_args,
            train_dataset=train_formatted,
            eval_dataset=val_formatted,
            tokenizer=tokenizer,
            max_length=512,
            max_prompt_length=256,
        )

        dpo_trainer.train()

    except ImportError:
        # 如果没有 trl 库，使用简化版的 preference loss 训练
        print("  [注意] 未安装 trl 库，使用简化版 Preference Loss 训练")
        print("  安装方式: pip install trl")

        # 构建 preference 训练数据
        train_prompts = [item["prompt"] for item in train_data]
        train_chosen = [item["chosen"] for item in train_data]
        train_rejected = [item["rejected"] for item in train_data]

        # 构建 preference dataset
        from datasets import Dataset

        pref_dataset = Dataset.from_dict({
            "prompt": train_prompts,
            "chosen": train_chosen,
            "rejected": train_rejected,
        })

        # 简化版：直接用 chosen 作为正例训练
        # 这里只是占位，实际推荐安装 trl 使用标准 DPO
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=pref_dataset,
            tokenizer=tokenizer,
        )
        trainer.train()

    # 保存
    print("\n保存模型...")
    model.save_pretrained(str(OUTPUT_DIR / "final"))
    tokenizer.save_pretrained(str(OUTPUT_DIR / "final"))

    print(f"\n✅ DPO 训练完成！")
    print(f"   模型路径: {OUTPUT_DIR / 'final'}")


if __name__ == "__main__":
    main()
