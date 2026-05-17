from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict


class PaginationParams(BaseModel):
    """分页请求通用参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, alias="pageSize", description="每页条数")

    model_config = ConfigDict(populate_by_name=True)


class PaginationResponse(BaseModel):
    """分页响应通用字段"""
    total: int = Field(..., description="总条数")
    has_more: bool = Field(..., alias="hasMore", description="是否有更多")

    model_config = ConfigDict(populate_by_name=True)