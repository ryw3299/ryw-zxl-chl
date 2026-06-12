# 将上传的raw文件处理后切成DocumentUnit流，再把document流转换成ParsedDocument
# 然后得到ParsedDocument之后，该程序使命完成，agent会调用变成structuredLessonContent
from collections.abc import Iterable
from typing import Optional

from src.schemas import (
    PageBlock,
    ParsedDocument,
    ParserInput,
    SectionBlock,
    StructuredLessonContent,
)
from src.utils.file_loader import load_assets


def run_file_parser_pipeline(request: ParserInput, logger=None) -> dict:
    normalized_assets, source_files, units = load_assets(request.assets, logger=logger)
    knowledge_points = _derive_knowledge_points(units)

    sections = _build_sections(
        units=units,
        course_id=request.course_id,
        lesson_id=request.lesson_id,
    )
    pages = _build_pages(
        units=units,
        sections=sections,
        course_id=request.course_id,
        lesson_id=request.lesson_id,
    )

    parsed_document = ParsedDocument(
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        source_assets=normalized_assets,
        units=units,
        sections=sections,
        parse_instruction=request.parse_instruction,
        knowledge_points=knowledge_points,
        metadata={"asset_count": len(normalized_assets)},
    )
    if logger is not None:
        logger.info("Built ParsedDocument with %d unit(s)", len(parsed_document.units))

    structured_content = StructuredLessonContent(
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        source_asset_ids=[asset.asset_id for asset in normalized_assets if asset.asset_id],
        lesson_summary=_build_lesson_summary(units),
        pages=pages,
        sections=sections,
        knowledge_points=knowledge_points,
        parse_instruction=request.parse_instruction,
        metadata={"page_count": len(pages), "section_count": len(sections)},
    )
    if logger is not None:
        logger.info("Built StructuredLessonContent with %d page(s)", len(structured_content.pages))

    return {
        "normalized_assets": normalized_assets,
        "source_files": source_files,
        "units": units,
        "knowledge_points": knowledge_points,
        "pages": pages,
        "sections": sections,
        "parsed_document": parsed_document,
        "structured_content": structured_content,
    }


def _build_sections(units, course_id: Optional[str], lesson_id: str) -> list[SectionBlock]:
    sections: list[SectionBlock] = []
    for unit in units:
        section_type = _infer_section_type(unit)
        sections.append(
            SectionBlock(
                section_id=f"sec_{unit.index}",
                course_id=course_id,
                lesson_id=lesson_id,
                name=unit.title or f"Section {unit.index}",
                summary=_short_text(unit.text),
                page_range=[unit.index],
                key_points=[unit.title] if unit.title else [],
                knowledge_points=[unit.title] if unit.title else [],
                source_unit_ids=[unit.unit_id],
                section_type=section_type,
            )
        )
    return sections


def _build_pages(
    units, sections: list[SectionBlock], course_id: Optional[str], lesson_id: str
) -> list[PageBlock]:
    pages: list[PageBlock] = []
    for unit, section in zip(units, sections):
        page_role = _infer_page_role(unit)
        pages.append(
            PageBlock(
                page_id=f"page_{unit.index}",
                course_id=course_id,
                lesson_id=lesson_id,
                section_id=section.section_id,
                page=unit.index,
                title=unit.title or unit.source_ref or f"Page {unit.index}",
                content=unit.text,
                summary=_short_text(unit.text),
                key_points=[unit.title] if unit.title else [],
                knowledge_points=[unit.title] if unit.title else [],
                source_unit_ids=[unit.unit_id],
                page_role=page_role,
                file_id=unit.source_asset_id,
                file_type=unit.metadata.get("file_type"),
            )
        )
    return pages


def _derive_knowledge_points(units: Iterable) -> list[str]:
    points: list[str] = []
    for unit in units:
        candidate = unit.title.strip() if unit.title else ""
        if candidate and candidate not in points:
            points.append(candidate)
    return points


def _short_text(text: str, limit: int = 120) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _build_lesson_summary(units: Iterable, limit: int = 240) -> str:
    snippets: list[str] = []
    for unit in units:
        if unit.title:
            snippets.append(unit.title.strip())
        if len(snippets) >= 3:
            break

    if not snippets:
        for unit in units:
            if unit.text:
                snippets.append(_short_text(unit.text, limit=80))
            if len(snippets) >= 2:
                break

    summary = "; ".join(part for part in snippets if part)
    if len(summary) <= limit:
        return summary
    return summary[: limit - 3] + "..."


def _infer_page_role(unit) -> str:
    title = (unit.title or "").strip().lower()
    text = (unit.text or "").strip().lower()
    combined = f"{title} {text}".strip()

    if unit.index == 1 and (title or text):
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
    if combined:
        return "content"
    return "other"


def _infer_section_type(unit) -> str:
    page_role = _infer_page_role(unit)
    if page_role in {"cover", "agenda"}:
        return "intro"
    if page_role in {"example"}:
        return "example"
    if page_role in {"summary"}:
        return "summary"
    if page_role in {"exercise"}:
        return "exercise"
    if page_role in {"content", "definition", "formula"}:
        return "content"
    return "other"
