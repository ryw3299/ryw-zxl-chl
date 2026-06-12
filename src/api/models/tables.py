import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, text
from sqlalchemy.dialects.mysql import LONGTEXT as _MYSQL_LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from src.api.config import settings

from .database import Base


def _is_mysql() -> bool:
    """Check at import-time whether the effective DB is MySQL.

    Falls back to ``False`` so SQLite (zero-config dev) works out of the box.
    """
    return (settings.DATABASE_URL or "").startswith("mysql")


# LONGTEXT is MySQL-only.  On SQLite we fall back to plain Text (which has no
# size cap on SQLite anyway).
LONGTEXT = _MYSQL_LONGTEXT().with_variant(Text(), "sqlite")

# MySQL-specific table args are silently ignored by other dialects in
# SQLAlchemy (they are scoped via the ``mysql_*`` prefix), so it is safe to
# always pass them.
_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}

_NOW = text("CURRENT_TIMESTAMP")
_NOW_ON_UPDATE = text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP") if _is_mysql() else _NOW


class User(Base):
    __tablename__ = "users"
    __table_args__ = ({"comment": "用户表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="系统内部用户ID")
    platform_user_id: Mapped[Optional[str]] = mapped_column(String(128), comment="外部平台用户ID")
    platform_id: Mapped[Optional[str]] = mapped_column(String(64), comment="外部平台标识")
    user_name: Mapped[str] = mapped_column(String(128), default="", comment="用户姓名")
    role: Mapped[str] = mapped_column(String(16), default="student", comment="角色: student/teacher")
    school_id: Mapped[Optional[str]] = mapped_column(String(64), comment="学校ID")
    email: Mapped[Optional[str]] = mapped_column(String(256), comment="邮箱")
    phone: Mapped[Optional[str]] = mapped_column(String(32), comment="手机号")
    password_hash: Mapped[Optional[str]] = mapped_column(Text, comment="Password hash for local accounts")
    auth_token: Mapped[Optional[str]] = mapped_column(Text, comment="身份验证令牌")
    related_course_ids: Mapped[Optional[str]] = mapped_column(Text, comment="关联课程ID列表(JSON)")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = ({"comment": "课程表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="系统内部课程ID")
    platform_course_id: Mapped[Optional[str]] = mapped_column(String(128), comment="外部平台课程ID")
    platform_id: Mapped[Optional[str]] = mapped_column(String(64), comment="外部平台标识")
    course_name: Mapped[str] = mapped_column(String(256), default="", comment="课程名称")
    school_id: Mapped[Optional[str]] = mapped_column(String(64), comment="学校ID")
    school_name: Mapped[Optional[str]] = mapped_column(String(256), comment="学校名称")
    teacher_info: Mapped[Optional[str]] = mapped_column(Text, comment="教师信息(JSON)")
    term: Mapped[Optional[str]] = mapped_column(String(32), comment="学期")
    credit: Mapped[Optional[float]] = mapped_column(Float, comment="学分")
    period: Mapped[Optional[int]] = mapped_column(Integer, comment="学时")
    course_cover: Mapped[Optional[str]] = mapped_column(String(512), comment="课程封面URL")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class ParseTask(Base):
    __tablename__ = "parse_tasks"
    __table_args__ = ({"comment": "解析任务表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parse_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="解析任务ID")
    school_id: Mapped[Optional[str]] = mapped_column(String(64), comment="学校ID")
    user_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="发起用户ID")
    course_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="课程ID")
    file_type: Mapped[str] = mapped_column(String(16), comment="文件类型")
    file_url: Mapped[str] = mapped_column(String(1024), comment="文件URL/路径")
    file_name: Mapped[str] = mapped_column(String(512), default="", comment="文件名")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, comment="文件大小(字节)")
    page_count: Mapped[Optional[int]] = mapped_column(Integer, comment="页数")
    is_extract_key_point: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否提取重点")
    task_status: Mapped[str] = mapped_column(
        String(16), default="processing", comment="状态: processing/completed/failed"
    )
    structure_preview: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="知识点结构预览(JSON)")
    parser_output: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="完整解析输出(JSON)")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class Script(Base):
    __tablename__ = "scripts"
    __table_args__ = ({"comment": "脚本表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    script_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="脚本ID")
    parse_id: Mapped[str] = mapped_column(String(64), index=True, comment="关联解析任务ID")
    lesson_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="关联智课ID")
    teaching_style: Mapped[str] = mapped_column(String(32), default="standard", comment="讲授风格")
    speech_speed: Mapped[str] = mapped_column(String(16), default="normal", comment="语速")
    custom_opening: Mapped[Optional[str]] = mapped_column(Text, comment="自定义开场白")
    script_structure: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="脚本结构(JSON)")
    generate_output: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="完整生成输出(JSON)")
    task_status: Mapped[str] = mapped_column(
        String(16), default="processing", comment="状态: processing/completed/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class AudioTask(Base):
    __tablename__ = "audio_tasks"
    __table_args__ = ({"comment": "音频任务表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audio_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="音频任务ID")
    script_id: Mapped[str] = mapped_column(String(64), index=True, comment="关联脚本ID")
    voice_type: Mapped[str] = mapped_column(String(32), default="female_standard", comment="语音类型")
    audio_format: Mapped[str] = mapped_column(String(8), default="mp3", comment="音频格式")
    section_ids: Mapped[Optional[str]] = mapped_column(Text, comment="指定章节ID(JSON)")
    audio_url: Mapped[Optional[str]] = mapped_column(String(1024), comment="音频文件URL")
    total_duration: Mapped[Optional[int]] = mapped_column(Integer, comment="总时长(秒)")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, comment="文件大小(字节)")
    bit_rate: Mapped[Optional[int]] = mapped_column(Integer, comment="比特率")
    section_audios: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="分章节音频信息(JSON)")
    task_status: Mapped[str] = mapped_column(
        String(16), default="processing", comment="状态: processing/completed/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = ({"comment": "智课表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="智课ID")
    course_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="课程ID")
    parse_id: Mapped[Optional[str]] = mapped_column(String(64), comment="关联解析任务ID")
    script_id: Mapped[Optional[str]] = mapped_column(String(64), comment="关联脚本ID")
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(String(64), comment="关联知识库ID")
    lesson_name: Mapped[str] = mapped_column(String(256), default="", comment="智课名称")
    status: Mapped[str] = mapped_column(String(16), default="draft", comment="状态: draft/published/archived")
    structured_content: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="结构化教学内容(JSON)")
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), comment="结构化内容版本哈希")
    ppt_outline: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="PPT大纲(JSON)")
    rendered_ppt_path: Mapped[Optional[str]] = mapped_column(String(1024), comment="渲染后PPTX路径")
    courseware_project_dir: Mapped[Optional[str]] = mapped_column(String(1024), comment="课件项目目录")
    slide_plan_path: Mapped[Optional[str]] = mapped_column(String(1024), comment="slide_plan.json路径")
    slide_plan_json: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="slide_plan.json内容")
    courseware_status: Mapped[Optional[str]] = mapped_column(String(32), comment="课件链路状态")
    courseware_render_mode: Mapped[Optional[str]] = mapped_column(String(16), comment="课件渲染模式: flash/pro")
    narration_paths: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="四档讲稿路径(JSON)")
    courseware_error: Mapped[Optional[str]] = mapped_column(Text, comment="课件链路错误信息")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class QASession(Base):
    __tablename__ = "qa_sessions"
    __table_args__ = ({"comment": "问答会话表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="会话ID")
    user_id: Mapped[str] = mapped_column(String(64), index=True, comment="学生用户ID")
    school_id: Mapped[Optional[str]] = mapped_column(String(64), comment="学校ID")
    course_id: Mapped[str] = mapped_column(String(64), comment="课程ID")
    lesson_id: Mapped[str] = mapped_column(String(64), comment="智课ID")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="状态: active/paused/completed")
    current_section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="当前章节ID")
    current_page: Mapped[Optional[int]] = mapped_column(Integer, comment="当前页码")
    current_script_block_id: Mapped[Optional[str]] = mapped_column(String(64), comment="当前讲稿块ID")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, comment="会话进度百分比")
    last_action: Mapped[Optional[str]] = mapped_column(String(32), comment="最近一次教学动作")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class QARecord(Base):
    __tablename__ = "qa_records"
    __table_args__ = ({"comment": "问答记录表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    answer_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="回答ID")
    session_id: Mapped[str] = mapped_column(String(64), index=True, comment="所属会话ID")
    user_id: Mapped[str] = mapped_column(String(64), index=True, comment="学生用户ID")
    course_id: Mapped[str] = mapped_column(String(64), comment="课程ID")
    lesson_id: Mapped[str] = mapped_column(String(64), comment="智课ID")
    question_type: Mapped[str] = mapped_column(String(8), default="text", comment="提问类型: text/voice")
    student_question_type: Mapped[Optional[str]] = mapped_column(String(32), comment="学生问题语义分类")
    question_content: Mapped[str] = mapped_column(Text, comment="提问内容")
    current_section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="提问时所在章节ID")
    current_page: Mapped[Optional[int]] = mapped_column(Integer, comment="提问时所在页码")
    current_script_block_id: Mapped[Optional[str]] = mapped_column(String(64), comment="提问时所在讲稿块ID")
    answer_content: Mapped[Optional[str]] = mapped_column(Text, comment="系统回答")
    answer_type: Mapped[str] = mapped_column(String(16), default="text", comment="回答类型: text/mixed")
    related_knowledge: Mapped[Optional[str]] = mapped_column(Text, comment="关联知识点(JSON)")
    suggestions: Mapped[Optional[str]] = mapped_column(Text, comment="追问建议(JSON)")
    references_json: Mapped[Optional[str]] = mapped_column(LONGTEXT, comment="检索引用(JSON)")
    understanding_level: Mapped[Optional[str]] = mapped_column(
        String(16), comment="理解程度: full/partial/none"
    )
    next_action: Mapped[Optional[str]] = mapped_column(String(32), comment="下一步教学动作")
    reason: Mapped[Optional[str]] = mapped_column(Text, comment="动作原因")
    matched_section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="主命中章节ID")
    matched_page: Mapped[Optional[int]] = mapped_column(Integer, comment="主命中页码")
    target_section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="目标章节ID")
    target_page: Mapped[Optional[int]] = mapped_column(Integer, comment="目标页码")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = ({"comment": "学习进度表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="追踪记录ID")
    school_id: Mapped[Optional[str]] = mapped_column(String(64), comment="学校ID")
    user_id: Mapped[str] = mapped_column(String(64), index=True, comment="学生用户ID")
    course_id: Mapped[str] = mapped_column(String(64), comment="课程ID")
    lesson_id: Mapped[str] = mapped_column(String(64), index=True, comment="智课ID")
    current_section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="当前章节ID")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, comment="章节学习进度(0-100)")
    total_progress: Mapped[float] = mapped_column(Float, default=0.0, comment="智课总学习进度(0-100)")
    next_section_suggest: Mapped[Optional[str]] = mapped_column(String(64), comment="建议后续学习章节")
    last_operate_time: Mapped[Optional[str]] = mapped_column(String(32), comment="最后操作时间")
    qa_record_id: Mapped[Optional[str]] = mapped_column(String(64), comment="最近问答记录ID")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = ({"comment": "知识库表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="知识库ID")
    course_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="课程ID")
    kb_name: Mapped[str] = mapped_column(String(256), default="", comment="知识库名称")
    scope_type: Mapped[str] = mapped_column(
        String(16), default="course", comment="范围: lesson/course/custom"
    )
    status: Mapped[str] = mapped_column(
        String(16), default="draft", comment="状态: draft/indexing/ready/failed"
    )
    index_backend: Mapped[str] = mapped_column(String(16), default="faiss", comment="索引后端")
    embedding_model: Mapped[Optional[str]] = mapped_column(String(64), comment="Embedding模型标识")
    index_path: Mapped[Optional[str]] = mapped_column(String(1024), comment="索引文件路径")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="Chunk总数")
    source_count: Mapped[int] = mapped_column(Integer, default=0, comment="来源文档总数")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=_NOW_ON_UPDATE, comment="更新时间"
    )


class KnowledgeBaseSource(Base):
    __tablename__ = "knowledge_base_sources"
    __table_args__ = ({"comment": "知识库来源表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_source_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="来源记录ID")
    kb_id: Mapped[str] = mapped_column(String(64), index=True, comment="知识库ID")
    source_kind: Mapped[str] = mapped_column(String(16), comment="来源类型: lesson/parse_task/file")
    lesson_id: Mapped[Optional[str]] = mapped_column(String(64), comment="关联智课ID")
    parse_id: Mapped[Optional[str]] = mapped_column(String(64), comment="关联解析任务ID")
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), comment="文件URL")
    file_name: Mapped[Optional[str]] = mapped_column(String(512), comment="文件名")
    source_hash: Mapped[Optional[str]] = mapped_column(String(64), comment="来源内容哈希")
    status: Mapped[str] = mapped_column(String(16), default="pending", comment="状态: pending/indexed/failed")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = ({"comment": "知识库Chunk元数据表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="Chunk ID")
    kb_id: Mapped[str] = mapped_column(String(64), index=True, comment="知识库ID")
    lesson_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="关联智课ID")
    source_type: Mapped[str] = mapped_column(String(32), comment="来源类型")
    source_id: Mapped[str] = mapped_column(String(128), comment="来源对象ID")
    section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="章节ID")
    page: Mapped[Optional[int]] = mapped_column(Integer, comment="页码")
    title: Mapped[Optional[str]] = mapped_column(String(512), comment="标题")
    text: Mapped[str] = mapped_column(LONGTEXT, comment="Chunk文本")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, comment="Chunk序号")
    key_points_json: Mapped[Optional[str]] = mapped_column(Text, comment="关键知识点(JSON)")
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, comment="附加元数据(JSON)")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")


class AdjustRecord(Base):
    __tablename__ = "adjust_records"
    __table_args__ = ({"comment": "节奏调整记录表", **_TABLE_ARGS},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adjust_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="调整记录ID")
    user_id: Mapped[str] = mapped_column(String(64), index=True, comment="学生用户ID")
    lesson_id: Mapped[str] = mapped_column(String(64), index=True, comment="智课ID")
    current_section_id: Mapped[str] = mapped_column(String(64), comment="当前章节ID")
    understanding_level: Mapped[str] = mapped_column(String(16), comment="理解程度")
    qa_record_id: Mapped[Optional[str]] = mapped_column(String(64), comment="关联问答记录ID")
    adjust_type: Mapped[str] = mapped_column(String(32), comment="调整类型: normal/supplement")
    continue_section_id: Mapped[Optional[str]] = mapped_column(String(64), comment="续讲章节ID")
    supplement_content: Mapped[Optional[str]] = mapped_column(Text, comment="补充内容(JSON)")
    next_sections: Mapped[Optional[str]] = mapped_column(Text, comment="后续章节调整方案(JSON)")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=_NOW, comment="创建时间")
