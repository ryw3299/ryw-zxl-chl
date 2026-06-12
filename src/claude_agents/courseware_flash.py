#!/usr/bin/env python3
"""
courseware_flash.py — Courseware Flash 全自动 Agent 启动器

用法：
    python -m src.claude_agents.courseware_flash \\
        --instruction "帮我做一份材料力学第二章轴向拉压的课件" \\
        --source "第二章 拉伸、压缩1.pptx" \\
        --audience "大二自动化"

Agent 自主完成全部流程：
    源文件转换 → 生成 slide_plan → 验证 → 修复 → 渲染 → 检查 → 后处理 → 导出
Python 只负责解析参数、创建目录、启动 Agent、最终确认输出。
"""

import argparse
import asyncio
import io
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Windows 编码修复：强制 stdout/stderr 用 UTF-8，避免打印 Unicode 字符时 gbk 报错
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from dotenv import load_dotenv

# 项目根目录（从 src/claude_agents/ 上溯两级到 ChaoXingAgent/）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Standalone-script support (see narration_from_ppt.py for rationale).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 加载项目 .env，覆盖系统环境变量
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

from claude_sdk.infra.agent_factory import AgentFactory

PPT_MASTER_DIR = PROJECT_ROOT / "ppt-master"
COURSEWARE_FLASH_DIR = PPT_MASTER_DIR / "skills" / "courseware-flash"
PPT_MASTER_SCRIPTS_DIR = PPT_MASTER_DIR / "skills" / "ppt-master" / "scripts"

# 独立运行 workspace：把 Agent 运行目录隔离到仓库内部的独立目录
# 避免 Claude SDK 的 session 污染代码仓库根目录的 /resume
DEFAULT_WORKSPACE = PROJECT_ROOT / "ChaoXingAgentWorkspace"


def slugify(text: str) -> str:
    """把主题转成目录安全的 slug"""
    text = re.sub(r"[^\w\u4e00-\u9fff\s]", "", text)
    text = text.strip()[:40]
    text = text.replace(" ", "_")
    return text or "courseware"


def find_output_narrations(project_path: Path) -> dict[str, Path]:
    """查找项目目录下的 4 个档位讲稿文件，返回存在的文件映射。"""
    levels = ["A", "B", "C", "D"]
    result = {}
    for lvl in levels:
        path = project_path / f"narration_{lvl}.json"
        if path.exists():
            result[lvl] = path
    return result


def find_output_pptx(project_path: Path) -> Path | None:
    exports_dir = project_path / "exports"
    if exports_dir.exists():
        pptx_files = sorted(exports_dir.glob("*.pptx"))
        if pptx_files:
            return pptx_files[-1]
    return None


async def run_courseware_agent(
    instruction: str,
    source_path: str | None,
    audience: str,
    project_path: Path,
):
    """
    启动 courseware_flash agent，由 agent 自己完成从源文件转换到 PPTX 导出的全部流程。
    Python 不干预中间步骤。
    """
    claude_sdk_root = PROJECT_ROOT / "claude_sdk"

    agent = AgentFactory.create_agent(
        agent_name="courseware_flash",
        skills=["courseware_flash"],
        # 关键：cwd 必须使用本次运行目录，不要用代码仓库根目录
        # 否则 Claude SDK 的 session 会污染代码仓库的 /resume
        cwd=str(project_path),
        workspace=str(project_path),
        project_root=str(claude_sdk_root),
        provider="xfyun",
        tools=["Bash", "Read", "Edit", "Write", "Glob"],
        permission_mode="acceptEdits",
    )

    # 构建总控任务 prompt — agent 拿到后自己驱动整个 pipeline
    prompt_parts = [
        "你是 Courseware Flash 全自动课件生成 Agent。",
        "",
        f"用户需求：{instruction}",
    ]

    if source_path:
        prompt_parts.append(f"源文件路径：{source_path}")
    if audience:
        prompt_parts.append(f"目标受众：{audience}")

    prompt_parts.extend(
        [
            "",
            f"项目目录：{project_path}",
            f"项目根目录：{PROJECT_ROOT}",
            f"Courseware Flash 脚本目录：{COURSEWARE_FLASH_DIR / 'scripts'}",
            f"PPT Master 脚本目录：{PPT_MASTER_SCRIPTS_DIR}",
            "",
            "你必须从零开始亲自完成整个 PPTX 生成流程。不要只描述步骤，必须实际使用工具执行。",
            "",
            "完整流程如下：",
            "",
            "1. 如果提供了源文件路径，先检查文件是否存在。",
            "",
            "2. 调用源文件转换脚本（如果提供了源文件）：",
            f'   python "{COURSEWARE_FLASH_DIR / "scripts" / "auto_source_convert.py"}" "<source_path>" "{project_path}"',
            "   转换完成后，读取 {project_path}/sources/ 目录下的 .md 文件内容。",
            "",
            "3. 基于用户需求、目标受众和源文档内容，创建 slide_plan.json：",
            f"   写入路径：{project_path / 'slide_plan.json'}",
            "   格式必须严格遵守 slide_plan_schema.json，每个 slide 必须有 slide_id、slug、type、filename、title、rhythm 字段。",
            "   type 只能是：title_slide、chapter_transition、lesson_objectives、concept_explanation、comparison、classroom_question、summary_slide。",
            "   filename 格式为：{NN}_{type}.svg（NN 是两位数字序号）。",
            '   slug 是小写英文+数字+下划线，如 "title_slide"、"concept_explanation"。',
            "   不要在字符串值内部使用未转义的英文双引号，术语引用用中文引号或书名号。",
            "",
            "4. 验证 slide_plan.json：",
            f'   python "{COURSEWARE_FLASH_DIR / "scripts" / "validate_slide_plan.py"}" "{project_path}"',
            "   如果验证失败，必须阅读错误输出，然后 Read/Edit 修复 slide_plan.json，再重新运行验证。",
            "   每个错误最多修复重试 3 次，不允许跳过验证。",
            "",
            "5. 渲染 SVG：",
            f'   python "{COURSEWARE_FLASH_DIR / "scripts" / "render_from_plan.py"}" "{project_path}"',
            "   如果失败，诊断原因、修复问题、重试。",
            "",
            "6. 顺序运行后处理和导出脚本：",
            f'   python "{PPT_MASTER_SCRIPTS_DIR / "svg_quality_checker.py"}" "{project_path}"',
            f'   python "{PPT_MASTER_SCRIPTS_DIR / "total_md_split.py"}" "{project_path}"',
            f'   python "{PPT_MASTER_SCRIPTS_DIR / "finalize_svg.py"}" "{project_path}"',
            f'   python "{PPT_MASTER_SCRIPTS_DIR / "svg_to_pptx.py"}" "{project_path}"',
            "   每一步失败后必须诊断、修复、重试（最多 3 次）。",
            "",
            "7. PPTX 导出检查：",
            f"   确认 {project_path / 'exports'} 目录下存在 .pptx 文件。",
            "   如果不存在，回溯检查哪一步失败，修复后重新运行。",
            "",
            "8. 生成讲稿（基于 slide_plan.json 内容）：",
            "   PPTX 导出成功后，先 Read(slide_plan.json) 获取每页完整信息，",
            "   然后生成 4 个档位的讲稿 JSON 文件：",
            f"   - {project_path / 'narration_A.json'} — A档（最详细，~400字/页，完整展开+举例+互动）",
            f"   - {project_path / 'narration_B.json'} — B档（详细，~250字/页，充分讲解+适当举例）",
            f"   - {project_path / 'narration_C.json'} — C档（简要，~150字/页，要点清晰+少量展开）",
            f"   - {project_path / 'narration_D.json'} — D档（最略，~80字/页，只讲核心要点）",
            "",
            "   每个讲稿文件的 JSON 格式：",
            "   {",
            '     "deck_title": "课件标题",',
            '     "audience": "目标受众",',
            '     "detail_level": "A",',
            '     "total_slides": 14,',
            '     "slides": [',
            "       {",
            '         "slide_id": 1,',
            '         "topic": "页面标题（从 slide_plan 的 title 字段提取）",',
            '         "script": "完整的口头讲稿，口语化、自然流畅..."',
            "       }",
            "     ]",
            "   }",
            "",
            "   讲稿生成要求：",
            "   - script 用第一人称'我们''同学们'，营造课堂氛围",
            "   - 不要逐字念 slide_plan 上的 bullet 文字，要基于要点扩展讲解",
            "   - 适当使用类比、举例、反问等修辞手法",
            "   - 页与页之间自然过渡，前一页结尾为后一页铺垫",
            "   - 不同档位只在详细程度上区分，内容要点保持一致",
            "",
            "规则：",
            "- 你必须实际调用 Bash/Read/Edit/Write 工具。",
            "- 不要只回答计划或描述步骤。",
            "- 每一步失败后必须诊断、修复、重试，不要把失败交给用户。",
            "- 不要跳过任何失败步骤。",
            "- 最终回答必须给出 PPTX 文件路径、项目目录，以及 4 个讲稿文件路径。",
        ]
    )

    prompt = "\n".join(prompt_parts)

    print("[2/7 LLM 生成] Agent 正在自主完成全部流程...")
    await agent.start()
    try:
        response = await agent.ask_with_retry(prompt, timeout=1200)
        print(f"\n[Agent 完成]\n{response}\n")
    finally:
        await agent.close()


def main():
    parser = argparse.ArgumentParser(
        description="一键课件生成器 — Courseware Flash Agent Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python -m src.claude_agents.courseware_flash -i "材料力学第二章：轴向拉压" -a "大二自动化"
  python -m src.claude_agents.courseware_flash -i "英语Unit 3课件" -s "unit3_notes.docx" -a "大一英语"
        """,
    )
    parser.add_argument(
        "--instruction",
        "-i",
        required=True,
        help="教学主题/需求描述",
    )
    parser.add_argument(
        "--source",
        "-s",
        default=None,
        help="源文件路径 (PDF/PPTX/DOCX/XLSX/MD/TXT)",
    )
    parser.add_argument(
        "--audience",
        "-a",
        default="",
        help="目标受众",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(DEFAULT_WORKSPACE / "projects"),
        help=f"输出目录 (默认: {DEFAULT_WORKSPACE / 'projects'})",
    )

    args = parser.parse_args()

    # 创建项目目录
    # 使用 时间戳+UUID 命名，避免中文/特殊字符问题，便于追溯
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = f"{timestamp}_{uuid.uuid4().hex[:8]}"
    if args.output_dir == str(DEFAULT_WORKSPACE / "projects"):
        project_path = DEFAULT_WORKSPACE / "projects" / project_name
    else:
        # 用户显式指定了其他目录，尊重用户选择
        project_path = Path(args.output_dir) / project_name
    project_path.mkdir(parents=True, exist_ok=True)
    print(f"[项目目录] {project_path}")

    # 检查源文件（提前检查，避免 agent 跑空）
    if args.source and not os.path.exists(args.source):
        print(f"[错误] 源文件不存在: {args.source}", file=sys.stderr)
        sys.exit(1)

    # 启动 agent，由 agent 自主完成全部流程
    asyncio.run(
        run_courseware_agent(
            instruction=args.instruction,
            source_path=args.source,
            audience=args.audience,
            project_path=project_path,
        )
    )

    # Agent 完成后，最终检查输出
    pptx_path = find_output_pptx(project_path)
    narrations = find_output_narrations(project_path)

    if pptx_path:
        print(f"\n{'=' * 50}")
        print("✅ 课件生成成功！")
        print(f"📄 PPTX: {pptx_path}")
        if narrations:
            print("📜 讲稿文件：")
            for lvl in ["A", "B", "C", "D"]:
                if lvl in narrations:
                    print(f"   {lvl}档: {narrations[lvl]}")
                else:
                    print(f"   {lvl}档: ⚠️ 缺失")
        print(f"📁 项目目录: {project_path}")
        print(f"{'=' * 50}")
    else:
        print("\n⚠️ 未找到 PPTX 输出文件", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
