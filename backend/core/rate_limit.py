"""
Redis 限流：
1. rate_limit() — 每路由依赖注入（已有）
2. RateLimitMiddleware — 全局限流中间件（新增）

全局限流作为兜底，防止单 IP 整体打爆服务；
每路由限流控制具体接口频率。两层配合，企业级标准。
"""

from fastapi import Request, HTTPException
from starlette.responses import JSONResponse

from core.redis_config import get_rate_limit_redis
from utils.logger_handler import logger


def rate_limit(limit: int = 10, window: int = 60):
    """
    限流依赖工厂函数
    :param limit:  时间窗口内最大请求数
    :param window: 时间窗口大小（秒）
    :return: FastAPI 依赖函数
    """

    async def dependency(request: Request):
        # 获取客户端 IP
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # 从 Token 中提取用户标识（实现用户级限流）
        auth = request.headers.get("Authorization", "")
        if auth and len(auth) > 16:
            user_key = auth[-16:]  # Token 后16位作为用户标识
        else:
            user_key = client_ip

        # 生成限流键：rate_limit:{路径}:{用户标识}
        path = request.url.path
        key = f"rate_limit:{path}:{user_key}"

        try:
            r = await get_rate_limit_redis()
            current = await r.get(key)
            current = int(current) if current else 0

            if current >= limit:
                logger.warning(f"[限流] 触发限流 key={key}, current={current}/{limit}")
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请 {window} 秒后再试（限制：{limit}次/{window}秒）"
                )

            # 增加计数
            if current == 0:
                # 第一次请求，设置过期时间
                await r.setex(key, window, 1)
            else:
                # 后续请求，仅增加计数
                await r.incr(key)

        except HTTPException:
            raise  # 限流异常正常抛出
        except Exception as e:
            # Redis 不可用时降级放行，不阻塞业务
            logger.warning(f"[限流] Redis 异常，降级放行: {e}")

    return dependency


class RateLimitMiddleware:
    """
    全局限流中间件：基于 IP 的请求总数限制
    在 main.py 中通过 app.add_middleware(RateLimitMiddleware, limit=100, window=60) 注册
    每个路由的 rate_limit 仍然生效，全局限流是额外的兜底层
    """

    def __init__(self, app, limit: int = 100, window: int = 60):
        self.app = app
        self.limit = limit
        self.window = window

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # 构建请求对象
        request = Request(scope, receive)

        # 获取客户端 IP
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # 全局限流键
        key = f"rate_limit:global:{client_ip}"

        try:
            r = await get_rate_limit_redis()
            current = await r.get(key)
            current = int(current) if current else 0

            if current >= self.limit:
                logger.warning(f"[全局限流] IP={client_ip} 触发全局限制 {current}/{self.limit}")
                response = JSONResponse(
                    {"code": 429, "message": "请求过于频繁，请稍后再试", "data": None},
                    status_code=429
                )
                await response(scope, receive, send)
                return

            # 增加计数
            if current == 0:
                await r.setex(key, self.window, 1)
            else:
                await r.incr(key)

        except Exception as e:
            # Redis 不可用时降级放行
            logger.warning(f"[全局限流] Redis 异常，降级放行: {e}")

        await self.app(scope, receive, send)
