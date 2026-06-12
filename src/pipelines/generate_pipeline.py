import json
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import yaml

from src.schemas import (
    GenerateInput,
    LessonScript,
    PageBlock,
    PPTOutline,
    PresentationCard,
    PresentationOutline,
    PresentationSection,
    ScriptBlock,
    SectionBlock,
    SlideOutline,
    VisualPlan,
)
from src.utils.rate_limiter import RateLimiter

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[1] / "agents" / "prompts" / "generate.yaml"
VALID_CARD_TYPES = {
    "cover",
    "agenda",
    "concept",
    "formula",
    "example",
    "comparison",
    "process",
    "summary",
}
VALID_VISUAL_TYPES = {"none", "source_image", "source_table", "source_formula"}
CARD_TYPE_BY_PAGE_ROLE = {
    "cover": "cover",
    "agenda": "agenda",
    "content": "concept",
    "definition": "concept",
    "formula": "formula",
    "example": "example",
    "summary": "summary",
    "exercise": "example",
    "other": "concept",
}
LAYOUT_TEMPLATE_BY_CARD_TYPE = {
    "cover": "cover_layout",
    "agenda": "agenda_layout",
    "concept": "content_layout",
    "formula": "formula_layout",
    "example": "example_layout",
    "comparison": "comparison_layout",
    "process": "process_layout",
    "summary": "summary_layout",
}
SCRIPT_BLOCK_TYPE_BY_CARD_TYPE = {
    "cover": "opening",
    "agenda": "opening",
    "concept": "teaching",
    "formula": "teaching",
    "example": "teaching",
    "comparison": "teaching",
    "process": "teaching",
    "summary": "summary",
}
OVERVIEW_CARD_KEYWORDS = (
    "概述",
    "提纲",
    "目录",
    "主要内容",
    "本节内容",
    "本章内容",
    "学习目标",
    "内容结构",
    "课程简介",
    "章节概览",
)


def run_generate_pipeline(
    generate_input: GenerateInput,
    llm_callable: Optional[Callable[..., Any]] = None,
    prompt_path: Optional[str] = None,
    logger=None,
    max_sections: Optional[int] = None,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
    section_cache: Optional[dict[str, PresentationSection]] = None,
) -> dict:
    prompt_config = _load_prompt_config(prompt_path)
    structured_content = generate_input.structured_content
    pages = list(generate_input.pages or structured_content.pages)
    sections = list(generate_input.sections or structured_content.sections)
    total_input_sections = len(sections)
    cache = section_cache if section_cache is not None else {}

    if max_sections is not None and max_sections > 0 and len(sections) > max_sections:
        sections, pages = _limit_sections_and_pages(sections, pages, max_sections)
        if logger is not None:
            logger.info(
                "Generate preview mode enabled: limiting sections from %d to %d",
                total_input_sections,
                len(sections),
            )

    known_page_ids = {page.page_id or f"page_{page.page}" for page in pages}
    known_unit_ids = {unit_id for page in pages for unit_id in page.source_unit_ids}

    if logger is not None:
        logger.info(
            "Starting generate pipeline for lesson=%s with %d section(s) and %d page(s)",
            generate_input.lesson_id,
            len(sections),
            len(pages),
        )

    if not sections and pages:
        sections = _synthesize_sections_from_pages(generate_input.lesson_id, pages)

    if not sections:
        outline = _fallback_presentation_outline(generate_input, [])
        teacher_feedback_text = _build_teacher_feedback_text(outline)
        lesson_script = _build_lesson_script(generate_input, outline)
        ppt_outline = _build_ppt_outline(outline)
        return {
            "presentation_outline": outline,
            "teacher_feedback_text": teacher_feedback_text,
            "lesson_script": lesson_script,
            "ppt_outline": ppt_outline,
            "used_fallback": True,
            "section_results": [],
            "validation_errors": ["No sections available for generation."],
            "section_errors": [
                {"section_id": "", "errors": ["No sections available for generation."], "used_fallback": True}
            ],
        }

    page_lookup = _build_page_lookup(pages)
    section_pages_map = _build_section_pages_map(sections, page_lookup)

    section_results: list[PresentationSection] = []
    section_errors: list[dict[str, Any]] = []
    used_fallback = llm_callable is None

    # Determine whether to use parallel or serial processing
    # Parallel when max_workers is specified and > 1
    use_parallel = max_workers is not None and max_workers > 1

    # Batch mode: use batching + parallel (most efficient for many sections)
    # Automatically enabled when using parallel, batch_size > 1, and there are enough sections
    effective_batch_size = batch_size if batch_size is not None else 1
    use_batch = use_parallel and effective_batch_size > 1 and len(sections) >= 3

    if use_parallel:
        if logger is not None:
            if use_batch:
                logger.info(
                    "Running batch-parallel section generation with %d workers for %d sections",
                    max_workers,
                    len(sections),
                )
            else:
                logger.info(
                    "Running parallel section generation with %d workers for %d sections",
                    max_workers,
                    len(sections),
                )

        if use_batch:
            effective_batch_size = batch_size if batch_size is not None else 1
            section_results, section_errors = _run_sections_parallel_with_batching(
                sections=sections,
                section_pages_map=section_pages_map,
                generate_input=generate_input,
                structured_content=structured_content,
                prompt_config=prompt_config,
                llm_callable=llm_callable,
                known_page_ids=known_page_ids,
                known_unit_ids=known_unit_ids,
                logger=logger,
                max_workers=max_workers,
                batch_size=effective_batch_size,
                section_cache=cache,
            )
        else:
            section_results, section_errors = _run_sections_parallel(
                sections=sections,
                section_pages_map=section_pages_map,
                generate_input=generate_input,
                structured_content=structured_content,
                prompt_config=prompt_config,
                llm_callable=llm_callable,
                known_page_ids=known_page_ids,
                known_unit_ids=known_unit_ids,
                logger=logger,
                max_workers=max_workers,
                section_cache=cache,
            )
        # Check if any section used fallback
        used_fallback = any(error.get("used_fallback", False) for error in section_errors)
    else:
        # Serial processing (original behavior for backward compatibility)
        for section_index, section in enumerate(sections, start=1):
            section_pages = list(section_pages_map.get(section.section_id, []))
            if logger is not None:
                logger.info(
                    "Generating section %d/%d: %s (%d page(s))",
                    section_index,
                    len(sections),
                    section.name or section.section_id,
                    len(section_pages),
                )
            cache_key = _section_cache_key(generate_input, section)
            if cache_key in cache:
                presentation_section = cache[cache_key]
                error_dict = {
                    "section_id": section.section_id,
                    "errors": [],
                    "used_fallback": False,
                    "cached": True,
                }
            elif llm_callable is None:
                presentation_section = _fallback_presentation_section(section, section_pages, section_index)
                error_dict = {  # noqa: F841 - kept for future error aggregation
                    "section_id": section.section_id,
                    "errors": ["No llm_callable was provided to the generate pipeline."],
                    "used_fallback": True,
                }
            else:
                try:
                    section_prompt_context = _build_section_prompt_context(section, section_pages)
                    payload = _build_section_payload(
                        generate_input=generate_input,
                        section=section,
                        section_pages=section_pages,
                        prompt_config=prompt_config,
                        section_prompt_context=section_prompt_context,
                    )
                    raw_response = _call_generate_llm(
                        llm_callable=llm_callable,
                        system_prompt=prompt_config["section_generation_prompt"]["system"],
                        user_prompt=payload,
                        stage="generate_section",
                        metadata=_build_section_generation_metadata(
                            generate_input=generate_input,
                            structured_content=structured_content,
                            section=section,
                            section_pages=section_pages,
                            section_prompt_context=section_prompt_context,
                        ),
                    )
                    presentation_section = _parse_presentation_section_result(
                        raw_response=raw_response,
                        section=section,
                        section_pages=section_pages,
                        section_index=section_index,
                    )
                    presentation_section = _normalize_presentation_section(
                        presentation_section=presentation_section,
                        section=section,
                        section_pages=section_pages,
                        section_index=section_index,
                    )
                    errors = _validate_presentation_section(
                        presentation_section=presentation_section,
                        known_page_ids=known_page_ids,
                        known_unit_ids=known_unit_ids,
                        expected_section_id=section.section_id,
                    )
                    if errors:
                        used_fallback = True
                        if logger is not None:
                            logger.warning(
                                "Generate section %s fell back after validation: %s",
                                section.section_id,
                                "; ".join(errors),
                            )
                        section_errors.append(
                            {
                                "section_id": section.section_id,
                                "errors": errors,
                                "used_fallback": True,
                                "response_preview": _response_preview(raw_response),
                            }
                        )
                        presentation_section = _fallback_presentation_section(
                            section, section_pages, section_index
                        )
                    else:
                        section_errors.append(
                            {
                                "section_id": section.section_id,
                                "errors": [],
                                "used_fallback": False,
                            }
                        )
                except Exception as exc:
                    used_fallback = True
                    presentation_section = _fallback_presentation_section(
                        section, section_pages, section_index
                    )
                    if logger is not None:
                        logger.warning(
                            "Generate section %s failed and fell back: %s",
                            section.section_id,
                            exc,
                        )
                    section_errors.append(
                        {
                            "section_id": section.section_id,
                            "errors": [str(exc)],
                            "used_fallback": True,
                        }
                    )
                finally:
                    if logger is not None:
                        logger.info(
                            "Generate section %s completed with %d card(s)",
                            section.section_id,
                            len(presentation_section.cards),
                        )
                    cache[cache_key] = presentation_section

            section_results.append(presentation_section)

    outline = _assemble_presentation_outline(generate_input, section_results)
    validation_errors = _validate_presentation_outline(
        outline=outline,
        known_page_ids=known_page_ids,
        known_unit_ids=known_unit_ids,
    )
    if validation_errors:
        used_fallback = True
        outline = _fallback_presentation_outline(generate_input, sections)
    elif used_fallback:
        outline.metadata["fallback"] = True

    teacher_feedback_text = _build_teacher_feedback_text(outline)
    lesson_script = _build_lesson_script(generate_input, outline)
    ppt_outline = _build_ppt_outline(outline)

    if logger is not None:
        logger.info(
            "Generate pipeline finished with %d section(s), %d card(s), %d script block(s), %d slide(s)",
            len(outline.sections),
            sum(len(section.cards) for section in outline.sections),
            len(lesson_script.script_blocks),
            len(ppt_outline.slides),
        )

    return {
        "presentation_outline": outline,
        "teacher_feedback_text": teacher_feedback_text,
        "lesson_script": lesson_script,
        "ppt_outline": ppt_outline,
        "used_fallback": used_fallback,
        "section_results": section_results,
        "validation_errors": validation_errors,
        "section_errors": section_errors,
        "processed_section_count": len(sections),
        "total_input_sections": total_input_sections,
        "max_sections_applied": max_sections if max_sections is not None and max_sections > 0 else None,
    }


def _load_prompt_config(prompt_path: Optional[str] = None) -> dict:
    resolved_path = Path(prompt_path) if prompt_path else DEFAULT_PROMPT_PATH
    data = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("generate prompt config must load into a dict.")

    required_keys = {"section_generation_prompt", "output_contract"}
    missing = sorted(required_keys - set(data.keys()))
    if missing:
        raise ValueError(f"Generate prompt config is missing required keys: {missing}")

    return data


def _derive_lesson_title(generate_input: GenerateInput) -> str:
    if generate_input.lesson_name.strip():
        return generate_input.lesson_name.strip()

    structured_content = generate_input.structured_content
    for page in structured_content.pages:
        if page.title.strip():
            return page.title.strip()

    for section in structured_content.sections:
        if section.name.strip():
            return section.name.strip()

    return generate_input.lesson_id


def _select_section_pages(section: SectionBlock, pages: Sequence[PageBlock]) -> list[PageBlock]:
    selected = [page for page in pages if page.section_id == section.section_id]
    if selected:
        return sorted(selected, key=lambda item: item.page)

    if section.page_range:
        page_range = set(section.page_range)
        selected = [page for page in pages if page.page in page_range]
        if selected:
            return sorted(selected, key=lambda item: item.page)

    source_unit_ids = set(section.source_unit_ids)
    selected = [page for page in pages if source_unit_ids.intersection(page.source_unit_ids)]
    return sorted(selected, key=lambda item: item.page)


def _build_page_lookup(pages: Sequence[PageBlock]) -> dict[str, Any]:
    sorted_pages = sorted(pages, key=lambda item: item.page)
    by_section_id: dict[str, list[PageBlock]] = {}
    by_page_number = {page.page: page for page in sorted_pages}
    by_unit_id: dict[str, list[PageBlock]] = {}

    for page in sorted_pages:
        if page.section_id:
            by_section_id.setdefault(page.section_id, []).append(page)
        for unit_id in page.source_unit_ids:
            by_unit_id.setdefault(unit_id, []).append(page)

    return {
        "pages": sorted_pages,
        "by_section_id": by_section_id,
        "by_page_number": by_page_number,
        "by_unit_id": by_unit_id,
    }


def _build_section_pages_map(
    sections: Sequence[SectionBlock],
    page_lookup: dict[str, Any],
) -> dict[str, list[PageBlock]]:
    pages = list(page_lookup.get("pages", []))
    by_section_id = dict(page_lookup.get("by_section_id", {}))
    by_page_number = dict(page_lookup.get("by_page_number", {}))
    by_unit_id = dict(page_lookup.get("by_unit_id", {}))

    section_pages_map: dict[str, list[PageBlock]] = {}
    for section in sections:
        section_pages = list(by_section_id.get(section.section_id, []))
        if not section_pages and section.page_range:
            section_pages = [
                by_page_number[page_number]
                for page_number in section.page_range
                if page_number in by_page_number
            ]
        if not section_pages and section.source_unit_ids:
            seen_page_ids = set()
            section_pages = []
            for unit_id in section.source_unit_ids:
                for page in by_unit_id.get(unit_id, []):
                    page_id = page.page_id or f"page_{page.page}"
                    if page_id in seen_page_ids:
                        continue
                    seen_page_ids.add(page_id)
                    section_pages.append(page)
            section_pages.sort(key=lambda item: item.page)
        if not section_pages:
            section_pages = _select_section_pages(section, pages)
        section_pages_map[section.section_id] = section_pages

    return section_pages_map


def _process_single_section(
    section_index: int,
    section: SectionBlock,
    section_pages_map: dict[str, list[PageBlock]],
    generate_input: GenerateInput,
    structured_content: Any,
    prompt_config: dict[str, Any],
    llm_callable: Optional[Callable[..., Any]],
    known_page_ids: set,
    known_unit_ids: set,
    logger: Any,
    section_cache: dict[str, PresentationSection],
) -> tuple[PresentationSection, dict[str, Any]]:
    """Process a single section to generate a PresentationSection.

    This function is designed to be called in parallel via ThreadPoolExecutor.

    Returns:
        Tuple of (PresentationSection, error_dict)
    """
    section_pages = list(section_pages_map.get(section.section_id, []))
    cache_key = _section_cache_key(generate_input, section)
    cached_section = section_cache.get(cache_key)
    if cached_section is not None:
        return cached_section, {
            "section_id": section.section_id,
            "errors": [],
            "used_fallback": False,
            "cached": True,
        }
    section_num = section_index + 1

    if logger is not None:
        logger.info(
            "Generating section %d: %s (%d page(s))",
            section_num,
            section.name or section.section_id,
            len(section_pages),
        )

    used_fallback = llm_callable is None

    if llm_callable is None:
        presentation_section = _fallback_presentation_section(section, section_pages, section_num)
        error_dict = {
            "section_id": section.section_id,
            "errors": ["No llm_callable was provided to the generate pipeline."],
            "used_fallback": True,
        }
        return presentation_section, error_dict

    try:
        section_prompt_context = _build_section_prompt_context(section, section_pages)
        payload = _build_section_payload(
            generate_input=generate_input,
            section=section,
            section_pages=section_pages,
            prompt_config=prompt_config,
            section_prompt_context=section_prompt_context,
        )
        raw_response = _call_generate_llm(
            llm_callable=llm_callable,
            system_prompt=prompt_config["section_generation_prompt"]["system"],
            user_prompt=payload,
            stage="generate_section",
            metadata=_build_section_generation_metadata(
                generate_input=generate_input,
                structured_content=structured_content,
                section=section,
                section_pages=section_pages,
                section_prompt_context=section_prompt_context,
            ),
        )
        presentation_section = _parse_presentation_section_result(
            raw_response=raw_response,
            section=section,
            section_pages=section_pages,
            section_index=section_num,
        )
        presentation_section = _normalize_presentation_section(
            presentation_section=presentation_section,
            section=section,
            section_pages=section_pages,
            section_index=section_num,
        )
        errors = _validate_presentation_section(
            presentation_section=presentation_section,
            known_page_ids=known_page_ids,
            known_unit_ids=known_unit_ids,
            expected_section_id=section.section_id,
        )
        if errors:
            used_fallback = True
            if logger is not None:
                logger.warning(
                    "Generate section %s fell back after validation: %s",
                    section.section_id,
                    "; ".join(errors),
                )
            error_dict = {
                "section_id": section.section_id,
                "errors": errors,
                "used_fallback": True,
                "response_preview": _response_preview(raw_response),
            }
            presentation_section = _fallback_presentation_section(section, section_pages, section_num)
        else:
            error_dict = {
                "section_id": section.section_id,
                "errors": [],
                "used_fallback": False,
            }
            if logger is not None:
                logger.info(
                    "Generate section %s completed with %d card(s)",
                    section.section_id,
                    len(presentation_section.cards),
                )
    except Exception as exc:
        used_fallback = True  # noqa: F841 - retained for symmetry / future telemetry
        presentation_section = _fallback_presentation_section(section, section_pages, section_num)
        if logger is not None:
            logger.warning(
                "Generate section %s failed and fell back: %s",
                section.section_id,
                exc,
            )
        error_dict = {  # noqa: F841 - kept for future error aggregation
            "section_id": section.section_id,
            "errors": [str(exc)],
            "used_fallback": True,
        }

    section_cache[cache_key] = presentation_section
    return presentation_section, error_dict


def _run_sections_parallel(
    sections: list[SectionBlock],
    section_pages_map: dict[str, list[PageBlock]],
    generate_input: GenerateInput,
    structured_content: Any,
    prompt_config: dict[str, Any],
    llm_callable: Optional[Callable[..., Any]],
    known_page_ids: set,
    known_unit_ids: set,
    logger: Any,
    max_workers: int,
    section_cache: dict[str, PresentationSection],
) -> tuple[list[PresentationSection], list[dict[str, Any]]]:
    """Run section generation in parallel using ThreadPoolExecutor.

    Args:
        sections: List of sections to process.
        section_pages_map: Precomputed mapping from section_id to section pages.
        generate_input: The generate input.
        structured_content: The structured content.
        prompt_config: Prompt configuration.
        llm_callable: LLM callable.
        known_page_ids: Set of known page IDs for validation.
        known_unit_ids: Set of known unit IDs for validation.
        logger: Logger instance.
        max_workers: Maximum number of concurrent workers.

    Returns:
        Tuple of (list of PresentationSection, list of error dicts)
    """
    limiter = RateLimiter(max_concurrent=max_workers)

    def _limited_process(args):
        with limiter():
            return _process_single_section(*args)

    # Prepare arguments for each section
    args_list = [
        (
            section_index,
            section,
            section_pages_map,
            generate_input,
            structured_content,
            prompt_config,
            llm_callable,
            known_page_ids,
            known_unit_ids,
            logger,
            section_cache,
        )
        for section_index, section in enumerate(sections)
    ]

    # Run in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_limited_process, args_list))

    # Unpack results
    section_results = [result[0] for result in results]
    section_errors = [result[1] for result in results]

    return section_results, section_errors


def _group_sections_for_batching(
    sections: list[SectionBlock],
    section_pages_map: dict[str, list[PageBlock]],
    batch_size: int = 3,
) -> list[list[SectionBlock]]:
    """Group sections into batches for batch LLM calls.

    Args:
        sections: List of sections to group.
        pages: All available pages (used for estimating complexity).
        batch_size: Maximum sections per batch.

    Returns:
        List of section batches.
    """
    if not sections:
        return []

    # Sort sections by number of pages (process simpler sections first)
    section_with_page_count = []
    for section in sections:
        section_pages = list(section_pages_map.get(section.section_id, []))
        page_count = len(section_pages)
        section_with_page_count.append((section, page_count))

    # Sort by page count (ascending - smaller sections first for faster initial results)
    section_with_page_count.sort(key=lambda x: x[1])

    # Group into batches
    batches: list[list[SectionBlock]] = []
    current_batch: list[SectionBlock] = []
    current_page_count = 0

    for section, page_count in section_with_page_count:
        # If adding this section would exceed batch size or page limit, start new batch
        if current_batch and (len(current_batch) >= batch_size or current_page_count + page_count > 15):
            batches.append(current_batch)
            current_batch = []
            current_page_count = 0

        current_batch.append(section)
        current_page_count += page_count

    # Add remaining sections
    if current_batch:
        batches.append(current_batch)

    return batches


def _build_batch_payload(
    generate_input: GenerateInput,
    sections: list[SectionBlock],
    section_pages_map: dict[str, list[PageBlock]],
    prompt_config: dict[str, Any],
) -> str:
    """Build payload for batch section generation.

    Args:
        generate_input: The generate input.
        sections: List of sections to include in batch.
        section_pages_map: Precomputed mapping from section_id to section pages.
        prompt_config: Prompt configuration.

    Returns:
        Formatted prompt string for batch generation.
    """
    sections_payload = []
    for section in sections:
        section_pages = list(section_pages_map.get(section.section_id, []))
        sections_payload.append(_build_section_prompt_context(section, section_pages))

    prompt_template = prompt_config["batch_section_generation_prompt"]["user_template"]
    return prompt_template.format(
        lesson_title=_derive_lesson_title(generate_input),
        lesson_summary=generate_input.structured_content.lesson_summary,
        generate_instruction=generate_input.generate_instruction or "",
        teacher_notes=generate_input.teacher_notes or "",
        sections_payload=json.dumps(sections_payload, ensure_ascii=False, indent=2),
    )


def _parse_batch_presentation_section_result(
    raw_response: Any,
    sections: list[SectionBlock],
    section_pages_map: dict[str, list[PageBlock]],
    start_index: int,
) -> list[PresentationSection]:
    """Parse batch LLM response into list of PresentationSections.

    Args:
        raw_response: Raw LLM response.
        sections: Original sections corresponding to the batch.
        section_pages_map: Precomputed mapping from section_id to section pages.
        start_index: Starting index for card numbering.

    Returns:
        List of PresentationSection objects.

    Raises:
        ValueError: If parsing fails.
    """
    # Extract JSON from response
    if isinstance(raw_response, str):
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        payload = json.loads(cleaned)
    elif isinstance(raw_response, dict):
        payload = raw_response
    else:
        raise ValueError(f"Unsupported batch response type: {type(raw_response)}")

    # Extract sections array
    if "sections" not in payload:
        raise ValueError("Batch response missing 'sections' key")

    sections_data = payload["sections"]

    if len(sections_data) != len(sections):
        raise ValueError(f"Section count mismatch: expected {len(sections)}, got {len(sections_data)}")

    # Parse each section
    presentation_sections = []
    for i, section_data in enumerate(sections_data):
        section = sections[i]
        section_pages = list(section_pages_map.get(section.section_id, []))
        section_index = start_index + i

        try:
            normalized = _normalize_section_payload(section_data, section, section_pages, section_index)
            presentation_section = PresentationSection.model_validate(normalized)
            presentation_sections.append(presentation_section)
        except Exception as e:
            raise ValueError(f"Failed to parse section {i}: {e}")

    return presentation_sections


def _process_batch_sections(
    batch: list[SectionBlock],
    batch_index: int,
    total_batches: int,
    section_pages_map: dict[str, list[PageBlock]],
    generate_input: GenerateInput,
    structured_content: Any,
    prompt_config: dict[str, Any],
    llm_callable: Optional[Callable[..., Any]],
    known_page_ids: set,
    known_unit_ids: set,
    start_index: int,
    logger: Any,
    section_cache: Optional[dict[str, PresentationSection]] = None,
) -> tuple[list[PresentationSection], list[dict[str, Any]]]:
    """Process a batch of sections with a single LLM call.

    Args:
        batch: List of sections in this batch.
        batch_index: Index of this batch.
        total_batches: Total number of batches.
        section_pages_map: Precomputed mapping from section_id to section pages.
        generate_input: The generate input.
        structured_content: The structured content.
        prompt_config: Prompt configuration.
        llm_callable: LLM callable.
        known_page_ids: Set of known page IDs.
        known_unit_ids: Set of known unit IDs.
        start_index: Starting section index for card numbering.
        logger: Logger instance.

    Returns:
        Tuple of (list of PresentationSection, list of error dicts)
    """
    if logger is not None:
        logger.info(
            "Processing batch %d/%d with %d sections",
            batch_index + 1,
            total_batches,
            len(batch),
        )

    if llm_callable is None:
        # Fallback for all sections in batch
        results = []
        errors = []
        for i, section in enumerate(batch):
            section_pages = list(section_pages_map.get(section.section_id, []))
            section_num = start_index + i + 1
            results.append(_fallback_presentation_section(section, section_pages, section_num))
            errors.append(
                {
                    "section_id": section.section_id,
                    "errors": ["No llm_callable provided"],
                    "used_fallback": True,
                }
            )
        return results, errors

    try:
        # Build batch payload
        payload = _build_batch_payload(
            generate_input=generate_input,
            sections=batch,
            section_pages_map=section_pages_map,
            prompt_config=prompt_config,
        )

        # Call LLM
        raw_response = _call_generate_llm(
            llm_callable=llm_callable,
            system_prompt=prompt_config["batch_section_generation_prompt"]["system"],
            user_prompt=payload,
            stage="generate_batch_sections",
            metadata={
                "lesson_title": _derive_lesson_title(generate_input),
                "batch_index": batch_index,
                "section_ids": [s.section_id for s in batch],
            },
        )

        # Parse batch response
        presentation_sections = _parse_batch_presentation_section_result(
            raw_response=raw_response,
            sections=batch,
            section_pages_map=section_pages_map,
            start_index=start_index,
        )

        # Validate each section
        results = []
        errors = []
        for i, section in enumerate(batch):
            section_pages = list(section_pages_map.get(section.section_id, []))
            section_index = start_index + i + 1
            ps = presentation_sections[i]

            # Normalize
            ps = _normalize_presentation_section(
                presentation_section=ps,
                section=section,
                section_pages=section_pages,
                section_index=section_index,
            )

            # Validate
            validation_errors = _validate_presentation_section(
                presentation_section=ps,
                known_page_ids=known_page_ids,
                known_unit_ids=known_unit_ids,
                expected_section_id=section.section_id,
            )

            if validation_errors:
                if logger is not None:
                    logger.warning(
                        "Batch section %s failed validation, using fallback",
                        section.section_id,
                    )
                errors.append(
                    {
                        "section_id": section.section_id,
                        "errors": validation_errors,
                        "used_fallback": True,
                    }
                )
                results.append(_fallback_presentation_section(section, section_pages, section_index))
            else:
                errors.append(
                    {
                        "section_id": section.section_id,
                        "errors": [],
                        "used_fallback": False,
                    }
                )
                results.append(ps)

        if logger is not None:
            logger.info(
                "Batch %d/%d completed with %d sections",
                batch_index + 1,
                total_batches,
                len(results),
            )

        return results, errors

    except Exception as exc:
        if logger is not None:
            logger.warning(
                "Batch %d/%d failed: %s, falling back to individual processing",
                batch_index + 1,
                total_batches,
                exc,
            )

        # Fallback: process each section individually
        results = []
        errors = []
        for i, section in enumerate(batch):
            section_pages = list(section_pages_map.get(section.section_id, []))
            section_index = start_index + i + 1

            try:
                ps, err = _process_single_section(
                    section_index=section_index - 1,  # Convert to 0-indexed
                    section=section,
                    section_pages_map=section_pages_map,
                    generate_input=generate_input,
                    structured_content=structured_content,
                    prompt_config=prompt_config,
                    llm_callable=llm_callable,
                    known_page_ids=known_page_ids,
                    known_unit_ids=known_unit_ids,
                    logger=logger,
                    section_cache=section_cache,
                )
                results.append(ps)
                errors.append(err)
            except Exception as inner_exc:
                if logger is not None:
                    logger.warning(
                        "Fallback also failed for section %s: %s",
                        section.section_id,
                        inner_exc,
                    )
                results.append(_fallback_presentation_section(section, section_pages, section_index))
                errors.append(
                    {
                        "section_id": section.section_id,
                        "errors": [str(inner_exc)],
                        "used_fallback": True,
                    }
                )

        return results, errors


def _run_sections_parallel_with_batching(
    sections: list[SectionBlock],
    section_pages_map: dict[str, list[PageBlock]],
    generate_input: GenerateInput,
    structured_content: Any,
    prompt_config: dict[str, Any],
    llm_callable: Optional[Callable[..., Any]],
    known_page_ids: set,
    known_unit_ids: set,
    logger: Any,
    max_workers: int,
    section_cache: dict[str, PresentationSection],
    batch_size: int = 3,
) -> tuple[list[PresentationSection], list[dict[str, Any]]]:
    """Run section generation with batching + parallel processing.

    Strategy:
    1. Group sections into batches (each batch = 1 LLM call)
    2. Run multiple batch calls in parallel
    3. Fallback to individual processing if batch fails

    Args:
        sections: List of sections to process.
        section_pages_map: Precomputed mapping from section_id to section pages.
        generate_input: The generate input.
        structured_content: The structured content.
        prompt_config: Prompt configuration.
        llm_callable: LLM callable.
        known_page_ids: Set of known page IDs.
        known_unit_ids: Set of known unit IDs.
        logger: Logger instance.
        max_workers: Maximum concurrent batch workers.
        batch_size: Sections per batch.

    Returns:
        Tuple of (list of PresentationSection, list of error dicts)
    """
    # Check if batch prompt is available
    if "batch_section_generation_prompt" not in prompt_config:
        if logger is not None:
            logger.info("Batch prompt not available, using parallel individual processing")
        return _run_sections_parallel(
            sections=sections,
            section_pages_map=section_pages_map,
            generate_input=generate_input,
            structured_content=structured_content,
            prompt_config=prompt_config,
            llm_callable=llm_callable,
            known_page_ids=known_page_ids,
            known_unit_ids=known_unit_ids,
            logger=logger,
            max_workers=max_workers,
            section_cache=section_cache,
        )

    # Group sections into batches
    batches = _group_sections_for_batching(sections, section_pages_map, batch_size=batch_size)

    if logger is not None:
        logger.info(
            "Processing %d sections in %d batches (batch_size=%d)",
            len(sections),
            len(batches),
            batch_size,
        )

    # Calculate starting indices for each batch
    batch_start_indices = []
    current_index = 0
    for batch in batches:
        batch_start_indices.append(current_index)
        current_index += len(batch)

    # Prepare batch arguments
    batch_args = [
        (
            batch,
            batch_index,
            len(batches),
            section_pages_map,
            generate_input,
            structured_content,
            prompt_config,
            llm_callable,
            known_page_ids,
            known_unit_ids,
            batch_start_indices[batch_index],
            logger,
            section_cache,
        )
        for batch_index, batch in enumerate(batches)
    ]

    # Process batches in parallel with rate limiting
    limiter = RateLimiter(max_concurrent=max_workers)

    def _limited_batch_process(args):
        with limiter():
            return _process_batch_sections(*args)

    # Run batches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch_results = list(executor.map(_limited_batch_process, batch_args))

    # Flatten results
    all_results = []
    all_errors = []
    for results, errors in batch_results:
        all_results.extend(results)
        all_errors.extend(errors)

    return all_results, all_errors


def _limit_sections_and_pages(
    sections: Sequence[SectionBlock],
    pages: Sequence[PageBlock],
    max_sections: int,
) -> tuple[list[SectionBlock], list[PageBlock]]:
    limited_sections = list(sections[:max_sections])
    selected_section_ids = {section.section_id for section in limited_sections}
    limited_pages = [page for page in pages if page.section_id in selected_section_ids]

    if not limited_pages:
        selected_page_numbers = {
            page_number for section in limited_sections for page_number in section.page_range
        }
        limited_pages = [page for page in pages if page.page in selected_page_numbers]

    return limited_sections, limited_pages


def _merge_small_sections(
    sections: Sequence[SectionBlock],
    logger,
) -> list[SectionBlock]:
    merged: list[SectionBlock] = []
    buffer: list[SectionBlock] = []
    for section in sections:
        if len(section.page_range) <= 1 and section.section_type in {"content", "other"}:
            buffer.append(section)
            continue
        if len(buffer) > 1:
            merged.append(_combine_sections(buffer, logger))
        elif len(buffer) == 1:
            merged.append(buffer[0])
        buffer = []
        merged.append(section)
    if len(buffer) > 1:
        merged.append(_combine_sections(buffer, logger))
    elif len(buffer) == 1:
        merged.append(buffer[0])
    return merged


def _combine_sections(
    sections: list[SectionBlock],
    logger,
) -> SectionBlock:
    base = sections[0]
    combined = SectionBlock(
        section_id=f"{base.section_id}_combined",
        course_id=base.course_id,
        lesson_id=base.lesson_id,
        name=base.name or sections[-1].name,
        summary="；".join(sec.summary for sec in sections if sec.summary.strip()) or base.summary,
        page_range=[page for sec in sections for page in sec.page_range],
        key_points=[kp for sec in sections for kp in sec.key_points],
        knowledge_points=[kp for sec in sections for kp in sec.knowledge_points],
        source_unit_ids=[uid for sec in sections for uid in sec.source_unit_ids],
        section_type=base.section_type,
        parent_section_id=base.parent_section_id,
    )
    if logger is not None:
        logger.info(
            "Merged %d short sections into %s",
            len(sections),
            combined.section_id,
        )
    return combined


def _build_section_payload(
    generate_input: GenerateInput,
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    prompt_config: dict,
    section_prompt_context: Optional[dict[str, Any]] = None,
) -> str:
    section_payload = section_prompt_context or _build_section_prompt_context(section, section_pages)
    prompt_template = prompt_config["section_generation_prompt"]["user_template"]
    return prompt_template.format(
        lesson_title=_derive_lesson_title(generate_input),
        lesson_summary=generate_input.structured_content.lesson_summary,
        generate_instruction=generate_input.generate_instruction or "",
        teacher_notes=generate_input.teacher_notes or "",
        section_payload=json.dumps(section_payload, ensure_ascii=False, indent=2),
    )


def _build_section_generation_metadata(
    generate_input: GenerateInput,
    structured_content: Any,
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    section_prompt_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    prompt_context = section_prompt_context or _build_section_prompt_context(section, section_pages)
    return {
        "lesson_title": _derive_lesson_title(generate_input),
        "lesson_summary": structured_content.lesson_summary,
        "generate_instruction": generate_input.generate_instruction,
        "teacher_notes": generate_input.teacher_notes,
        "section": prompt_context["section"],
        "section_pages": prompt_context["pages"],
    }


def _build_section_prompt_context(
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
) -> dict[str, Any]:
    return {
        "section": _serialize_section_for_prompt(section),
        "pages": [_serialize_page_for_prompt(page) for page in section_pages],
        "knowledge_points": _dedupe_strings(section.knowledge_points[:8]),
    }


def _serialize_section_for_prompt(section: SectionBlock) -> dict[str, Any]:
    return {
        "section_id": section.section_id,
        "name": section.name,
        "summary": _clean_text(section.summary, limit=240),
        "page_range": list(section.page_range),
        "key_points": _dedupe_strings(section.key_points[:8]),
        "knowledge_points": _dedupe_strings(section.knowledge_points[:8]),
        "source_unit_ids": list(section.source_unit_ids),
        "section_type": section.section_type,
        "parent_section_id": section.parent_section_id,
    }


def _serialize_page_for_prompt(page: PageBlock) -> dict[str, Any]:
    content_excerpt = _prompt_content_excerpt(page)
    return {
        "page_id": page.page_id or f"page_{page.page}",
        "page": page.page,
        "title": page.title,
        "summary": _clean_text(page.summary, limit=240),
        "key_points": _dedupe_strings(page.key_points[:8]),
        "knowledge_points": _dedupe_strings(page.knowledge_points[:8]),
        "content": content_excerpt,
        "page_role": page.page_role,
        "source_unit_ids": list(page.source_unit_ids),
    }


def _prompt_content_excerpt(page: PageBlock) -> str:
    if page.content.strip():
        return _clean_text(page.content, limit=2400)
    if page.summary.strip():
        return _clean_text(page.summary, limit=480)
    return ""


def _call_generate_llm(
    llm_callable: Callable[..., Any],
    system_prompt: str,
    user_prompt: str,
    stage: str,
    metadata: dict[str, Any],
) -> Any:
    return llm_callable(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        stage=stage,
        metadata=metadata,
    )


def _parse_presentation_section_result(
    raw_response: Any,
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    section_index: int,
) -> PresentationSection:
    if isinstance(raw_response, PresentationSection):
        return raw_response
    if isinstance(raw_response, dict):
        payload = raw_response.get("presentation_section", raw_response)
        normalized_payload = _normalize_section_payload(payload, section, section_pages, section_index)
        return PresentationSection.model_validate(normalized_payload)
    if isinstance(raw_response, str):
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        payload = json.loads(cleaned)
        normalized_payload = _normalize_section_payload(payload, section, section_pages, section_index)
        return PresentationSection.model_validate(normalized_payload)
    raise TypeError(f"Unsupported generate LLM response type: {type(raw_response)!r}")


def _normalize_section_payload(
    payload: dict[str, Any],
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    section_index: int,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("PresentationSection payload must be a dict.")

    section_id = str(payload.get("section_id") or section.section_id).strip() or section.section_id
    title = str(payload.get("title") or payload.get("name") or section.name).strip() or section.name
    summary = str(payload.get("summary") or section.summary).strip()
    source_page_ids = _normalize_page_ids(payload.get("source_page_ids"), section_pages)
    source_unit_ids = _normalize_unit_ids(payload.get("source_unit_ids"), section, section_pages)
    cards_payload = payload.get("cards")
    cards = _normalize_cards(
        cards_payload=cards_payload,
        section=section,
        section_pages=section_pages,
        fallback_section_id=section_id,
        section_index=section_index,
    )

    return {
        "section_id": section_id,
        "title": title,
        "summary": summary,
        "cards": cards,
        "source_page_ids": source_page_ids,
        "source_unit_ids": source_unit_ids,
        "metadata": dict(payload.get("metadata") or {}),
    }


def _normalize_cards(
    cards_payload: Any,
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    fallback_section_id: str,
    section_index: int,
) -> list[dict[str, Any]]:
    if not isinstance(cards_payload, list):
        return []

    cards: list[dict[str, Any]] = []
    for card_index, item in enumerate(cards_payload, start=1):
        if not isinstance(item, dict):
            continue

        source_page_ids = _normalize_page_ids(item.get("source_page_ids"), section_pages)
        source_unit_ids = _normalize_unit_ids(item.get("source_unit_ids"), section, section_pages)
        visual_plan = _normalize_visual_plan(item.get("visual_plan") or item.get("visuals"), source_unit_ids)
        title = str(item.get("title") or item.get("card_title") or "").strip()
        if not title:
            title = _fallback_card_title(source_page_ids, section_pages, section)

        bullets = _normalize_bullets(item.get("bullets"))
        if not bullets and item.get("body_text"):
            bullets = _normalize_bullets([str(item["body_text"])])

        raw_card_type = str(item.get("card_type") or item.get("slide_type") or "").strip().lower()
        if raw_card_type not in VALID_CARD_TYPES:
            raw_card_type = _fallback_card_type_for_page_set(source_page_ids, section_pages, card_index)
        card_type = _finalize_card_type(
            raw_card_type=raw_card_type,
            title=title,
            bullets=bullets,
            source_page_ids=source_page_ids,
            section_pages=section_pages,
            section_index=section_index,
            card_index=card_index,
        )

        speaker_notes = str(item.get("speaker_notes") or item.get("notes") or "").strip()
        cards.append(
            {
                "card_id": str(item.get("card_id") or f"card_{section_index}_{card_index}"),
                "card_type": card_type,
                "title": title,
                "subtitle": _normalize_optional_text(item.get("subtitle")),
                "bullets": bullets,
                "body_text": _normalize_optional_text(item.get("body_text")),
                "speaker_notes": speaker_notes,
                "visual_plan": visual_plan,
                "source_section_ids": [fallback_section_id],
                "source_page_ids": source_page_ids,
                "source_unit_ids": source_unit_ids,
                "metadata": dict(item.get("metadata") or {}),
            }
        )

    return cards


def _normalize_visual_plan(visual_payload: Any, fallback_unit_ids: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(visual_payload, list):
        return [{"visual_type": "none", "source_unit_ids": [], "caption": "", "metadata": {}}]

    visuals: list[dict[str, Any]] = []
    for item in visual_payload:
        if not isinstance(item, dict):
            continue
        visual_type = str(item.get("visual_type") or item.get("type") or "none").strip().lower()
        if visual_type not in VALID_VISUAL_TYPES:
            visual_type = "none"
        source_unit_ids = [value for value in _normalize_string_list(item.get("source_unit_ids")) if value]
        if visual_type == "none":
            source_unit_ids = []
        elif not source_unit_ids:
            source_unit_ids = list(fallback_unit_ids)
        visuals.append(
            {
                "visual_type": visual_type,
                "source_unit_ids": source_unit_ids,
                "caption": str(item.get("caption") or "").strip(),
                "metadata": dict(item.get("metadata") or {}),
            }
        )

    return visuals or [{"visual_type": "none", "source_unit_ids": [], "caption": "", "metadata": {}}]


def _normalize_bullets(value: Any) -> list[str]:
    if isinstance(value, list):
        bullets = []
        for item in value:
            if isinstance(item, str):
                cleaned = " ".join(item.split())
                if cleaned:
                    bullets.append(cleaned)
        return _dedupe_strings(bullets[:5])
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return [cleaned] if cleaned else []
    return []


def _normalize_optional_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _normalize_page_ids(value: Any, section_pages: Sequence[PageBlock]) -> list[str]:
    known_page_ids = [page.page_id or f"page_{page.page}" for page in section_pages]
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item in known_page_ids:
                result.append(item)
        return _dedupe_strings(result)
    return _dedupe_strings(known_page_ids)


def _normalize_unit_ids(value: Any, section: SectionBlock, section_pages: Sequence[PageBlock]) -> list[str]:
    known_unit_ids = _dedupe_strings(
        unit_id for page in section_pages for unit_id in page.source_unit_ids
    ) or list(section.source_unit_ids)
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item in known_unit_ids:
                result.append(item)
        return _dedupe_strings(result)
    return _dedupe_strings(known_unit_ids)


def _fallback_card_type_for_page_set(
    source_page_ids: Sequence[str],
    section_pages: Sequence[PageBlock],
    card_index: int,
) -> str:
    page_by_id = {page.page_id or f"page_{page.page}": page for page in section_pages}
    if source_page_ids:
        first_page = page_by_id.get(source_page_ids[0])
        if first_page is not None:
            if first_page.page_role == "cover":
                return "cover"
            return CARD_TYPE_BY_PAGE_ROLE.get(first_page.page_role, "concept")
    if card_index == 1:
        return "concept"
    return "summary"


def _finalize_card_type(
    raw_card_type: str,
    title: str,
    bullets: Sequence[str],
    source_page_ids: Sequence[str],
    section_pages: Sequence[PageBlock],
    section_index: int,
    card_index: int,
) -> str:
    if raw_card_type not in VALID_CARD_TYPES:
        raw_card_type = "concept"

    if raw_card_type == "cover":
        if section_index == 1 and card_index == 1:
            return "cover"
        if _looks_like_overview_card(title, bullets):
            return "agenda"
        return _non_cover_card_type_for_page_set(source_page_ids, section_pages)

    if raw_card_type == "agenda":
        if card_index != 1 and not _looks_like_overview_card(title, bullets):
            return _non_cover_card_type_for_page_set(source_page_ids, section_pages)
        return "agenda"

    return raw_card_type


def _non_cover_card_type_for_page_set(
    source_page_ids: Sequence[str],
    section_pages: Sequence[PageBlock],
) -> str:
    page_by_id = {page.page_id or f"page_{page.page}": page for page in section_pages}
    if source_page_ids:
        first_page = page_by_id.get(source_page_ids[0])
        if first_page is not None:
            mapped = CARD_TYPE_BY_PAGE_ROLE.get(first_page.page_role, "concept")
            if mapped == "cover":
                return "concept"
            return mapped
    return "concept"


def _looks_like_overview_card(title: str, bullets: Sequence[str]) -> bool:
    combined = " ".join([title, *list(bullets)[:3]])
    return any(keyword in combined for keyword in OVERVIEW_CARD_KEYWORDS)


def _fallback_card_title(
    source_page_ids: Sequence[str],
    section_pages: Sequence[PageBlock],
    section: SectionBlock,
) -> str:
    page_by_id = {page.page_id or f"page_{page.page}": page for page in section_pages}
    for page_id in source_page_ids:
        page = page_by_id.get(page_id)
        if page is not None and page.title.strip():
            return page.title.strip()
    return section.name


def _validate_presentation_section(
    presentation_section: PresentationSection,
    known_page_ids: set[str],
    known_unit_ids: set[str],
    expected_section_id: str,
) -> list[str]:
    errors: list[str] = []
    if not presentation_section.cards:
        errors.append("cards is empty")
    if presentation_section.section_id != expected_section_id:
        errors.append(
            f"section_id mismatch: expected {expected_section_id}, got {presentation_section.section_id}"
        )
    if not presentation_section.source_page_ids:
        errors.append("source_page_ids is empty")
    if not presentation_section.source_unit_ids:
        errors.append("source_unit_ids is empty")

    for page_id in presentation_section.source_page_ids:
        if page_id not in known_page_ids:
            errors.append(f"unknown source_page_id={page_id}")
    for unit_id in presentation_section.source_unit_ids:
        if unit_id not in known_unit_ids:
            errors.append(f"unknown source_unit_id={unit_id}")

    for index, card in enumerate(presentation_section.cards, start=1):
        if card.card_type not in VALID_CARD_TYPES:
            errors.append(f"card[{index}] has invalid card_type={card.card_type}")
        if not card.title.strip():
            errors.append(f"card[{index}] title is empty")
        if not card.source_section_ids:
            errors.append(f"card[{index}] source_section_ids is empty")
        if presentation_section.section_id not in card.source_section_ids:
            errors.append(f"card[{index}] missing section_id={presentation_section.section_id}")
        if not card.source_page_ids:
            errors.append(f"card[{index}] source_page_ids is empty")
        if not card.source_unit_ids:
            errors.append(f"card[{index}] source_unit_ids is empty")
        for page_id in card.source_page_ids:
            if page_id not in known_page_ids:
                errors.append(f"card[{index}] unknown source_page_id={page_id}")
        for unit_id in card.source_unit_ids:
            if unit_id not in known_unit_ids:
                errors.append(f"card[{index}] unknown source_unit_id={unit_id}")
        for visual_index, visual in enumerate(card.visual_plan, start=1):
            if visual.visual_type not in VALID_VISUAL_TYPES:
                errors.append(
                    f"card[{index}].visual_plan[{visual_index}] invalid visual_type={visual.visual_type}"
                )

    return errors


def _normalize_presentation_section(
    presentation_section: PresentationSection,
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    section_index: int,
) -> PresentationSection:
    page_by_id = {page.page_id or f"page_{page.page}": page for page in section_pages}
    cards: list[PresentationCard] = []
    for card_index, card in enumerate(presentation_section.cards, start=1):
        source_page_ids = [
            page_id for page_id in _dedupe_strings(card.source_page_ids) if page_id in page_by_id
        ]
        if not source_page_ids:
            source_page_ids = list(presentation_section.source_page_ids)
        source_unit_ids = [
            unit_id
            for unit_id in _dedupe_strings(card.source_unit_ids)
            if unit_id in presentation_section.source_unit_ids
        ]
        if not source_unit_ids:
            source_unit_ids = list(presentation_section.source_unit_ids)

        cards.append(
            card.model_copy(
                update={
                    "card_id": card.card_id or f"card_{section_index}_{card_index}",
                    "card_type": card.card_type if card.card_type in VALID_CARD_TYPES else "concept",
                    "title": card.title or section.name,
                    "bullets": _dedupe_strings(card.bullets[:5]),
                    "speaker_notes": card.speaker_notes
                    or _build_card_speaker_notes(card.title or section.name, card.bullets),
                    "visual_plan": [
                        visual
                        if visual.visual_type in VALID_VISUAL_TYPES
                        else VisualPlan(visual_type="none", source_unit_ids=[], caption="")
                        for visual in card.visual_plan
                    ]
                    or [VisualPlan(visual_type="none", source_unit_ids=[], caption="")],
                    "source_section_ids": [section.section_id],
                    "source_page_ids": source_page_ids,
                    "source_unit_ids": source_unit_ids,
                }
            )
        )

    section_source_page_ids = _dedupe_strings(
        page_id for card in cards for page_id in card.source_page_ids
    ) or [page.page_id or f"page_{page.page}" for page in section_pages]
    section_source_unit_ids = _dedupe_strings(
        unit_id for card in cards for unit_id in card.source_unit_ids
    ) or list(section.source_unit_ids)

    return presentation_section.model_copy(
        update={
            "section_id": section.section_id,
            "title": presentation_section.title or section.name,
            "summary": presentation_section.summary
            or section.summary
            or _build_section_summary(section_pages),
            "cards": cards,
            "source_page_ids": section_source_page_ids,
            "source_unit_ids": section_source_unit_ids,
        }
    )


def _fallback_presentation_section(
    section: SectionBlock,
    section_pages: Sequence[PageBlock],
    section_index: int,
) -> PresentationSection:
    cards: list[PresentationCard] = []
    for card_index, page in enumerate(section_pages, start=1):
        page_id = page.page_id or f"page_{page.page}"
        bullets = _build_card_bullets_from_page(page)
        card_type = _finalize_card_type(
            raw_card_type=CARD_TYPE_BY_PAGE_ROLE.get(page.page_role, "concept"),
            title=page.title or section.name or f"Page {page.page}",
            bullets=bullets,
            source_page_ids=[page_id],
            section_pages=section_pages,
            section_index=section_index,
            card_index=card_index,
        )
        cards.append(
            PresentationCard(
                card_id=f"card_{section_index}_{card_index}",
                card_type=card_type,
                title=page.title or section.name or f"Page {page.page}",
                subtitle=None,
                bullets=bullets,
                body_text=None,
                speaker_notes=_build_card_speaker_notes(page.title or section.name, bullets, page.summary),
                visual_plan=[_infer_visual_plan_from_page(page)],
                source_section_ids=[section.section_id],
                source_page_ids=[page_id],
                source_unit_ids=list(page.source_unit_ids),
                metadata={"fallback": True},
            )
        )

    if not cards:
        cards.append(
            PresentationCard(
                card_id=f"card_{section_index}_1",
                card_type="summary",
                title=section.name or f"Section {section_index}",
                subtitle=None,
                bullets=_dedupe_strings(
                    section.key_points[:4]
                    or section.knowledge_points[:4]
                    or [section.summary or section.name]
                ),
                body_text=None,
                speaker_notes=_clean_text(section.summary or section.name),
                visual_plan=[VisualPlan(visual_type="none", source_unit_ids=[], caption="")],
                source_section_ids=[section.section_id],
                source_page_ids=[],
                source_unit_ids=list(section.source_unit_ids),
                metadata={"fallback": True},
            )
        )

    return PresentationSection(
        section_id=section.section_id,
        title=section.name or f"Section {section_index}",
        summary=section.summary or _build_section_summary(section_pages),
        cards=cards,
        source_page_ids=_dedupe_strings(page.page_id or f"page_{page.page}" for page in section_pages),
        source_unit_ids=_dedupe_strings(unit_id for page in section_pages for unit_id in page.source_unit_ids)
        or list(section.source_unit_ids),
        metadata={"fallback": True},
    )


def _build_card_bullets_from_page(page: PageBlock) -> list[str]:
    candidates = list(page.key_points) + list(page.knowledge_points)
    if not candidates:
        summary = _clean_text(page.summary or page.content, limit=90)
        candidates = [summary] if summary else []
    return _dedupe_strings(candidates[:4])


def _build_card_speaker_notes(title: str, bullets: Sequence[str], summary: str = "") -> str:
    parts = []
    if title:
        parts.append(f"本页主题：{title}")
    if bullets:
        parts.append("重点包括：" + "；".join(bullets[:3]))
    if summary:
        cleaned_summary = _clean_text(summary, limit=120)
        if cleaned_summary:
            parts.append(cleaned_summary)
    return " ".join(parts).strip()


def _infer_visual_plan_from_page(page: PageBlock) -> VisualPlan:
    summary_text = f"{page.title} {page.summary} {page.content}".lower()
    if any(keyword in summary_text for keyword in ["表", "table"]):
        visual_type = "source_table"
    elif any(keyword in summary_text for keyword in ["公式", "equation", "="]):
        visual_type = "source_formula"
    elif page.file_type in {"ppt", "pptx", "pdf"}:
        visual_type = "source_image"
    else:
        visual_type = "none"
    source_unit_ids = list(page.source_unit_ids) if visual_type != "none" else []
    return VisualPlan(
        visual_type=visual_type,
        source_unit_ids=source_unit_ids,
        caption="",
        metadata={},
    )


def _build_section_summary(section_pages: Sequence[PageBlock]) -> str:
    parts: list[str] = []
    for page in section_pages:
        if page.summary:
            parts.append(_clean_text(page.summary, limit=80))
        elif page.title:
            parts.append(page.title)
        if len(parts) >= 2:
            break
    return "；".join(part for part in parts if part)


def _assemble_presentation_outline(
    generate_input: GenerateInput,
    sections: Sequence[PresentationSection],
) -> PresentationOutline:
    structured_content = generate_input.structured_content
    lesson_title = _derive_lesson_title(generate_input)
    knowledge_points = _dedupe_strings(
        list(structured_content.knowledge_points)
        + [bullet for section in sections for card in section.cards for bullet in card.bullets]
    )
    metadata = {
        "source": "generate_pipeline",
        "section_count": len(sections),
        "card_count": sum(len(section.cards) for section in sections),
    }
    return PresentationOutline(
        lesson_title=lesson_title,
        lesson_summary=_build_outline_lesson_summary(structured_content.lesson_summary, sections),
        sections=list(sections),
        knowledge_points=knowledge_points,
        metadata=metadata,
    )


def _build_outline_lesson_summary(
    source_summary: str,
    sections: Sequence[PresentationSection],
) -> str:
    cleaned_source = _clean_text(source_summary, limit=180)
    if (
        cleaned_source
        and len(cleaned_source) <= 140
        and cleaned_source.count("；") <= 2
        and cleaned_source.count(";") <= 2
    ):
        return cleaned_source

    section_summaries = [
        _clean_text(section.summary, limit=60) for section in sections if section.summary.strip()
    ]
    section_summaries = _dedupe_strings(section_summaries[:3])
    if section_summaries:
        return "；".join(section_summaries)
    return cleaned_source


def _validate_presentation_outline(
    outline: PresentationOutline,
    known_page_ids: set[str],
    known_unit_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    if not outline.lesson_title.strip():
        errors.append("lesson_title is empty")
    if not outline.sections:
        errors.append("sections is empty")

    for section_index, section in enumerate(outline.sections, start=1):
        section_errors = _validate_presentation_section(
            section,
            known_page_ids=known_page_ids,
            known_unit_ids=known_unit_ids,
            expected_section_id=section.section_id,
        )
        for error in section_errors:
            errors.append(f"section[{section_index}] {error}")

    return errors


def _fallback_presentation_outline(
    generate_input: GenerateInput,
    sections: Sequence[SectionBlock],
) -> PresentationOutline:
    if not sections:
        sections = _synthesize_sections_from_pages(generate_input.lesson_id, generate_input.pages)
    fallback_sections = [
        _fallback_presentation_section(section, _select_section_pages(section, generate_input.pages), index)
        for index, section in enumerate(sections, start=1)
    ]
    outline = _assemble_presentation_outline(generate_input, fallback_sections)
    outline.metadata["fallback"] = True
    return outline


def _synthesize_sections_from_pages(lesson_id: str, pages: Sequence[PageBlock]) -> list[SectionBlock]:
    sections: list[SectionBlock] = []
    for index, page in enumerate(sorted(pages, key=lambda item: item.page), start=1):
        sections.append(
            SectionBlock(
                section_id=page.section_id or f"sec_{index}",
                course_id=page.course_id,
                lesson_id=page.lesson_id or lesson_id,
                name=page.title or f"Section {index}",
                summary=page.summary,
                page_range=[page.page],
                key_points=list(page.key_points),
                knowledge_points=list(page.knowledge_points),
                source_unit_ids=list(page.source_unit_ids),
                section_type="content",
            )
        )
    return sections


def _build_teacher_feedback_text(outline: PresentationOutline) -> str:
    section_titles = [section.title for section in outline.sections[:3] if section.title]
    card_count = sum(len(section.cards) for section in outline.sections)
    topics_text = "、".join(section_titles) if section_titles else "课程重点内容"
    return (
        f"已根据上传资料整理出《{outline.lesson_title}》的展示内容，"
        f"当前共生成 {len(outline.sections)} 个章节、{card_count} 张展示卡片，"
        f"重点覆盖 {topics_text}。"
        "结果已包含展示结构、讲解稿基础和 PPT 大纲，可继续用于前端展示或后续导出。"
    )


def _build_lesson_script(generate_input: GenerateInput, outline: PresentationOutline) -> LessonScript:
    script_blocks: list[ScriptBlock] = []
    block_index = 1
    for section in outline.sections:
        for card in section.cards:
            page_numbers = _page_numbers_from_ids(card.source_page_ids)
            script_text = _build_script_text_from_card(card)
            script_blocks.append(
                ScriptBlock(
                    script_block_id=f"script_{block_index}",
                    course_id=generate_input.course_id,
                    lesson_id=generate_input.lesson_id,
                    section_id=section.section_id,
                    title=card.title,
                    page_range=page_numbers,
                    script_text=script_text,
                    key_points=list(card.bullets),
                    block_type=SCRIPT_BLOCK_TYPE_BY_CARD_TYPE.get(card.card_type, "teaching"),
                )
            )
            block_index += 1

    return LessonScript(
        lesson_title=outline.lesson_title,
        script_blocks=script_blocks,
        metadata={"source": "presentation_outline"},
    )


def _build_script_text_from_card(card: PresentationCard) -> str:
    parts = []
    if card.title:
        parts.append(f"本部分讲解 {card.title}。")
    if card.bullets:
        parts.append("重点包括：" + "；".join(card.bullets[:4]) + "。")
    if card.speaker_notes:
        parts.append(card.speaker_notes)
    return " ".join(part.strip() for part in parts if part and part.strip())


def _page_numbers_from_ids(page_ids: Sequence[str]) -> list[int]:
    numbers: list[int] = []
    for page_id in page_ids:
        suffix = page_id.split("_")[-1]
        if suffix.isdigit():
            numbers.append(int(suffix))
    return numbers


def _build_ppt_outline(outline: PresentationOutline) -> PPTOutline:
    slides: list[SlideOutline] = []
    slide_index = 1
    for section in outline.sections:
        for card in section.cards:
            slides.append(
                SlideOutline(
                    slide_id=f"slide_{slide_index}",
                    slide_type=card.card_type,
                    layout_template=_map_card_type_to_layout_template(card.card_type),
                    title=card.title,
                    subtitle=card.subtitle,
                    bullets=list(card.bullets),
                    speaker_notes=card.speaker_notes,
                    visual_plan=list(card.visual_plan),
                    source_section_ids=list(card.source_section_ids),
                    source_page_ids=list(card.source_page_ids),
                    source_unit_ids=list(card.source_unit_ids),
                    metadata={"derived_from_card_id": card.card_id},
                )
            )
            slide_index += 1

    return PPTOutline(
        deck_title=outline.lesson_title,
        theme_name="default_teaching",
        slides=slides,
        metadata={"source": "presentation_outline"},
    )


def _map_card_type_to_layout_template(card_type: str) -> str:
    return LAYOUT_TEMPLATE_BY_CARD_TYPE.get(card_type, "content_layout")


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = " ".join(item.split())
            if cleaned:
                result.append(cleaned)
    return _dedupe_strings(result)


def _dedupe_strings(items: Iterable[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        cleaned = " ".join(str(item).split())
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _clean_text(text: str, limit: int = 140) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _response_preview(raw_response: Any, limit: int = 500) -> str:
    if isinstance(raw_response, (dict, list)):
        preview = json.dumps(raw_response, ensure_ascii=False)
    else:
        preview = str(raw_response)
    compact = " ".join(preview.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _section_cache_key(generate_input: GenerateInput, section: SectionBlock) -> str:
    parts = [
        generate_input.lesson_id or "",
        section.section_id,
        (generate_input.generate_instruction or "").strip(),
        (generate_input.teacher_notes or "").strip(),
        "|".join(sorted(section.source_unit_ids)),
    ]
    return "|".join(parts)
