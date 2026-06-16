"""画像 Schema。"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ProfileInitRequest(BaseModel):
    chat_history: list[ChatMessage]
    conversation_id: str = ""


class ProfileResponse(BaseModel):
    id: int | None = None
    profile_json: dict | None = None
    student_profile: dict | None = None
    summary: str | None = None
    profile_summary: str | None = None
    profile_ready: bool = False
    profile_type: str = ""
    dialogue_summary: str = ""
    collected_info: dict = Field(default_factory=dict)
    frontend_message: str = ""
    conversation_id: str = ""
    message_id: str = ""
    generation_record_id: int | None = None
    missing_information: list = Field(default_factory=list)
    version: int = 0
    created_at: str = ""
    updated_at: str = ""


class ProfileHistoryItem(BaseModel):
    id: int
    summary: str | None = None
    version: int
    created_at: str = ""


class ProfileInitStateResponse(BaseModel):
    has_draft: bool = False
    conversation_id: str = ""
    generation_record_id: int | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    updated_at: str = ""
