from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


class BaseRequest(SchemaModel):
    trace_id: Optional[str] = Field(default=None, description="链路追踪 ID，便于日志排查")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展字段")


class BaseResponse(SchemaModel):
    status: Literal["success", "partial", "error"] = Field(
        default="success",
        description="处理状态：success=成功，partial=部分成功，error=失败",
    )
    message: str = Field(default="", description="返回信息")
    error_code: Optional[str] = Field(default=None, description="错误码")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展字段")
