"""
会话管理 API 路由（代理 HistoryService）
为 Vue3 前端提供统一的会话/消息管理入口，
后端通过 history_client 转发请求到 HistoryService (Port 8000)
"""

from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.history_client import history_client
from utils.logger_handler import logger
from utils.response import success_response

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ==================== 请求模型 ====================

class SessionCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="会话标题，不传则自动生成")


class SessionUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="新的会话标题")


# ==================== 辅助函数 ====================

def _extract_token(request: Request) -> str:
    """从请求头提取 Bearer Token"""
    auth = request.headers.get("Authorization", "")
    if not auth:
        raise HTTPException(status_code=401, detail="缺少 Authorization 请求头")
    return auth.replace("Bearer ", "")


# ==================== Session 端点 ====================

@router.post("", summary="创建新会话")
async def create_session(data: SessionCreateRequest, request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.create_session(token, title=data.title)
        return success_response(message="会话创建成功", data=result)
    except Exception as e:
        logger.error(f"[session create]创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("", summary="获取会话列表（支持搜索）")
async def get_session_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    keyword: Optional[str] = Query(None, description="按会话标题模糊搜索"),
):
    token = _extract_token(request)
    try:
        result = await history_client.get_session_list(
            token, page=page, page_size=page_size, keyword=keyword
        )
        return success_response(data=result)
    except Exception as e:
        logger.error(f"[session list]获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.delete("", summary="清空用户所有会话")
async def clear_all_sessions(request: Request):
    """注意：此路由必须在 /{session_id} 之前注册，避免路径参数误匹配"""
    token = _extract_token(request)
    try:
        result = await history_client.clear_all_sessions(token)
        return success_response(message="会话已清空", data=result)
    except Exception as e:
        logger.error(f"[session clear]清空会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空会话失败: {str(e)}")


@router.get("/search", summary="搜索会话消息内容")
async def search_messages(
    request: Request,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
):
    token = _extract_token(request)
    try:
        result = await history_client.search_messages(
            token, keyword=keyword, page=page, page_size=page_size
        )
        return success_response(data=result)
    except Exception as e:
        logger.error(f"[session search]搜索会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/{session_id}", summary="获取会话详情（含消息列表）")
async def get_session_detail(session_id: int, request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.get_session_detail(token, session_id)
        return success_response(data=result)
    except Exception as e:
        logger.error(f"[session detail]获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.put("/{session_id}", summary="更新会话标题")
async def update_session(session_id: int, data: SessionUpdateRequest, request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.update_session_title(token, session_id, data.title)
        return success_response(message="标题更新成功", data=result)
    except Exception as e:
        logger.error(f"[session update]更新会话标题失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新会话标题失败: {str(e)}")


@router.delete("/{session_id}", summary="删除会话")
async def delete_session(session_id: int, request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.delete_session(token, session_id)
        return success_response(message="会话已删除", data=result)
    except Exception as e:
        logger.error(f"[session delete]删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


# ==================== Message 端点 ====================

@router.get("/{session_id}/messages", summary="获取会话消息列表（分页）")
async def get_messages(
    session_id: int,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
):
    token = _extract_token(request)
    try:
        result = await history_client.get_messages(
            token, session_id, page=page, page_size=page_size
        )
        return success_response(data=result)
    except Exception as e:
        logger.error(f"[messages]获取消息列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取消息列表失败: {str(e)}")


@router.get("/{session_id}/messages/all", summary="获取会话全部消息（供LangChain加载）")
async def get_all_messages(session_id: int, request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.get_all_messages(token, session_id)
        return success_response(data=result)
    except Exception as e:
        logger.error(f"[messages all]获取全部消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取全部消息失败: {str(e)}")
