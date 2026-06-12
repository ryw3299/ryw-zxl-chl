#!/usr/bin/env python
"""CLI tool to build a knowledge base from one or more lessons.

Usage:
    python scripts/build_knowledge_base.py --course_id cou30001
    python scripts/build_knowledge_base.py --lesson_ids lesson1 lesson2 lesson3
    python scripts/build_knowledge_base.py --course_id cou30001 --kb_name "材料力学知识库"
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.models.database import SessionLocal  # noqa: E402
from src.api.models.tables import Lesson  # noqa: E402
from src.services.knowledge_base.ingestion_pipeline import KBIngestionPipeline  # noqa: E402
from src.services.knowledge_base.kb_service import KBService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a knowledge base from lessons")
    parser.add_argument("--course_id", type=str, help="Course ID (ingests all lessons for this course)")
    parser.add_argument("--lesson_ids", nargs="+", type=str, help="Explicit list of lesson IDs")
    parser.add_argument("--kb_name", type=str, default="", help="Knowledge base name")
    parser.add_argument("--index_backend", type=str, default="faiss", choices=["faiss", "numpy"])
    args = parser.parse_args()

    if not args.course_id and not args.lesson_ids:
        parser.error("Must provide --course_id or --lesson_ids")

    db = SessionLocal()
    try:
        if args.lesson_ids:
            lesson_ids = args.lesson_ids
            course_id = args.course_id or "unknown"
        else:
            lessons = db.query(Lesson).filter(Lesson.course_id == args.course_id).all()
            lesson_ids = [l.lesson_id for l in lessons if l.structured_content]
            course_id = args.course_id
            if not lesson_ids:
                logger.error("No lessons with structured_content found for course %s", course_id)
                sys.exit(1)

        kb_name = args.kb_name or f"KB for {course_id}"
        logger.info("Creating knowledge base '%s' with %d lessons", kb_name, len(lesson_ids))

        kb = KBService.create_kb(
            db,
            course_id=course_id,
            kb_name=kb_name,
            index_backend=args.index_backend,
        )
        logger.info("Knowledge base created: %s", kb.kb_id)

        for lid in lesson_ids:
            KBService.add_lesson_source(db, kb.kb_id, lid)

        pipeline = KBIngestionPipeline(db, kb.kb_id)
        index_path = pipeline.run(lesson_ids)

        logger.info("Knowledge base ready at: %s", index_path)

    finally:
        db.close()


if __name__ == "__main__":
    main()
