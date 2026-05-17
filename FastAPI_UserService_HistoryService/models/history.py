from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, DateTime, ForeignKey, Index, Text, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .users import User, Base


class ConversationSession(Base):
    """
    会话表 - 存储每次对话会话的元信息
    用于 LangChain + RAG 集成时管理会话上下文
    """
    __tablename__ = 'conversation_session'

    __table_args__ = (
        Index('fk_session_user_idx', 'user_id'),
        Index('idx_session_updated', 'updated_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="会话标题（可由首条消息自动生成）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                 nullable=False, comment="最后更新时间")

    # 关联消息
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="session", lazy="selectin",
        order_by="ConversationMessage.created_at"
    )

    def __repr__(self):
        return f"<ConversationSession(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class ConversationMessage(Base):
    """
    会话消息表 - 存储每条对话消息
    role: user(用户) / assistant(AI) / system(系统提示)
    sources: JSON字段，存储 RAG 检索到的来源文档信息
    metadata: JSON字段，存储 LangChain 所需的额外元数据（如token用量、模型名等）
    """
    __tablename__ = 'conversation_message'

    __table_args__ = (
        Index('fk_message_session_idx', 'session_id'),
        Index('idx_message_created', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey(ConversationSession.id), nullable=False, comment="所属会话ID")
    role: Mapped[str] = mapped_column(
        SAEnum('user', 'assistant', 'system', name='message_role_enum'),
        nullable=False, comment="消息角色：user/assistant/system"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="RAG检索来源文档（JSON格式）")
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="额外元数据（token用量、模型等）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="消息创建时间")

    # 关联会话
    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="messages")

    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"
