"""练习题路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.quiz import QuizRecord
from src.models.user import User
from src.schemas.event_schema import QuizGenerateRequest, QuizSubmitRequest
from src.utils.response import success

router = APIRouter(prefix="/quiz", tags=["练习题"])


@router.post("/generate", summary="生成练习题")
async def generate_quiz(
    body: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    kps = body.knowledge_points or ["Python"]
    questions = []
    for i in range(body.count):
        questions.append(
            {
                "id": i + 1,
                "type": "choice",
                "knowledge_point": kps[i % len(kps)],
                "difficulty": body.difficulty,
                "question": f"在 {kps[i % len(kps)]} 中，以下哪个描述是正确的？",
                "options": [
                    "A. 选项一：这是正确的描述",
                    "B. 选项二：这是一个常见的误解",
                    "C. 选项三：这是部分正确的",
                    "D. 选项四：以上都不对",
                ],
                "answer": "A",
                "explanation": f"这是关于 {kps[i % len(kps)]} 的基础知识点。",
            }
        )
    return success(questions, "生成成功")


@router.post("/submit", summary="提交答案")
def submit_answer(
    body: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = QuizRecord(
        user_id=current_user.id,
        question_id=body.question_id,
        knowledge_point=body.knowledge_point,
        user_answer=body.user_answer,
        correct_answer=body.correct_answer or "",
        is_correct=body.user_answer == body.correct_answer if body.correct_answer else None,
        time_spent_seconds=body.time_spent_seconds,
    )
    db.add(record)
    db.commit()

    return success(
        {
            "id": record.id,
            "is_correct": record.is_correct,
            "correct_answer": body.correct_answer,
        },
        "提交成功",
    )


@router.get("/records", summary="获取答题记录")
def get_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(QuizRecord)
        .filter(QuizRecord.user_id == current_user.id)
        .order_by(QuizRecord.created_at.desc())
        .limit(50)
        .all()
    )
    data = [
        {
            "id": r.id,
            "question_id": r.question_id,
            "knowledge_point": r.knowledge_point,
            "is_correct": r.is_correct,
            "time_spent_seconds": r.time_spent_seconds,
            "created_at": str(r.created_at),
        }
        for r in records
    ]
    return success(data, "获取成功")


@router.get("/wrong", summary="获取错题列表")
def get_wrong(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(QuizRecord)
        .filter(QuizRecord.user_id == current_user.id, QuizRecord.is_correct == False)
        .order_by(QuizRecord.created_at.desc())
        .limit(50)
        .all()
    )
    data = [
        {
            "id": r.id,
            "question_id": r.question_id,
            "knowledge_point": r.knowledge_point,
            "user_answer": r.user_answer,
            "correct_answer": r.correct_answer,
            "created_at": str(r.created_at),
        }
        for r in records
    ]
    return success(data, "获取成功")
