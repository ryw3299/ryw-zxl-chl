# Skill: Definition

## 适用场景

- 学生问“什么是 X”“X 的定义是什么”“X 的概念是什么”
- 需要解释术语、概念、定理、方法名词
- 需要优先从课程材料中抽取原始定义并给出解释

## 推荐工具

- `内容获取工具`：从 `structured_content.pages` 或 `structured_content.sections` 精确找定义
- `知识匹配工具`：把问题中的关键词对齐到课程知识点
- `引用工具`：返回定义出处，尽量指向课件原文

## 回答策略

1. 先给出一句话定义。
2. 再补充 2 到 3 个关键点。
3. 结合课程语境举一个贴近教材的例子。
4. 如有必要，确认学生是否还需要更基础的解释。

## 禁止行为

- 不要给模糊定义或循环定义
- 不要脱离课程材料自行扩展太多课外内容
- 不要把多个概念混在一起解释
- 不要忽略课件里已有的定义

## 输入要求

- `question`
- `structured_content`
- `current_section_id` / `current_page`

## 输出要求

- `answer`
- `references`
- `matched_knowledge_points`
- `suggested_questions`
