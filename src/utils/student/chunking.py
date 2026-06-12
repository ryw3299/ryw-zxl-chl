"""
Chunk builders for lesson retrieval.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

from src.schemas.common import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript


@dataclass
class ChunkRecord:
    """A retrieval chunk aligned to a parent lesson source."""

    chunk_id: str
    lesson_id: str
    source_type: Literal["page", "section", "script_block"]
    source_id: str
    parent_source_type: Literal["page", "section", "script_block"]
    parent_source_id: str
    section_id: str | None
    page: int | None
    title: str
    text: str
    chunk_index: int
    key_points: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize chunk record to a JSON-friendly dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChunkRecord:
        """Deserialize a chunk record from a dictionary."""
        return cls(**data)


def split_text_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into Chinese-friendly chunks with overlap.

    Prefers paragraph/sentence boundaries and falls back to hard cutting only
    when a single segment is still too long.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = (text or "").strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    segments = _split_on_boundaries(normalized)
    chunks: list[str] = []
    current = ""

    for segment in segments:
        if not segment:
            continue
        if len(segment) > chunk_size:
            chunks.extend(_flush_and_hard_split(current, segment, chunk_size, overlap))
            current = ""
            continue

        candidate = f"{current}{segment}" if current else segment
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        chunks.append(current.strip())
        current = _apply_overlap(current, overlap) + segment

    if current.strip():
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


class ChunkBuilder:
    """Build retrieval chunks from structured lesson content."""

    def __init__(self, chunk_size: int, overlap: int):
        self._chunk_size = chunk_size
        self._overlap = overlap

    def build(
        self,
        structured_content: StructuredLessonContent | None,
        lesson_script: LessonScript | None,
    ) -> list[ChunkRecord]:
        """Build chunks from page, section, and script sources."""
        if structured_content is None:
            return []

        section_names = {
            section.section_id: section.name for section in structured_content.sections if section.section_id
        }
        chunks: list[ChunkRecord] = []

        for page in structured_content.pages:
            source_id = str(page.page_id or page.page)
            title = page.title or f"Page {page.page}"
            header = self._build_header(
                section_title=section_names.get(page.section_id or ""),
                title=title,
                key_points=page.key_points,
            )
            body = self._combine_parts(page.summary, page.content)
            chunks.extend(
                self._build_source_chunks(
                    lesson_id=structured_content.lesson_id,
                    source_type="page",
                    source_id=source_id,
                    section_id=page.section_id,
                    page=page.page,
                    title=title,
                    header=header,
                    body=body,
                    fallback_text=header,
                    key_points=page.key_points,
                )
            )

        for section in structured_content.sections:
            header = self._build_header(
                section_title=section.name,
                title=section.name,
                key_points=section.key_points or section.knowledge_points,
            )
            body = self._combine_parts(section.summary, "\n".join(section.knowledge_points))
            page = section.page_range[0] if section.page_range else None
            chunks.extend(
                self._build_source_chunks(
                    lesson_id=structured_content.lesson_id,
                    source_type="section",
                    source_id=section.section_id,
                    section_id=section.section_id,
                    page=page,
                    title=section.name,
                    header=header,
                    body=body,
                    fallback_text=header,
                    key_points=section.key_points or section.knowledge_points,
                )
            )

        if lesson_script is not None:
            for block in lesson_script.script_blocks:
                source_id = block.script_block_id or f"script-{len(chunks)}"
                header = self._build_header(
                    section_title=section_names.get(block.section_id, ""),
                    title=block.title,
                    key_points=block.key_points,
                )
                page = block.page_range[0] if block.page_range else None
                chunks.extend(
                    self._build_source_chunks(
                        lesson_id=structured_content.lesson_id,
                        source_type="script_block",
                        source_id=source_id,
                        section_id=block.section_id,
                        page=page,
                        title=block.title,
                        header=header,
                        body=block.script_text,
                        fallback_text=header,
                        key_points=block.key_points,
                    )
                )

        return chunks

    def _build_source_chunks(
        self,
        *,
        lesson_id: str,
        source_type: Literal["page", "section", "script_block"],
        source_id: str,
        section_id: str | None,
        page: int | None,
        title: str,
        header: str,
        body: str,
        fallback_text: str,
        key_points: Iterable[str],
    ) -> list[ChunkRecord]:
        body = (body or "").strip()
        header = (header or "").strip()
        if not body and not header:
            return []

        available_size = self._chunk_size
        if header:
            available_size = max(120, self._chunk_size - len(header) - 1)

        body_chunks = (
            split_text_into_chunks(body, available_size, min(self._overlap, available_size - 1))
            if body
            else []
        )
        if not body_chunks:
            body_chunks = [fallback_text.strip()]

        records: list[ChunkRecord] = []
        for chunk_index, body_chunk in enumerate(body_chunks):
            text = body_chunk.strip()
            if header and header not in text:
                text = f"{header}\n{text}".strip()
            chunk_id = f"{source_type}:{source_id}:chunk:{chunk_index}"
            records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    lesson_id=lesson_id,
                    source_type=source_type,
                    source_id=source_id,
                    parent_source_type=source_type,
                    parent_source_id=source_id,
                    section_id=section_id,
                    page=page,
                    title=title,
                    text=text,
                    chunk_index=chunk_index,
                    key_points=[item for item in key_points if item],
                )
            )

        return records

    @staticmethod
    def _build_header(
        *,
        section_title: str | None,
        title: str | None,
        key_points: Iterable[str] | None,
    ) -> str:
        lines: list[str] = []
        if section_title:
            lines.append(f"Section: {section_title}")
        if title:
            lines.append(f"Title: {title}")
        if key_points:
            points = ", ".join(item for item in key_points if item)
            if points:
                lines.append(f"Key points: {points}")
        return "\n".join(lines).strip()

    @staticmethod
    def _combine_parts(*parts: Optional[str]) -> str:
        return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _split_on_boundaries(text: str) -> list[str]:
    paragraphs = [item.strip() for item in re.split(r"\n{2,}", text) if item.strip()]
    segments: list[str] = []
    for paragraph in paragraphs:
        parts = re.split(r"(?<=[。！？；?!;])", paragraph)
        segments.extend(part for part in parts if part)
        if not paragraph.endswith(("\n", "。", "！", "？", "；", "?", "!", ";")):
            segments.append("\n")
    return segments or [text]


def _apply_overlap(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    tail = text[-overlap:].strip()
    return f"{tail}" if tail else ""


def _flush_and_hard_split(current: str, segment: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    if current.strip():
        chunks.append(current.strip())

    start = 0
    step = chunk_size - overlap
    while start < len(segment):
        end = start + chunk_size
        chunks.append(segment[start:end].strip())
        start += step
    return [chunk for chunk in chunks if chunk]
