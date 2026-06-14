"""学习路径模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class LearningPath(Base):
    __tablename__ = "learning_path"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("student_profile.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    natural_language_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active | completed | archived
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="learning_paths")
