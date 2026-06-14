"""学习事件 Schema。"""

from pydantic import BaseModel


class EventCreateRequest(BaseModel):
    event_type: str
    resource_id: int | None = None
    page_id: str | None = None
    knowledge_point: str | None = None
    event_data: dict | None = None


class BatchEventsRequest(BaseModel):
    events: list[EventCreateRequest]


class MasteryResponse(BaseModel):
    knowledge_point: str
    mastery_score: float = 0.0
    confidence: float = 0.0
    updated_at: str = ""


class AssistantChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str
    context_type: str | None = None
    context_id: str | None = None
    context_text: str | None = None


class AssistantMessageResponse(BaseModel):
    id: int
    role: str
    content: str | None = None
    created_at: str = ""


class QuizGenerateRequest(BaseModel):
    knowledge_points: list[str] = []
    count: int = 5
    difficulty: str = "intermediate"


class QuizSubmitRequest(BaseModel):
    question_id: int
    knowledge_point: str = ""
    user_answer: str
    correct_answer: str = ""
    time_spent_seconds: int = 0
