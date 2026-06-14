"""智能助手路由（基础版）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.assistant import AssistantConversation, AssistantMessage
from src.models.user import User
from src.schemas.event_schema import AssistantChatRequest
from src.utils.response import success

router = APIRouter(prefix="/assistant", tags=["智能助手"])


@router.post("/chat", summary="发送消息给智能助手")
def chat(
    body: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_id = body.conversation_id

    if not conv_id:
        conv = AssistantConversation(
            user_id=current_user.id,
            title="新对话",
            context_type=body.context_type,
            context_id=body.context_id,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    # 保存用户消息
    user_msg = AssistantMessage(
        conversation_id=conv_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    # 模拟助手回复
    assistant_msg = AssistantMessage(
        conversation_id=conv_id,
        role="assistant",
        content=f"你好！我是你的学习助手。关于「{body.message[:50]}」的问题，建议你先查阅相关文档资料，我也可以帮你整理学习要点。请告诉我你具体想了解哪方面的内容？",
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return success(
        {
            "conversation_id": conv_id,
            "message": {
                "id": assistant_msg.id,
                "role": "assistant",
                "content": assistant_msg.content,
                "created_at": str(assistant_msg.created_at),
            },
        },
        "回复成功",
    )


@router.get("/conversations", summary="获取会话列表")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convs = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == current_user.id)
        .order_by(AssistantConversation.updated_at.desc())
        .limit(20)
        .all()
    )
    data = [
        {
            "id": c.id,
            "title": c.title,
            "context_type": c.context_type,
            "created_at": str(c.created_at),
        }
        for c in convs
    ]
    return success(data, "获取成功")


@router.get("/conversations/{conv_id}/messages", summary="获取会话消息")
def get_messages(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msgs = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.conversation_id == conv_id)
        .order_by(AssistantMessage.created_at)
        .all()
    )
    data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": str(m.created_at),
        }
        for m in msgs
    ]
    return success(data, "获取成功")
