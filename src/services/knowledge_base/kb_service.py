"""Knowledge-base CRUD service.

Manages ``knowledge_bases``, ``knowledge_base_sources``, and provides
helpers for linking lessons to knowledge bases.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session as DBSession

from src.api.models.tables import (
    KnowledgeBase,
    KnowledgeBaseSource,
    Lesson,
)

logger = logging.getLogger(__name__)


class KBService:
    @staticmethod
    def create_kb(
        db: DBSession,
        *,
        course_id: str,
        kb_name: str,
        scope_type: str = "course",
        index_backend: str = "faiss",
        embedding_model: Optional[str] = None,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            kb_id=f"kb_{uuid4().hex[:12]}",
            course_id=course_id,
            kb_name=kb_name,
            scope_type=scope_type,
            status="draft",
            index_backend=index_backend,
            embedding_model=embedding_model,
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)
        return kb

    @staticmethod
    def get_kb(db: DBSession, kb_id: str) -> Optional[KnowledgeBase]:
        return db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()

    @staticmethod
    def get_kb_for_lesson(db: DBSession, lesson_id: str) -> Optional[KnowledgeBase]:
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        if lesson is None or not getattr(lesson, "knowledge_base_id", None):
            return None
        return db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == lesson.knowledge_base_id).first()

    @staticmethod
    def add_lesson_source(
        db: DBSession,
        kb_id: str,
        lesson_id: str,
        source_hash: Optional[str] = None,
    ) -> KnowledgeBaseSource:
        src = KnowledgeBaseSource(
            kb_source_id=f"kbs_{uuid4().hex[:12]}",
            kb_id=kb_id,
            source_kind="lesson",
            lesson_id=lesson_id,
            source_hash=source_hash,
            status="pending",
        )
        db.add(src)
        db.commit()
        db.refresh(src)
        return src

    @staticmethod
    def add_file_source(
        db: DBSession,
        kb_id: str,
        file_url: str,
        file_name: str,
        source_hash: Optional[str] = None,
    ) -> KnowledgeBaseSource:
        src = KnowledgeBaseSource(
            kb_source_id=f"kbs_{uuid4().hex[:12]}",
            kb_id=kb_id,
            source_kind="file",
            file_url=file_url,
            file_name=file_name,
            source_hash=source_hash,
            status="pending",
        )
        db.add(src)
        db.commit()
        db.refresh(src)
        return src

    @staticmethod
    def list_sources(db: DBSession, kb_id: str) -> list[KnowledgeBaseSource]:
        return db.query(KnowledgeBaseSource).filter(KnowledgeBaseSource.kb_id == kb_id).all()

    @staticmethod
    def update_kb_status(
        db: DBSession,
        kb_id: str,
        status: str,
        *,
        chunk_count: Optional[int] = None,
        source_count: Optional[int] = None,
        index_path: Optional[str] = None,
    ) -> None:
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
        if kb is None:
            return
        kb.status = status  # type: ignore[assignment]
        if chunk_count is not None:
            kb.chunk_count = chunk_count  # type: ignore[assignment]
        if source_count is not None:
            kb.source_count = source_count  # type: ignore[assignment]
        if index_path is not None:
            kb.index_path = index_path  # type: ignore[assignment]
        db.commit()

    @staticmethod
    def link_lesson_to_kb(db: DBSession, lesson_id: str, kb_id: str) -> None:
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        if lesson is not None and hasattr(lesson, "knowledge_base_id"):
            lesson.knowledge_base_id = kb_id  # type: ignore[assignment]
            db.commit()
