"""Backend pre-RAG retrieval service.

Runs *before* the student agent so that the agent receives pre-retrieved
context instead of having to call search / retrieve tools itself.

Supports two modes:
1. **KB mode** -- if the lesson has a linked knowledge base whose index is
   ready, load the pre-built index and search it.
2. **Legacy mode** -- build / reuse a per-lesson ``HybridRetriever`` via
   ``RetrieverFactory`` (instant index build).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.schemas import RetrievedContextItem
from src.schemas.common import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript
from src.utils.student.config import get_rag_settings
from src.utils.student.content_getter import ContentGetter
from src.utils.student.embedder import create_embedder
from src.utils.student.hybrid_retriever import HybridRetriever
from src.utils.student.retriever_factory import RetrieverFactory

logger = logging.getLogger(__name__)

_kb_retriever_cache: dict[str, HybridRetriever] = {}


@dataclass
class RetrievalResult:
    """Aggregated output of the pre-RAG retrieval stage."""

    chunks: list[RetrievedContextItem] = field(default_factory=list)
    exact_source: Optional[RetrievedContextItem] = None
    total: int = 0


class RetrievalService:
    @staticmethod
    def do_retrieval(
        *,
        lesson_id: str,
        question: str,
        structured_content: StructuredLessonContent,
        lesson_script: Optional[LessonScript] = None,
        prefer_section_id: Optional[str] = None,
        prefer_page: Optional[int] = None,
        prefer_script_block_id: Optional[str] = None,
        top_k: int = 5,
        kb_index_path: Optional[str] = None,
    ) -> RetrievalResult:
        """Execute the full pre-RAG pipeline and return results.

        When ``kb_index_path`` is provided and a valid index exists on disk,
        the pre-built KB index is used (Phase 3 path).  Otherwise falls back
        to ``RetrieverFactory`` instant build (Phase 1 path).
        """
        retriever = _load_kb_retriever(
            kb_index_path,
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        if retriever is None:
            retriever = RetrieverFactory.get_or_create(
                structured_content=structured_content,
                lesson_script=lesson_script,
            )

        chunks = retriever.retrieve(
            query=question,
            top_k=top_k,
            prefer_section_id=prefer_section_id,
            prefer_page=prefer_page,
            prefer_script_block_id=prefer_script_block_id,
        )

        primary = _choose_primary(
            chunks,
            prefer_section_id=prefer_section_id,
            prefer_page=prefer_page,
            prefer_script_block_id=prefer_script_block_id,
        )

        exact_source: Optional[RetrievedContextItem] = None
        if primary is not None:
            exact_source = _fetch_exact_source(
                primary,
                structured_content=structured_content,
                lesson_script=lesson_script,
            )
        elif prefer_script_block_id or prefer_page is not None or prefer_section_id:
            exact_source = _fetch_fallback_source(
                structured_content=structured_content,
                lesson_script=lesson_script,
                prefer_script_block_id=prefer_script_block_id,
                prefer_page=prefer_page,
                prefer_section_id=prefer_section_id,
            )

        return RetrievalResult(
            chunks=chunks,
            exact_source=exact_source,
            total=len(chunks),
        )


def _choose_primary(
    results: list[RetrievedContextItem],
    *,
    prefer_section_id: Optional[str],
    prefer_page: Optional[int],
    prefer_script_block_id: Optional[str],
) -> Optional[RetrievedContextItem]:
    if not results:
        return None

    for item in results:
        if (
            prefer_script_block_id
            and item.source == "script_block"
            and item.source_id == prefer_script_block_id
        ):
            return item
    for item in results:
        if prefer_section_id and item.section_id == prefer_section_id:
            return item
    for item in results:
        if prefer_page is not None and item.page == prefer_page:
            return item
    return results[0]


def _fetch_exact_source(
    primary: RetrievedContextItem,
    *,
    structured_content: StructuredLessonContent,
    lesson_script: Optional[LessonScript],
) -> Optional[RetrievedContextItem]:
    getter = ContentGetter(
        structured_content=structured_content,
        lesson_script=lesson_script,
    )
    try:
        return getter.get_source(primary.source, primary.source_id)
    except (ValueError, KeyError):
        return None


def _load_kb_retriever(
    kb_index_path: Optional[str],
    *,
    structured_content: StructuredLessonContent,
    lesson_script: Optional[LessonScript],
) -> Optional[HybridRetriever]:
    """Try to load a pre-built KB index; return None if unavailable."""
    if not kb_index_path:
        return None

    path = Path(kb_index_path)
    if not path.exists():
        return None

    cache_key = str(path)
    cached = _kb_retriever_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        settings = get_rag_settings()
        embedder = create_embedder()
        retriever = HybridRetriever.load_from_disk(
            path,
            structured_content=structured_content,
            lesson_script=lesson_script,
            embedder=embedder,
            rag_settings=settings,
        )
        _kb_retriever_cache[cache_key] = retriever
        return retriever
    except Exception:
        logger.debug("Failed to load KB index from %s, falling back", kb_index_path)
        return None


def _fetch_fallback_source(
    *,
    structured_content: StructuredLessonContent,
    lesson_script: Optional[LessonScript],
    prefer_script_block_id: Optional[str],
    prefer_page: Optional[int],
    prefer_section_id: Optional[str],
) -> Optional[RetrievedContextItem]:
    getter = ContentGetter(
        structured_content=structured_content,
        lesson_script=lesson_script,
    )
    if prefer_script_block_id:
        result = getter.get_script_block(prefer_script_block_id)
        if result:
            return result
    if prefer_page is not None:
        result = getter.get_page(prefer_page)
        if result:
            return result
    if prefer_section_id:
        result = getter.get_section(prefer_section_id)
        if result:
            return result
    return None
