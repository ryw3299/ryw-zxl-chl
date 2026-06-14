"""画像 Schema。"""

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ProfileInitRequest(BaseModel):
    chat_history: list[ChatMessage]


class ProfileResponse(BaseModel):
    id: int
    profile_json: dict
    summary: str | None = None
    version: int = 1
    created_at: str = ""
    updated_at: str = ""


class ProfileHistoryItem(BaseModel):
    id: int
    summary: str | None = None
    version: int
    created_at: str = ""
