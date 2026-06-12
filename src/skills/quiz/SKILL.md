# Skill: Quiz

## 适用场景

- 学生进入练习模式
- 学生请求测验或练习题
- 需要用提问检查学生理解程度

## 推荐工具

- `内容获取工具`：找适合出题的课程内容
- `题目生成工具`：根据知识点生成题目
- `知识匹配工具`：对齐当前学习进度
- `历史工具`：参考历史答题情况

## 回答策略

1. 先确认练习范围。
2. 题目由易到难。
3. 混合选择、填空、判断、简答等题型。
4. 学生答完后给即时反馈。
5. 记录薄弱知识点。

## 禁止行为

- 不要出超纲题
- 不要一次给太多题
- 不要只给答案不解释
- 不要忽略学习进度

## 输入要求

- `question`
- `structured_content`
- `current_section_id` / `current_page`
- `history_qa`

## 输出要求

- `answer`
- `question_type`: `quiz`
- `understanding_level`
- `suggested_questions`
