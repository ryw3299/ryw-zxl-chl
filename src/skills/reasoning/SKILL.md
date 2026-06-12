# Skill: Reasoning

## 适用场景

- 学生问“为什么”“怎么会这样”“X 为什么会导致 Y”
- 需要解释原理、机制、因果关系
- 需要把课程中的推导链路讲清楚

## 推荐工具

- `内容获取工具`：获取原理相关讲解
- `脚本获取工具`：获取 `lesson_script` 中的讲解段落
- `知识匹配工具`：匹配因果链条中的关键知识点

## 回答策略

1. 先说结论。
2. 再按因果顺序拆成 2 到 3 层。
3. 每一步都给出依据。
4. 回到课程材料中的具体章节或教师讲解。

## 禁止行为

- 不要只给结论不解释原因
- 不要跳步推导
- 不要把常识当成课程结论
- 不要编造课外原理

## 输入要求

- `question`
- `structured_content`
- `lesson_script`
- `current_section_id` / `current_page`

## 输出要求

- `answer`
- `references`
- `matched_knowledge_points`
- `suggested_questions`
