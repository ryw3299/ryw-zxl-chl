"""资源 Schema。"""

from pydantic import BaseModel


class ResourceQuery(BaseModel):
    resource_type: str = ""
    direction: str = ""
    difficulty: str = ""
    keyword: str = ""
    page: int = 1
    page_size: int = 20


class ResourceResponse(BaseModel):
    id: int
    title: str
    resource_type: str
    direction: str | None = None
    difficulty: str | None = None
    description: str | None = None
    knowledge_points: list | None = None
    created_at: str = ""


class ResourceDetailResponse(ResourceResponse):
    content_url: str | None = None
    content_text: str | None = None
    duration_seconds: int | None = None


class ResourceListResponse(BaseModel):
    items: list[ResourceResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class GeneratedResourceRequest(BaseModel):
    resource_type: str  # document | ppt | mindmap | quiz | project | video_script
    title: str = ""
    path_id: int | None = None
    knowledge_points: list[str] = []
    difficulty: str = "intermediate"
    style: str = ""


class GeneratedResourceResponse(BaseModel):
    id: int
    resource_type: str
    title: str
    content: str = ""
    content_json: dict | None = None
    related_knowledge_points: list | None = None
    created_at: str = ""
