# 故障排除指南

## 目录

- [安装问题](#安装问题)
- [配置问题](#配置问题)
- [启动问题](#启动问题)
- [运行时问题](#运行时问题)
- [数据库问题](#数据库问题)
- [API 问题](#api-问题)
- [前端问题](#前端问题)
- [性能问题](#性能问题)

## 安装问题

### 1. Python 依赖安装失败

**问题**: `pip install -r requirements.txt` 失败

**可能原因**:
- 网络问题
- Python 版本不兼容
- 缺少系统依赖

**解决方案**:
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 检查 Python 版本
python --version  # 需要 3.12+

# 安装系统依赖（Ubuntu/Debian）
sudo apt update
sudo apt install build-essential python3-dev

# 安装系统依赖（CentOS/RHEL）
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

### 2. Node.js 依赖安装失败

**问题**: `npm install` 失败

**解决方案**:
```bash
# 清除 npm 缓存
npm cache clean --force

# 删除 node_modules 和 package-lock.json
rm -rf node_modules package-lock.json

# 重新安装
npm install

# 使用国内镜像
npm config set registry https://registry.npmmirror.com
npm install
```

### 3. PyTorch 安装问题

**问题**: torch 安装失败或无法使用 GPU

**解决方案**:
```bash
# CPU 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# GPU 版本（CUDA 11.8）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 验证安装
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

## 配置问题

### 1. 环境变量未生效

**问题**: `.env` 文件配置未生效

**解决方案**:
```bash
# 检查 .env 文件位置是否正确
# backend/.env
# FastAPI_UserService_HistoryService/.env

# 检查环境变量加载
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DASHSCOPE_API_KEY'))"

# 确保安装了 python-dotenv
pip install python-dotenv
```

### 2. 数据库连接失败

**问题**: 无法连接到 MySQL

**解决方案**:
```bash
# 检查 MySQL 是否运行
sudo systemctl status mysql  # Linux
net start | findstr MySQL    # Windows

# 测试连接
mysql -u root -p -h localhost

# 检查配置文件中的数据库信息
# DB_HOST=localhost
# DB_PORT=3306
# DB_USER=root
# DB_PASSWORD=your_password
# DB_NAME=chatbot

# 创建数据库
mysql -u root -p
CREATE DATABASE chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Redis 连接失败

**问题**: 无法连接到 Redis

**解决方案**:
```bash
# 检查 Redis 是否运行
sudo systemctl status redis  # Linux
redis-cli ping               # 应返回 PONG

# 启动 Redis
sudo systemctl start redis   # Linux
redis-server                 # Windows

# 检查配置
# REDIS_CACHE_URL=redis://localhost:6379/0
```

## 启动问题

### 1. FastAPI 服务启动失败

**问题**: `uvicorn api.main:app --port 8001` 失败

**错误示例**:
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**:
```bash
# 确保在正确的目录
cd backend

# 检查 Python 路径
python -c "import sys; print(sys.path)"

# 安装缺失的模块
pip install <module_name>

# 检查 main.py 语法
python -m py_compile api/main.py
```

### 2. 端口被占用

**问题**: 端口 8000/8001 已被占用

**解决方案**:
```bash
# 查找占用端口的进程（Windows）
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 查找占用端口的进程（Linux）
lsof -i :8000
kill -9 <PID>

# 或使用其他端口
uvicorn api.main:app --port 8002
```

### 3. 前端启动失败

**问题**: `npm run dev` 失败

**解决方案**:
```bash
# 检查 Node.js 版本
node --version  # 需要 16+

# 清理并重新安装
rm -rf node_modules dist
npm install
npm run dev

# 检查端口是否被占用
# Vite 默认使用 5173 端口
```

## 运行时问题

### 1. API 返回 500 错误

**问题**: 请求 API 时返回 500 Internal Server Error

**排查步骤**:
```bash
# 查看后端日志
tail -f logs/agent.log

# 检查异常处理器是否正常工作
# backend/utils/exception_handlers.py

# 启用调试模式
# 在 api/main.py 中添加
app.debug = True
```

### 2. SSE 流式输出中断

**问题**: 流式响应中途断开

**解决方案**:
```python
# 检查 Nginx 配置（如果使用）
location /api/chat/stream {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;  # 增加超时时间
}

# 检查 FastAPI 配置
# 确保正确实现 StreamingResponse
from fastapi.responses import StreamingResponse
```

### 3. RAG 检索无结果

**问题**: 提问后返回空结果

**排查步骤**:
```bash
# 1. 检查向量数据库是否有数据
cd backend
python -c "
from rag.vector_store import VectorStoreService
vs = VectorStoreService()
print(vs.get_collection_count())
"

# 2. 检查文档是否正常导入
ls -la data/

# 3. 检查嵌入模型配置
cat config/rag.yml

# 4. 手动测试检索
python -c "
from rag.rag_service import RagService
rag = RagService()
results = rag.search('测试问题')
print(results)
"
```

## 数据库问题

### 1. 数据库迁移失败

**问题**: SQLAlchemy 模型无法同步到数据库

**解决方案**:
```bash
# 检查数据库连接
python -c "
from sqlalchemy import create_engine
from config.db_conf import DATABASE_URL
engine = create_engine(DATABASE_URL)
print(engine.connect())
"

# 手动创建表
python -c "
from models.users import Base
from config.db_conf import engine
Base.metadata.create_all(engine)
"
```

### 2. 数据不一致

**问题**: 数据库中存在不一致的数据

**解决方案**:
```sql
-- 检查外键约束
SHOW CREATE TABLE conversation_message;

-- 清理孤立记录
DELETE FROM conversation_message 
WHERE session_id NOT IN (SELECT id FROM conversation_session);

-- 备份并重建数据库
mysqldump -u root -p chatbot > backup.sql
mysql -u root -p chatbot < backup.sql
```

## API 问题

### 1. 认证失败 (401 Unauthorized)

**问题**: 请求返回 401 错误

**排查步骤**:
```bash
# 1. 检查 Token 是否有效
curl -H "Authorization: Bearer your_token" http://localhost:8000/api/user/info

# 2. 检查 Token 生成逻辑
# FastAPI_UserService_HistoryService/utils/auth.py

# 3. 检查 Token 过期时间
# 默认 7 天，可在配置中调整

# 4. 重新登录获取新 Token
curl -X POST http://localhost:8000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"123456"}'
```

### 2. CORS 错误

**问题**: 前端请求被 CORS 策略阻止

**解决方案**:
```python
# backend/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI_UserService_HistoryService/main.py
# 同样添加 CORS 配置
```

### 3. 请求参数验证失败

**问题**: 返回 422 Unprocessable Entity

**解决方案**:
```bash
# 检查请求体格式
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"query": "测试问题"}'

# 检查 Pydantic 模型定义
# backend/api/routes/chat.py
```

## 前端问题

### 1. 页面白屏

**问题**: 访问前端页面显示白屏

**排查步骤**:
```bash
# 1. 检查浏览器控制台错误
# F12 -> Console

# 2. 检查路由配置
cat src/router/index.js

# 3. 检查 API 连接
cat src/api/request.js

# 4. 重新构建
npm run build
npm run dev
```

### 2. API 请求失败

**问题**: 前端无法连接到后端

**解决方案**:
```javascript
// src/api/request.js
// 检查 base URL 配置
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
  timeout: 5000
})

// 创建 .env.local 文件
VITE_API_BASE_URL=http://localhost:8001
VITE_USER_SERVICE_URL=http://localhost:8000
```

### 3. 样式异常

**问题**: 页面样式显示不正常

**解决方案**:
```bash
# 1. 清除浏览器缓存
# Ctrl + Shift + Delete

# 2. 重新安装依赖
rm -rf node_modules
npm install

# 3. 检查 CSS 导入
cat src/main.js
```

## 性能问题

### 1. 响应速度慢

**问题**: API 响应时间过长

**优化方案**:
```python
# 1. 启用 Redis 缓存
# backend/core/redis_cache.py

# 2. 优化数据库查询
# 添加索引
CREATE INDEX idx_session_user ON conversation_session(user_id);
CREATE INDEX idx_message_session ON conversation_message(session_id);

# 3. 使用连接池
# SQLAlchemy 配置
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# 4. 启用 Gzip 压缩
pip install brotli asgiref
```

### 2. 内存泄漏

**问题**: 服务运行一段时间后内存占用过高

**排查步骤**:
```bash
# 1. 监控内存使用
import psutil
import os

process = psutil.Process(os.getpid())
print(process.memory_info().rss / 1024 / 1024)  # MB

# 2. 检查是否有未关闭的连接
# 数据库连接、HTTP 连接等

# 3. 使用 memory_profiler
pip install memory_profiler
python -m memory_profiler your_script.py
```

### 3. 数据库查询慢

**问题**: 数据库查询响应慢

**优化方案**:
```sql
-- 1. 分析慢查询
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;

-- 2. 添加索引
CREATE INDEX idx_user_username ON user(username);
CREATE INDEX idx_session_updated ON conversation_session(updated_at);

-- 3. 优化查询语句
-- 避免 SELECT *
-- 使用 LIMIT 分页
-- 避免 N+1 查询
```

## 日志分析

### 1. 查看服务日志

```bash
# 后端日志
tail -f backend/logs/agent.log

# 用户服务日志
tail -f FastAPI_UserService_HistoryService/logs/service.log

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 2. 日志级别调整

```python
# backend/utils/logger_handler.py
import logging

# 调整为 DEBUG 级别获取更多信息
logging.basicConfig(level=logging.DEBUG)
```

## 紧急恢复

### 1. 服务崩溃恢复

```bash
# 1. 检查服务状态
ps aux | grep uvicorn
ps aux | grep nginx

# 2. 重启服务
cd backend
uvicorn api.main:app --port 8001 --reload &

cd FastAPI_UserService_HistoryService
uvicorn main:app --port 8000 --reload &

# 3. 重启 Nginx
sudo systemctl restart nginx
```

### 2. 数据库恢复

```bash
# 1. 从备份恢复
mysql -u root -p chatbot < backup_20260517.sql

# 2. 检查数据完整性
SELECT COUNT(*) FROM conversation_session;
SELECT COUNT(*) FROM conversation_message;
SELECT COUNT(*) FROM user;
```

### 3. 向量数据库恢复

```bash
# 1. 备份 ChromaDB
cp -r backend/data/chromadb chromadb_backup/

# 2. 重新导入文档
python backend/rag/vector_store.py

# 3. 验证数据
python -c "
from rag.vector_store import VectorStoreService
vs = VectorStoreService()
print(f'文档数量: {vs.get_collection_count()}')
"
```

## 联系支持

如果以上方法无法解决您的问题，请：

1. 查看项目 GitHub Issues
2. 提交新的 Issue，包含：
   - 详细的错误信息
   - 复现步骤
   - 环境信息（OS、Python 版本等）
   - 相关日志