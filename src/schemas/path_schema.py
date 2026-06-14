"""学习路径 Schema。"""

from pydantic import BaseModel


class PathGenerateRequest(BaseModel):
    profile_id: int
    daily_hours: float = 2.0
    learning_cycle_days: int = 30
    goal: str = ""


class PathResponse(BaseModel):
    id: int
    title: str = ""
    natural_language_summary: str | None = None
    path_json: dict = {}
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""


class PathListItem(BaseModel):
    id: int
    title: str
    status: str
    created_at: str = ""


class PathStatusUpdate(BaseModel):
    status: str  # active | completed | archived
