# FastAPI 用户服务 API 文档

> **项目**: FastAPI UserService + HistoryService  
> **服务**: 用户认证与会话管理  
> **端口**: 8000  
> **版本**: 2.0.0  
> **更新日期**: 2026-05-17  
> **认证方式**: Bearer Token（Header: `Authorization: Bearer <token>`）

---

## 1. 通用说明

### 1.1 统一响应格式

所有接口返回 JSON，结构如下：

```json
{
  "code": 200,
  "message": "操作描述",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，200 表示成功 |
| message | string | 操作结果描述 |
| data | object/array/null | 响应数据，错误时为 null |

### 1.2 分页响应

分页接口的 `data` 中包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| list | array | 数据列表 |
| total | int | 总条数 |
| hasMore | bool | 是否有更多数据 |

### 1.3 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token 无效或过期） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 2. 用户认证 API

### 2.1 用户注册

```
POST /api/user/register
```

**Request Body:**
```json
{
  "username": "testuser",
  "password": "123456"
}
```

**Response (200):**
```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "userInfo": {
      "id": 1,
      "username": "testuser",
      "nickname": null,
      "avatar": "https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg",
      "gender": "unknown",
      "bio": "这个人很懒，什么都没留下"
    }
  }
}
```

---

### 2.2 用户登录

```
POST /api/user/login
```

**Request Body:**
```json
{
  "username": "testuser",
  "password": "123456"
}
```

**Response (200):**
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "userInfo": {
      "id": 1,
      "username": "testuser",
      "nickname": null,
      "avatar": "https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg",
      "gender": "unknown",
      "bio": "这个人很懒，什么都没留下"
    }
  }
}
```

---

### 2.3 获取用户信息

```
GET /api/user/info
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "code": 200,
  "message": "获取用户信息成功",
  "data": {
    "id": 1,
    "username": "testuser",
    "nickname": null,
    "avatar": "https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg",
    "gender": "unknown",
    "bio": "这个人很懒，什么都没留下"
  }
}
```

---

### 2.4 修改用户信息

```
PUT /api/user/update
```

**Request Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "nickname": "小智",
  "avatar": "https://example.com/avatar.png",
  "gender": "male",
  "bio": "扫地机器人爱好者",
  "phone": "13800138000"
}
```

> 所有字段均为可选，只传需要修改的字段。

**Response (200):**
```json
{
  "code": 200,
  "message": "修改用户信息成功",
  "data": {
    "id": 1,
    "username": "testuser",
    "nickname": "小智",
    "avatar": "https://example.com/avatar.png",
    "gender": "male",
    "bio": "扫地机器人爱好者"
  }
}
```

---

### 2.5 修改密码

```
PUT /api/user/password
```

**Request Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "oldPassword": "123456",
  "newPassword": "654321"
}
```

**Response (200):**
```json
{
  "code": 200,
  "message": "修改密码成功",
  "data": null
}
```

---

## 3. 会话管理 API

### 3.1 创建新会话

点击界面「新会话」按钮时调用。

```
POST /api/sessions
```

**Request Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "可选标题"        // string, 可选，不传则由首条消息自动生成
}
```

**Response (200):**
```json
{
  "code": 200,
  "message": "会话创建成功",
  "data": {
    "id": 1,
    "userId": 1,
    "title": "新对话 2026-05-17 20:00",
    "createdAt": "2026-05-17T12:00:00",
    "updatedAt": "2026-05-17T12:00:00",
    "updatedAtFormatted": "2026/05/17 20:00",
    "messageCount": 0
  }
}
```

**说明:**  
创建会话时不传 `title`，标题将自动生成为"新对话 + 时间"。随后第一条 `user` 消息会自动替换此标题。

---

### 3.2 获取历史会话列表（支持搜索）

界面左侧「历史会话」列表的数据源，支持关键词搜索。

```
GET /api/sessions?page=1&pageSize=10&keyword=fastapi
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码（从1开始） |
| pageSize | int | 否 | 10 | 每页条数（1-100） |
| keyword | string | 否 | 无 | 按会话标题模糊搜索，不传则返回全部 |

**搜索示例:**
```
# 搜索标题中包含 'fastapi' 的会话
GET /api/sessions?keyword=fastapi&page=1&pageSize=10

# 搜索标题中包含 'langchain' 的会话
GET /api/sessions?keyword=langchain

# 不传 keyword 则返回全部会话
GET /api/sessions?page=1&pageSize=10
```

**Response (200):**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 5,
        "userId": 1,
        "title": "讲讲什么是fastapi",
        "createdAt": "2026-03-24T12:20:00",
        "updatedAt": "2026-03-24T12:23:00",
        "updatedAtFormatted": "2026/03/24 20:23",
        "messageCount": 4
      },
      {
        "id": 4,
        "userId": 1,
        "title": "langchain的chain是什么，详细介绍一下",
        "createdAt": "2026-03-24T08:00:00",
        "updatedAt": "2026-03-24T08:06:00",
        "updatedAtFormatted": "2026/03/24 16:06",
        "messageCount": 6
      }
    ],
    "total": 5,
    "hasMore": false
  }
}
```

**字段说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 会话ID |
| userId | int | 用户ID |
| title | string | 会话标题（首条用户消息自动生成） |
| createdAt | datetime | 创建时间（ISO 8601） |
| updatedAt | datetime | 最后更新时间（ISO 8601） |
| updatedAtFormatted | string | 格式化时间 `YYYY/MM/DD HH:MM` |
| messageCount | int | 消息总条数 |

---

### 3.3 获取会话详情

进入某个会话时的详情（含消息列表）。

```
GET /api/sessions/{session_id}
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "userId": 1,
    "title": "讲讲什么是fastapi",
    "createdAt": "2026-03-24T12:20:00",
    "updatedAt": "2026-03-24T12:23:00",
    "updatedAtFormatted": "2026/03/24 20:23",
    "messageCount": 4,
    "messages": [
      {
        "id": 1,
        "sessionId": 1,
        "role": "user",
        "content": "讲讲什么是fastapi",
        "sources": null,
        "metaData": null,
        "createdAt": "2026-03-24T12:20:00"
      },
      {
        "id": 2,
        "sessionId": 1,
        "role": "assistant",
        "content": "FastAPI 是一个现代、快速的 Web 框架...",
        "sources": [
          { "title": "FastAPI官方文档", "url": "https://fastapi.tiangolo.com", "score": 0.95 }
        ],
        "metaData": { "model": "qwen3-max", "tokens": 120 },
        "createdAt": "2026-03-24T12:20:05"
      }
    ]
  }
}
```

**错误 (404):**
```json
{
  "code": 404,
  "message": "会话不存在",
  "data": null
}
```

---

### 3.4 更新会话标题

```
PUT /api/sessions/{session_id}
```

**Request Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "FastAPI技术讨论"
}
```

**Response (200):**
```json
{
  "code": 200,
  "message": "标题更新成功",
  "data": { ... }       // SessionItemResponse
}
```

---

### 3.5 删除单个会话

界面「删除」按钮点击时调用。

```
DELETE /api/sessions/{session_id}
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "code": 200,
  "message": "会话已删除",
  "data": null
}
```

**说明:** 删除会话会级联删除该会话下的所有消息。

---

### 3.6 清空所有会话

```
DELETE /api/sessions/clear/all
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "code": 200,
  "message": "已清空 5 个会话",
  "data": null
}
```

---

## 4. 消息管理 API

### 4.1 添加消息

LangChain 每轮对话调用此接口存储消息记录。

```
POST /api/sessions/{session_id}/messages
```

**Request Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "role": "user",                    // 必填: user | assistant | system
  "content": "什么是RAG？",           // 必填: 消息文本
  "sources": [],                      // 可选: RAG检索来源
  "metaData": {                       // 可选: 额外元数据
    "model": "qwen3-max",
    "tokens": 50
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role | string | 是 | 消息角色: `user` / `assistant` / `system` |
| content | string | 是 | 消息内容 |
| sources | array[object] | 否 | RAG 检索到的来源文档列表，每个对象可含 `title`, `url`, `score` 等 |
| metaData | object | 否 | LangChain 元数据（模型名、token 用量等） |

**Response (200):**
```json
{
  "code": 200,
  "message": "消息已添加",
  "data": {
    "id": 10,
    "sessionId": 1,
    "role": "user",
    "content": "什么是RAG？",
    "sources": [],
    "metaData": { "model": "qwen3-max", "tokens": 50 },
    "createdAt": "2026-05-17T12:00:00"
  }
}
```

> **自动标题:** 当第一条 `role=user` 的消息添加时，会自动将会话标题更新为该消息内容（截取前40字）。

---

### 4.2 分页获取消息列表

```
GET /api/sessions/{session_id}/messages?page=1&pageSize=50
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| pageSize | int | 否 | 50 | 每页条数（1-200） |

**Response (200):**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [ ... ],        // MessageItemResponse[]
    "total": 10,
    "hasMore": false
  }
}
```

---

### 4.3 获取全部消息（LangChain 历史加载）

供 LangChain `BaseChatMessageHistory` 加载完整对话历史，不分页。

```
GET /api/sessions/{session_id}/messages/all
```

**Request Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "sessionId": 1,
      "role": "user",
      "content": "什么是RAG？",
      "sources": [],
      "metaData": { "model": "qwen3-max" },
      "createdAt": "2026-05-17T12:00:00"
    },
    {
      "id": 2,
      "sessionId": 1,
      "role": "assistant",
      "content": "RAG（Retrieval-Augmented Generation）是...",
      "sources": [
        { "title": "RAG论文", "url": "https://arxiv.org/abs/2005.11401", "score": 0.95 }
      ],
      "metaData": { "model": "qwen3-max", "tokens": 150 },
      "createdAt": "2026-05-17T12:00:03"
    }
  ]
}
```

---

## 5. API 接口总览

| 方法 | 路径 | 说明 | 界面作用 |
|------|------|------|----------|
| `POST` | `/api/user/register` | 用户注册 | 注册页 |
| `POST` | `/api/user/login` | 用户登录 | 登录页 |
| `GET` | `/api/user/info` | 获取用户信息 | 用户中心 |
| `PUT` | `/api/user/update` | 修改用户信息 | 编辑资料 |
| `PUT` | `/api/user/password` | 修改密码 | 修改密码 |
| `POST` | `/api/sessions` | 创建新会话 | 「新会话」按钮 |
| `GET` | `/api/sessions` | 分页获取会话列表（支持 keyword 搜索） | 「历史会话」列表 + 搜索 |
| `GET` | `/api/sessions/{id}` | 获取会话详情 | 点击进入会话 |
| `PUT` | `/api/sessions/{id}` | 更新会话标题 | 重命名会话 |
| `DELETE` | `/api/sessions/{id}` | 删除单个会话 | 「删除」按钮 |
| `DELETE` | `/api/sessions/clear/all` | 清空所有会话 | 批量清空 |
| `POST` | `/api/sessions/{id}/messages` | 添加消息 | LangChain 存储对话 |
| `GET` | `/api/sessions/{id}/messages` | 分页获取消息 | 聊天记录分页 |
| `GET` | `/api/sessions/{id}/messages/all` | 获取全部消息 | LangChain 加载历史 |

---

## 6. LangChain 集成示例

```python
import requests

BASE_URL = "http://127.0.0.1:8000"
TOKEN = "your_bearer_token"

headers = {"Authorization": f"Bearer {TOKEN}"}

# 1. 创建新会话
resp = requests.post(f"{BASE_URL}/api/sessions", headers=headers)
session_id = resp.json()["data"]["id"]

# 2. 每轮对话添加消息
requests.post(
    f"{BASE_URL}/api/sessions/{session_id}/messages",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "role": "user",
        "content": "什么是RAG？",
        "metaData": {"model": "qwen3-max"}
    }
)

requests.post(
    f"{BASE_URL}/api/sessions/{session_id}/messages",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "role": "assistant",
        "content": "RAG是检索增强生成技术...",
        "sources": [{"title": "RAG论文", "score": 0.95}],
        "metaData": {"model": "qwen3-max", "tokens": 150}
    }
)

# 3. 加载历史消息（供 LangChain BaseChatMessageHistory 使用）
resp = requests.get(
    f"{BASE_URL}/api/sessions/{session_id}/messages/all",
    headers=headers
)
history_messages = resp.json()["data"]
# 转换为 LangChain 消息格式
from langchain_core.messages import HumanMessage, AIMessage
lc_messages = [
    HumanMessage(content=m["content"]) if m["role"] == "user"
    else AIMessage(content=m["content"])
    for m in history_messages
]
```

---

## 7. 数据模型

### ConversationSession（会话表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键，自增 |
| user_id | int | 用户ID（外键 → user） |
| title | varchar(200) | 会话标题 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 最后更新时间 |

### ConversationMessage（消息表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键，自增 |
| session_id | int | 会话ID（外键 → conversation_session） |
| role | enum | 角色: `user` / `assistant` / `system` |
| content | text | 消息内容 |
| sources | json | RAG 检索来源文档 |
| meta_data | json | 元数据（模型、token 等） |
| created_at | datetime | 创建时间 |

---

## 8. 交互式 API 文档

启动服务后访问：
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
