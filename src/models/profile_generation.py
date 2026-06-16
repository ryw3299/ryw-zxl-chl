"""画像生成日志模型。"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ProfileGenerationRecord(Base):
    __tablename__ = "profile_generation_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("student_profile.id"), nullable=True, index=True
    )
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_ready: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    profile_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    dialogue_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    frontend_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="profile_generation_records")
    profile = relationship("StudentProfile", back_populates="generation_records")
