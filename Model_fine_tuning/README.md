# 认知状态估计 + 强化学习自适应问答系统

## 目录结构

```
Model_fine_tuning/
├── README.md
├── SFT/                          # 第一阶段：认知状态估计（SFT微调）
│   ├── prepare_data.py           # SFT 数据准备
│   ├── train.py                  # SFT 训练脚本（分类头版本）
│   ├── inference.py               # SFT 推理脚本
│   └── data/                     # 输出的 SFT 格式数据
└── RL/                          # 第二阶段：DPO 强化学习（策略优化）
    ├── prepare_data.py           # DPO 偏好数据生成
    ├── train.py                 # DPO 训练脚本
    ├── inference.py             # DPO 推理脚本
    └── data/                    # 输出的 DPO 格式数据
```

## 模型说明

### SFT 模型（认知状态估计）

**任务**：给定学生问题 + RAG上下文 + 对话历史，输出认知水平

**输入**：
```
学生问题："什么是卷积神经网络？"
RAG上下文："卷积神经网络是深度学习的一种架构..."
历史：无（第一轮提问）
```

**输出**：
```
{
    "level": "novice",
    "level_probs": [0.70, 0.20, 0.08, 0.02],
    "expected_score": 23.15,
    "question_type": "definition",
    "qtype_probs": [0.65, 0.10, 0.15, ...]
}
```

---

### DPO 模型（回答策略优化）

**任务**：给定认知等级和问题类型，决定怎么回答

**输入**（来自SFT模型的输出）：
```
{
    "level": "novice",
    "expected_score": 23.15,
    "question_type": "definition"
}
```

**输出**（回答策略）：
```
{
    "detail_level": 5,           # 1-5级，5最详细
    "need_example": true,        # 需要带例子
    "need_background": true,     # 需要背景知识
    "need_derivation": false,    # 不需要推导
    "response_length": "非常详细"
}
```

---

## 完整推理流程（两次模型调用）

```
学生提问
    │
    ▼
┌─────────────────────────────────┐
│  第1次推理：SFT 模型            │
│  输入：问题 + RAG + 历史        │
│  输出：认知分数(23.15)          │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  第2次推理：DPO 模型            │
│  输入：{level, score, qtype}   │
│  输出：回答策略                  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Agent：根据策略生成回答         │
│  detail=5, need_example=true... │
└─────────────────────────────────┘
    │
    ▼
用户反馈 → DPO 持续优化
```

## 训练流程

```bash
# ========== 第一阶段：SFT ==========
cd Model_fine_tuning/SFT

# 1. 准备 SFT 数据
python prepare_data.py

# 2. 训练 SFT 模型（需要 GPU）
python train.py

# 3. 测试 SFT 推理
python inference.py --question "什么是卷积神经网络？"

# ========== 第二阶段：DPO ==========
cd ../RL

# 1. 生成偏好数据
python prepare_data.py

# 2. DPO 训练（在 SFT 基础上）
python train.py

# 3. 测试 DPO 推理
python inference.py --level novice --qtype definition
```

## 依赖

```bash
pip install transformers peft bitsandbytes accelerate trl
pip install datasets torch
```

## 注意事项

- 训练需要 GPU，Qwen2.5-1.7B + QLoRA 需要约 4GB 显存
- DPO 训练需要安装 `trl` 库：`pip install trl`
- 推理可以在 CPU 上运行（速度较慢）
