from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config.db_conf import async_engine
from models.users import Base
from routers import users, history
from utils.exception_handlers import register_exception_handlers

# 头像上传目录
AVATAR_DIR = os.path.join(os.path.dirname(__file__), "uploads", "avatars")


@asynccontextmanager
async def lifespan(application: FastAPI):
    # 启动时：创建所有表（history 模块导入会注册其表到同一个 Base.metadata）
    import models.history  # 确保表注册到 Base.metadata
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 确保头像上传目录存在
    os.makedirs(AVATAR_DIR, exist_ok=True)
    yield
    # 关闭时：释放引擎
    await async_engine.dispose()


app = FastAPI(
    title="FastAPI UserService + Conversation API",
    description="用户认证 + 历史会话管理，服务于 LangChain + RAG 项目",
    version="2.0.0",
    lifespan=lifespan,
)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(users.router)
app.include_router(history.router)

# 挂载静态文件：头像图片可通过 /uploads/avatars/xxx.jpg 访问
app.mount("/uploads", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "uploads")), name="uploads")


@app.get("/")
async def root():
    return {"message": "FastAPI UserService is running", "version": "2.0.0"}


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "healthy", "service": "history-service"}
