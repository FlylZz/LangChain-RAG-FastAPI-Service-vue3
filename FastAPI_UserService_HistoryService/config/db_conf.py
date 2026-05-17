import os

from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession,create_async_engine

#数据库URL — 优先读环境变量（Docker 部署），否则用本地默认值
ASYNC_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root:123456@localhost:3306/ai_chat?charset=utf8mb4"
)

#创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,      # 每小时回收连接，防止 MySQL 断开
    pool_pre_ping=True,     # 每次取连接前先 ping，确保连接存活
)


# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, #绑定引擎
    class_=AsyncSession, #指定会话类
    expire_on_commit=False #设置会话结束后不关闭连接
)


# 依赖项，用于获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()





