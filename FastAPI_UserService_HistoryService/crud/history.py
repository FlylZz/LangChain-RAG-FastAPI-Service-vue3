from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.history import ConversationSession, ConversationMessage


# ==================== Session CRUD ====================

async def create_session(db: AsyncSession, user_id: int, title: Optional[str] = None) -> ConversationSession:
    """
    创建新会话
    """
    session = ConversationSession(
        user_id=user_id,
        title=title or f"新对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_list(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10,
    keyword: Optional[str] = None
) -> tuple[list[ConversationSession], int]:
    """
    获取用户的会话列表（分页，按更新时间倒序）
    - keyword: 可选，按会话标题模糊搜索
    """
    offset = (page - 1) * page_size

    # 基础过滤条件
    filters = [ConversationSession.user_id == user_id]
    if keyword:
        filters.append(ConversationSession.title.like(f'%{keyword}%'))

    count_query = select(func.count(ConversationSession.id)).where(*filters)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = (
        select(ConversationSession)
        .where(*filters)
        .order_by(ConversationSession.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    return sessions, total


async def get_session_by_id(db: AsyncSession, session_id: int) -> Optional[ConversationSession]:
    """
    根据ID获取会话（含消息列表）
    """
    query = (
        select(ConversationSession)
        .where(ConversationSession.id == session_id)
        .options(selectinload(ConversationSession.messages))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_session_title(db: AsyncSession, session_id: int, title: str) -> Optional[ConversationSession]:
    """
    更新会话标题
    """
    query = (
        update(ConversationSession)
        .where(ConversationSession.id == session_id)
        .values(title=title, updated_at=datetime.now())
    )
    result = await db.execute(query)
    await db.commit()
    if result.rowcount == 0:
        return None
    return await get_session_by_id(db, session_id)


async def delete_session(db: AsyncSession, session_id: int) -> bool:
    """
    删除会话（级联删除所有关联消息）
    """
    # 先删消息、再删会话
    await db.execute(
        delete(ConversationMessage).where(ConversationMessage.session_id == session_id)
    )
    result = await db.execute(
        delete(ConversationSession).where(ConversationSession.id == session_id)
    )
    await db.commit()
    return result.rowcount > 0


async def clear_user_sessions(db: AsyncSession, user_id: int) -> int:
    """
    清空用户所有会话及消息
    """
    # 先获取会话ID列表
    session_ids_query = select(ConversationSession.id).where(ConversationSession.user_id == user_id)
    session_ids_result = await db.execute(session_ids_query)
    session_ids = session_ids_result.scalars().all()

    if not session_ids:
        return 0

    # 删除所有关联消息
    await db.execute(
        delete(ConversationMessage).where(ConversationMessage.session_id.in_(session_ids))
    )
    # 删除所有会话
    result = await db.execute(
        delete(ConversationSession).where(ConversationSession.user_id == user_id)
    )
    await db.commit()
    return result.rowcount or 0


# ==================== Message CRUD ====================

async def add_message(
    db: AsyncSession,
    session_id: int,
    role: str,
    content: str,
    sources: Optional[list] = None,
    meta_data: Optional[dict] = None,
) -> ConversationMessage:
    """
    添加消息到会话（同时更新会话 updated_at）
    - 供 LangChain/RAG 调用
    - 首条 user 消息会自动设为会话标题（截取前40字）
    """
    message = ConversationMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=sources,
        meta_data=meta_data,
    )
    db.add(message)

    # 同步更新会话的 updated_at
    await db.execute(
        update(ConversationSession)
        .where(ConversationSession.id == session_id)
        .values(updated_at=datetime.now())
    )

    # 首条 user 消息自动设为会话标题
    if role == 'user':
        session = await db.get(ConversationSession, session_id)
        if session and (not session.title or session.title.startswith('新对话')):
            auto_title = content[:40] + ('...' if len(content) > 40 else '')
            session.title = auto_title
            db.add(session)

    await db.commit()
    await db.refresh(message)
    return message


async def get_messages_by_session(
    db: AsyncSession, session_id: int, page: int = 1, page_size: int = 50
) -> tuple[list[ConversationMessage], int]:
    """
    获取会话的消息列表（分页，按时间正序）
    """
    offset = (page - 1) * page_size

    count_query = select(func.count(ConversationMessage.id)).where(
        ConversationMessage.session_id == session_id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    query = (
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    messages = result.scalars().all()
    return messages, total


async def get_all_messages_by_session(
    db: AsyncSession, session_id: int
) -> list[ConversationMessage]:
    """
    获取会话的全部消息（不分页，供 LangChain 加载历史消息用）
    """
    query = (
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


# ==================== 搜索 ====================

async def search_messages(
    db: AsyncSession,
    user_id: int,
    keyword: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    按关键词搜索用户所有会话的消息内容（提问 + AI 回复）
    返回匹配的消息列表（带所属会话信息）和总数
    """
    from sqlalchemy import and_, or_

    # 过滤条件：属于该用户的会话 + 消息内容包含关键词
    filters = [
        ConversationSession.user_id == user_id,
        ConversationMessage.content.like(f'%{keyword}%'),
        ConversationMessage.role.in_(['user', 'assistant']),
    ]

    # 计算总数
    count_query = (
        select(func.count(ConversationMessage.id))
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(and_(*filters))
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # 查询匹配的消息，按时间倒序
    offset = (page - 1) * page_size
    query = (
        select(ConversationMessage, ConversationSession.title, ConversationSession.updated_at)
        .join(ConversationSession, ConversationMessage.session_id == ConversationSession.id)
        .where(and_(*filters))
        .order_by(ConversationMessage.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for msg, session_title, session_updated_at in rows:
        # 截取关键词附近的内容作为摘要
        content = msg.content
        idx = content.lower().find(keyword.lower())
        start = max(0, idx - 30)
        end = min(len(content), idx + len(keyword) + 30)
        snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')

        items.append({
            "messageId": msg.id,
            "sessionId": msg.session_id,
            "sessionTitle": session_title or "未命名会话",
            "role": msg.role,
            "snippet": snippet,
            "createdAt": msg.created_at.isoformat(),
            "sessionUpdatedAt": session_updated_at.isoformat(),
        })

    return items, total