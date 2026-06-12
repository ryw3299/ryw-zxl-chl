import json
import re
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import yaml

from src.schemas import DocumentUnit, PageBlock, ParsedDocument, SectionBlock, StructuredLessonContent
from src.utils.rate_limiter import RateLimiter

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[1] / "agents" / "prompts" / "file_parser.yaml"
DEFAULT_CHUNK_THRESHOLD = 8
DEFAULT_CHUNK_SIZE = 6
DEFAULT_BOUNDARY_SHIFT = 1
VALID_PAGE_ROLES = {
    "cover",
    "agenda",
    "content",
    "definition",
    "formula",
    "example",
    "summary",
    "exercise",
    "other",
}
VALID_SECTION_TYPES = {"intro", "content", "example", "summary", "exercise", "other"}


def run_file_structuring_pipeline(
    parsed_document: ParsedDocument,
    baseline_structured_content: StructuredLessonContent,
    parse_instruction: Optional[str] = None,
    llm_callable: Optional[Callable[..., Any]] = None,
    prompt_path: Optional[str] = None,
    logger=None,
    chunk_threshold: int = DEFAULT_CHUNK_THRESHOLD,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    boundary_shift: int = DEFAULT_BOUNDARY_SHIFT,
    use_global_merge_llm: bool = False,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> dict:
    prompt_config = _load_prompt_config(prompt_path)
    units = list(parsed_document.units)
    parse_instruction = (
        parse_instruction if parse_instruction is not None else parsed_document.parse_instruction
    )
    strategy = (
        "chunked" if _should_use_chunked_structuring(units, threshold=chunk_threshold) else "single_pass"
    )
    chunk_count = 1

    if logger is not None:
        logger.info(
            "Starting file structuring pipeline with %d unit(s), strategy=%s",
            len(units),
            strategy,
        )

    if not units:
        return _fallback_result(
            baseline_structured_content=baseline_structured_content,
            strategy=strategy,
            chunk_count=0,
            validation_errors=["ParsedDocument has no units."],
            logger=logger,
        )

    if llm_callable is None:
        return _fallback_result(
            baseline_structured_content=baseline_structured_content,
            strategy=strategy,
            chunk_count=1
            if strategy == "single_pass"
            else len(_chunk_units(units, chunk_size, boundary_shift)),
            validation_errors=["No llm_callable was provided to the file structuring pipeline."],
            logger=logger,
        )

    try:
        if strategy == "single_pass":
            payload = _build_single_pass_payload(parsed_document, parse_instruction)
            raw_response = _call_structuring_llm(
                llm_callable=llm_callable,
                system_prompt=prompt_config["single_pass_prompt"]["system"],
                user_prompt=payload,
                stage="single_pass",
                metadata={
                    "parsed_document": _build_parsed_document_context(parsed_document),
                    "parse_instruction": parse_instruction,
                },
            )
            structured_content = _parse_structured_result(raw_response, parsed_document, parse_instruction)
            single_pass_preview = _response_preview(raw_response)
        else:
            chunks = _chunk_units(units, chunk_size=chunk_size, boundary_shift=boundary_shift)
            chunk_count = len(chunks)
            if logger is not None:
                logger.info("Chunked structuring enabled with %d chunk(s)", chunk_count)

            # Determine whether to use parallel processing
            effective_max_workers = max_workers if max_workers is not None and max_workers > 1 else 1

            local_results: list[StructuredLessonContent] = []
            local_response_previews: list[dict[str, Any]] = []

            if effective_max_workers > 1:
                # Parallel processing
                local_results, local_errors, first_error_preview = _run_chunks_parallel(
                    chunks=chunks,
                    parsed_document=parsed_document,
                    parse_instruction=parse_instruction,
                    prompt_config=prompt_config,
                    llm_callable=llm_callable,
                    logger=logger,
                    max_workers=effective_max_workers,
                    batch_size=batch_size if batch_size else 3,
                )

                # Build response previews for logging
                for i, result in enumerate(local_results):
                    local_response_previews.append(
                        {
                            "chunk_index": i + 1,
                            "response_preview": "(parallel mode)",
                        }
                    )

                # Check if any chunks failed
                if local_results and any(err.get("errors") for err in local_errors):
                    error_chunks = [err for err in local_errors if err.get("errors")]
                    if logger is not None:
                        logger.warning(
                            "Some chunks failed in parallel mode: %s",
                            error_chunks,
                        )
                    return _fallback_result(
                        baseline_structured_content=baseline_structured_content,
                        strategy=strategy,
                        chunk_count=chunk_count,
                        validation_errors=[
                            f"Chunk {err.get('chunk_index')} failed: {err.get('errors')}"
                            for err in error_chunks
                        ],
                        debug_info={"local_response_previews": local_response_previews},
                        logger=logger,
                    )
            else:
                # Serial processing (original behavior)
                for index, chunk in enumerate(chunks, start=1):
                    if logger is not None:
                        logger.info(
                            "Structuring chunk %d/%d with %d unit(s)",
                            index,
                            chunk_count,
                            len(chunk),
                        )

                    payload = _build_chunk_payload(
                        parsed_document=parsed_document,
                        chunk_units=chunk,
                        parse_instruction=parse_instruction,
                        chunk_index=index,
                        total_chunks=chunk_count,
                    )
                    raw_response = _call_structuring_llm(
                        llm_callable=llm_callable,
                        system_prompt=prompt_config["local_chunk_prompt"]["system"],
                        user_prompt=payload,
                        stage="local_chunk",
                        metadata={
                            "chunk_index": index,
                            "total_chunks": chunk_count,
                            "chunk_units": [_serialize_unit(unit) for unit in chunk],
                            "parse_instruction": parse_instruction,
                        },
                    )
                    local_response_previews.append(
                        {
                            "chunk_index": index,
                            "response_preview": _response_preview(raw_response),
                        }
                    )
                    local_structured_content = _parse_structured_result(
                        raw_response, parsed_document, parse_instruction
                    )
                    local_structured_content = _normalize_structured_content(
                        local_structured_content,
                        parsed_document=parsed_document,
                        parse_instruction=parse_instruction,
                        units_scope=chunk,
                    )
                    local_errors_chunk = _validate_structured_content(local_structured_content, chunk)
                    if local_errors_chunk:
                        if logger is not None:
                            logger.warning(
                                "Chunk %d raw LLM response preview: %s",
                                index,
                                local_response_previews[-1]["response_preview"],
                            )
                        return _fallback_result(
                            baseline_structured_content=baseline_structured_content,
                            strategy=strategy,
                            chunk_count=chunk_count,
                            validation_errors=[
                                f"Chunk {index} validation failed: {error}" for error in local_errors_chunk
                            ],
                            debug_info={"local_response_previews": local_response_previews},
                            logger=logger,
                        )
                    local_results.append(local_structured_content)

            if use_global_merge_llm:
                payload = _build_global_merge_payload(local_results, parse_instruction)
                raw_response = _call_structuring_llm(
                    llm_callable=llm_callable,
                    system_prompt=prompt_config["global_merge_prompt"]["system"],
                    user_prompt=payload,
                    stage="global_merge",
                    metadata={
                        "local_results": [result.model_dump(mode="python") for result in local_results],
                        "parse_instruction": parse_instruction,
                    },
                )
                structured_content = _parse_structured_result(
                    raw_response, parsed_document, parse_instruction
                )
                global_merge_preview = _response_preview(raw_response)
            else:
                structured_content = _merge_local_results(
                    local_results=local_results,
                    parsed_document=parsed_document,
                    parse_instruction=parse_instruction,
                    baseline_structured_content=baseline_structured_content,
                )

        structured_content = _normalize_structured_content(
            structured_content,
            parsed_document=parsed_document,
            parse_instruction=parse_instruction,
            units_scope=units,
        )
        validation_errors = _validate_structured_content(structured_content, units)
        if validation_errors:
            debug_info: dict[str, Any] = {}
            if strategy == "single_pass":
                debug_info["single_pass_response_preview"] = single_pass_preview
            elif use_global_merge_llm:
                debug_info["global_merge_response_preview"] = global_merge_preview
            return _fallback_result(
                baseline_structured_content=baseline_structured_content,
                strategy=strategy,
                chunk_count=chunk_count,
                validation_errors=validation_errors,
                debug_info=debug_info,
                logger=logger,
            )

        if logger is not None:
            logger.info(
                "File structuring pipeline finished with %d page(s) and %d section(s)",
                len(structured_content.pages),
                len(structured_content.sections),
            )

        return {
            "structured_content": structured_content,
            "used_fallback": False,
            "strategy": strategy,
            "chunk_count": chunk_count,
            "validation_errors": [],
            "debug_info": {},
        }
    except Exception as exc:
        return _fallback_result(
            baseline_structured_content=baseline_structured_content,
            strategy=strategy,
            chunk_count=chunk_count,
            validation_errors=[str(exc)],
            debug_info={},
            logger=logger,
        )


def _load_prompt_config(prompt_path: Optional[str] = None) -> dict:
    resolved_path = Path(prompt_path) if prompt_path else DEFAULT_PROMPT_PATH
    data = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("file_parser prompt config must load into a dict.")

    required_keys = {"single_pass_prompt", "local_chunk_prompt", "global_merge_prompt"}
    missing = sorted(required_keys - set(data.keys()))
    if missing:
        raise ValueError(f"Prompt config is missing required keys: {missing}")

    return data


def _should_use_chunked_structuring(
    units: Sequence[DocumentUnit], threshold: int = DEFAULT_CHUNK_THRESHOLD
) -> bool:
    return len(units) > threshold


def _chunk_units(
    units: Sequence[DocumentUnit],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    boundary_shift: int = DEFAULT_BOUNDARY_SHIFT,
) -> list[list[DocumentUnit]]:
    if not units:
        return []

    chunks: list[list[DocumentUnit]] = []
    start = 0
    total = len(units)

    while start < total:
        target_end = min(start + chunk_size, total)
        if target_end >= total:
            chunks.append(list(units[start:total]))
            break

        split_after = _choose_chunk_boundary(units, start, target_end, boundary_shift)
        chunks.append(list(units[start:split_after]))
        start = split_after

    return chunks


def _process_single_chunk(
    chunk_index: int,
    chunk: list[DocumentUnit],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
    prompt_config: dict[str, Any],
    llm_callable: Optional[Callable[..., Any]],
    chunk_count: int,
    logger: Any,
) -> tuple[int, StructuredLessonContent, dict[str, Any], Optional[str]]:
    """Process a single chunk to generate StructuredLessonContent.

    Returns:
        Tuple of (chunk_index, structured_content, error_dict, response_preview)
    """
    index = chunk_index + 1

    if logger is not None:
        logger.info(
            "Structuring chunk %d/%d with %d unit(s)",
            index,
            chunk_count,
            len(chunk),
        )

    try:
        payload = _build_chunk_payload(
            parsed_document=parsed_document,
            chunk_units=chunk,
            parse_instruction=parse_instruction,
            chunk_index=index,
            total_chunks=chunk_count,
        )
        raw_response = _call_structuring_llm(
            llm_callable=llm_callable,
            system_prompt=prompt_config["local_chunk_prompt"]["system"],
            user_prompt=payload,
            stage="local_chunk",
            metadata={
                "chunk_index": index,
                "total_chunks": chunk_count,
                "chunk_units": [_serialize_unit(unit) for unit in chunk],
                "parse_instruction": parse_instruction,
            },
        )
        response_preview = _response_preview(raw_response)
        local_structured_content = _parse_structured_result(raw_response, parsed_document, parse_instruction)
        local_structured_content = _normalize_structured_content(
            local_structured_content,
            parsed_document=parsed_document,
            parse_instruction=parse_instruction,
            units_scope=chunk,
        )
        local_errors = _validate_structured_content(local_structured_content, chunk)

        if local_errors:
            error_dict = {
                "chunk_index": index,
                "errors": local_errors,
            }
            return index, None, error_dict, response_preview

        return index, local_structured_content, {"chunk_index": index, "errors": []}, response_preview

    except Exception as exc:
        error_dict = {
            "chunk_index": index,
            "errors": [str(exc)],
        }
        if logger is not None:
            logger.warning("Chunk %d failed: %s", index, exc)
        return index, None, error_dict, None


def _run_chunks_parallel(
    chunks: list[list[DocumentUnit]],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
    prompt_config: dict[str, Any],
    llm_callable: Optional[Callable[..., Any]],
    logger: Any,
    max_workers: int,
    batch_size: int,
) -> tuple[list[StructuredLessonContent], list[dict[str, Any]], Optional[str]]:
    """Run chunk processing in parallel.

    Returns:
        Tuple of (list of StructuredLessonContent, list of error dicts, first error preview)
    """
    chunk_count = len(chunks)

    if logger is not None:
        logger.info(
            "Processing %d chunks in parallel with %d workers, batch_size=%d",
            chunk_count,
            max_workers,
            batch_size,
        )

    limiter = RateLimiter(max_concurrent=max_workers)

    def _limited_process(args):
        with limiter():
            return _process_single_chunk(*args)

    # Prepare arguments
    args_list = [
        (
            chunk_index,
            chunk,
            parsed_document,
            parse_instruction,
            prompt_config,
            llm_callable,
            chunk_count,
            logger,
        )
        for chunk_index, chunk in enumerate(chunks)
    ]

    # Run in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_limited_process, args_list))

    # Sort results by chunk index to maintain order
    results.sort(key=lambda x: x[0])

    # Unpack results
    local_results = []
    local_errors = []
    first_error_preview = None

    for chunk_index, structured_content, error_dict, response_preview in results:
        if structured_content is not None:
            local_results.append(structured_content)
            local_errors.append(error_dict)
        else:
            # Chunk failed, return fallback immediately
            if first_error_preview is None:
                first_error_preview = response_preview
            return [], [error_dict], first_error_preview

    return local_results, local_errors, first_error_preview


def _choose_chunk_boundary(
    units: Sequence[DocumentUnit],
    start: int,
    target_end: int,
    boundary_shift: int,
) -> int:
    min_split = max(start + 1, target_end - boundary_shift)
    max_split = min(len(units) - 1, target_end + boundary_shift)
    best_split = target_end
    best_score = float("-inf")
    best_distance = float("inf")

    for split_after in range(min_split, max_split + 1):
        score = _boundary_score(units, split_after)
        distance = abs(split_after - target_end)
        if score > best_score or (score == best_score and distance < best_distance):
            best_score = score
            best_split = split_after
            best_distance = distance

    return best_split


def _boundary_score(units: Sequence[DocumentUnit], split_after: int) -> float:
    left = units[split_after - 1]
    right = units[split_after]
    similarity = _unit_similarity(left, right)
    role_change_bonus = 1.5 if _infer_unit_role(left) != _infer_unit_role(right) else 0.0
    title_change_bonus = 1.0 if _normalize_title(left.title) != _normalize_title(right.title) else 0.0
    continuity_penalty = 2.0 if similarity > 0.55 else 0.0
    return role_change_bonus + title_change_bonus + (1.0 - similarity) - continuity_penalty


def _unit_similarity(left: DocumentUnit, right: DocumentUnit) -> float:
    left_tokens = _tokenize(f"{left.title} {left.text}")
    right_tokens = _tokenize(f"{right.title} {right.text}")
    if not left_tokens or not right_tokens:
        return 0.0

    overlap = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(overlap) / max(len(union), 1)


def _tokenize(text: str) -> set[str]:
    normalized = text.lower()
    tokens = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", normalized)
    return {token for token in tokens if token}


def _normalize_title(title: str) -> str:
    return " ".join((title or "").strip().lower().split())


def _infer_unit_role(unit: DocumentUnit) -> str:
    title = (unit.title or "").lower()
    text = (unit.text or "").lower()
    combined = f"{title} {text}"

    if unit.index == 1 and combined.strip():
        return "cover"
    if any(keyword in combined for keyword in ["目录", "agenda", "contents", "table of contents"]):
        return "agenda"
    if any(keyword in combined for keyword in ["定义", "definition", "概念"]):
        return "definition"
    if any(keyword in combined for keyword in ["公式", "formula", "定理"]) or "=" in unit.text:
        return "formula"
    if any(keyword in combined for keyword in ["例题", "example", "案例"]):
        return "example"
    if any(keyword in combined for keyword in ["总结", "summary", "小结", "结论"]):
        return "summary"
    if any(keyword in combined for keyword in ["练习", "exercise", "思考题", "习题"]):
        return "exercise"
    if combined.strip():
        return "content"
    return "other"


def _build_single_pass_payload(parsed_document: ParsedDocument, parse_instruction: Optional[str]) -> str:
    context = _build_parsed_document_context(parsed_document)
    return (
        "Convert the following ParsedDocument into one StructuredLessonContent object.\n\n"
        f"parse_instruction:\n{parse_instruction or ''}\n\n"
        "ParsedDocument:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _build_chunk_payload(
    parsed_document: ParsedDocument,
    chunk_units: Sequence[DocumentUnit],
    parse_instruction: Optional[str],
    chunk_index: int,
    total_chunks: int,
) -> str:
    chunk_context = [_serialize_unit(unit) for unit in chunk_units]
    chunk_metadata = {
        "course_id": parsed_document.course_id,
        "lesson_id": parsed_document.lesson_id,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "unit_count": len(chunk_units),
        "unit_index_range": [chunk_units[0].index, chunk_units[-1].index],
    }
    return (
        "Build a local structured result for the following chunk of source units.\n\n"
        f"parse_instruction:\n{parse_instruction or ''}\n\n"
        "chunk_metadata:\n"
        f"{json.dumps(chunk_metadata, ensure_ascii=False, indent=2)}\n\n"
        "chunk_units:\n"
        f"{json.dumps(chunk_context, ensure_ascii=False, indent=2)}"
    )


def _build_global_merge_payload(
    local_results: Sequence[StructuredLessonContent],
    parse_instruction: Optional[str],
) -> str:
    payload = [result.model_dump(mode="python") for result in local_results]
    return (
        "Merge the following local structured results into one final StructuredLessonContent object.\n\n"
        f"parse_instruction:\n{parse_instruction or ''}\n\n"
        "local_structured_results:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _build_parsed_document_context(parsed_document: ParsedDocument) -> dict:
    return {
        "course_id": parsed_document.course_id,
        "lesson_id": parsed_document.lesson_id,
        "parse_instruction": parsed_document.parse_instruction,
        "knowledge_points": list(parsed_document.knowledge_points),
        "units": [_serialize_unit(unit) for unit in parsed_document.units],
    }


def _serialize_unit(unit: DocumentUnit) -> dict:
    return {
        "unit_id": unit.unit_id,
        "unit_type": unit.unit_type,
        "index": unit.index,
        "title": unit.title,
        "text": unit.text,
        "source_ref": unit.source_ref,
        "source_asset_id": unit.source_asset_id,
        "metadata": dict(unit.metadata),
    }


def _call_structuring_llm(
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


def _parse_structured_result(
    raw_response: Any,
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
) -> StructuredLessonContent:
    if isinstance(raw_response, StructuredLessonContent):
        return raw_response
    if isinstance(raw_response, dict):
        payload = (
            raw_response["structured_content"]
            if "structured_content" in raw_response and isinstance(raw_response["structured_content"], dict)
            else raw_response
        )
        payload = _coerce_structured_payload(payload, parsed_document, parse_instruction)
        return StructuredLessonContent.model_validate(
            _inject_structured_defaults(payload, parsed_document, parse_instruction)
        )
    if isinstance(raw_response, str):
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        payload = json.loads(cleaned)
        payload = _coerce_structured_payload(payload, parsed_document, parse_instruction)
        return StructuredLessonContent.model_validate(
            _inject_structured_defaults(payload, parsed_document, parse_instruction)
        )
    raise TypeError(f"Unsupported LLM response type: {type(raw_response)!r}")


def _coerce_structured_payload(
    payload: dict[str, Any],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    if "local_structured_summary" in payload and (not payload.get("pages")) and (not payload.get("sections")):
        return _coerce_local_structured_summary_payload(payload, parsed_document, parse_instruction)

    if payload.get("sections") and not payload.get("pages"):
        return _backfill_pages_from_sections_payload(payload, parsed_document, parse_instruction)

    return _normalize_loose_structured_payload(payload, parsed_document, parse_instruction)


def _coerce_local_structured_summary_payload(
    payload: dict[str, Any],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
) -> dict[str, Any]:
    items = payload.get("local_structured_summary")
    if not isinstance(items, list):
        return payload

    units_by_id = {unit.unit_id: unit for unit in parsed_document.units}
    sections: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    knowledge_points: list[str] = []
    lesson_summary_parts: list[str] = []
    seen_page_units: set[str] = set()

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        source_unit_ids = _filter_known_unit_ids(item.get("source_unit_ids", []), units_by_id)
        if not source_unit_ids:
            continue

        section_name = (item.get("section_title") or item.get("name") or f"Section {index}").strip()
        section_summary = _clean_summary_text(
            item.get("summary") or item.get("section_summary") or section_name
        )
        section_points = _dedupe_strings(
            item.get("knowledge_points", []) or item.get("key_points", []) or [section_name]
        )
        section_id = f"sec_{index}"
        section_type = item.get("section_type")
        if section_type not in VALID_SECTION_TYPES:
            section_type = _infer_section_type_from_units(source_unit_ids, units_by_id)

        sections.append(
            {
                "section_id": section_id,
                "name": section_name,
                "summary": section_summary,
                "page_range": [
                    units_by_id[unit_id].index for unit_id in source_unit_ids if unit_id in units_by_id
                ],
                "key_points": section_points,
                "knowledge_points": section_points,
                "source_unit_ids": source_unit_ids,
                "section_type": section_type,
            }
        )

        lesson_summary_parts.append(section_summary or section_name)
        knowledge_points.extend(section_points)

        for unit_id in source_unit_ids:
            if unit_id in seen_page_units or unit_id not in units_by_id:
                continue

            unit = units_by_id[unit_id]
            page_points = _dedupe_strings(
                item.get("knowledge_points", []) or item.get("key_points", []) or [unit.title or section_name]
            )
            pages.append(
                {
                    "page": unit.index,
                    "title": unit.title or unit.source_ref or section_name,
                    "content": unit.text,
                    "summary": _clean_summary_text(unit.text) or section_summary,
                    "key_points": page_points,
                    "knowledge_points": page_points,
                    "source_unit_ids": [unit_id],
                    "page_role": _infer_unit_role(unit),
                    "section_id": section_id,
                    "file_id": unit.source_asset_id,
                    "file_type": unit.metadata.get("file_type"),
                }
            )
            seen_page_units.add(unit_id)

    if not pages and not sections:
        return payload

    return {
        "course_id": parsed_document.course_id,
        "lesson_id": parsed_document.lesson_id,
        "source_asset_ids": [asset.asset_id for asset in parsed_document.source_assets if asset.asset_id],
        "lesson_summary": _build_summary_from_parts(lesson_summary_parts),
        "pages": pages,
        "sections": sections,
        "knowledge_points": _dedupe_strings(knowledge_points),
        "parse_instruction": parse_instruction,
        "metadata": {
            "coerced_from_local_structured_summary": True,
            "original_top_level_keys": sorted(payload.keys()),
        },
    }


def _backfill_pages_from_sections_payload(
    payload: dict[str, Any],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
) -> dict[str, Any]:
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return payload

    units_by_id = {unit.unit_id: unit for unit in parsed_document.units}
    pages: list[dict[str, Any]] = []
    seen_page_units: set[str] = set()

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_id = section.get("section_id")
        section_name = section.get("name") or section.get("section_title") or "Section"
        section_summary = _clean_summary_text(section.get("summary") or section_name)
        source_unit_ids = _filter_known_unit_ids(section.get("source_unit_ids", []), units_by_id)
        for unit_id in source_unit_ids:
            if unit_id in seen_page_units:
                continue
            unit = units_by_id.get(unit_id)
            if unit is None:
                continue
            page_points = _dedupe_strings(
                section.get("knowledge_points", [])
                or section.get("key_points", [])
                or [unit.title or section_name]
            )
            pages.append(
                {
                    "page": unit.index,
                    "title": unit.title or unit.source_ref or section_name,
                    "content": unit.text,
                    "summary": _clean_summary_text(unit.text) or section_summary,
                    "key_points": page_points,
                    "knowledge_points": page_points,
                    "source_unit_ids": [unit_id],
                    "page_role": _infer_unit_role(unit),
                    "section_id": section_id,
                    "file_id": unit.source_asset_id,
                    "file_type": unit.metadata.get("file_type"),
                }
            )
            seen_page_units.add(unit_id)

    if not pages:
        return payload

    enriched = dict(payload)
    enriched["course_id"] = parsed_document.course_id
    enriched["lesson_id"] = parsed_document.lesson_id
    enriched["source_asset_ids"] = [
        asset.asset_id for asset in parsed_document.source_assets if asset.asset_id
    ]
    enriched["lesson_summary"] = enriched.get("lesson_summary") or _build_summary_from_parts(
        [section.get("summary", "") for section in sections if isinstance(section, dict)]
    )
    enriched["pages"] = pages
    enriched["parse_instruction"] = parse_instruction
    metadata = dict(enriched.get("metadata") or {})
    metadata["pages_backfilled_from_sections"] = True
    enriched["metadata"] = metadata
    return enriched


def _normalize_loose_structured_payload(
    payload: dict[str, Any],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    units_by_id = {unit.unit_id: unit for unit in parsed_document.units}
    pages = payload.get("pages")
    sections = payload.get("sections")

    normalized_pages = _normalize_loose_pages(pages, units_by_id)
    normalized_sections = _normalize_loose_sections(sections, units_by_id)
    normalized_knowledge_points = _normalize_loose_knowledge_points(payload.get("knowledge_points"))

    enriched = dict(payload)
    if normalized_pages is not None:
        enriched["pages"] = normalized_pages
    if normalized_sections is not None:
        enriched["sections"] = normalized_sections
    if normalized_knowledge_points is not None:
        enriched["knowledge_points"] = normalized_knowledge_points

    enriched.setdefault("course_id", parsed_document.course_id)
    enriched.setdefault("lesson_id", parsed_document.lesson_id)
    enriched.setdefault(
        "source_asset_ids",
        [asset.asset_id for asset in parsed_document.source_assets if asset.asset_id],
    )
    enriched.setdefault("parse_instruction", parse_instruction)

    metadata = dict(enriched.get("metadata") or {})
    metadata["loose_payload_normalized"] = True
    enriched["metadata"] = metadata
    return enriched


def _normalize_loose_pages(
    pages: Any,
    units_by_id: dict[str, DocumentUnit],
) -> Optional[list[dict[str, Any]]]:
    if not isinstance(pages, list):
        return None

    normalized_pages: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            continue

        source_unit_ids = _normalize_source_unit_ids(page.get("source_unit_ids"), units_by_id)
        first_unit = units_by_id.get(source_unit_ids[0]) if source_unit_ids else None
        page_number = page.get("page")
        if not isinstance(page_number, int):
            page_number = _infer_numeric_value(page.get("page_id")) or (
                first_unit.index if first_unit else index
            )

        section_id = page.get("section_id")
        if not section_id:
            section_id = f"sec_{index}"

        title = page.get("title") or (first_unit.title if first_unit else f"Page {page_number}")
        summary = _clean_summary_text(
            page.get("summary") or page.get("content") or (first_unit.text if first_unit else title)
        )
        key_points = (
            _normalize_string_list(page.get("key_points"))
            or _normalize_loose_knowledge_points(page.get("knowledge_points"))
            or [title]
        )
        knowledge_points = _normalize_loose_knowledge_points(page.get("knowledge_points")) or key_points
        page_role = page.get("page_role")
        if page_role not in VALID_PAGE_ROLES:
            page_role = _infer_unit_role(first_unit) if first_unit else "content"

        normalized_pages.append(
            {
                **page,
                "page": page_number,
                "section_id": section_id,
                "title": title,
                "summary": summary,
                "key_points": key_points,
                "knowledge_points": knowledge_points,
                "source_unit_ids": source_unit_ids,
                "page_role": page_role,
                "content": page.get("content") or (first_unit.text if first_unit else ""),
                "file_id": page.get("file_id") or (first_unit.source_asset_id if first_unit else None),
                "file_type": page.get("file_type")
                or (first_unit.metadata.get("file_type") if first_unit else None),
            }
        )

    return normalized_pages


def _normalize_loose_sections(
    sections: Any,
    units_by_id: dict[str, DocumentUnit],
) -> Optional[list[dict[str, Any]]]:
    if not isinstance(sections, list):
        return None

    normalized_sections: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue

        source_unit_ids = _normalize_source_unit_ids(section.get("source_unit_ids"), units_by_id)
        first_unit = units_by_id.get(source_unit_ids[0]) if source_unit_ids else None
        section_id = (
            section.get("section_id") or _extract_section_id(section.get("page_id")) or f"sec_{index}"
        )
        name = (
            section.get("name")
            or section.get("section_title")
            or section.get("title")
            or (first_unit.title if first_unit else f"Section {index}")
        )
        summary = _clean_summary_text(section.get("summary") or section.get("content") or name)
        key_points = (
            _normalize_string_list(section.get("key_points"))
            or _normalize_loose_knowledge_points(section.get("knowledge_points"))
            or [name]
        )
        knowledge_points = _normalize_loose_knowledge_points(section.get("knowledge_points")) or key_points
        page_range = section.get("page_range")
        if not isinstance(page_range, list) or not page_range:
            inferred_pages = [
                units_by_id[unit_id].index for unit_id in source_unit_ids if unit_id in units_by_id
            ]
            if inferred_pages:
                page_range = inferred_pages
            else:
                inferred_page = (
                    _infer_numeric_value(section.get("page"))
                    or _infer_numeric_value(section.get("page_id"))
                    or index
                )
                page_range = [inferred_page]
        section_type = section.get("section_type")
        if section_type not in VALID_SECTION_TYPES:
            section_type = _infer_section_type_from_units(source_unit_ids, units_by_id)

        normalized_sections.append(
            {
                **section,
                "section_id": section_id,
                "name": name,
                "summary": summary,
                "page_range": page_range,
                "key_points": key_points,
                "knowledge_points": knowledge_points,
                "source_unit_ids": source_unit_ids,
                "section_type": section_type,
            }
        )

    return normalized_sections


def _normalize_loose_knowledge_points(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                cleaned = " ".join(item.split())
                if cleaned:
                    normalized.append(cleaned)
                continue
            if isinstance(item, dict):
                candidate = (
                    item.get("name")
                    or item.get("title")
                    or item.get("knowledge_point")
                    or item.get("text")
                    or item.get("summary")
                )
                if isinstance(candidate, str):
                    cleaned = " ".join(candidate.split())
                    if cleaned:
                        normalized.append(cleaned)
        return _dedupe_strings(normalized)
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return [cleaned] if cleaned else []
    return []


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            cleaned = " ".join(item.split())
            if cleaned:
                normalized.append(cleaned)
    return _dedupe_strings(normalized)


def _normalize_source_unit_ids(value: Any, units_by_id: dict[str, DocumentUnit]) -> list[str]:
    if isinstance(value, list):
        return _filter_known_unit_ids([item for item in value if isinstance(item, str)], units_by_id)
    if isinstance(value, str):
        return _filter_known_unit_ids([value], units_by_id)
    return []


def _infer_numeric_value(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"(\d+)$", value.strip())
    if not match:
        return None
    return int(match.group(1))


def _extract_section_id(page_id: Any) -> Optional[str]:
    numeric = _infer_numeric_value(page_id)
    if numeric is None:
        return None
    return f"sec_{numeric}"


def _inject_structured_defaults(
    payload: dict[str, Any],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
) -> dict[str, Any]:
    enriched = dict(payload)
    enriched.setdefault("course_id", parsed_document.course_id)
    enriched.setdefault("lesson_id", parsed_document.lesson_id)
    enriched.setdefault(
        "source_asset_ids",
        [asset.asset_id for asset in parsed_document.source_assets if asset.asset_id],
    )
    enriched.setdefault("parse_instruction", parse_instruction)
    return enriched


def _normalize_structured_content(
    structured_content: StructuredLessonContent,
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
    units_scope: Sequence[DocumentUnit],
) -> StructuredLessonContent:
    units_by_id = {unit.unit_id: unit for unit in units_scope}
    unit_index_by_id = {unit.unit_id: unit.index for unit in units_scope}
    source_asset_ids = [asset.asset_id for asset in parsed_document.source_assets if asset.asset_id]

    sections_sorted = sorted(
        structured_content.sections,
        key=lambda item: _sort_key(
            item.source_unit_ids, unit_index_by_id, fallback=min(item.page_range or [10**9])
        ),
    )
    section_id_map: dict[str, str] = {}
    normalized_sections: list[SectionBlock] = []
    for index, section in enumerate(sections_sorted, start=1):
        source_unit_ids = _filter_known_unit_ids(section.source_unit_ids, units_by_id)
        provisional_section_id = f"prov_sec_{index}"
        if section.section_id:
            section_id_map[section.section_id] = provisional_section_id

        normalized_sections.append(
            section.model_copy(
                update={
                    "section_id": provisional_section_id,
                    "course_id": parsed_document.course_id,
                    "lesson_id": parsed_document.lesson_id,
                    "source_unit_ids": source_unit_ids,
                    "section_type": section.section_type
                    if section.section_type in VALID_SECTION_TYPES
                    else _infer_section_type_from_units(source_unit_ids, units_by_id),
                }
            )
        )

    pages_sorted = sorted(
        structured_content.pages,
        key=lambda item: _sort_key(item.source_unit_ids, unit_index_by_id, fallback=item.page),
    )
    normalized_pages: list[PageBlock] = []
    for index, page in enumerate(pages_sorted, start=1):
        source_unit_ids = _filter_known_unit_ids(page.source_unit_ids, units_by_id)
        section_id = section_id_map.get(page.section_id or "")
        if section_id is None:
            section_id = _resolve_page_section_id(source_unit_ids, normalized_sections)
        source_unit = units_by_id.get(source_unit_ids[0]) if source_unit_ids else None

        normalized_pages.append(
            page.model_copy(
                update={
                    "page_id": f"page_{index}",
                    "course_id": parsed_document.course_id,
                    "lesson_id": parsed_document.lesson_id,
                    "section_id": section_id,
                    "page": index,
                    "source_unit_ids": source_unit_ids,
                    "page_role": page.page_role
                    if page.page_role in VALID_PAGE_ROLES
                    else _infer_page_role_from_units(source_unit_ids, units_by_id),
                    "file_id": page.file_id or (source_unit.source_asset_id if source_unit else None),
                    "file_type": page.file_type
                    or (source_unit.metadata.get("file_type") if source_unit else None),
                }
            )
        )

    page_numbers_by_section: dict[str, list[int]] = {}
    for page in normalized_pages:
        if page.section_id:
            page_numbers_by_section.setdefault(page.section_id, []).append(page.page)

    finalized_sections, final_section_assignment = _rebuild_sections_from_pages(
        normalized_sections=normalized_sections,
        normalized_pages=normalized_pages,
    )

    finalized_pages: list[PageBlock] = []
    for page in normalized_pages:
        assigned_section_id = final_section_assignment.get((page.section_id, page.page))
        finalized_pages.append(page.model_copy(update={"section_id": assigned_section_id}))

    lesson_summary = (structured_content.lesson_summary or "").strip() or _fallback_lesson_summary(
        units_scope
    )
    knowledge_points = _dedupe_strings(
        list(structured_content.knowledge_points)
        + [point for section in finalized_sections for point in section.knowledge_points]
        + [point for page in finalized_pages for point in page.knowledge_points]
    )

    metadata = dict(structured_content.metadata)
    metadata.update(
        {
            "normalized": True,
            "page_count": len(finalized_pages),
            "section_count": len(finalized_sections),
        }
    )

    return structured_content.model_copy(
        update={
            "course_id": parsed_document.course_id,
            "lesson_id": parsed_document.lesson_id,
            "source_asset_ids": source_asset_ids,
            "lesson_summary": lesson_summary,
            "pages": finalized_pages,
            "sections": finalized_sections,
            "knowledge_points": knowledge_points,
            "parse_instruction": parse_instruction,
            "metadata": metadata,
        }
    )


def _merge_local_results(
    local_results: Sequence[StructuredLessonContent],
    parsed_document: ParsedDocument,
    parse_instruction: Optional[str],
    baseline_structured_content: StructuredLessonContent,
) -> StructuredLessonContent:
    all_pages: list[PageBlock] = []
    all_sections: list[SectionBlock] = []
    knowledge_points: list[str] = []
    lesson_summaries: list[str] = []

    for chunk_index, result in enumerate(local_results, start=1):
        section_id_map = {
            section.section_id: f"chunk_{chunk_index}_{section.section_id}" for section in result.sections
        }
        for section in result.sections:
            all_sections.append(
                section.model_copy(
                    update={"section_id": section_id_map.get(section.section_id, section.section_id)}
                )
            )
        for page in result.pages:
            all_pages.append(
                page.model_copy(update={"section_id": section_id_map.get(page.section_id, page.section_id)})
            )
        knowledge_points.extend(result.knowledge_points)
        if result.lesson_summary:
            lesson_summaries.append(result.lesson_summary.strip())

    if not lesson_summaries:
        lesson_summaries.append(baseline_structured_content.lesson_summary)

    merged_summary = "; ".join(summary for summary in lesson_summaries if summary)
    merged_summary = merged_summary[:237] + "..." if len(merged_summary) > 240 else merged_summary

    return StructuredLessonContent(
        course_id=parsed_document.course_id,
        lesson_id=parsed_document.lesson_id,
        source_asset_ids=[asset.asset_id for asset in parsed_document.source_assets if asset.asset_id],
        lesson_summary=merged_summary,
        pages=all_pages,
        sections=all_sections,
        knowledge_points=_dedupe_strings(knowledge_points or baseline_structured_content.knowledge_points),
        parse_instruction=parse_instruction,
        metadata={"merged_from_chunks": len(local_results)},
    )


def _rebuild_sections_from_pages(
    normalized_sections: Sequence[SectionBlock],
    normalized_pages: Sequence[PageBlock],
) -> tuple[list[SectionBlock], dict[tuple[Optional[str], int], str]]:
    sections_by_id = {section.section_id: section for section in normalized_sections}
    pages_by_section: dict[Optional[str], list[PageBlock]] = {}
    for page in normalized_pages:
        pages_by_section.setdefault(page.section_id, []).append(page)

    rebuilt_candidates: list[tuple[int, SectionBlock, list[int], Optional[str]]] = []
    for provisional_section_id, pages in pages_by_section.items():
        if not pages:
            continue

        pages_sorted = sorted(pages, key=lambda item: item.page)
        original_section = sections_by_id.get(provisional_section_id)
        contiguous_groups = _split_page_groups(pages_sorted)
        for group in contiguous_groups:
            page_numbers = [page.page for page in group]
            source_unit_ids = _dedupe_strings(unit_id for page in group for unit_id in page.source_unit_ids)
            if original_section is not None:
                name = original_section.name
                summary = original_section.summary
                key_points = original_section.key_points
                knowledge_points = original_section.knowledge_points
                section_type = original_section.section_type
            else:
                first_page = group[0]
                name = first_page.title or f"Section {page_numbers[0]}"
                summary = first_page.summary
                key_points = list(first_page.key_points)
                knowledge_points = list(first_page.knowledge_points)
                section_type = "content"

            rebuilt_section = SectionBlock(
                section_id="",
                course_id=group[0].course_id,
                lesson_id=group[0].lesson_id,
                name=name,
                summary=summary,
                page_range=page_numbers,
                key_points=list(key_points),
                knowledge_points=list(knowledge_points),
                source_unit_ids=source_unit_ids,
                section_type=section_type,
                parent_section_id=None,
            )
            rebuilt_candidates.append(
                (page_numbers[0], rebuilt_section, page_numbers, provisional_section_id)
            )

    rebuilt_candidates.sort(key=lambda item: item[0])

    finalized_sections: list[SectionBlock] = []
    final_section_assignment: dict[tuple[Optional[str], int], str] = {}
    for index, (_first_page, section, page_numbers, provisional_section_id) in enumerate(
        rebuilt_candidates, start=1
    ):
        final_section_id = f"sec_{index}"
        finalized_sections.append(section.model_copy(update={"section_id": final_section_id}))
        for page_number in page_numbers:
            final_section_assignment[(provisional_section_id, page_number)] = final_section_id

    return finalized_sections, final_section_assignment


def _split_page_groups(pages: Sequence[PageBlock]) -> list[list[PageBlock]]:
    if not pages:
        return []

    groups: list[list[PageBlock]] = [[pages[0]]]
    for page in pages[1:]:
        previous_page = groups[-1][-1]
        if page.page == previous_page.page + 1:
            groups[-1].append(page)
        else:
            groups.append([page])
    return groups


def _validate_structured_content(
    structured_content: StructuredLessonContent,
    units_scope: Sequence[DocumentUnit],
) -> list[str]:
    errors: list[str] = []
    known_unit_ids = {unit.unit_id for unit in units_scope}
    known_section_ids = {section.section_id for section in structured_content.sections}

    if not structured_content.lesson_summary.strip():
        errors.append("lesson_summary is empty")
    if not structured_content.pages:
        errors.append("pages is empty")
    if not structured_content.sections:
        errors.append("sections is empty")

    for index, page in enumerate(structured_content.pages, start=1):
        if not page.source_unit_ids:
            errors.append(f"page[{index}] has no source_unit_ids")
        if any(unit_id not in known_unit_ids for unit_id in page.source_unit_ids):
            errors.append(f"page[{index}] contains unknown source_unit_ids")
        if page.page_role not in VALID_PAGE_ROLES:
            errors.append(f"page[{index}] has invalid page_role={page.page_role}")
        if page.section_id and page.section_id not in known_section_ids:
            errors.append(f"page[{index}] references unknown section_id={page.section_id}")

    for index, section in enumerate(structured_content.sections, start=1):
        if not section.source_unit_ids:
            errors.append(f"section[{index}] has no source_unit_ids")
        if any(unit_id not in known_unit_ids for unit_id in section.source_unit_ids):
            errors.append(f"section[{index}] contains unknown source_unit_ids")
        if section.section_type not in VALID_SECTION_TYPES:
            errors.append(f"section[{index}] has invalid section_type={section.section_type}")
        if not section.page_range:
            errors.append(f"section[{index}] has empty page_range")

    return errors


def _fallback_result(
    baseline_structured_content: StructuredLessonContent,
    strategy: str,
    chunk_count: int,
    validation_errors: list[str],
    debug_info: Optional[dict[str, Any]] = None,
    logger=None,
) -> dict:
    if logger is not None:
        logger.warning("File structuring pipeline fallback triggered: %s", "; ".join(validation_errors))

    return {
        "structured_content": baseline_structured_content,
        "used_fallback": True,
        "strategy": strategy,
        "chunk_count": chunk_count,
        "validation_errors": validation_errors,
        "debug_info": debug_info or {},
    }


def _filter_known_unit_ids(source_unit_ids: Iterable[str], units_by_id: dict[str, DocumentUnit]) -> list[str]:
    return [unit_id for unit_id in source_unit_ids if unit_id in units_by_id]


def _resolve_page_section_id(
    source_unit_ids: Sequence[str], sections: Sequence[SectionBlock]
) -> Optional[str]:
    best_section_id: Optional[str] = None
    best_overlap = -1
    page_unit_ids = set(source_unit_ids)
    for section in sections:
        overlap = len(page_unit_ids & set(section.source_unit_ids))
        if overlap > best_overlap:
            best_overlap = overlap
            best_section_id = section.section_id
    return best_section_id


def _sort_key(source_unit_ids: Sequence[str], unit_index_by_id: dict[str, int], fallback: int) -> int:
    indices = [unit_index_by_id[unit_id] for unit_id in source_unit_ids if unit_id in unit_index_by_id]
    if indices:
        return min(indices)
    return fallback


def _infer_page_role_from_units(source_unit_ids: Sequence[str], units_by_id: dict[str, DocumentUnit]) -> str:
    if not source_unit_ids:
        return "other"
    return _infer_unit_role(units_by_id[source_unit_ids[0]])


def _infer_section_type_from_units(
    source_unit_ids: Sequence[str], units_by_id: dict[str, DocumentUnit]
) -> str:
    if not source_unit_ids:
        return "other"

    roles = [_infer_unit_role(units_by_id[unit_id]) for unit_id in source_unit_ids if unit_id in units_by_id]
    if not roles:
        return "other"
    if any(role in {"cover", "agenda"} for role in roles):
        return "intro"
    if any(role == "example" for role in roles):
        return "example"
    if any(role == "summary" for role in roles):
        return "summary"
    if any(role == "exercise" for role in roles):
        return "exercise"
    if any(role in {"content", "definition", "formula"} for role in roles):
        return "content"
    return "other"


def _fallback_lesson_summary(units_scope: Sequence[DocumentUnit]) -> str:
    parts: list[str] = []
    for unit in units_scope:
        if unit.title:
            parts.append(unit.title.strip())
        if len(parts) >= 3:
            break
    if not parts:
        for unit in units_scope:
            text = " ".join(unit.text.split())
            if text:
                parts.append(text[:80] + ("..." if len(text) > 80 else ""))
            if len(parts) >= 2:
                break
    return "; ".join(part for part in parts if part)


def _build_summary_from_parts(parts: Iterable[str]) -> str:
    summary = "; ".join(part.strip() for part in parts if part and part.strip())
    if len(summary) > 240:
        return summary[:237] + "..."
    return summary


def _clean_summary_text(text: str, limit: int = 160) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _dedupe_strings(items: Iterable[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join((item or "").split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _response_preview(raw_response: Any, limit: int = 500) -> str:
    if isinstance(raw_response, StructuredLessonContent):
        preview = json.dumps(raw_response.model_dump(mode="python"), ensure_ascii=False)
    elif isinstance(raw_response, dict):
        preview = json.dumps(raw_response, ensure_ascii=False)
    else:
        preview = str(raw_response)

    compact = " ".join(preview.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
