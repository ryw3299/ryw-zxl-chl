"""Offline knowledge-base ingestion pipeline.

Takes a list of lesson IDs (or structured content dicts), chunks them,
embeds them, builds a FAISS index, and writes chunk metadata to MySQL.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.api.models.tables import KnowledgeChunk, Lesson
from src.schemas.common import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript
from src.utils.student.chunking import ChunkBuilder, ChunkRecord
from src.utils.student.config import get_rag_settings
from src.utils.student.embedder import create_embedder
from src.utils.student.hybrid_retriever import HybridRetriever

from .kb_service import KBService

logger = logging.getLogger(__name__)


class KBIngestionPipeline:
    """Build a knowledge-base index from one or more lessons."""

    def __init__(self, db: DBSession, kb_id: str):
        self._db = db
        self._kb_id = kb_id
        self._rag_settings = get_rag_settings()

    def run(self, lesson_ids: list[str]) -> str:
        """Ingest all lessons and build a combined index.

        Returns the path to the persisted index directory.
        """
        KBService.update_kb_status(self._db, self._kb_id, "indexing")

        all_chunks: list[ChunkRecord] = []
        source_count = 0

        for lesson_id in lesson_ids:
            lesson = self._db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
            if lesson is None or not lesson.structured_content:
                logger.warning("Lesson %s has no structured_content, skipping", lesson_id)
                continue

            sc_dict = json.loads(lesson.structured_content)
            sc = StructuredLessonContent.model_validate(sc_dict)

            ls: Optional[LessonScript] = None
            if lesson.script_id:
                from src.api.models.tables import Script

                script = self._db.query(Script).filter(Script.script_id == lesson.script_id).first()
                if script and script.generate_output:
                    gen = json.loads(script.generate_output)
                    ls_dict = gen.get("lesson_script")
                    if ls_dict:
                        ls = LessonScript.model_validate(ls_dict)

            builder = ChunkBuilder(
                chunk_size=self._rag_settings.chunk_size,
                overlap=self._rag_settings.chunk_overlap,
            )
            chunks = builder.build(sc, ls)
            all_chunks.extend(chunks)
            source_count += 1

            content_hash = hashlib.sha256(lesson.structured_content.encode("utf-8")).hexdigest()[:16]
            if hasattr(lesson, "content_hash"):
                lesson.content_hash = content_hash  # type: ignore[assignment]

            KBService.link_lesson_to_kb(self._db, lesson_id, self._kb_id)

        if not all_chunks:
            KBService.update_kb_status(self._db, self._kb_id, "failed")
            raise ValueError("No chunks produced from the provided lessons")

        embedder = create_embedder()
        retriever = HybridRetriever(
            embedder=embedder,
            chunks=all_chunks,
            rag_settings=self._rag_settings,
        )

        index_dir = self._rag_settings.index_dir / "kb" / self._kb_id
        retriever.save_to_disk(index_dir)

        self._persist_chunk_metadata(all_chunks)

        KBService.update_kb_status(
            self._db,
            self._kb_id,
            "ready",
            chunk_count=len(all_chunks),
            source_count=source_count,
            index_path=str(index_dir),
        )
        self._db.commit()

        logger.info(
            "KB %s ingestion complete: %d chunks from %d lessons",
            self._kb_id,
            len(all_chunks),
            source_count,
        )
        return str(index_dir)

    def _persist_chunk_metadata(self, chunks: list[ChunkRecord]) -> None:
        """Write chunk metadata rows to MySQL."""
        self._db.query(KnowledgeChunk).filter(KnowledgeChunk.kb_id == self._kb_id).delete()
        self._db.flush()

        for chunk in chunks:
            raw_key = f"{self._kb_id}:{chunk.lesson_id}:{chunk.chunk_id}"
            unique_id = f"ck_{hashlib.md5(raw_key.encode()).hexdigest()[:16]}"
            row = KnowledgeChunk(
                chunk_id=unique_id,
                kb_id=self._kb_id,
                lesson_id=chunk.lesson_id,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                section_id=chunk.section_id,
                page=chunk.page,
                title=chunk.title,
                text=chunk.text,
                chunk_index=chunk.chunk_index,
                key_points_json=json.dumps(list(chunk.key_points), ensure_ascii=False)
                if chunk.key_points
                else None,
            )
            self._db.add(row)
        self._db.flush()
