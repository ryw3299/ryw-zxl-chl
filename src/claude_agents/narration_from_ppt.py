#!/usr/bin/env python3
"""
narration_from_ppt.py — 讲稿自动生成器（基于 slide_plan.json）

用法：
    python -m src.claude_agents.narration_from_ppt -s "project_path/slide_plan.json" -a "大二工科"
    python -m src.claude_agents.narration_from_ppt -s "project_path/slide_plan.json" -o "./output_dir"

输入：slide_plan.json（courseware_flash 生成的课件计划）
输出：同目录下 4 个档位讲稿 JSON（narration_A.json ~ narration_D.json）
"""

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

# Windows 编码修复：强制 stdout/stderr 用 UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from dotenv import load_dotenv

# 项目根目录（从 src/claude_agents/ 上溯两级到 ChaoXingAgent/）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# When invoked as a script (``python src/claude_agents/narration_from_ppt.py``),
# the project root may not be on sys.path.  Adding it as a no-op when already
# present keeps the standalone script path runnable without polluting normal
# ``import src.claude_agents.narration_from_ppt`` flows.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

from claude_sdk.infra.agent_factory import AgentFactory


def load_slide_plan(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def infer_output_dir(slide_plan_path: Path) -> Path:
    """讲稿输出到 slide_plan.json 同目录。"""
    return slide_plan_path.parent


async def run_narration_agent(
    slide_plan_path: Path,
    audience: str,
    output_dir: Path,
):
    """启动 narration agent，由 agent 基于 slide_plan.json 生成 4 个档位讲稿。"""
    claude_sdk_root = PROJECT_ROOT / "claude_sdk"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 预读 slide_plan，把关键信息注入 prompt（减少 agent 的 Read 次数）
    plan = load_slide_plan(slide_plan_path)
    deck_title = plan.get("deck_title", "未命名课件")
    slide_count = plan.get("slide_count", len(plan.get("slides", [])))
    slides_summary = []
    for s in plan.get("slides", []):
        slides_summary.append(f"  Slide {s.get('slide_id')}: [{s.get('type')}] {s.get('title', '无标题')}")

    agent = AgentFactory.create_agent(
        agent_name="narration_from_ppt",
        skills=["narration_from_ppt"],
        cwd=str(PROJECT_ROOT),
        workspace=str(output_dir),
        project_root=str(claude_sdk_root),
        provider="xfyun",
        tools=["Read", "Write", "Edit"],
        permission_mode="acceptEdits",
    )

    # agent 任务：基于 slide_plan.json 生成 4 个档位讲稿
    prompt_parts = [
        "你是课件讲稿生成 Agent。",
        "",
        f"课件标题：{deck_title}",
        f"总页数：{slide_count}",
        f"目标受众：{audience or '未指定，按通用大学生水平撰写'}",
        f"slide_plan.json 路径：{slide_plan_path}",
        f"讲稿输出目录：{output_dir}",
        "",
        "课件页面概览：",
        *slides_summary,
        "",
        "你的任务：",
        "",
        f"1. 读取 {slide_plan_path}，获取每页的完整信息（title、bullets、teaching_goal、type 等）。",
        "",
        "2. 基于 slide_plan 的内容，生成 4 个档位的讲稿 JSON 文件：",
        f"   - {output_dir / 'narration_A.json'} — A档（最详细，~400字/页，完整展开+举例+互动）",
        f"   - {output_dir / 'narration_B.json'} — B档（详细，~250字/页，充分讲解+适当举例）",
        f"   - {output_dir / 'narration_C.json'} — C档（简要，~150字/页，要点清晰+少量展开）",
        f"   - {output_dir / 'narration_D.json'} — D档（最略，~80字/页，只讲核心要点）",
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
        '         "script": "完整的口头讲稿..."',
        "       }",
        "     ]",
        "   }",
        "",
        "3. 讲稿生成要求：",
        "   - script 用第一人称'我们''同学们'，营造课堂氛围",
        "   - 不要逐字念 slide_plan 上的 bullet 文字，要基于要点扩展讲解",
        "   - 适当使用类比、举例、反问等修辞手法",
        "   - 页与页之间自然过渡，前一页结尾为后一页铺垫",
        "   - 不同档位只在详细程度上区分，内容要点保持一致",
        "   - 封面/过渡页简短（30-60秒），知识点页充分展开（2-3分钟）",
        "",
        "4. 最终确认 4 个讲稿文件都已正确写入。",
        "",
        "规则：",
        "- 必须实际调用 Read/Write 工具。",
        "- 不要只描述计划。",
        "- 4 个档位必须全部生成，不要跳过。",
    ]

    prompt = "\n".join(prompt_parts)

    print("[Agent 启动] 正在基于 slide_plan 生成讲稿...")
    await agent.start()
    try:
        response = await agent.ask_with_retry(prompt, timeout=900)
        print(f"\n[Agent 完成]\n{response}\n")
    finally:
        await agent.close()


def check_outputs(output_dir: Path) -> dict[str, bool]:
    """检查 4 个档位讲稿是否都已生成。"""
    return {lvl: (output_dir / f"narration_{lvl}.json").exists() for lvl in ["A", "B", "C", "D"]}


def main():
    parser = argparse.ArgumentParser(
        description="讲稿自动生成器 — 基于 slide_plan.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python -m src.claude_agents.narration_from_ppt -s "ppt-master/projects/xxx/slide_plan.json" -a "大二工科"
  python -m src.claude_agents.narration_from_ppt -s "./slide_plan.json" -o "./讲稿输出"
        """,
    )
    parser.add_argument(
        "--slide-plan",
        "-s",
        required=True,
        help="输入 slide_plan.json 文件路径",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="输出目录（默认：slide_plan.json 同目录）",
    )
    parser.add_argument(
        "--audience",
        "-a",
        default="",
        help="目标受众，如'大二工科'、'高一数学'",
    )

    args = parser.parse_args()

    slide_plan_path = Path(args.slide_plan).resolve()
    if not slide_plan_path.exists():
        print(f"[错误] slide_plan.json 不存在: {slide_plan_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output).resolve() if args.output else infer_output_dir(slide_plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[slide_plan] {slide_plan_path}")
    print(f"[输出目录] {output_dir}")

    # 启动 agent
    asyncio.run(
        run_narration_agent(
            slide_plan_path=slide_plan_path,
            audience=args.audience,
            output_dir=output_dir,
        )
    )

    # 最终检查
    results = check_outputs(output_dir)
    all_ok = all(results.values())

    print(f"\n{'=' * 50}")
    if all_ok:
        print("✅ 讲稿生成成功！")
    else:
        print("⚠️ 部分讲稿缺失")
    for lvl, ok in results.items():
        status = "✅" if ok else "❌"
        path = output_dir / f"narration_{lvl}.json"
        print(f"   {status} {lvl}档: {path}")
    print(f"{'=' * 50}")

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
