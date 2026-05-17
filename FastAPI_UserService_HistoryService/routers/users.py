from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
import os
import uuid

from models.users import User, Base
from schemas.users import UserRequest, UserAuthResponse, UserInfoResponse, UserUpdateRequest, UserChangePasswordRequest
from config.db_conf import get_db
from crud import users
from utils.response import success_response
from utils.auth import get_current_user

router = APIRouter(prefix="/api/user", tags=["users"])

# 头像上传目录
AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "avatars")


@router.post("/register")
async def register(user_data: UserRequest,db: AsyncSession = Depends(get_db)):  # 用户信息 和 db
  # 注册逻辑
  # 1. 验证用户是否存在
  # 2. 创建用户
  # 3. 生成 token
  # 4. 返回结果
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    user = await users.create_user(db, user_data)

    token = await users.create_token(db, user.id)


    # return {
    #   "code": 200,
    #   "message": "注册成功",
    #   "data": {
    #     "token": token,
    #     "userInfo": {
    #       "id": user.id,
    #       "username": user.username,
    #       "bio": user.bio,
    #       "avatar": user.avatar
    #     }
    #   }
    # }
    response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    return success_response(message="注册成功",data=response_data)



@router.post("/login")
async def login(user_data: UserRequest,db: AsyncSession = Depends(get_db)):
  # 登录逻辑: 验证用户是否存在-> 验证密码-> 生成token-> 返回结果
  user = await users.authenticate_user(db, user_data.username, user_data.password)
  if not user:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名或密码错误")
  token = await users.create_token(db, user.id)
  response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))

  return success_response(message="登录成功",data=response_data)



# 获取用户信息 :查Token查用户 ->功能整合成一个工具函数 -> 路由导入使用：依赖注入
@router.get("/info")
async def get_user_info(user:User = Depends(get_current_user)):
  return success_response(message="获取用户信息成功",data=UserInfoResponse.model_validate(user))



# 修改用户信息：验证Token ->更新（用户输入数据 put提交 ->请求体参数 ->定义pydantic模型类） - >响应结果
# 参数：用户输入的 + 验证Token + db（调用更新的方法）
@router.put("/update")
async def update_user_info(user_data: UserUpdateRequest,user:User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):


  user = await users.update_user(db, user.username, user_data)
  return success_response(message="修改用户信息成功",data=UserInfoResponse.model_validate(user))


@router.put("/password")
async def update_password(password_data: UserChangePasswordRequest,
                          user:User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):


  res_change_pwd = await users.change_password(db, user, password_data.old_password, password_data.new_password)
  if not res_change_pwd:
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="修改密码失败，请稍后再试。。。")
  return success_response(message="修改密码成功")


@router.post("/avatar", summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/GIF/WebP 格式的图片")
    # 验证文件大小（2MB）
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 2MB")
    # 生成唯一文件名
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    # 删除旧头像文件（非默认头像才删）
    if user.avatar and "/uploads/avatars/" in user.avatar:
        old_filename = user.avatar.split("/uploads/avatars/")[-1]
        old_filepath = os.path.join(AVATAR_DIR, old_filename)
        if os.path.exists(old_filepath):
            os.remove(old_filepath)
    # 保存新文件
    with open(filepath, "wb") as f:
        f.write(content)
    # 更新数据库
    avatar_url = f"/uploads/avatars/{filename}"
    user_data = UserUpdateRequest(avatar=avatar_url)
    updated_user = await users.update_user(db, user.username, user_data)
    return success_response(
        message="头像上传成功",
        data={"avatar": avatar_url, **UserInfoResponse.model_validate(updated_user).model_dump()},
    )









