"""
全局异常处理器注册
注册顺序：子类在前，父类在后；具体在前，抽象在后
"""
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from utils.exception import (
    http_exception_handler,
    validation_exception_handler,
    business_exception_handler,
    BusinessException,
    general_exception_handler,
)


def register_exception_handlers(app):
    """
    注册全局异常处理器
    """
    app.add_exception_handler(HTTPException, http_exception_handler)              # HTTP 业务异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # 参数校验异常
    app.add_exception_handler(BusinessException, business_exception_handler)      # 业务自定义异常
    app.add_exception_handler(Exception, general_exception_handler)              # 兜底异常
