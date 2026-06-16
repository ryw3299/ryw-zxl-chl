# Debug Session: profile-multiturn-flow [OPEN]

## Goal
- 验证学生画像初始化是否能在 Dify chatflow 中从 `false` 分支继续追问，随后在补充信息后进入 `true` 分支。
- 验证多轮过程中 `conversation_id` 是否持续复用。
- 验证仅在 `true` 分支时是否成功写入 `student_profile`，以及画像生成日志是否符合当前实现。

## Scope
- 仅做运行时验证与证据收集。
- 本阶段不修改业务逻辑。

## Hypotheses
1. 第 1 轮会因为缺少 `learning_situation` 等关键字段走 `false` 分支，并返回追问文案。
2. 只要第 2 轮带上第 1 轮返回的 `conversation_id`，chatflow 会基于会话变量补齐信息并有机会进入 `true` 分支。
3. `true` 分支返回的 `answer` 仍然可能包含 `<think>` 包裹，但当前解析逻辑应能提取出最终 JSON。
4. `profile_service.init_profile()` 只有在 `profile_ready=true` 时才会写入 `student_profile`，`false` 时不会生成画像记录到该表。
5. 即使 `false` 不落 `student_profile`，当前实现仍会写入 `profile_generation_record` 调用日志。

## Planned Steps
1. 用同一个 `user_id` 发起第 1 轮，记录 `profile_ready`、`frontend_message`、`conversation_id`。
2. 用第 1 轮的 `conversation_id` 发起第 2 轮，补充 `learning_situation` 等缺失字段。
3. 检查第 2 轮是否进入 `true` 分支。
4. 检查数据库中 `student_profile` 与 `profile_generation_record` 的写入结果。

## Evidence
- 第 1 轮使用不完整信息调用，返回 `profile_ready=false`，并返回追问文案与 `conversation_id=cfccff61-9e5e-4585-984f-19adb2e6b87a`。
- 第 2 轮带上同一个 `conversation_id` 并补充 `learning_situation` 后，返回 `profile_ready=true`，`profile_type=initial_student_profile`。
- 第 1 轮后 `student_profile` 数量保持不变；第 2 轮后 `student_profile` 数量从 1 增加到 2，新增画像 `id=9`。
- 第 2 轮最新 `profile_generation_record` 显示 `profile_ready=true`、`profile_id=9`、`conversation_id=cfccff61-9e5e-4585-984f-19adb2e6b87a`。
- 流式模式下本次验证未再出现阻塞模式中的 `504 Gateway Timeout`。

## Conclusion
- 假设 1、2、4、5 已被验证；多轮对话从 `false -> true` 可以正常跑通，且 `true` 分支会写入 `student_profile`。
- 通过将 Dify 调用切换为 `streaming` 并在后端拼接 `answer`，当前已绕过此前阻塞模式下的超时问题。
