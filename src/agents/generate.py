from typing import Optional

from src.pipelines import run_generate_pipeline
from src.schemas import GenerateInput, GenerateOutput
from src.utils.llm_client import LLMConfigurationError, build_llm_callable, load_rate_limit_config
from src.utils.logging_utils import get_logger


def run_generate(
    generate_input: dict,
    log_file: Optional[str] = None,
    llm_callable=None,
    env_path: Optional[str] = None,
    max_sections: Optional[int] = None,
) -> dict:
    stages = build_generate_stages(
        generate_input,
        log_file=log_file,
        llm_callable=llm_callable,
        env_path=env_path,
        max_sections=max_sections,
    )
    output = stages["output"]
    return output.model_dump(mode="python")


def build_generate_stages(
    generate_input: dict,
    log_file: Optional[str] = None,
    llm_callable=None,
    env_path: Optional[str] = None,
    max_sections: Optional[int] = None,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> dict:
    logger = get_logger("chaoxing.generate", log_file=log_file)
    runtime_log_path = getattr(logger, "runtime_log_path", None)
    logger.info("Starting generate pipeline")

    request = GenerateInput.model_validate(generate_input)
    logger.info(
        "Validated generate input for lesson=%s with %d section(s) and %d page(s)",
        request.lesson_id,
        len(request.sections),
        len(request.pages),
    )

    resolved_llm_callable = llm_callable
    generation_enabled = resolved_llm_callable is not None
    if resolved_llm_callable is None:
        try:
            resolved_llm_callable = build_llm_callable(env_path=env_path)
            generation_enabled = True
            logger.info("Loaded LLM callable from environment configuration")
        except LLMConfigurationError as exc:
            logger.warning(
                "LLM configuration unavailable, rule-based generate fallback will be used: %s", exc
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize LLM callable, rule-based generate fallback will be used: %s", exc
            )

    resolved_max_workers = _resolve_generate_max_workers(
        request=request,
        env_path=env_path,
        generation_enabled=generation_enabled,
        explicit_max_workers=max_workers,
    )
    logger.info(
        "Generate scheduling resolved to max_workers=%d, batch_size=%d",
        resolved_max_workers,
        batch_size if batch_size is not None else 1,
    )

    pipeline_result = run_generate_pipeline(
        generate_input=request,
        llm_callable=resolved_llm_callable,
        logger=logger,
        max_sections=max_sections,
        max_workers=resolved_max_workers,
        batch_size=batch_size,
    )

    output = GenerateOutput(
        status="success",
        message="generate finished",
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        presentation_outline=pipeline_result["presentation_outline"],
        teacher_feedback_text=pipeline_result["teacher_feedback_text"],
        lesson_script=pipeline_result["lesson_script"],
        ppt_outline=pipeline_result["ppt_outline"],
        metadata={
            "log_file": runtime_log_path,
            "generation_enabled": generation_enabled,
            "generation_used_fallback": pipeline_result["used_fallback"],
            "generation_validation_errors": pipeline_result["validation_errors"],
            "generation_section_errors": pipeline_result["section_errors"],
            "generation_processed_sections": pipeline_result["processed_section_count"],
            "generation_total_input_sections": pipeline_result["total_input_sections"],
            "generation_max_sections": pipeline_result["max_sections_applied"],
            "generation_max_workers": resolved_max_workers,
            "generation_batch_size": batch_size if batch_size is not None else 1,
        },
    )
    logger.info("Generate pipeline finished successfully")

    return {
        "request": request,
        "presentation_outline": pipeline_result["presentation_outline"],
        "teacher_feedback_text": pipeline_result["teacher_feedback_text"],
        "lesson_script": pipeline_result["lesson_script"],
        "ppt_outline": pipeline_result["ppt_outline"],
        "pipeline_result": pipeline_result,
        "output": output,
    }


def _resolve_generate_max_workers(
    request: GenerateInput,
    env_path: Optional[str],
    generation_enabled: bool,
    explicit_max_workers: Optional[int],
) -> int:
    if explicit_max_workers is not None:
        return max(1, explicit_max_workers)

    sections = list(request.sections or request.structured_content.sections)
    pages = list(request.pages or request.structured_content.pages)
    section_count = len(sections)
    if section_count <= 1:
        return 1

    configured_limit = 5
    try:
        configured_limit = max(1, load_rate_limit_config(env_path=env_path).max_concurrent)
    except Exception:
        configured_limit = 5

    max_page_span = max((len(section.page_range) for section in sections), default=1)
    total_pages = len(pages)

    if not generation_enabled:
        safe_cap = 4
    elif total_pages >= 40 or max_page_span >= 8:
        safe_cap = 2
    else:
        safe_cap = 3

    return max(1, min(section_count, configured_limit, safe_cap))
