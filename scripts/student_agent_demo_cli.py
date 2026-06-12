from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any

from pydantic import SecretStr

from openhands.sdk.llm import LLM

from src.agents.student import build_student_agent_turn
from src.schemas import (
    LearningProgress,
    LearningSession,
    QAHistoryItem,
    StudentAgentRequest,
)
from src.tools.game import GameAction, GameTool
from src.utils.env_utils import get_env_value, load_env_file


ROOT = Path(__file__).resolve().parents[1]

DEMO_QUESTIONS = [
    "什么是应力？",
    "为什么外力会形成应力？",
    "怎么一步一步理解应力的形成过程？",
    "给我举一个生活中的例子。",
    "给我出一道选择题检验一下。",
]


def configure_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def configure_logging() -> None:
    logging.getLogger("openhands").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)


def build_mock_structured_content() -> dict[str, Any]:
    return {
        "course_id": "COURSE_MECH_1",
        "lesson_id": "LESSON_STRESS_1",
        "lesson_summary": "本节课介绍应力的定义、形成原因、分析步骤和生活化理解。",
        "pages": [
            {
                "page_id": "page_1",
                "lesson_id": "LESSON_STRESS_1",
                "section_id": "sec_definition",
                "page": 1,
                "title": "应力的定义",
                "content": "应力表示单位面积上的内力，是材料在外力作用下内部产生的抵抗效应。",
                "summary": "应力是单位面积上的内力。",
                "key_points": ["应力定义", "单位面积内力"],
                "knowledge_points": ["应力", "内力"],
                "page_role": "definition",
            },
            {
                "page_id": "page_2",
                "lesson_id": "LESSON_STRESS_1",
                "section_id": "sec_reason",
                "page": 2,
                "title": "应力的形成原因",
                "content": "当外力作用于材料时，材料内部会产生抵抗变形的内力，这些内力分布在截面上就形成了应力。",
                "summary": "外力作用会在材料内部形成应力。",
                "key_points": ["外力", "抵抗变形", "内力分布"],
                "knowledge_points": ["应力", "内力", "外力"],
                "page_role": "content",
            },
            {
                "page_id": "page_3",
                "lesson_id": "LESSON_STRESS_1",
                "section_id": "sec_procedure",
                "page": 3,
                "title": "分析应力的基本步骤",
                "content": "先识别受力情况，再判断截面上的内力分布，最后结合面积关系分析应力大小与方向。",
                "summary": "分析应力时先看受力，再看内力分布，最后联系面积。",
                "key_points": ["受力分析", "内力分布", "面积关系"],
                "knowledge_points": ["应力分析", "受力分析"],
                "page_role": "content",
            },
            {
                "page_id": "page_4",
                "lesson_id": "LESSON_STRESS_1",
                "section_id": "sec_example",
                "page": 4,
                "title": "生活中的应力例子",
                "content": "例如手压海绵时，海绵内部会产生抵抗压缩的内力；针尖比手指更容易刺入物体，也和接触面积导致的应力变化有关。",
                "summary": "手压海绵和针尖刺入都能帮助理解应力。",
                "key_points": ["海绵", "针尖", "接触面积"],
                "knowledge_points": ["应力例子", "接触面积"],
                "page_role": "example",
            },
        ],
        "sections": [
            {
                "section_id": "sec_definition",
                "lesson_id": "LESSON_STRESS_1",
                "name": "基础定义",
                "summary": "讲解应力是什么。",
                "page_range": [1],
                "key_points": ["应力定义"],
                "knowledge_points": ["应力", "内力"],
                "section_type": "content",
            },
            {
                "section_id": "sec_reason",
                "lesson_id": "LESSON_STRESS_1",
                "name": "形成原因",
                "summary": "讲解为什么外力会导致应力。",
                "page_range": [2],
                "key_points": ["外力作用", "内力分布"],
                "knowledge_points": ["应力", "内力", "外力"],
                "section_type": "content",
            },
            {
                "section_id": "sec_procedure",
                "lesson_id": "LESSON_STRESS_1",
                "name": "分析步骤",
                "summary": "讲解如何分析应力。",
                "page_range": [3],
                "key_points": ["受力分析", "面积关系"],
                "knowledge_points": ["应力分析"],
                "section_type": "content",
            },
            {
                "section_id": "sec_example",
                "lesson_id": "LESSON_STRESS_1",
                "name": "生活例子",
                "summary": "通过生活化例子帮助理解。",
                "page_range": [4],
                "key_points": ["海绵", "针尖"],
                "knowledge_points": ["应力例子"],
                "section_type": "example",
            },
        ],
        "knowledge_points": ["应力", "内力", "外力", "应力分析", "应力例子"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive student agent demo CLI.")
    parser.add_argument("--artifact-dir", type=str, default=None, help="Directory containing structured_content.json and optionally lesson_script.json.")
    parser.add_argument("--structured-content", type=str, default=None, help="Path to structured_content.json")
    parser.add_argument("--lesson-script", type=str, default=None, help="Path to lesson_script.json")
    return parser.parse_args()


def load_json_file(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_structured_content_payload(path: str | Path) -> dict[str, Any]:
    data = load_json_file(path)
    if "parser_output" in data and isinstance(data["parser_output"], dict):
        payload = data["parser_output"].get("structured_content")
        if isinstance(payload, dict):
            return payload
    if "structured_content" in data and isinstance(data["structured_content"], dict):
        return data["structured_content"]
    return data


def extract_lesson_script_payload(path: str | Path) -> dict[str, Any] | None:
    if not Path(path).exists():
        return None
    data = load_json_file(path)
    if "generate_output" in data and isinstance(data["generate_output"], dict):
        payload = data["generate_output"].get("lesson_script")
        if isinstance(payload, dict):
            return payload
    if "lesson_script" in data and isinstance(data["lesson_script"], dict):
        return data["lesson_script"]
    return data if isinstance(data, dict) else None


def build_initial_state(
    *,
    structured_content: dict[str, Any] | None = None,
    lesson_script: dict[str, Any] | None = None,
) -> dict[str, Any]:
    structured_content = structured_content or build_mock_structured_content()
    course_id = structured_content.get("course_id") or "COURSE_MECH_1"
    lesson_id = structured_content.get("lesson_id") or "LESSON_STRESS_1"
    first_section_id = None
    first_page = None
    if structured_content.get("sections"):
        first_section_id = structured_content["sections"][0].get("section_id")
    if structured_content.get("pages"):
        first_page = structured_content["pages"][0].get("page")

    return {
        "structured_content": structured_content,
        "lesson_script": lesson_script,
        "session": LearningSession(
            session_id="SESSION_DEMO_1",
            course_id=course_id,
            lesson_id=lesson_id,
            current_section_id=first_section_id,
            current_page=first_page,
            current_script_block_id=None,
            progress_percent=12.0,
        ),
        "progress": LearningProgress(
            session_id="SESSION_DEMO_1",
            course_id=course_id,
            lesson_id=lesson_id,
            current_section_id=first_section_id,
            current_page=first_page,
            current_script_block_id=None,
            progress_percent=12.0,
        ),
        "history_qa": [],
        "turns": [],
    }


def build_llm_from_env() -> LLM | None:
    env_path = ROOT / ".env"
    load_env_file(str(env_path), override=False)

    provider = get_env_value("LLM_PROVIDER", env_path=str(env_path)) or "deepseek"
    model = get_env_value("LLM_MODEL", env_path=str(env_path))
    api_key = get_env_value("LLM_API_KEY", env_path=str(env_path))
    base_url = get_env_value("LLM_BASE_URL", env_path=str(env_path))

    if not model or not api_key or not base_url:
        return None

    resolved_model = model if "/" in model else f"{provider}/{model}"
    return LLM(
        model=resolved_model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        litellm_extra_body={},
    )


def build_request(question: str, state: dict[str, Any]) -> StudentAgentRequest:
    session = state["session"].model_copy(deep=True) if state["session"] else None
    progress = state["progress"].model_copy(deep=True) if state["progress"] else None
    history = [item.model_copy(deep=True) for item in state["history_qa"]]
    structured_content = request_structured_content(state)

    return StudentAgentRequest(
        course_id=structured_content.course_id,
        lesson_id=structured_content.lesson_id,
        session_id="SESSION_DEMO_1",
        question=question,
        structured_content=structured_content,
        lesson_script=state.get("lesson_script"),
        session=session,
        progress=progress,
        history_qa=history,
    )


def apply_turn_result(state: dict[str, Any], stages: dict[str, Any], question: str) -> None:
    output = stages["output"]
    if output.updated_session is not None:
        state["session"] = output.updated_session.model_copy(deep=True)
    if output.updated_progress is not None:
        state["progress"] = output.updated_progress.model_copy(deep=True)
    if output.qa_record is not None:
        state["history_qa"].append(
            QAHistoryItem(
                qa_record_id=output.qa_record.qa_record_id,
                question=output.qa_record.question,
                answer=output.qa_record.answer,
                understanding_level=output.qa_record.understanding_level,
                current_section_id=output.qa_record.current_section_id,
                current_page=output.qa_record.current_page,
            )
        )

    state["turns"].append(
        {
            "question": question,
            "answer": output.answer,
            "next_action": output.next_action,
            "reason": output.reason,
            "tool_trace": stages["tool_trace"],
            "game": output.metadata.get("game"),
        }
    )


def print_help() -> None:
    print(
        "\n可用命令:\n"
        "  直接输入问题           与 student agent 对话\n"
        "  /help                 查看帮助\n"
        "  /lesson               查看 mock 课程结构\n"
        "  /state                查看当前 session/progress\n"
        "  /history              查看历史问答\n"
        "  /trace                查看上一轮 tool trace\n"
        "  /demo                 自动跑一组覆盖定义/原因/步骤/例子/游戏的问题\n"
        "  /preview-game         直接预览 game tool 生成的选择题\n"
        "  /reset                重置为初始状态\n"
        "  /quit                 退出\n"
    )


def print_lesson(state: dict[str, Any]) -> None:
    content = state["structured_content"]
    print("\n=== Mock 课程概览 ===")
    print(f"课时: {content['lesson_summary']}")
    print("\nSections:")
    for section in content["sections"]:
        print(f"- {section['section_id']}: {section['name']} | pages={section['page_range']} | {section['summary']}")
    print("\nPages:")
    for page in content["pages"]:
        print(f"- page={page['page']} | {page['title']} | section={page['section_id']}")


def print_state(state: dict[str, Any]) -> None:
    session = state["session"]
    progress = state["progress"]
    print("\n=== 当前状态 ===")
    if session is not None:
        print(
            f"session: section={session.current_section_id}, page={session.current_page}, "
            f"script_block={session.current_script_block_id}, progress={session.progress_percent:.1f}%"
        )
    if progress is not None:
        print(
            f"progress: section={progress.current_section_id}, page={progress.current_page}, "
            f"last_action={progress.last_action}, progress={progress.progress_percent:.1f}%"
        )
    print(f"history size: {len(state['history_qa'])}")


def print_history(state: dict[str, Any]) -> None:
    print("\n=== 历史问答 ===")
    if not state["history_qa"]:
        print("(空)")
        return
    for index, item in enumerate(state["history_qa"], start=1):
        print(f"{index}. Q: {item.question}")
        print(f"   A: {item.answer}")
        print(
            f"   understanding={item.understanding_level}, "
            f"section={item.current_section_id}, page={item.current_page}"
        )


def print_turn_result(stages: dict[str, Any]) -> None:
    output = stages["output"]
    qa_output = stages["qa_output"]
    decision_output = stages["decision_output"]
    tool_trace = stages["tool_trace"]

    print("\n=== Agent 回答 ===")
    print(output.answer)

    print("\n=== Agent 决断 ===")
    print(
        json.dumps(
            {
                "question_type": output.question_type,
                "understanding_level": output.understanding_level,
                "next_action": output.next_action,
                "reason": output.reason,
                "target_section_id": output.target_section_id,
                "target_page": output.target_page,
                "answer_source": qa_output.get("answer_source"),
                "decision_source": decision_output.get("decision_source"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n=== References ===")
    if not output.references:
        print("(空)")
    for ref in output.references:
        print(
            f"- [{ref.source_type}] {ref.source_name} | section={ref.section_id} | page={ref.page} | snippet={ref.snippet}"
        )

    print("\n=== Tool Trace ===")
    print(json.dumps(tool_trace, ensure_ascii=False, indent=2, default=str))

    game_payload = output.metadata.get("game")
    if game_payload:
        print("\n=== Game Payload ===")
        print(json.dumps(game_payload, ensure_ascii=False, indent=2, default=str))

    if output.updated_session is not None or output.updated_progress is not None:
        print("\n=== 状态更新 ===")
        print(
            json.dumps(
                {
                    "updated_session": output.updated_session.model_dump(mode="python")
                    if output.updated_session is not None
                    else None,
                    "updated_progress": output.updated_progress.model_dump(mode="python")
                    if output.updated_progress is not None
                    else None,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


def run_one_turn(question: str, state: dict[str, Any], llm: LLM | None) -> None:
    request = build_request(question, state)
    stages = build_student_agent_turn(request, llm=llm)
    print_turn_result(stages)
    apply_turn_result(state, stages, question)


def preview_game(state: dict[str, Any], question: str = "给我出一道选择题检验一下。") -> None:
    tool = GameTool(structured_content=request_structured_content(state))
    observation = tool.run(
        GameAction(
            question=question,
            lesson_id=request_structured_content(state).lesson_id,
            session_id="SESSION_DEMO_1",
            section_id=state["session"].current_section_id if state["session"] else None,
            page=state["session"].current_page if state["session"] else None,
        )
    )
    print("\n=== 直接预览 Game Tool ===")
    print(json.dumps(observation.model_dump(mode="python"), ensure_ascii=False, indent=2))


def request_structured_content(state: dict[str, Any]):
    return StudentAgentRequest(
        course_id=state["structured_content"].get("course_id"),
        lesson_id=state["structured_content"]["lesson_id"],
        session_id="SESSION_DEMO_1",
        question="preview",
        structured_content=state["structured_content"],
        lesson_script=state.get("lesson_script"),
        session=state["session"],
        progress=state["progress"],
        history_qa=[],
    ).structured_content


def run_demo_sequence(state: dict[str, Any], llm: LLM | None) -> None:
    print("\n开始自动 demo，共 5 轮。")
    for index, question in enumerate(DEMO_QUESTIONS, start=1):
        print(f"\n----- Demo Turn {index} -----")
        print(f"用户: {question}")
        run_one_turn(question, state, llm)


def main() -> None:
    configure_stdio()
    configure_logging()
    args = parse_args()
    llm = build_llm_from_env()

    structured_content = None
    lesson_script = None
    if args.artifact_dir:
        artifact_dir = Path(args.artifact_dir)
        structured_content = extract_structured_content_payload(artifact_dir / "structured_content.json")
        lesson_script = extract_lesson_script_payload(artifact_dir / "lesson_script.json")
    elif args.structured_content:
        structured_content = extract_structured_content_payload(args.structured_content)
        if args.lesson_script:
            lesson_script = extract_lesson_script_payload(args.lesson_script)

    state = build_initial_state(structured_content=structured_content, lesson_script=lesson_script)

    print("=== Student Agent Interactive Demo ===")
    print("说明: 这个脚本支持 mock 数据或外部 structured_content/lesson_script，多轮交互展示 agent 的工具调用和决断。")
    print(f"LLM mode: {'real_llm' if llm is not None else 'fallback_only'}")
    if args.artifact_dir:
        print(f"Artifact dir: {args.artifact_dir}")
    elif args.structured_content:
        print(f"Structured content: {args.structured_content}")
    print_help()

    while True:
        try:
            raw = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            return

        if not raw:
            continue
        if raw == "/quit":
            print("退出。")
            return
        if raw == "/help":
            print_help()
            continue
        if raw == "/lesson":
            print_lesson(state)
            continue
        if raw == "/state":
            print_state(state)
            continue
        if raw == "/history":
            print_history(state)
            continue
        if raw == "/trace":
            if not state["turns"]:
                print("\n还没有对话记录。")
            else:
                print(json.dumps(state["turns"][-1]["tool_trace"], ensure_ascii=False, indent=2, default=str))
            continue
        if raw == "/demo":
            run_demo_sequence(state, llm)
            continue
        if raw == "/preview-game":
            preview_game(state)
            continue
        if raw == "/reset":
            state = build_initial_state(structured_content=structured_content, lesson_script=lesson_script)
            print("\n已重置为初始状态。")
            continue

        run_one_turn(raw, state, llm)


if __name__ == "__main__":
    main()
