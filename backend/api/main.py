"""
FastAPI 应用入口 — Backend Agent 服务
为 Vue3 前端提供统一 API 入口：
  - /api/chat, /api/chat/stream    — Agent 对话
  - /api/sessions/*                — 会话管理（代理 HistoryService）
  - /api/user/*                    — 用户认证（代理 HistoryService）

启动方式:
    uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
"""

from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chat import router as chat_router
from api.routes.history import router as history_router
from api.routes.users import router as users_router
from core.redis_config import check_redis_connection, close_redis
from core.rate_limit import RateLimitMiddleware
from utils.exception_handlers import register_exception_handlers
from utils.logger_handler import logger


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("[Agent API]服务启动中...")
    logger.info("[Agent API]API 入口：http://127.0.0.1:8001/docs")
    # 检查 Redis 连接状态
    redis_ok = await check_redis_connection()
    if redis_ok:
        logger.info("[Agent API]Redis 连接正常（限流+缓存已启用）")
    else:
        logger.warning("[Agent API]Redis 不可用，限流和缓存将降级跳过")
    yield
    # 关闭 Redis 连接池
    await close_redis()
    logger.info("[Agent API]服务关闭")


app = FastAPI(
    title="智扫通机器人 Agent API",
    description="LangChain + RAG 智能对话服务 + 用户/会话管理，为 Vue3 前端提供统一 API 入口",
    version="2.0.0",
    lifespan=lifespan,
)

# ==================== 全局异常处理 ====================
register_exception_handlers(app)

# ==================== 全局限流中间件 ====================
app.add_middleware(RateLimitMiddleware, limit=100, window=60)  # 每 IP 每分钟最多 100 次请求

# ==================== 处理耗时中间件 ====================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response

# ==================== CORS 配置 ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vue3 开发服务器
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 注册路由 ====================
app.include_router(users_router)
app.include_router(history_router)
app.include_router(chat_router)


# ==================== 基础端点 ====================

@app.get("/")
async def root():
    return {
        "code": 200,
        "message": "success",
        "data": {
            "service": "智扫通机器人 Agent API",
            "version": "2.0.0",
            "endpoints": {
                "chat": "/api/chat (POST), /api/chat/stream (POST SSE)",
                "sessions": "/api/sessions (GET, POST), /api/sessions/{id} (GET, PUT, DELETE)",
                "users": "/api/user/register (POST), /api/user/login (POST), /api/user/info (GET)",
            },
            "docs": "/docs",
        },
    }


@app.get("/health", summary="健康检查")
async def health():
    redis_ok = await check_redis_connection()
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "healthy",
            "service": "agent-backend",
            "redis": "connected" if redis_ok else "disconnected (degraded)",
        },
    }
