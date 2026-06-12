"""Internal router for knowledge-base management (/internal/kb/*).

These endpoints are NOT part of the external open API.  They are intended
for the admin/test panel and internal tooling.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import generate_request_id
from src.api.models.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb", tags=["知识库(内部)"])


class CreateKBRequest(BaseModel):
    courseId: str = Field(..., description="课程ID")
    kbName: str = Field("", description="知识库名称")
    indexBackend: str = Field("faiss", description="索引后端: faiss/numpy")


class AddSourceRequest(BaseModel):
    kbId: str = Field(..., description="知识库ID")
    lessonIds: list[str] = Field(default_factory=list, description="智课ID列表")


class BuildKBRequest(BaseModel):
    kbId: str = Field(..., description="知识库ID")
    lessonIds: list[str] = Field(default_factory=list, description="智课ID列表(可选，不传则用已添加的来源)")


@router.post("/create", summary="创建知识库")
def create_kb(body: CreateKBRequest, db: Session = Depends(get_db)):
    from src.services.knowledge_base.kb_service import KBService

    kb = KBService.create_kb(
        db,
        course_id=body.courseId,
        kb_name=body.kbName or f"KB for {body.courseId}",
        index_backend=body.indexBackend,
    )
    return {
        "code": 200,
        "msg": "知识库创建成功",
        "data": {
            "kbId": kb.kb_id,
            "courseid": kb.course_id,
            "kbName": kb.kb_name,
            "status": kb.status,
        },
        "requestId": generate_request_id(),
    }


@router.post("/addSources", summary="添加来源到知识库")
def add_sources(body: AddSourceRequest, db: Session = Depends(get_db)):
    from src.services.knowledge_base.kb_service import KBService

    added = []
    for lid in body.lessonIds:
        src = KBService.add_lesson_source(db, body.kbId, lid)
        added.append({"kbSourceId": src.kb_source_id, "lessonId": lid})

    return {
        "code": 200,
        "msg": f"已添加 {len(added)} 个来源",
        "data": {"sources": added},
        "requestId": generate_request_id(),
    }


@router.post("/build", summary="构建知识库索引")
def build_kb(body: BuildKBRequest, db: Session = Depends(get_db)):
    from src.api.models.tables import Lesson
    from src.services.knowledge_base.ingestion_pipeline import KBIngestionPipeline
    from src.services.knowledge_base.kb_service import KBService

    lesson_ids = body.lessonIds
    if not lesson_ids:
        sources = KBService.list_sources(db, body.kbId)
        lesson_ids = [s.lesson_id for s in sources if s.lesson_id and s.source_kind == "lesson"]

    if not lesson_ids:
        kb = KBService.get_kb(db, body.kbId)
        if kb and kb.course_id:
            lesson_ids = [
                lesson.lesson_id
                for lesson in db.query(Lesson).filter(Lesson.course_id == kb.course_id).all()
                if lesson.structured_content
            ]

    if not lesson_ids:
        return {
            "code": 400,
            "msg": "没有找到可用的智课来源",
            "data": None,
            "requestId": generate_request_id(),
        }

    try:
        pipeline = KBIngestionPipeline(db, body.kbId)
        index_path = pipeline.run(lesson_ids)
        return {
            "code": 200,
            "msg": "知识库索引构建完成",
            "data": {
                "kbId": body.kbId,
                "indexPath": index_path,
                "lessonCount": len(lesson_ids),
            },
            "requestId": generate_request_id(),
        }
    except Exception as e:
        logger.exception("KB build failed for %s", body.kbId)
        return {
            "code": 500,
            "msg": f"索引构建失败: {str(e)[:200]}",
            "data": None,
            "requestId": generate_request_id(),
        }


@router.get("/status/{kb_id}", summary="查询知识库状态")
def kb_status(kb_id: str, db: Session = Depends(get_db)):
    from src.services.knowledge_base.kb_service import KBService

    kb = KBService.get_kb(db, kb_id)
    if kb is None:
        return {
            "code": 404,
            "msg": "知识库不存在",
            "data": None,
            "requestId": generate_request_id(),
        }

    sources = KBService.list_sources(db, kb_id)

    return {
        "code": 200,
        "msg": "查询成功",
        "data": {
            "kbId": kb.kb_id,
            "courseId": kb.course_id,
            "kbName": kb.kb_name,
            "status": kb.status,
            "indexBackend": kb.index_backend,
            "indexPath": kb.index_path,
            "chunkCount": kb.chunk_count,
            "sourceCount": kb.source_count,
            "sources": [
                {
                    "kbSourceId": s.kb_source_id,
                    "sourceKind": s.source_kind,
                    "lessonId": s.lesson_id,
                    "fileName": s.file_name,
                    "status": s.status,
                }
                for s in sources
            ],
        },
        "requestId": generate_request_id(),
    }


@router.get("/list", summary="列出所有知识库")
def list_kbs(db: Session = Depends(get_db)):
    from src.api.models.tables import KnowledgeBase

    kbs = db.query(KnowledgeBase).order_by(KnowledgeBase.id.desc()).all()
    return {
        "code": 200,
        "msg": "查询成功",
        "data": [
            {
                "kbId": kb.kb_id,
                "courseId": kb.course_id,
                "kbName": kb.kb_name,
                "status": kb.status,
                "chunkCount": kb.chunk_count,
                "sourceCount": kb.source_count,
            }
            for kb in kbs
        ],
        "requestId": generate_request_id(),
    }
