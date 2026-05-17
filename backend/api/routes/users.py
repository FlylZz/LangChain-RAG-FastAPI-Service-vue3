"""
用户管理 API 路由（代理 HistoryService）
为 Vue3 前端提供统一的用户认证入口，
后端通过 history_client 转发请求到 HistoryService (Port 8000)
"""

from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from api.services.history_client import history_client
from utils.logger_handler import logger
from utils.response import success_response
from utils.upload_validator import (
    validate_upload,
    AVATAR_ALLOWED_EXTENSIONS, AVATAR_ALLOWED_MIME_TYPES, AVATAR_MAX_SIZE,
)

router = APIRouter(prefix="/api/user", tags=["users"])


# ==================== 请求模型 ====================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")


class UserLoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    avatar: str | None = None
    gender: str | None = None
    bio: str | None = None
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., alias="oldPassword", description="旧密码")
    new_password: str = Field(..., min_length=6, alias="newPassword", description="新密码")

    model_config = {"populate_by_name": True}


# ==================== 辅助函数 ====================

def _extract_token(request: Request) -> str:
    """从请求头提取 Bearer Token"""
    auth = request.headers.get("Authorization", "")
    if not auth:
        raise HTTPException(status_code=401, detail="缺少 Authorization 请求头")
    return auth.replace("Bearer ", "")


# ==================== 端点 ====================

@router.post("/register", summary="用户注册")
async def register(data: UserRegisterRequest):
    try:
        result = await history_client.register(data.username, data.password)
        return success_response(message="注册成功", data=result)
    except Exception as e:
        logger.error(f"[user register]注册失败: {e}")
        # 尝试提取 httpx 的原始错误信息
        detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                detail = error_data.get("message", detail)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=detail)


@router.post("/login", summary="用户登录")
async def login(data: UserLoginRequest):
    try:
        result = await history_client.login(data.username, data.password)
        return success_response(message="登录成功", data=result)
    except Exception as e:
        logger.error(f"[user login]登录失败: {e}")
        detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                detail = error_data.get("message", detail)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=detail)


@router.get("/info", summary="获取当前用户信息")
async def get_user_info(request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.get_user_info(token)
        return success_response(message="获取用户信息成功", data=result)
    except Exception as e:
        logger.error(f"[user info]获取用户信息失败: {e}")
        raise HTTPException(status_code=401, detail="无效的令牌或已过期")


@router.put("/update", summary="更新用户信息")
async def update_user_info(data: UserUpdateRequest, request: Request):
    token = _extract_token(request)
    try:
        update_data = data.model_dump(exclude_none=True)
        result = await history_client.update_user_info(token, **update_data)
        return success_response(message="修改用户信息成功", data=result)
    except Exception as e:
        logger.error(f"[user update]更新用户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")


@router.put("/password", summary="修改密码")
async def change_password(data: ChangePasswordRequest, request: Request):
    token = _extract_token(request)
    try:
        result = await history_client.change_password(
            token, data.old_password, data.new_password
        )
        return success_response(message="修改密码成功", data=result)
    except Exception as e:
        logger.error(f"[user password]修改密码失败: {e}")
        raise HTTPException(status_code=500, detail=f"修改密码失败: {str(e)}")


@router.post("/avatar", summary="上传头像")
async def upload_avatar(file: UploadFile = File(...), request: Request = None):
    token = _extract_token(request)
    try:
        # 安全校验：扩展名 + 大小 + MIME
        await validate_upload(
            file,
            allowed_extensions=AVATAR_ALLOWED_EXTENSIONS,
            allowed_mime_types=AVATAR_ALLOWED_MIME_TYPES,
            max_size=AVATAR_MAX_SIZE,
            category="头像",
        )
        result = await history_client.upload_avatar(token, file)
        return success_response(message="头像上传成功", data=result)
    except Exception as e:
        logger.error(f"[user avatar]上传头像失败: {e}")
        detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                detail = error_data.get("detail", error_data.get("message", detail))
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=detail)
