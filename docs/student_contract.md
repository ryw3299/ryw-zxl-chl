### Student Contract

本文定义 student 端第一版最小 contract。目标是先跑通一轮“提问 -> 回答 -> 判断 -> 下一步动作”的闭环，再逐步扩展。

### 设计原则

- 先定义最小闭环，不追求一次设计完整系统。
- 先保证字段可执行，再讨论更复杂的 agent 能力。
- 输出中的教学动作必须可被后端和前端消费，不能是自由文本建议。
- 检索结果、问答历史、最终响应都使用稳定结构，避免后续模块各自定义。

### StudentAgentRequest

`StudentAgentRequest` 表示 student agent 单轮输入。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `course_id` | `str \| None` | 课程标识；可从 `structured_content`、`session`、`progress` 或 `turn_context` 补齐。 |
| `lesson_id` | `str` | 当前课时标识。 |
| `session_id` | `str` | 当前学习会话标识。 |
| `question` | `str` | 学生本轮提问。 |
| `structured_content` | `dict \| None` | 教师链路产出的结构化课程内容；旧路径的主要知识底座。 |
| `lesson_script` | `dict \| None` | 教师链路产出的讲稿，可选。 |
| `turn_context` | `dict \| None` | 后端预组装的一轮上下文；新路径可用它承载检索、历史和当前教学位置。 |
| `session` | `dict \| None` | 当前学习会话快照。 |
| `progress` | `dict \| None` | 当前学习进度快照。 |
| `current_section_id` | `str \| None` | 当前讲到的 section。 |
| `current_page` | `int \| None` | 当前讲到的 page。 |
| `current_script_block_id` | `str \| None` | 当前讲到的讲稿块。 |
| `history_qa` | `list[dict]` | 最近几轮问答历史。 |
| `student_profile` | `dict` | 可选学生画像或偏好信号。 |

校验约束：

- `structured_content.lesson_id` 必须等于 `lesson_id`。
- `lesson_script.metadata.lesson_id` 如存在，必须等于 `lesson_id`。
- `session` 和 `progress` 如存在，必须与请求的 `lesson_id`、`session_id` 一致。

### StudentAgentResponse

`StudentAgentResponse` 表示 student agent 单轮输出。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `answer` | `str` | 学生直接看到的回答。 |
| `references` | `list[dict]` | 回答依据的来源列表。 |
| `question_type` | `str` | 问题类型，固定为 `definition / reasoning / procedure / example / comparison / summary / chitchat / unknown`。 |
| `understanding_level` | `str \| None` | 学生理解程度。当前固定为 `full / partial / none`。 |
| `recommended_narration_level` | `str \| None` | 推荐讲稿档位，固定为 `A / B / C / D`。 |
| `next_action` | `str \| None` | 下一步教学动作。当前固定为 `resume / supplement_then_resume / reteach_slowly / trigger_game`。 |
| `reason` | `str` | 给出 `next_action` 的原因。 |
| `matched_knowledge_points` | `list[dict]` | 匹配到的知识点、置信度和来源位置。 |
| `matched_section_id` | `str \| None` | 本轮回答主要匹配的 section。 |
| `matched_page` | `int \| None` | 本轮回答主要匹配的 page。 |
| `matched_script_block_id` | `str \| None` | 本轮回答主要匹配的讲稿块。 |
| `target_section_id` | `str \| None` | 下一步推荐跳转的 section。 |
| `target_page` | `int \| None` | 下一步推荐跳转的 page。 |
| `target_script_block_id` | `str \| None` | 下一步推荐跳转的讲稿块。 |
| `suggested_questions` | `list[str]` | 推荐学生继续追问的问题。 |
| `updated_session` | `dict \| None` | 本轮之后的会话快照。 |
| `updated_progress` | `dict \| None` | 本轮之后的进度快照。 |
| `qa_record` | `dict \| None` | 本轮问答的可持久化记录。 |
| `metadata` | `dict` | 调试和扩展信息；包含 `tool_trace`，触发互动题时包含 `game`。 |

### RetrievedContextItem

`RetrievedContextItem` 是检索模块返回给 agent 的统一上下文结构。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source` | `str` | 来源类型，当前约定为 `page / section / script_block`。 |
| `source_id` | `str` | 来源对象的唯一 ID。 |
| `title` | `str` | 该内容标题。 |
| `text` | `str` | 提供给 LLM 的正文内容。 |
| `section_id` | `str \| None` | 所属 section。 |
| `page` | `int \| None` | 所属页码。 |
| `score` | `float \| None` | 检索相关度分数；精确获取时可为空。 |

### QAHistoryItem

`QAHistoryItem` 是 student agent 读取历史时使用的最小结构。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `qa_record_id` | `str \| None` | 历史问答记录标识。 |
| `question` | `str` | 历史问题。 |
| `answer` | `str` | 历史回答。 |
| `understanding_level` | `str \| None` | 历史理解程度。 |
| `current_section_id` | `str \| None` | 当时所在 section。 |
| `current_page` | `int \| None` | 当时所在 page。 |

### QARecord

`QARecord` 是本轮问答写回存储层时的最小结构。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `qa_record_id` | `str` | 问答记录标识。 |
| `course_id` | `str \| None` | 课程标识。 |
| `session_id` | `str` | 学习会话标识。 |
| `lesson_id` | `str` | 课时标识。 |
| `question` | `str` | 学生问题。 |
| `answer` | `str` | 系统回答。 |
| `understanding_level` | `str \| None` | 理解程度。 |
| `references` | `list[dict]` | 引用来源。 |
| `current_section_id` | `str \| None` | 当前 section。 |
| `current_page` | `int \| None` | 当前 page。 |

### 当前冻结枚举

- `understanding_level`: `full / partial / none`
- `next_action`: `resume / supplement_then_resume / reteach_slowly / trigger_game`
- `question_type`: `definition / reasoning / procedure / example / comparison / summary / chitchat / unknown`
- `recommended_narration_level`: `A / B / C / D`

当前阶段不扩展新的枚举值。后续如需扩展，优先增加 `target_*` 和 `reason` 等参数，而不是先增加大量动作名称。

### Game Metadata

当 `next_action = "trigger_game"` 时，agent 会优先调用 `game` 工具。结构化题目放在 `metadata["game"]`，用于前端渲染交互题。

`metadata["game"]` 当前字段：

- `game_type`: 固定为 `multiple_choice`
- `prompt`: 题干
- `choices`: 选项列表
- `correct_index`: 正确选项下标
- `correct_choice`: 正确选项文本
- `explanation`: 解析
- `references`: 题目依据

`answer` 仍应包含学生可直接看到的题面；`metadata["tool_trace"]` 用于调试和审计。

### 数据流

student 端最小数据流如下：

1. 后端读取教师链路产物中的 `structured_content` 和 `lesson_script`。
2. 后端结合 `turn_context`，或结合 `session / progress / history_qa` 组装 `StudentAgentRequest`。
3. student agent 检索上下文并生成 `StudentAgentResponse`。
4. 后端消费 `answer / references / next_action / suggested_questions / qa_record`。
5. 后端据此更新会话状态，进入下一轮交互。
