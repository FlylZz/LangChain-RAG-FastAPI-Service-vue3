"""
Reranker 重排序服务：使用本地 Qwen3-Reranker-0.6B Cross Encoder 对混合检索召回结果精排

参考项目: LangChain-RAG-FastAPI-Service 的 reorder_service.py
模型: Qwen3-Reranker-0.6B (阿里巴巴轻量化中文重排序模型)
评分机制: CausalLM + last-token yes/no logits → relevance probability
优势: 数据不出本地、离线可用、无 API 调用成本、符合企业合规要求
"""
import os
from typing import List

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

from utils.logger_handler import logger

# 国内用户通过 HF 镜像加速模型下载
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


class RerankerService:
    """文档重排序服务 — 基于本地 Qwen3-Reranker-0.6B Cross Encoder"""

    MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"
    LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "Qwen3-Reranker-0.6B")

    # 类级别共享模型实例，避免重复加载
    _model = None
    _tokenizer = None
    _model_loaded = False

    def __init__(self, top_n: int = 5):
        self.top_n = top_n
        # 不在 __init__ 加载模型，避免阻塞服务启动
        # 模型在首次调用 rerank() 时懒加载

    @classmethod
    def _find_model_path(cls):
        """
        查找模型实际路径，兼容多种下载方式：
        - HuggingFace snapshot_download: models/Qwen3-Reranker-0.6B/ (文件直接在根目录)
        - ModelScope snapshot_download: models/Qwen3-Reranker-0.6B/Qwen/Qwen3-Reranker-0.6B/ (嵌套子目录)
        """
        if not os.path.isdir(cls.LOCAL_MODEL_DIR):
            return None

        # 先检查根目录是否直接有模型文件
        if os.path.isfile(os.path.join(cls.LOCAL_MODEL_DIR, "config.json")):
            return cls.LOCAL_MODEL_DIR

        # 递归搜索子目录（最多2层）寻找包含 config.json 的目录
        for root, dirs, files in os.walk(cls.LOCAL_MODEL_DIR):
            depth = root[len(cls.LOCAL_MODEL_DIR):].count(os.sep)
            if depth > 2:
                continue
            if "config.json" in files and "model.safetensors" in files:
                return root

        return None

    @classmethod
    def _ensure_model_loaded(cls):
        """懒加载模型，首次使用时加载到内存"""
        if cls._model_loaded:
            return

        # 优先使用本地已下载的模型目录，否则从 HF 自动下载
        local_path = cls._find_model_path()
        if local_path:
            model_path = local_path
            logger.info(f"【Reranker】从本地加载模型 {model_path}")
        else:
            model_path = cls.MODEL_NAME
            logger.info(f"【Reranker】本地模型不存在，从 HuggingFace 下载 {cls.MODEL_NAME} ...")

        try:
            cls._tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=True,
            )
            # 设置 padding token（Qwen3 tokenizer 默认无 pad_token）
            if cls._tokenizer.pad_token is None:
                cls._tokenizer.pad_token = cls._tokenizer.eos_token

            cls._model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                dtype=torch.float32,
            )
            cls._model.eval()

            # 预计算 yes/no token id
            cls._yes_token_id = cls._tokenizer.encode("yes", add_special_tokens=False)[0]
            cls._no_token_id = cls._tokenizer.encode("no", add_special_tokens=False)[0]

            cls._model_loaded = True
            logger.info(f"【Reranker】模型加载完成 (设备: {'GPU' if torch.cuda.is_available() else 'CPU'}, "
                        f"yes_id={cls._yes_token_id}, no_id={cls._no_token_id})")
        except Exception as e:
            logger.error(f"【Reranker】模型加载失败，重排序功能将不可用: {e}")
            raise

    def rerank(self, query: str, documents: List[str]) -> List[dict]:
        """
        对文档列表进行重排序
        :param query:     用户查询
        :param documents: 待排序的文档内容列表
        :return: [{"document": str, "score": float}, ...] 按 score 降序排列
        """
        if not documents:
            return []

        if len(documents) <= 1:
            return [{"document": d, "score": 1.0} for d in documents]

        try:
            # 懒加载模型（首次调用时触发）
            self._ensure_model_loaded()

            # 构建 Qwen3 Reranker 消息格式：逐条推理获取 yes/no logits
            scores = []
            for doc in documents:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "Judge whether the Document meets the requirements based on the Query "
                            "and the Instruct provided. Output only \"yes\" or \"no\"."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}\nDocument: {doc}",
                    },
                ]
                text = self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                inputs = self._tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                )

                with torch.no_grad():
                    outputs = self._model(**inputs)
                    # 取最后一个 token 在 yes/no 上的 logits
                    last_logits = outputs.logits[0, -1, :]
                    yes_logit = last_logits[self._yes_token_id].item()
                    no_logit = last_logits[self._no_token_id].item()

                # yes 的概率作为相关性分数
                yes_prob = F.softmax(
                    torch.tensor([yes_logit, no_logit]), dim=0
                )[0].item()
                scores.append(yes_prob)

            # 按分数降序排列
            ranked_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )
            ranked = [
                {"document": documents[i], "score": scores[i]}
                for i in ranked_indices[:self.top_n]
            ]

            logger.info(
                f"【Reranker】重排序完成，输入{len(documents)}篇 -> 输出{len(ranked)}篇，"
                f"最高分={ranked[0]['score']:.4f}" if ranked else f"【Reranker】无有效结果"
            )
            return ranked

        except Exception as e:
            logger.error(f"【Reranker】推理失败，降级保留原顺序: {e}")
            return self._fallback(documents)

    def rerank_batch(self, query: str, documents: List[str], batch_size: int = 32) -> List[dict]:
        """
        分批重排序：当文档数量过多时自动分批，避免显存溢出
        :param query:      用户查询
        :param documents:  待排序文档列表
        :param batch_size: 每批最大文档数
        """
        if len(documents) <= batch_size:
            return self.rerank(query, documents)

        logger.info(f"【Reranker】文档数({len(documents)})超过批次限制({batch_size})，启用分批重排")

        all_ranked = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            ranked_batch = self.rerank(query, batch)
            all_ranked.extend(ranked_batch)

        # 按分数全局排序
        all_ranked.sort(key=lambda x: x["score"], reverse=True)
        return all_ranked[:self.top_n]

    @staticmethod
    def _fallback(documents: List[str]) -> List[dict]:
        """降级方案：保持原顺序，分数置为 0"""
        return [{"document": d, "score": 0.0} for d in documents]
