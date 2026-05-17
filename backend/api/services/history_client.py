"""
HistoryService HTTP 异步客户端
负责与 FastAPI_UserService_HistoryService (Port 8000) 通信：
  - 用户认证（代理登录/注册/用户信息）
  - 会话 CRUD
  - 消息记录的存取
"""

import os
from typing import Optional

import httpx
from utils.logger_handler import logger

# HistoryService 地址，可通过环境变量覆盖
HISTORY_SERVICE_URL = os.getenv("HISTORY_SERVICE_BASE_URL", "http://127.0.0.1:8000")


class HistoryClient:
    """异步 HTTP 客户端，封装对 HistoryService 的所有调用"""

    def __init__(self, base_url: str = HISTORY_SERVICE_URL):
        self.base_url = base_url.rstrip("/")

    # ==================== User 认证代理 ====================

    async def register(self, username: str, password: str) -> dict:
        """用户注册"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/user/register",
                json={"username": username, "password": password},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"注册失败: {result.get('message')}")
            return result["data"]

    async def login(self, username: str, password: str) -> dict:
        """用户登录"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/user/login",
                json={"username": username, "password": password},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"登录失败: {result.get('message')}")
            return result["data"]

    async def get_user_info(self, token: str) -> dict:
        """获取当前用户信息"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/user/info",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"获取用户信息失败: {result.get('message')}")
            return result["data"]

    async def update_user_info(self, token: str, **kwargs) -> dict:
        """更新用户信息"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.put(
                f"{self.base_url}/api/user/update",
                json=kwargs,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"更新用户信息失败: {result.get('message')}")
            return result["data"]

    async def change_password(self, token: str, old_password: str, new_password: str) -> dict:
        """修改密码"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.put(
                f"{self.base_url}/api/user/password",
                json={"oldPassword": old_password, "newPassword": new_password},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"修改密码失败: {result.get('message')}")
            return result["data"]

    async def upload_avatar(self, token: str, file) -> dict:
        """上传头像文件"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            file_content = await file.read()
            files = {"file": (file.filename, file_content, file.content_type)}
            resp = await client.post(
                f"{self.base_url}/api/user/avatar",
                files=files,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"上传头像失败: {result.get('message')}")
            return result["data"]

    # ==================== Session ====================

    async def create_session(self, token: str, title: Optional[str] = None) -> dict:
        """创建新会话，返回会话数据"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            body = {}
            if title:
                body["title"] = title
            resp = await client.post(
                f"{self.base_url}/api/sessions",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"创建会话失败: {result.get('message')}")
            return result["data"]

    async def get_session_list(
        self,
        token: str,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
    ) -> dict:
        """获取用户的会话列表（分页）"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {"page": page, "pageSize": page_size}
            if keyword:
                params["keyword"] = keyword
            resp = await client.get(
                f"{self.base_url}/api/sessions",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"获取会话列表失败: {result.get('message')}")
            return result["data"]

    async def get_session_detail(self, token: str, session_id: int) -> dict:
        """获取会话详情（含消息列表）"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/sessions/{session_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"获取会话详情失败: {result.get('message')}")
            return result["data"]

    async def update_session_title(self, token: str, session_id: int, title: str) -> dict:
        """更新会话标题"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.put(
                f"{self.base_url}/api/sessions/{session_id}",
                json={"title": title},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"更新会话标题失败: {result.get('message')}")
            return result["data"]

    async def delete_session(self, token: str, session_id: int) -> dict:
        """删除会话（级联删除消息）"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{self.base_url}/api/sessions/{session_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"删除会话失败: {result.get('message')}")
            return result["data"]

    async def clear_all_sessions(self, token: str) -> dict:
        """清空用户所有会话"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{self.base_url}/api/sessions",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"清空会话失败: {result.get('message')}")
            return result["data"]

    # ==================== Message ====================

    async def add_message(
        self,
        token: str,
        session_id: int,
        role: str,
        content: str,
        sources: Optional[list] = None,
        meta_data: Optional[dict] = None,
    ) -> dict:
        """添加消息到会话"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            body = {"role": role, "content": content}
            if sources is not None:
                body["sources"] = sources
            if meta_data is not None:
                body["metaData"] = meta_data
            resp = await client.post(
                f"{self.base_url}/api/sessions/{session_id}/messages",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"添加消息失败: {result.get('message')}")
            return result["data"]

    async def get_messages(
        self,
        token: str,
        session_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """获取会话消息列表（分页）"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/sessions/{session_id}/messages",
                params={"page": page, "pageSize": page_size},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"获取消息列表失败: {result.get('message')}")
            return result["data"]

    async def get_all_messages(self, token: str, session_id: int) -> list[dict]:
        """获取会话全部消息（供 LangChain 加载历史）"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/sessions/{session_id}/messages/all",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"获取消息列表失败: {result.get('message')}")
            return result["data"] or []

    async def search_messages(
        self,
        token: str,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """按关键词搜索会话消息内容"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {"keyword": keyword, "page": page, "pageSize": page_size}
            resp = await client.get(
                f"{self.base_url}/api/sessions/search",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 200:
                raise RuntimeError(f"搜索失败: {result.get('message')}")
            return result["data"]


# 全局单例
history_client = HistoryClient()

