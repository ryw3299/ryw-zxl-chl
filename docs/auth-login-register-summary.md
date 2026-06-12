# 知微智课登录注册功能修改总结

## 修改目标

为项目增加一套简单可用的本地登录、注册功能，并把产品名称统一调整为“知微智课”。前端登录界面采用偏高级、简约的桌面端视觉风格，进入 PC 端页面前需要先完成登录。

## 后端改动

- 新增用户密码字段：在 `src/api/models/tables.py` 的 `User` 模型中加入 `password_hash`，用于保存本地账号密码哈希。
- 兼容已有数据库：在 `src/api/models/database.py` 中增加初始化时的字段检查逻辑，已有开发库缺少 `password_hash` 时会自动补字段。
- 新增认证服务：新增 `src/api/services/auth_service.py`，负责注册、登录、密码哈希校验、token 查询用户。
- 教师 / 学生账号分离：注册接口现在只允许创建学生账号；教师账号由系统预置，不在前端和文档中展示账号密码，并且登录时会校验所选入口身份。
- 新增认证接口：新增 `src/api/routers/auth.py`。
  - `POST /api/v1/auth/register`：注册本地账号。
  - `POST /api/v1/auth/login`：账号密码登录。
  - `GET /api/v1/auth/me`：根据 token 获取当前用户。
- 接入应用路由：在 `src/api/app.py` 注册认证路由。
- 项目名调整：在 `src/api/config.py` 中将后端项目名改为“知微智课”。

## 前端改动

- 新增认证 API：新增 `frontend/src/api/auth.js`，封装登录、注册、获取当前用户接口。
- 调整用户状态：更新 `frontend/src/store/userStore.js`，支持保存 `userName`、`schoolId`、`role`、`token`，并完善退出登录清理逻辑。
- 移除自动演示登录：更新 `frontend/src/main.js`，不再启动时自动写入演示登录态。
- 增加登录路由和鉴权守卫：更新 `frontend/src/router/index.js`。
  - 新增 `/login` 页面。
  - PC 端页面需要登录后访问。
  - 未登录访问 PC 页面会跳转到 `/login?returnUrl=...`。
  - 已登录访问登录页会跳回默认首页。
- 重做登录注册页面：更新 `frontend/src/views/Login.vue`。
  - 登录 / 学生注册双模式切换。
  - 登录支持学生入口和教师入口，不展示默认教师账号密码。
  - 注册支持姓名、账号、密码、确认密码，固定创建学生账号。
  - 视觉风格为深色品牌区 + 白色表单区，面向桌面端做了更简约的布局。
- 调整 PC 端框架：更新 `frontend/src/views/PcLayout.vue`。
  - 产品名改为“知微智课”。
  - 用户区显示当前用户名。
  - 原演示切换角色按钮改为退出登录。
- 调整应用壳样式：更新 `frontend/src/App.vue`，为登录页提供独立的全屏容器样式。
- 调整前端项目名：更新 `frontend/index.html` 和 `frontend/vite.config.js` 中的标题与 PWA 名称。

## 登录流程

1. 用户访问 PC 页面。
2. 如果本地没有 token，路由守卫跳转到 `/login`。
3. 用户可以选择学生登录、教师登录或学生注册。
4. 学生注册只能创建学生账号；教师使用系统预置账号登录，账号密码不在页面中展示。
5. 登录或注册成功后，前端保存 token 和用户信息。
6. 页面跳回原本要访问的地址，学生默认是 `/pc/home`，教师默认是 `/pc/teacher/upload`。
7. 用户点击右上角退出登录后，清空登录态并回到 `/login`。

## 已完成验证

- 前端构建已通过：`npm.cmd run build`。
- 后端认证接口单测已通过：`.venv\Scripts\python.exe -m pytest tests\api\test_auth_endpoints.py`，结果为 `7 passed`。
- 已确认 `/login` 页面可以在本地开发服务中渲染。

按要求已停止继续做完整浏览器交互测试，因此没有继续跑注册后跳转、退出登录等端到端流程。

## 涉及的主要文件

- `src/api/models/tables.py`
- `src/api/models/database.py`
- `src/api/services/auth_service.py`
- `src/api/routers/auth.py`
- `src/api/app.py`
- `src/api/config.py`
- `tests/api/test_auth_endpoints.py`
- `frontend/src/api/auth.js`
- `frontend/src/store/userStore.js`
- `frontend/src/main.js`
- `frontend/src/router/index.js`
- `frontend/src/views/Login.vue`
- `frontend/src/views/PcLayout.vue`
- `frontend/src/App.vue`
- `frontend/index.html`
- `frontend/vite.config.js`
