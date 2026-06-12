# PPT Master 课件链路接入总结

## 接入目标

教师端不再走旧的 `parse -> generateScript -> renderPPT` 主链路，改为接入 PPT Master 新链路：

1. 上传课件资料。
2. 后端生成 `slide_plan.json`。
3. 教师在前端编辑 `slide_plan.json`。
4. 教师选择 `Flash` 或 `Pro` 模式渲染 PPT。
5. 后端同步生成 `narration_A/B/C/D.json` 四档讲稿。
6. 学生提问后，QA 返回的 `recommendedNarrationLevel` 可用于读取对应讲稿。

## 后端修改

### 数据库字段

在 `lessons` 表新增字段：

- `courseware_project_dir`：PPT Master 项目目录。
- `slide_plan_path`：`slide_plan.json` 文件路径。
- `slide_plan_json`：可编辑的 slide plan 内容。
- `courseware_status`：新课件链路状态。
- `courseware_render_mode`：`flash` 或 `pro`。
- `narration_paths`：四档讲稿路径 JSON。
- `courseware_error`：失败原因。

`src/api/models/database.py` 已补充兼容迁移逻辑，旧库启动时会自动补列。

### 新增接口

- `POST /api/v1/lesson/courseware/slidePlanUpload`
  上传课件并启动 slide plan 生成任务。

- `POST /api/v1/lesson/courseware/status`
  查询 slide plan / PPT 渲染状态。

- `POST /api/v1/lesson/courseware/slidePlan`
  保存教师编辑后的 `slide_plan.json`。

- `POST /api/v1/lesson/courseware/render`
  按 `flash` 或 `pro` 模式渲染 PPT，并生成四档讲稿。

- `GET /api/v1/lesson/narration/{lessonId}/{level}`
  读取 `A/B/C/D` 某一档讲稿。

### 服务层

`src/api/services/lesson_service.py` 新增：

- `create_courseware_slide_plan_task`
- `run_courseware_slide_plan_task`
- `get_courseware_status`
- `update_courseware_slide_plan`
- `start_courseware_render`
- `run_courseware_render_task`
- `get_courseware_narration`

内部调用已有 agent 入口：

- `run_courseware_flash_slideplan`
- `run_courseware_flash_render`
- `run_courseware_pro_render`
- `run_courseware_flash_narration`

## 前端修改

### 教师端

`frontend/src/views/TeacherUpload.vue` 已改为新流程：

- 第一步：上传课件。
- 第二步：生成课件规划 `slide_plan.json`。
- 第三步：选择 `Flash` / `Pro` 渲染 PPT。
- 右侧新增“课件规划”Tab，可直接编辑 JSON。
- 发布仍复用原有 `publishLesson`。

### API 封装

`frontend/src/api/lesson.js` 新增：

- `generateCoursewareSlidePlan`
- `getCoursewareStatus`
- `updateCoursewareSlidePlan`
- `renderCoursewarePpt`
- `getLessonNarration`

### 学生端动态讲稿

- `frontend/src/api/qa.js` 透出 `recommendedNarrationLevel`。
- `frontend/src/components/ChatBox.vue` 将该字段传给播放器。
- `frontend/src/views/LessonPlayer.vue` 根据推荐档位尝试读取对应讲稿，并在 AI 建议区域提示当前推荐讲稿档位。

## 验证

- 后端语法检查通过：
  `python -m py_compile src/api/models/tables.py src/api/models/database.py src/api/services/lesson_service.py src/api/routers/lesson.py`

- 后端导入和数据库初始化通过：
  `from src.api.models.database import init_db; init_db()`

- 前端构建通过：
  `npm run build`
