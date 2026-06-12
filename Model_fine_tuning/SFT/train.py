"""
SFT 微调训练脚本（分类头版本）
使用 Qwen2.5-1.7B + QLoRA，输出 4 分类概率 + expected_score

关键改进：
- 不再是 Causal LM（生成文本），而是 Sequence Classification
- 输出 4 个理解等级的 softmax 概率分布
- expected_score = Σ(prob_i × center_i)，得到 0-100 连续分数
- 同时输出 question_type（通过第二个分类头或多任务学习）

用法：
    python train.py
"""

import json
import torch
import torch.nn as nn
from pathlib import Path

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
from transformers import (
    AutoModel,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
    set_seed,
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from datasets import Dataset
import numpy as np

# ── 配置 ──────────────────────────────────────────────
set_seed(42)

MODEL_NAME = "Qwen/Qwen2.5-1.7B"
OUTPUT_DIR = Path("./outputs/sft_model")
DATA_DIR = Path("./data")

# 理解等级
LEVEL2ID = {"novice": 0, "beginner": 1, "intermediate": 2, "advanced": 3}
ID2LEVEL = {v: k for k, v in LEVEL2ID.items()}
LEVEL_CENTERS = [12.5, 38.0, 63.0, 88.0]  # 每个等级对应的分数中心

# 问题类型（7类）
QTYPE2ID = {
    "definition": 0, "procedure": 1, "reasoning": 2,
    "comparison": 3, "derivation": 4, "application": 5, "example": 6,
}
NUM_QTYPES = len(QTYPE2ID)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[设备] {device}")


# ── 自定义模型：Qwen + 双分类头 ─────────────────────────
class QwenClassificationModel(nn.Module):
    """
    Qwen 基础模型 + 双分类头

    架构：
    Qwen2.5-1.7B Base Model (冻结 / LoRA微调)
           ↓
    Mean Pooling (序列 → 单向量)
           ↓
    ├── 理解等级头 (4分类) → softmax → prob[4]
    └── 问题类型头 (7分类) → softmax → prob[7]

    推理时：
    - prob_levels = softmax(level_logits) → [0.7, 0.2, 0.08, 0.02]
    - expected_score = Σ(prob_i × center_i)
                    = 0.7×12.5 + 0.2×38 + 0.08×63 + 0.02×88
                    = 23.15
    """

    def __init__(self, base_model_name: str, num_labels: int = 4, num_qtypes: int = 7):
        super().__init__()
        # 4bit 量化加载基础模型
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

        # LoRA adapter
        lora_config = LoraConfig(
            r=32,
            lora_alpha=64,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            lora_dropout=0.05,
            bias="none",
            task_type=TaskType.SEQ_CLS,
        )
        self.base_model = get_peft_model(self.base_model, lora_config)

        # 分类头维度 = 隐藏层维度
        hidden_size = self.base_model.config.hidden_size

        # 理解等级分类头（4分类）
        self.level_head = nn.Linear(hidden_size, num_labels, bias=True)

        # 问题类型分类头（7分类）
        self.qtype_head = nn.Linear(hidden_size, num_qtypes, bias=True)

        # 初始化
        self._init_weights()

    def _init_weights(self):
        nn.init.xavier_uniform_(self.level_head.weight)
        nn.init.xavier_uniform_(self.qtype_head.weight)

    def forward(self, input_ids, attention_mask, **kwargs):
        # 通过 Qwen backbone
        outputs = self.base_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        # Mean Pooling：序列向量 → 单向量
        last_hidden = outputs.hidden_states[-1]  # (batch, seq_len, hidden)
        mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
        sum_hidden = torch.sum(last_hidden * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        pooled = sum_hidden / sum_mask  # (batch, hidden)

        # 两个分类头的 logits
        level_logits = self.level_head(pooled)    # (batch, 4)
        qtype_logits = self.qtype_head(pooled)     # (batch, 7)

        return {
            "level_logits": level_logits,
            "qtype_logits": qtype_logits,
            "pooled_hidden": pooled,
        }


# ── 数据准备 ──────────────────────────────────────────
def load_sft_data(split: str):
    path = DATA_DIR / f"{split}_sft.jsonl"
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def build_prompt_from_item(item: dict) -> str:
    """从 item 构建 prompt"""
    messages = item["messages"]
    parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            parts.append(f"<|im_start|>system\n{content}<|im_end|>")
        elif role == "user":
            parts.append(f"<|im_start|>user\n{content}<|im_end|>")
        elif role == "assistant":
            parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
    return "".join(parts)


def parse_label(item: dict):
    """解析标签"""
    messages = item["messages"]
    assistant_msg = next((m["content"] for m in messages if m["role"] == "assistant"), "")
    qtype = "definition"
    for qt in QTYPE2ID:
        if qt in assistant_msg:
            qtype = qt
            break
    return LEVEL2ID[item["understanding_label"]], QTYPE2ID[qtype]


# ── Metrics ──────────────────────────────────────────
def compute_metrics_level(eval_pred):
    """计算理解等级指标"""
    logits, labels = eval_pred
    preds = logits.argmax(axis=-1)
    acc = (preds == labels).mean()
    return {"accuracy": float(acc)}


def compute_metrics_qtype(eval_pred):
    """计算问题类型指标"""
    logits, labels = eval_pred
    preds = logits.argmax(axis=-1)
    acc = (preds == labels).mean()
    return {"accuracy": float(acc)}


def preprocess_level_logits(logits, labels):
    """预处理 level logits 用于 metrics"""
    probs = torch.softmax(torch.tensor(logits), dim=-1)
    expected_scores = np.dot(probs, LEVEL_CENTERS)
    return probs, expected_scores


# ── 训练主流程 ─────────────────────────────────────────
def main():
    print("=" * 60)
    print("SFT 微调训练（分类头版本）")
    print("Qwen2.5-1.7B + QLoRA + 双分类头")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/5] 加载数据...")
    train_data = load_sft_data("train")
    val_data = load_sft_data("val")
    print(f"  Train: {len(train_data)} | Val: {len(val_data)}")

    # 2. Tokenizer
    print("\n[2/5] 加载 Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 3. 构建数据集
    print("\n[3/5] 构建数据集...")

    train_texts = [build_prompt_from_item(item) for item in train_data]
    val_texts = [build_prompt_from_item(item) for item in val_data]
    train_labels = [parse_label(item) for item in train_data]
    val_labels = [parse_label(item) for item in val_data]

    train_level_labels = [l[0] for l in train_labels]
    train_qtype_labels = [l[1] for l in train_labels]
    val_level_labels = [l[0] for l in val_labels]
    val_qtype_labels = [l[1] for l in val_labels]

    train_enc = tokenizer(
        train_texts,
        truncation=True,
        max_length=512,
        padding=False,
    )
    val_enc = tokenizer(
        val_texts,
        truncation=True,
        max_length=512,
        padding=False,
    )

    # 包装成 Dataset（支持两个 label）
    class MultiLabelDataset(Dataset):
        def __init__(self, encodings, level_labels, qtype_labels):
            self.encodings = encodings
            self.level_labels = level_labels
            self.qtype_labels = qtype_labels

        def __len__(self):
            return len(self.level_labels)

        def __getitem__(self, idx):
            item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
            item["labels"] = torch.tensor(self.level_labels[idx])
            item["qtype_labels"] = torch.tensor(self.qtype_labels[idx])
            return item

    train_ds = MultiLabelDataset(train_enc, train_level_labels, train_qtype_labels)
    val_ds = MultiLabelDataset(val_enc, val_level_labels, val_qtype_labels)
    print(f"  Dataset 构建完成")

    # 4. 模型
    print("\n[4/5] 加载模型...")
    model = QwenClassificationModel(MODEL_NAME, num_labels=4, num_qtypes=7)
    model.print_trainable_parameters()

    # 冻结 base model 的原始参数，只训练 LoRA + 分类头
    for name, param in model.base_model.named_parameters():
        if "lora" not in name.lower() and "classifier" not in name.lower():
            param.requires_grad = False

    # 统计可训练参数
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  可训练参数: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # 5. 训练
    print("\n[5/5] 开始训练...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=16,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=50,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_accuracy",
        greater_is_better=True,
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",
        dataloader_num_workers=4,
        remove_unused_columns=False,
    )

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics_level,
    )

    trainer.train()

    # 保存
    print("\n保存模型...")
    trainer.save_model(str(OUTPUT_DIR / "final"))
    tokenizer.save_pretrained(str(OUTPUT_DIR / "final"))

    # 保存标签映射
    with open(OUTPUT_DIR / "final" / "label_mapping.json", "w", encoding="utf-8") as f:
        json.dump({
            "level2id": LEVEL2ID,
            "id2level": ID2LEVEL,
            "level_centers": LEVEL_CENTERS,
            "qtype2id": QTYPE2ID,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ SFT 训练完成！")
    print(f"   模型路径: {OUTPUT_DIR / 'final'}")
    print(f"\n   推理时输出格式：")
    print(f"   - level_prob: [p_novice, p_beginner, p_intermediate, p_advanced]")
    print(f"   - expected_score = Σ(prob_i × center_i) → 0-100 连续分数")
    print(f"   - question_type_prob: [p_definition, p_procedure, ...]")


if __name__ == "__main__":
    main()
