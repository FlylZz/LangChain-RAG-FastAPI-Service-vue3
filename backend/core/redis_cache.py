"""
Redis 缓存工具：用于 RAG 查询结果缓存

用法：
    from core.redis_cache import rag_cache

    # 在 rag_service.py 中使用
    cached = await rag_cache.get(query)
    if cached:
        return cached
    result = self.chain.invoke(...)
    await rag_cache.set(query, result)

特性：
- 基于查询内容生成 MD5 缓存键，相同问题直接返回
- 默认 30 分钟过期
- Redis 不可用时静默降级
"""

import hashlib
from typing import Optional

from core.redis_config import get_cache, set_cache, delete_cache_pattern
from utils.logger_handler import logger


class RagCache:
    """RAG 查询结果缓存管理"""

    PREFIX = "rag_summarize"
    DEFAULT_EXPIRE = 1800  # 30 分钟

    @staticmethod
    def _make_key(query: str) -> str:
        """根据查询内容生成唯一缓存键"""
        # 对查询内容做 MD5，避免 key 过长
        query_hash = hashlib.md5(query.strip().encode("utf-8")).hexdigest()
        return f"{RagCache.PREFIX}:{query_hash}"

    @staticmethod
    async def get(query: str) -> Optional[str]:
        """
        尝试从缓存获取 RAG 查询结果
        :param query: 用户原始提问
        :return: 缓存的回答字符串，未命中返回 None
        """
        key = RagCache._make_key(query)
        result = await get_cache(key)
        if result is not None:
            logger.info(f"[Redis Cache] 命中 RAG 缓存 key={key}")
        return result

    @staticmethod
    async def set(query: str, answer: str, expire: int = None) -> bool:
        """
        将 RAG 查询结果写入缓存
        :param query: 用户原始提问
        :param answer: LLM 总结的回答
        :param expire: 过期时间（秒），默认 30 分钟
        """
        key = RagCache._make_key(query)
        ttl = expire or RagCache.DEFAULT_EXPIRE
        success = await set_cache(key, answer, ttl)
        if success:
            logger.info(f"[Redis Cache] RAG 结果已缓存 key={key}, expire={ttl}s")
        return success

    @staticmethod
    async def clear_all() -> int:
        """清空所有 RAG 缓存"""
        count = await delete_cache_pattern(f"{RagCache.PREFIX}:*")
        logger.info(f"[Redis Cache] 已清空 {count} 条 RAG 缓存")
        return count


# 全局单例
rag_cache = RagCache()
