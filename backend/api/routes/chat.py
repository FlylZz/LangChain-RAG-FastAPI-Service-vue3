"""
聊天对话 API 路由
提供 /api/chat（非流式）和 /api/chat/stream（SSE流式）两个端点
"""

import json
import asyncio
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.react_agent import ReactAgent
from api.services.history_client import history_client
from core.rate_limit import rate_limit
from utils.logger_handler import logger
from utils.response import success_response

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Agent 全局单例
_agent: Optional[ReactAgent] = None


def get_agent() -> ReactAgent:
    global _agent
    if _agent is None:
        _agent = ReactAgent()
    return _agent


# ==================== 请求模型 ====================

class ChatRequest(BaseModel):
    session_id: Optional[int] = Field(None, alias="sessionId", description="会话ID，不传则自动创建")
    query: str = Field(..., min_length=1, description="用户提问内容")

    model_config = {"populate_by_name": True}


# ==================== 辅助函数 ====================

def _extract_token(request: Request) -> str:
    """从请求头提取 Bearer Token"""
    auth = request.headers.get("Authorization", "")
    if not auth:
        raise HTTPException(status_code=401, detail="缺少 Authorization 请求头")
    return auth.replace("Bearer ", "")


async def _verify_token(token: str) -> dict:
    """调用 HistoryService 验证 token 并返回用户信息"""
    try:
        result = await history_client.get_user_info(token)
        return result
    except Exception as e:
        logger.error(f"[token verify]验证令牌失败: {e}")
        raise HTTPException(status_code=401, detail="无效的令牌或已过期")


async def _load_history(token: str, session_id: int) -> list[dict]:
    """从 HistoryService 加载会话历史消息"""
    try:
        return await history_client.get_all_messages(token, session_id)
    except Exception as e:
        logger.warning(f"[load history]加载历史消息失败: {e}")
        return []


# ==================== 非流式对话 ====================

@router.post("", summary="普通对话（非流式）")
async def chat(payload: ChatRequest, request: Request, _: None = Depends(rate_limit(limit=10, window=60))):
    """
    非流式对话：等待 Agent 完整回复后一次性返回 JSON
    """
    token = _extract_token(request)
    user_info = await _verify_token(token)

    # 1. 确定会话：有 sessionId 则复用，否则创建新会话
    session_id = payload.session_id
    if not session_id:
        session = await history_client.create_session(token)
        session_id = session["id"]

    # 2. 加载历史消息
    history = await _load_history(token, session_id)

    # 3. 保存用户消息到 HistoryService
    await history_client.add_message(token, session_id, role="user", content=payload.query)

    # 4. 执行 Agent
    agent = get_agent()
    full_answer = ""
    for chunk in agent.execute_stream(payload.query, history_messages=history):
        full_answer += chunk

    # 5. 保存 AI 回复
    full_answer = full_answer.strip()
    await history_client.add_message(
        token, session_id,
        role="assistant",
        content=full_answer,
        meta_data={"model": "qwen3-max"},
    )

    return success_response(data={"sessionId": session_id, "answer": full_answer})


# ==================== SSE 流式对话 ====================

@router.post("/stream", summary="流式对话（SSE）")
async def chat_stream(payload: ChatRequest, request: Request, _: None = Depends(rate_limit(limit=10, window=60))):
    """
    SSE 流式对话：逐字推送 AI 回复内容
    
    事件类型：
      - session: 会话信息（首次）
      - chunk:   AI 回复文本片段
      - done:    回复完成（含 metaData）
      - error:   出错
    """
    token = _extract_token(request)
    user_info = await _verify_token(token)

    async def event_generator():
        session_id = payload.session_id
        try:
            # 1. 确定会话
            if not session_id:
                session = await history_client.create_session(token)
                session_id = session["id"]

            # 推送 session 事件
            yield f"event: session\ndata: {json.dumps({'sessionId': session_id}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

            # 2. 加载历史消息
            history = await _load_history(token, session_id)

            # 3. 保存用户消息
            await history_client.add_message(token, session_id, role="user", content=payload.query)

            # 4. 执行 Agent 并流式输出
            agent = get_agent()
            full_answer = ""
            for chunk in agent.execute_stream(payload.query, history_messages=history):
                full_answer += chunk
                yield f"event: chunk\ndata: {json.dumps({'content': chunk.strip()}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)

            # 5. 保存 AI 回复
            full_answer = full_answer.strip()
            await history_client.add_message(
                token, session_id,
                role="assistant",
                content=full_answer,
                meta_data={"model": "qwen3-max"},
            )

            # 推送 done 事件
            yield f"event: done\ndata: {json.dumps({'metaData': {'model': 'qwen3-max'}}, ensure_ascii=False)}\n\n"

        except HTTPException as e:
            yield f"event: error\ndata: {json.dumps({'message': e.detail}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[chat stream]流式对话异常: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': f'服务内部错误: {str(e)}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",       # 禁用 nginx 缓冲
        },
    )
