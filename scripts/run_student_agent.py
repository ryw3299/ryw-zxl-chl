from __future__ import annotations

import json
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk.llm import LLM

from src.agents.student import build_student_agent_turn, run_student_agent
from src.schemas import LearningProgress, LearningSession, StudentAgentRequest
from src.utils.env_utils import get_env_value, load_env_file
from src.utils.student.config import get_embedding_settings, get_rag_settings


ROOT = Path(__file__).resolve().parents[1]


def build_demo_request() -> StudentAgentRequest:
    return StudentAgentRequest(
        course_id="COURSE_1",
        lesson_id="LESSON_1",
        session_id="SESSION_1",
        question="什么是应力？",
        structured_content={
            "course_id": "COURSE_1",
            "lesson_id": "LESSON_1",
            "lesson_summary": "材料力学基础",
            "pages": [
                {
                    "page_id": "page_1",
                    "lesson_id": "LESSON_1",
                    "section_id": "sec_1",
                    "page": 1,
                    "title": "应力基础",
                    "content": "应力表示单位面积上的内力，是材料力学中的基础概念。",
                    "summary": "应力是单位面积上的内力。",
                    "key_points": ["应力"],
                    "knowledge_points": ["应力"],
                    "page_role": "definition",
                },
                {
                    "page_id": "page_2",
                    "lesson_id": "LESSON_1",
                    "section_id": "sec_2",
                    "page": 2,
                    "title": "应力来源",
                    "content": "当外力作用于材料时，材料内部会产生抵抗变形的内力，这些内力分布在截面上形成应力。",
                    "summary": "外力作用会在材料内部形成应力。",
                    "key_points": ["应力来源"],
                    "knowledge_points": ["应力", "内力"],
                    "page_role": "content",
                },
            ],
            "sections": [
                {
                    "section_id": "sec_1",
                    "lesson_id": "LESSON_1",
                    "name": "基础概念",
                    "summary": "讲解应力的定义。",
                    "page_range": [1],
                    "key_points": ["应力"],
                    "knowledge_points": ["应力"],
                    "section_type": "content",
                },
                {
                    "section_id": "sec_2",
                    "lesson_id": "LESSON_1",
                    "name": "形成原因",
                    "summary": "讲解应力如何产生。",
                    "page_range": [2],
                    "key_points": ["应力来源"],
                    "knowledge_points": ["应力", "内力"],
                    "section_type": "content",
                },
            ],
            "knowledge_points": ["应力", "内力"],
        },
        session=LearningSession(
            session_id="SESSION_1",
            course_id="COURSE_1",
            lesson_id="LESSON_1",
            current_section_id="sec_1",
            current_page=1,
            current_script_block_id=None,
            progress_percent=20.0,
        ),
        progress=LearningProgress(
            session_id="SESSION_1",
            course_id="COURSE_1",
            lesson_id="LESSON_1",
            current_section_id="sec_1",
            current_page=1,
            current_script_block_id=None,
            progress_percent=20.0,
        ),
    )


LITELLM_PROVIDER_MAP = {
    "deepseek": "deepseek",
    "glm": "openai",
    "openai": "openai",
    "zhipu": "openai",
    "moonshot": "openai",
    "qwen": "openai",
}


def build_llm_from_env() -> LLM:
    env_path = ROOT / ".env"
    load_env_file(str(env_path), override=False)

    provider = get_env_value("LLM_PROVIDER", env_path=str(env_path)) or "deepseek"
    model = get_env_value("LLM_MODEL", env_path=str(env_path))
    api_key = get_env_value("LLM_API_KEY", env_path=str(env_path))
    base_url = get_env_value("LLM_BASE_URL", env_path=str(env_path))

    if not model or not api_key or not base_url:
        raise RuntimeError(
            "Missing LLM config in .env. Required: LLM_MODEL, LLM_API_KEY, LLM_BASE_URL."
        )

    if "/" in model:
        resolved_model = model
    else:
        litellm_provider = LITELLM_PROVIDER_MAP.get(provider.lower(), "openai")
        resolved_model = f"{litellm_provider}/{model}"

    return LLM(
        model=resolved_model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        litellm_extra_body={},
    )


def main() -> None:
    request = build_demo_request()
    llm = build_llm_from_env()
    embedding_settings = get_embedding_settings()
    rag_settings = get_rag_settings()

    stages = build_student_agent_turn(request, llm=llm)
    result = stages["output"].model_dump(mode="python")

    print("=== Retrieval Config ===")
    print(json.dumps({
        "embedding_mode": embedding_settings.mode,
        "embedding_model": embedding_settings.model,
        "vector_backend": rag_settings.vector_backend,
        "chunk_size": rag_settings.chunk_size,
        "chunk_overlap": rag_settings.chunk_overlap,
        "dense_top_k": rag_settings.dense_top_k,
        "bm25_top_k": rag_settings.bm25_top_k,
        "final_top_k": rag_settings.final_top_k,
    }, ensure_ascii=False, indent=2))

    print("=== Tool Trace ===")
    print(json.dumps(stages["tool_trace"], ensure_ascii=False, indent=2))

    print("\n=== QA Output ===")
    print(json.dumps(stages["qa_output"], ensure_ascii=False, indent=2, default=str))

    print("\n=== Decision Output ===")
    print(json.dumps(stages["decision_output"], ensure_ascii=False, indent=2, default=str))

    print("\n=== Final Response ===")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
