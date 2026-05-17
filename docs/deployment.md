# 部署指南

## 环境准备

### 1. 服务器要求

- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 8+) 或 Windows Server
- **CPU**: 4核及以上
- **内存**: 8GB及以上
- **存储**: 50GB及以上（根据知识库大小调整）
- **网络**: 稳定的互联网连接（用于访问AI模型API）

### 2. 软件依赖

#### 后端环境
- Python 3.12+
- MySQL 8.0+
- Redis 6.0+

#### 前端环境
- Node.js 16+
- Nginx（用于生产环境部署）

## 部署步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-username/LangChain-RAG-FastAPI-Service-vue3.git
cd LangChain-RAG-FastAPI-Service-vue3
```

### 2. 配置环境变量

#### 2.1 后端配置
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

#### 2.2 用户服务配置
```bash
cd FastAPI_UserService_HistoryService
# 创建 .env 文件，参考 .env.example 填写
```

### 3. 安装依赖

#### 3.1 后端依赖
```bash
cd backend
pip install -r requirements.txt
```

#### 3.2 前端依赖
```bash
cd front
npm install
```

#### 3.3 用户服务依赖
```bash
cd FastAPI_UserService_HistoryService
pip install -r requirements.txt
```

### 4. 数据库初始化

#### 4.1 创建数据库
```sql
CREATE DATABASE chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE user_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 4.2 初始化表结构
服务启动时会自动创建表结构（如果配置了自动迁移）。

### 5. 模型配置

#### 5.1 下载重排序模型
```bash
# 如果使用本地模型，需要下载 Qwen3-Reranker-0.6B
# 模型将自动下载到 backend/models/ 目录
```

#### 5.2 配置模型路径
在 `backend/config/rag.yml` 中配置模型路径：
```yaml
reranker_model_path: ./models/Qwen3-Reranker-0.6B
```

### 6. 启动服务

#### 6.1 启动 MySQL
```bash
# Linux
sudo systemctl start mysql

# Windows
net start mysql
```

#### 6.2 启动 Redis
```bash
# Linux
sudo systemctl start redis

# Windows
redis-server
```

#### 6.3 启动用户服务
```bash
cd FastAPI_UserService_HistoryService
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 6.4 启动后端服务
```bash
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8001 --workers 4
```

#### 6.5 构建前端
```bash
cd front
npm run build
```

### 7. 配置 Nginx（生产环境）

#### 7.1 安装 Nginx
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

#### 7.2 配置反向代理
创建 Nginx 配置文件 `/etc/nginx/sites-available/chatbot.conf`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/your/project/front/dist;
        try_files $uri $uri/ /index.html;
    }

    # 用户服务 API
    location /api/user/ {
        proxy_pass http://127.0.0.1:8000/api/user/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 会话服务 API
    location /api/sessions/ {
        proxy_pass http://127.0.0.1:8000/api/sessions/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Agent 服务 API
    location /api/chat/ {
        proxy_pass http://127.0.0.1:8001/api/chat/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

#### 7.3 启用配置
```bash
sudo ln -s /etc/nginx/sites-available/chatbot.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. 配置 HTTPS（推荐）

#### 8.1 使用 Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### 8.2 自动续期
```bash
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

## Docker 部署（可选）

### 1. 构建镜像

#### 1.1 后端服务
```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### 1.2 前端服务
```dockerfile
# front/Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2. Docker Compose 配置

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: chatbot
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  user-service:
    build: ./FastAPI_UserService_HistoryService
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=mysql
      - DB_PASSWORD=${DB_PASSWORD}
    depends_on:
      - mysql
      - redis

  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - DB_HOST=mysql
      - DB_PASSWORD=${DB_PASSWORD}
    depends_on:
      - mysql
      - redis
      - user-service

  frontend:
    build: ./front
    ports:
      - "80:80"
    depends_on:
      - backend
      - user-service

volumes:
  mysql_data:
```

### 3. 启动服务
```bash
docker-compose up -d
```

## 监控与日志

### 1. 日志配置

#### 1.1 后端日志
在 `backend/utils/logger_handler.py` 中配置日志：
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.log'),
        logging.StreamHandler()
    ]
)
```

#### 1.2 Nginx 日志
```nginx
access_log /var/log/nginx/chatbot_access.log;
error_log /var/log/nginx/chatbot_error.log;
```

### 2. 性能监控

#### 2.1 使用 Prometheus + Grafana
- 配置 FastAPI 的 `/metrics` 端点
- 使用 `prometheus-fastapi-instrumentator` 包

#### 2.2 数据库监控
- MySQL 慢查询日志
- Redis INFO 命令监控

## 安全建议

### 1. 防火墙配置
```bash
# 只开放必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 2. 数据库安全
- 不要使用 root 用户连接数据库
- 限制数据库访问IP
- 定期备份数据库

### 3. API 安全
- 使用 HTTPS
- 配置 CORS 策略
- 实施请求限流
- 定期更新 API Key

## 故障恢复

### 1. 数据库备份
```bash
# 备份
mysqldump -u root -p chatbot > backup_$(date +%Y%m%d).sql

# 恢复
mysql -u root -p chatbot < backup_20260517.sql
```

### 2. 服务重启
```bash
# 重启单个服务
sudo systemctl restart nginx
sudo pm2 restart backend

# 重启所有服务
docker-compose restart
```

## 常见问题

### 1. 端口冲突
```bash
# 查看端口占用
lsof -i :8000
lsof -i :8001

# 杀死占用进程
kill -9 <PID>
```

### 2. 内存不足
```bash
# 查看内存使用
free -h

# 优化方案
- 减少 worker 数量
- 启用 swap 分区
- 增加服务器内存
```

### 3. 模型加载失败
- 检查模型路径是否正确
- 确认有足够磁盘空间
- 验证模型文件完整性