"""
统一响应格式工具
所有接口统一返回 { code, message, data } 结构
"""
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(message: str = "success", data=None):
    """
    统一成功响应
    :param message: 提示信息
    :param data: 响应数据（支持 Pydantic Model、ORM 对象等）
    """
    content = {
        "code": 200,
        "message": message,
        "data": data
    }
    return JSONResponse(content=jsonable_encoder(content))
