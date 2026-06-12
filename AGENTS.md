# AGENTS.md

This file is for non-Claude coding agents working in this repository. Treat it as the canonical agent instruction file for this worktree.

## Current mode

The project is in demo/presentation mode. Prefer frontend-visible flow and visual polish over complete backend correctness. Mock data, hardcoded values, and stub implementations are acceptable when they make the demo clearer.

Unless the user explicitly says to modify the teacher side, treat PC frontend requests as student-side work. Do not change teacher workflows or teacher navigation when the user is discussing student learning pages.

## Run commands

```powershell
# Windows one-click local dev
.\start.bat   # backend 127.0.0.1:8001, frontend 127.0.0.1:3000
.\stop.bat

# Manual frontend
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
npm run build

# Manual backend
uv sync
$env:DEBUG="true"
uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8001
```

## Frontend notes

- PC shell sidebar lives in `frontend/src/views/PcLayout.vue`. It has two nav groups:
  - "教学工作" (teacher): `/pc/teacher/home`, `/pc/teacher/upload`, `/pc/teacher/resources`
  - "学习中心" (student): `/pc/home`, `/pc/my-courses`, `/pc/resources`
- Role-based routing: default home redirects to `/pc/teacher/home` for teachers, `/pc/home` for students. Configured in `frontend/src/router/index.js`.
- `/pc/my-courses` is the student's 智课 page, implemented in `frontend/src/views/MyCourses.vue`. Layout: top title/search/sort controls, a "正在学习" three-card grid, and a "已学完" list.
- `/pc/teacher/home` is the teacher dashboard in `frontend/src/views/TeacherHome.vue`.
- `/pc/home` (student home) is `frontend/src/views/Home.vue`.

## Docs

- `docs/student_backend_integration.md` -- backend engineers integrating the student agent
- `docs/courseware-integration-summary.md` -- PPT Master courseware pipeline
- `docs/student_contract.md` -- student-agent request/response schema contract
- `docs/setup_guide.md` -- full environment setup from scratch
- `docs/api_design.md` -- API design reference

## Safety

- Do not commit runtime data such as `data/runtime/*.db`.
- Do not push or force-push unless the user explicitly asks.
