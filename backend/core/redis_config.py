"""
Redis 异步连接管理
- 限流：DB 0
- 缓存：DB 1

配置通过环境变量覆盖：
  REDIS_HOST (默认 localhost)
  REDIS_PORT (默认 6379)
  REDIS_PASSWORD (默认 None)
"""

import os
import json
from typing import Any, Optional

import redis.asyncio as redis

from utils.logger_handler import logger

# ==================== 配置 ====================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB_RATE_LIMIT = 0
REDIS_DB_CACHE = 1

# ==================== 连接池 ====================
_rate_limit_client: Optional[redis.Redis] = None
_cache_client: Optional[redis.Redis] = None


async def get_rate_limit_redis() -> redis.Redis:
    """获取限流专用 Redis 连接"""
    global _rate_limit_client
    if _rate_limit_client is None:
        _rate_limit_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB_RATE_LIMIT,
            decode_responses=True,
        )
    return _rate_limit_client


async def get_cache_redis() -> redis.Redis:
    """获取缓存专用 Redis 连接"""
    global _cache_client
    if _cache_client is None:
        _cache_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB_CACHE,
            decode_responses=True,
        )
    return _cache_client


async def close_redis():
    """关闭所有 Redis 连接（应用关闭时调用）"""
    global _rate_limit_client, _cache_client
    if _rate_limit_client:
        await _rate_limit_client.aclose()
        _rate_limit_client = None
    if _cache_client:
        await _cache_client.aclose()
        _cache_client = None
    logger.info("[Redis] 连接已关闭")


async def check_redis_connection() -> bool:
    """检查 Redis 是否可用"""
    try:
        r = await get_rate_limit_redis()
        await r.ping()
        return True
    except Exception as e:
        logger.warning(f"[Redis] 连接失败（限流和缓存将降级跳过）: {e}")
        return False


# ==================== 缓存读写工具 ====================

async def get_cache(key: str) -> Optional[Any]:
    """从缓存获取数据（自动 JSON 反序列化）"""
    try:
        r = await get_cache_redis()
        data = await r.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception as e:
        logger.warning(f"[Redis Cache] GET 失败 key={key}: {e}")
        return None


async def set_cache(key: str, value: Any, expire: int = 3600) -> bool:
    """设置缓存（自动 JSON 序列化，默认 1 小时过期）"""
    try:
        r = await get_cache_redis()
        serialized = json.dumps(value, ensure_ascii=False)
        await r.set(key, serialized, ex=expire)
        return True
    except Exception as e:
        logger.warning(f"[Redis Cache] SET 失败 key={key}: {e}")
        return False


async def delete_cache(key: str) -> bool:
    """删除缓存"""
    try:
        r = await get_cache_redis()
        await r.delete(key)
        return True
    except Exception as e:
        logger.warning(f"[Redis Cache] DEL 失败 key={key}: {e}")
        return False


async def delete_cache_pattern(pattern: str) -> int:
    """根据模式批量删除缓存（如 rag_summarize:*）"""
    try:
        r = await get_cache_redis()
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            return await r.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"[Redis Cache] DEL pattern={pattern} 失败: {e}")
        return 0
