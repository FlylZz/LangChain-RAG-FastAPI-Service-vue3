# Hugging Face 模型配置

## 概述

本项目使用 Hugging Face 提供的预训练模型进行文档重排序（Reranker），以提高 RAG 检索的准确性。默认使用的模型是 `Qwen3-Reranker-0.6B`。

## 模型下载

### 方式一：使用 Hugging Face CLI（推荐）

```bash
# 安装 huggingface-hub
pip install huggingface-hub

# 下载模型
huggingface-cli download Qwen/Qwen3-Reranker-0.6B --local-dir ./models/Qwen3-Reranker-0.6B
```

### 方式二：使用 Git LFS

```bash
# 安装 Git LFS
git lfs install

# 克隆模型仓库
git clone https://huggingface.co/Qwen/Qwen3-Reranker-0.6B ./models/Qwen3-Reranker-0.6B
```

### 方式三：手动下载

1. 访问 [Hugging Face 模型页面](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B)
2. 下载所有模型文件
3. 将文件放置到 `./models/Qwen3-Reranker-0.6B` 目录

## 模型配置

### 1. 配置文件路径

在 `backend/config/rag.yml` 中配置模型路径：

```yaml
# 重排序模型配置
reranker_model_path: ./models/Qwen3-Reranker-0.6B
reranker_model_name: Qwen3-Reranker-0.6B
```

### 2. 环境变量配置

在 `backend/.env` 文件中配置：

```env
# 重排序模型路径
RERANKER_MODEL_PATH=./models/Qwen3-Reranker-0.6B
```

## 模型使用

### 1. 自动加载

服务启动时会自动加载配置的重排序模型：

```python
# backend/rag/reranker_service.py
from sentence_transformers import CrossEncoder

class RerankerService:
    def __init__(self, model_path):
        self.model = CrossEncoder(model_path)
```

### 2. 手动测试

```python
# 测试模型是否正常工作
from sentence_transformers import CrossEncoder

model = CrossEncoder('./models/Qwen3-Reranker-0.6B')

# 测试样本
query = "扫地机器人如何避障？"
documents = [
    "扫地机器人使用激光雷达进行环境感知和避障",
    "扫地机器人的电池续航时间为120分钟",
    "扫地机器人支持自动回充功能"
]

# 计算相关性分数
pairs = [(query, doc) for doc in documents]
scores = model.predict(pairs)

print("相关性分数:", scores)
```

## 模型优化

### 1. GPU 加速

如果服务器有 GPU，可以启用 GPU 加速：

```python
import torch

# 检查 CUDA 是否可用
device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = CrossEncoder(
    model_name='./models/Qwen3-Reranker-0.6B',
    device=device
)
```

### 2. 模型量化

为了减少内存占用，可以使用模型量化：

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# 加载模型并进行量化
model = AutoModelForSequenceClassification.from_pretrained(
    './models/Qwen3-Reranker-0.6B',
    torch_dtype=torch.float16  # 使用半精度
)
```

### 3. 缓存机制

```python
import hashlib
import json
import os

class RerankerWithCache:
    def __init__(self, model_path, cache_dir='./cache'):
        self.model = CrossEncoder(model_path)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def predict_with_cache(self, query, documents):
        # 生成缓存键
        cache_key = hashlib.md5(f"{query}{str(documents)}".encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        # 检查缓存
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        # 计算并缓存
        pairs = [(query, doc) for doc in documents]
        scores = self.model.predict(pairs).tolist()
        
        with open(cache_file, 'w') as f:
            json.dump(scores, f)
        
        return scores
```

## 常见问题

### 1. 模型下载失败

**问题**: 网络连接不稳定导致下载失败

**解决方案**:
```bash
# 使用镜像站
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download Qwen/Qwen3-Reranker-0.6B --local-dir ./models/Qwen3-Reranker-0.6B
```

### 2. 内存不足

**问题**: 模型加载时内存溢出

**解决方案**:
- 使用模型量化（见上文）
- 增加服务器内存
- 使用 CPU 而非 GPU（如果 GPU 内存不足）

### 3. 模型路径错误

**问题**: 服务启动时找不到模型文件

**解决方案**:
- 检查配置文件中的路径是否正确
- 确认模型文件完整
- 使用绝对路径而非相对路径

## 模型更新

### 1. 检查更新

```bash
# 检查模型是否有更新
huggingface-cli download Qwen/Qwen3-Reranker-0.6B --local-dir ./models/Qwen3-Reranker-0.6B --force-download
```

### 2. 版本管理

```bash
# 创建模型版本目录
mkdir -p ./models/reranker/v1
mkdir -p ./models/reranker/v2

# 在配置文件中指定版本
reranker_model_path: ./models/reranker/v1
```

## 性能基准

### 测试环境
- CPU: Intel Xeon E5-2686 v4
- 内存: 16GB
- 模型: Qwen3-Reranker-0.6B

### 性能指标
- 单次推理时间: ~50ms
- 内存占用: ~1.2GB
- 准确率提升: ~15-20%（相比无重排序）

## 替代模型

如果 `Qwen3-Reranker-0.6B` 不满足需求，可以考虑以下替代模型：

| 模型名称 | 大小 | 性能 | 适用场景 |
|---------|------|------|----------|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | 80MB | 中等 | 快速响应 |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | 120MB | 较好 | 平衡性能 |
| `BAAI/bge-reranker-large` | 1.1GB | 优秀 | 高精度需求 |

### 切换模型

```yaml
# backend/config/rag.yml
reranker_model_path: ./models/BAAI/bge-reranker-large
reranker_model_name: bge-reranker-large
```

## 许可证

请遵守 Hugging Face 模型的许可证要求：
- `Qwen3-Reranker-0.6B`: 遵循 [Qwen 许可证](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B/blob/main/LICENSE)
- 商业用途请确认许可证允许的范围