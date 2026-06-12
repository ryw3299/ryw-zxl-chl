from typing import Optional

from src.pipelines import run_file_parser_pipeline, run_file_structuring_pipeline
from src.schemas import ParserInput, ParserOutput
from src.utils.llm_client import LLMConfigurationError, build_llm_callable
from src.utils.logging_utils import get_logger


def run_file_parser(
    parser_input: dict,
    log_file: Optional[str] = None,
    llm_callable=None,
    env_path: Optional[str] = None,
) -> dict:
    stages = build_file_parser_stages(
        parser_input,
        log_file=log_file,
        llm_callable=llm_callable,
        env_path=env_path,
    )
    output = stages["output"]
    return output.model_dump(mode="python")


def build_file_parser_stages(
    parser_input: dict,
    log_file: Optional[str] = None,
    llm_callable=None,
    env_path: Optional[str] = None,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> dict:
    logger = get_logger("chaoxing.file_parser", log_file=log_file)
    runtime_log_path = getattr(logger, "runtime_log_path", None)
    logger.info("Starting file parser pipeline")

    request = ParserInput.model_validate(parser_input)
    logger.info(
        "Validated parser input for lesson=%s with %d asset(s)",
        request.lesson_id,
        len(request.assets),
    )

    pipeline_result = run_file_parser_pipeline(request, logger=logger)
    normalized_assets = pipeline_result["normalized_assets"]
    source_files = pipeline_result["source_files"]
    units = pipeline_result["units"]
    parsed_document = pipeline_result["parsed_document"]
    baseline_structured_content = pipeline_result["structured_content"]

    resolved_llm_callable = llm_callable
    structuring_enabled = resolved_llm_callable is not None
    if resolved_llm_callable is None:
        try:
            resolved_llm_callable = build_llm_callable(env_path=env_path)
            structuring_enabled = True
            logger.info("Loaded LLM callable from environment configuration")
        except LLMConfigurationError as exc:
            logger.warning("LLM configuration unavailable, baseline structured content will be used: %s", exc)
        except Exception as exc:
            logger.warning(
                "Failed to initialize LLM callable, baseline structured content will be used: %s", exc
            )

    structuring_result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline_structured_content,
        parse_instruction=request.parse_instruction,
        llm_callable=resolved_llm_callable,
        logger=logger,
        max_workers=max_workers,
        batch_size=batch_size,
    )
    structured_content = structuring_result["structured_content"]
    final_pages = list(structured_content.pages)
    final_sections = list(structured_content.sections)
    final_knowledge_points = list(structured_content.knowledge_points)

    output = ParserOutput(
        status="success",
        message="file parser finished",
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        source_file=source_files[0] if source_files else None,
        source_assets=normalized_assets,
        parsed_document=parsed_document,
        structured_content=structured_content,
        pages=final_pages,
        sections=final_sections,
        total_units=len(units),
        total_pages=len(final_pages),
        knowledge_points=final_knowledge_points,
        metadata={
            "log_file": runtime_log_path,
            "structuring_enabled": structuring_enabled,
            "structuring_strategy": structuring_result["strategy"],
            "structuring_used_fallback": structuring_result["used_fallback"],
            "structuring_chunk_count": structuring_result["chunk_count"],
            "structuring_validation_errors": structuring_result["validation_errors"],
        },
    )
    logger.info("Parser pipeline finished successfully")

    return {
        "request": request,
        "normalized_assets": normalized_assets,
        "source_files": source_files,
        "units": units,
        "parsed_document": parsed_document,
        "baseline_structured_content": baseline_structured_content,
        "structured_content": structured_content,
        "structuring_result": structuring_result,
        "output": output,
    }
