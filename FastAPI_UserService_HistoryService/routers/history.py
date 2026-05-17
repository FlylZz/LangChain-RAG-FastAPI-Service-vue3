from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_conf import get_db
from crud import history as history_crud
from models.users import User
from schemas.history import (
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionItemResponse,
    SessionListResponse,
    SessionDetailResponse,
    MessageAddRequest,
    MessageItemResponse,
    MessageListResponse,
)
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/sessions", tags=["conversation sessions"])


# ==================== Session 端点 ====================

@router.post("", summary="创建新会话")
async def create_session(
    data: SessionCreateRequest = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    title = data.title if data else None
    session = await history_crud.create_session(db, user.id, title)
    return success_response(
        message="会话创建成功",
        data=SessionItemResponse.model_validate(session),
    )


@router.get("", summary="获取会话列表（支持搜索）")
async def get_session_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    keyword: str = Query(None, description="按会话标题模糊搜索，例如 'fastapi'"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取历史会话列表，支持分页和关键词搜索。
    传 keyword 参数时按会话标题模糊匹配；不传则返回全部。
    """
    sessions, total = await history_crud.get_session_list(
        db, user.id, page, page_size, keyword=keyword
    )
    has_more = total > page * page_size

    session_list = [
        SessionItemResponse(
            id=s.id,
            userId=s.user_id,
            title=s.title,
            createdAt=s.created_at,
            updatedAt=s.updated_at,
            updatedAtFormatted=s.updated_at.strftime('%Y/%m/%d %H:%M'),
            messageCount=len(s.messages) if s.messages else 0,
        )
        for s in sessions
    ]

    return success_response(
        data=SessionListResponse(list=session_list, total=total, hasMore=has_more)
    )


@router.get("/search", summary="搜索会话消息内容")
async def search_messages(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    按关键词搜索用户所有会话中的消息内容（提问 + AI 回复），
    返回匹配的消息摘要以及所属会话信息。
    """
    items, total = await history_crud.search_messages(
        db, user.id, keyword, page, page_size
    )
    has_more = total > page * page_size
    return success_response(
        data={"list": items, "total": total, "hasMore": has_more}
    )


@router.get("/{session_id}", summary="获取会话详情（含消息列表）")
async def get_session_detail(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await history_crud.get_session_by_id(db, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
        )

    messages = [
        MessageItemResponse.model_validate(m) for m in (session.messages or [])
    ]

    detail = SessionDetailResponse(
        id=session.id,
        userId=session.user_id,
        title=session.title,
        createdAt=session.created_at,
        updatedAt=session.updated_at,
        updatedAtFormatted=session.updated_at.strftime('%Y/%m/%d %H:%M'),
        messageCount=len(messages),
        messages=messages,
    )
    return success_response(data=detail)


@router.put("/{session_id}", summary="更新会话标题")
async def update_session(
    session_id: int,
    data: SessionUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await history_crud.update_session_title(db, session_id, data.title)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
        )
    return success_response(
        message="标题更新成功",
        data=SessionItemResponse.model_validate(session),
    )


@router.delete("", summary="清空用户所有会话")
async def clear_all_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await history_crud.clear_user_sessions(db, user.id)
    return success_response(message=f"已清空 {count} 个会话")


@router.delete("/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await history_crud.delete_session(db, session_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
        )
    return success_response(message="会话已删除")


# ==================== Message 端点 ====================

@router.post("/{session_id}/messages", summary="添加消息到会话")
async def add_message(
    session_id: int,
    data: MessageAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    添加消息（LangChain/RAG 调用此接口存储对话记录）
    """
    # 验证会话归属
    session = await history_crud.get_session_by_id(db, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
        )

    message = await history_crud.add_message(
        db,
        session_id=session_id,
        role=data.role,
        content=data.content,
        sources=data.sources,
        meta_data=data.meta_data,
    )
    return success_response(
        message="消息已添加",
        data=MessageItemResponse.model_validate(message),
    )


@router.get("/{session_id}/messages", summary="获取会话消息列表")
async def get_messages(
    session_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 验证会话归属
    session = await history_crud.get_session_by_id(db, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
        )

    messages, total = await history_crud.get_messages_by_session(
        db, session_id, page, page_size
    )
    has_more = total > page * page_size

    message_list = [MessageItemResponse.model_validate(m) for m in messages]

    return success_response(
        data=MessageListResponse(list=message_list, total=total, hasMore=has_more)
    )


@router.get("/{session_id}/messages/all", summary="获取会话全部消息（供LangChain加载）")
async def get_all_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话的全部消息（不分页），供 LangChain 加载历史对话
    """
    session = await history_crud.get_session_by_id(db, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在"
        )

    messages = await history_crud.get_all_messages_by_session(db, session_id)
    message_list = [MessageItemResponse.model_validate(m) for m in messages]

    return success_response(data=message_list)
