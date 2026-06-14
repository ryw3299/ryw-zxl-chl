"""SQLAlchemy 引擎与会话管理。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有表并填充种子数据。"""
    from src.models import (  # noqa: F401
        Announcement,
        AssistantConversation,
        AssistantMessage,
        GeneratedResource,
        KnowledgeMastery,
        LearningEvent,
        LearningPath,
        PlatformResource,
        QuizRecord,
        StudentProfile,
        StudyRecord,
        StudyTask,
        User,
    )

    Base.metadata.create_all(bind=engine)

    from src.services.resource_service import seed_resources
    from src.services.auth_service import seed_admin
    db = SessionLocal()
    try:
        seed_resources(db)
        seed_admin(db)
        _seed_announcements(db)
        _seed_study_records(db)
    finally:
        db.close()


def _seed_announcements(db: Session) -> None:
    """填充公告种子数据。"""
    from src.models.supplement import Announcement

    if db.query(Announcement).count() > 0:
        return

    items = [
        Announcement(title="关于期末考试安排及线上监考说明", description="请同学们仔细阅读考试安排，提前做好准备。", type="置顶", tag="primary", date="2025-05-20"),
        Announcement(title="Python课程第6章作业已发布", description="本次作业截止时间为5月28日 23:59，请同学们按时提交。", type="教学", tag="success", date="2025-05-19"),
        Announcement(title="智学工坊学习打卡活动来啦！", description="参与即可获得积分奖励，快来一起坚持学习吧！", type="活动", tag="warning", date="2025-05-18"),
        Announcement(title="关于图书馆五一假期开放安排的通知", description="图书馆五一假期开放时间有所调整，请关注。", type="通知", tag="info", date="2025-05-15"),
        Announcement(title="系统维护通知：5月25日 2:00-6:00", description="平台将进行系统升级维护，届时暂停服务。", type="公告", tag="danger", date="2025-05-14"),
    ]
    for item in items:
        db.add(item)
    db.commit()


def _seed_study_records(db: Session) -> None:
    """填充学习记录种子数据。"""
    from src.models.supplement import StudyRecord

    if db.query(StudyRecord).count() > 0:
        return

    # Creates sample study records for existing users
    from src.models.user import User
    users = db.query(User).all()
    for user in users:
        records = [
            StudyRecord(user_id=user.id, resource_title="Python 函数与模块", study_date="2025-05-20", duration_minutes=45, record_type="video", progress_percent=72, chapter="第4章 函数参数"),
            StudyRecord(user_id=user.id, resource_title="线性回归原理与实现", study_date="2025-05-19", duration_minutes=30, record_type="reading", progress_percent=45, chapter="第2节 损失函数"),
            StudyRecord(user_id=user.id, resource_title="数据结构：栈与队列", study_date="2025-05-18", duration_minutes=35, record_type="reading", progress_percent=58, chapter="第3章 栈的应用"),
            StudyRecord(user_id=user.id, resource_title="SQL 基础入门", study_date="2025-05-17", duration_minutes=25, record_type="quiz", progress_percent=25, chapter="第1章 查询基础"),
        ]
        for r in records:
            db.add(r)
    db.commit()
