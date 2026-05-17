"""
全局异常处理器
- HTTPException：401/403/404/429 等
- RequestValidationError：参数校验失败
- BusinessException：业务逻辑主动抛出的结构化错误
- Exception：兜底未捕获异常
含敏感信息脱敏
"""
import re
import traceback

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

# 开发模式：返回详细错误信息（含堆栈）
# 生产模式：只返回友好提示
DEBUG_MODE = True


class BusinessException(Exception):
    """
    业务异常基类：业务逻辑主动抛出
    示例：
        if user_quota <= 0:
            raise BusinessException(code=4001, message="配额不足")
    """
    def __init__(self, code: int = 400, message: str = "出现错误"):
        self.code = code
        self.message = message
        super().__init__(message)


def mask_sensitive_info(text: str) -> str:
    """
    敏感信息脱敏：过滤 API 密钥、密码、数据库连接串等
    """
    if not text:
        return text

    sensitive_patterns = [
        r"sk-[a-zA-Z0-9]{32,}",                       # OpenAI / 通义千问 API 密钥
        r"api[-_]?key['\"]\s*[:=]\s*['\"][^'\"]{16,}['\"]",  # api_key=xxx
        r"password['\"]\s*[:=]\s*['\"][^'\"]{4,}['\"]",      # password=xxx
        r"passwd['\"]\s*[:=]\s*['\"][^'\"]{4,}['\"]",        # passwd=xxx
        r"mysql://[^@]+@",                                     # MySQL 连接串
        r"postgresql://[^@]+@",                                # PostgreSQL 连接串
    ]

    masked_text = text
    for pattern in sensitive_patterns:
        masked_text = re.sub(pattern, "***", masked_text)

    return masked_text


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    处理 HTTPException（401/403/404/405/429 等业务异常）
    """
    custom_msg_map = {
        401: "请先登录或确保您的令牌有效",
        403: "无权限访问该接口",
        404: "接口不存在，请检查URL",
        405: "请求方法不支持",
        429: "请求过于频繁，请稍后再试",
    }
    friendly_msg = custom_msg_map.get(exc.status_code, exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": friendly_msg, "data": None}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理 FastAPI 参数校验异常（最常见异常之一）
    将原始校验错误转换为用户友好的提示
    """
    error_details = exc.errors()
    friendly_msg_parts = []

    for err in error_details:
        # 提取字段名（过滤 'body'/'query'/'path' 等定位前缀）
        field_parts = [str(x) for x in err["loc"] if x not in ("body", "query", "path")]
        field = ".".join(field_parts) if field_parts else "请求参数"

        # 友好转换错误类型
        msg = err["msg"]
        if err["type"] == "missing":
            msg = "为必填项"
        elif err["type"] == "int_parsing":
            msg = "应为整数类型"
        elif err["type"] == "float_parsing":
            msg = "应为数字类型"
        elif err["type"] == "string_too_short":
            msg = "长度不足"
        elif err["type"] == "string_too_long":
            msg = "超出最大长度"

        friendly_msg_parts.append(f"字段「{field}」{msg}")

    friendly_msg = "；".join(friendly_msg_parts)

    # 开发模式保留原始校验信息
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": "RequestValidationError",
            "raw_errors": error_details,
            "path": str(request.url),
        }

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": 400, "message": friendly_msg, "data": error_data}
    )


async def business_exception_handler(request: Request, exc: BusinessException):
    """处理业务异常（业务逻辑主动抛出）"""
    logger.warning(f"业务异常: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # 业务异常 HTTP 200，用业务 code 区分
        content={"code": exc.code, "message": exc.message, "data": None}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    兜底异常处理器：处理所有未捕获的系统异常
    """
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": mask_sensitive_info(str(exc)),
            "traceback": mask_sensitive_info(traceback.format_exc()),
            "path": str(request.url),
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "服务器内部错误，请稍后重试", "data": error_data}
    )
