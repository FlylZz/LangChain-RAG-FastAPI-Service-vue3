from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict

from schemas.base import PaginationResponse


# ========== Session 相关 Schema ==========

class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, max_length=200, description="会话标题，不传则自动生成")


class SessionUpdateRequest(BaseModel):
    """更新会话标题请求"""
    title: str = Field(..., min_length=1, max_length=200, description="新的会话标题")


class SessionItemResponse(BaseModel):
    """会话列表单项响应"""
    id: int
    user_id: int = Field(alias="userId")
    title: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    updated_at_formatted: str = Field("", alias="updatedAtFormatted", description="格式化时间 YYYY/MM/DD HH:MM")
    message_count: int = Field(0, alias="messageCount", description="消息条数")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SessionListResponse(PaginationResponse):
    """会话列表响应"""
    list: list[SessionItemResponse]


# ========== Message 相关 Schema ==========

class MessageAddRequest(BaseModel):
    """添加消息请求（LangChain/RAG 调用时使用）"""
    role: str = Field(..., pattern="^(user|assistant|system)$", description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")
    sources: Optional[list[dict]] = Field(None, description="RAG检索来源文档列表")
    meta_data: Optional[dict] = Field(None, alias="metaData", description="额外元数据（token用量等）")

    model_config = ConfigDict(populate_by_name=True)


class MessageItemResponse(BaseModel):
    """消息列表单项响应"""
    id: int
    session_id: int = Field(alias="sessionId")
    role: str
    content: str
    sources: Optional[Any] = None
    meta_data: Optional[Any] = Field(None, alias="metaData")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessageListResponse(PaginationResponse):
    """消息列表响应"""
    list: list[MessageItemResponse]


# ========== 完整会话详情（含消息列表） ==========

class SessionDetailResponse(SessionItemResponse):
    """会话详情 - 包含消息列表"""
    messages: list[MessageItemResponse] = []