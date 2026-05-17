from datetime import datetime,timedelta
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from starlette import status

from models.users import User, UserToken
from schemas.users import UserRequest, UserUpdateRequest
from utils import security


# 根据用户名去查询数据库
async def get_user_by_username(db: AsyncSession, username: str):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()




# 创建用户
async def create_user(db: AsyncSession, user_data: UserRequest):
    # 先密码加密 -> add
    hashed_password = security.get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user) #从数据库读回最新的 user
    return user


# 生成Token
async def create_token(db: AsyncSession,user_id: int):
    # 生成token + 设置过期时间 -> 查询数据库当前用户是否有Token -> 有：更新 -> 无：添加
    token =str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=7)
    query = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()
    if user_token:
        user_token.token = token
        user_token.expires_at = expires_at
    else:
        user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(user_token)

    await db.commit()
    await db.refresh(user_token)
    return token


# 用户验证
async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user_by_username(db, username)
    if not user:
        return None
    #验证密码
    if not security.verify_password(password, user.password):
        return None

    return user



#根据Token 查询用户:验证Token ->查询用户
async def get_user_by_token(db: AsyncSession, token: str):
    query = select(UserToken).where(UserToken.token == token)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()
    # 验证Token是否存在或过期
    if not user_token or user_token.expires_at < datetime.now():
        return None

    # 根据用户ID查询用户
    query = select(User).where(User.id == user_token.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# 更新用户信息:update更新 + 检查是否命中 + 获取更新后的用户返回
async def update_user(db: AsyncSession, username: str, user_data: UserUpdateRequest):

    query = update(User).where(User.username == username).values(**user_data.model_dump(
        exclude_unset=True,
        exclude_none= True
    ))

    result = await db.execute(query)
    await db.commit()

    #检查更新
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    #获取一下更新后的用户
    update_user = await get_user_by_username(db, username)
    return update_user




# 修改密码：验证旧密码 —> 新密码加密 -> 修改密码
async def change_password(db: AsyncSession, user:User, oldpassword: str, newpassword: str):

    if not security.verify_password(oldpassword, user.password):
        return False
    user.password = security.get_hash_password(newpassword)
    db.add(user)   # 更新：由SQLAlchemy真正接管这个User 对象，确保可以 commit     #规避session 过期或关闭导致不能提交的问题
    await db.commit()
    await db.refresh(user)
    return True
