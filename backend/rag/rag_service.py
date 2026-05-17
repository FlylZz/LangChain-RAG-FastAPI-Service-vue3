"""
总结服务类：用户提问，搜索参考资料，将提问和参考资料交给模型，让模型总结回复
支持混合检索（向量 + BM25）、HyDE 查询增强、Cross Encoder 重排序、Redis 缓存
"""

import asyncio

from langsmith import traceable
from rag.vector_store import VectorStoreService
from rag.reranker_service import RerankerService
from utils.prompt_loader import load_rag_summarize_prompt
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from core.redis_cache import rag_cache
from utils.logger_handler import logger

class RagSummarizeService(object):
    def __init__(self, use_reranker: bool = True):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retrieve()
        self.prompt_text = load_rag_summarize_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()
        # HyDE：假设性文档生成的提示模板
        self.hyde_prompt_template = PromptTemplate.from_template(
            "基于以下问题，生成一个详细的假设性回答，我会根据你的这个假设性回答在向量数据库里检索文档：\n\n问题：{query}\n\n假设性回答："
        )
        # Cross Encoder 重排序（可选）
        self.use_reranker = use_reranker
        self.reranker = RerankerService(top_n=5) if use_reranker else None

    def _init_chain(self):
        chain = self.prompt_template | self.model |StrOutputParser()
        return chain

    @traceable
    def retriever_docs(self, query: str) -> list[Document]:
        """使用混合检索（向量 + BM25）检索文档"""
        try:
            docs = self.vector_store.hybrid_search(query)
            logger.info(f"【混合检索】检索到 {len(docs)} 个相关文档")
            return docs
        except Exception as e:
            logger.error(f"【混合检索】失败，降级为纯向量检索: {e}")
            return self.retriever.invoke(query)

    @traceable
    def rerank_docs(self, query: str, docs: list[Document]) -> list[Document]:
        """
        Cross Encoder 重排序：对混合检索结果进行精排
        :param query: 原始用户查询
        :param docs:  混合检索返回的文档列表
        :return: 重排序后的文档列表（仅保留 top-k）
        """
        if not self.reranker or len(docs) <= 1:
            return docs

        try:
            # 提取文档内容用于重排序
            contents = [doc.page_content for doc in docs]
            ranked = self.reranker.rerank(query, contents)

            # 构建 内容 -> Document 映射，重排后保留原始 Document 对象
            content_to_doc = {doc.page_content: doc for doc in docs}
            reranked_docs = []
            for item in ranked:
                doc = content_to_doc.get(item["document"])
                if doc:
                    reranked_docs.append(doc)

            # 未匹配的文档追加到末尾
            for doc in docs:
                if doc not in reranked_docs:
                    reranked_docs.append(doc)

            logger.info(
                f"【Reranker】重排后保留 {len(reranked_docs)} 篇文档"
                f"（最高分={ranked[0]['score']:.4f}）" if ranked else ""
            )
            return reranked_docs

        except Exception as e:
            logger.error(f"【Reranker】重排序失败，保留原顺序: {e}")
            return docs

    @traceable
    def generate_hypothetical_document(self, query: str) -> str:
        """
        HyDE 技术：让模型生成一个假设性回答，用假设性回答去检索，提高召回率
        """
        try:
            hyde_chain = self.hyde_prompt_template | self.model | StrOutputParser()
            hypothetical_doc = hyde_chain.invoke({"query": query})
            logger.info(f"【HyDE】生成假设性文档成功，长度={len(hypothetical_doc)}")
            return hypothetical_doc
        except Exception as e:
            logger.error(f"【HyDE】生成假设性文档失败: {e}")
            return query

    @traceable
    def rag_summarize(self, query: str, use_hyde: bool = True) -> str:
        """
        RAG 摘要：检索 + 重排序 + 总结
        完整流程: Redis缓存 → HyDE → 混合检索 → Cross Encoder 精排 → LLM 总结 → 写入缓存
        :param query: 用户提问
        :param use_hyde: 是否启用 HyDE 查询增强
        """
        # ===== Redis 缓存查询：相同问题直接返回 =====
        cached = self._get_cache(query)
        if cached is not None:
            logger.info(f"【RAG】命中 Redis 缓存，直接返回（query={query[:30]}...）")
            return cached

        # HyDE：用假设性文档替代原始查询进行检索
        retrieve_query = query
        if use_hyde:
            try:
                retrieve_query = self.generate_hypothetical_document(query)
            except Exception as e:
                logger.warning(f"【HyDE】降级为原始查询检索: {e}")

        context_docs = self.retriever_docs(retrieve_query)

        # Cross Encoder 重排序：用原始 query 精排召回结果
        if self.use_reranker and context_docs:
            try:
                context_docs = self.rerank_docs(query, context_docs)
            except Exception as e:
                logger.warning(f"【Reranker】降级跳过重排: {e}")

        context = ""
        counter = 0
        for doc in context_docs:
            context += f"参考资料{counter}:参考资料：{doc.page_content}| 参考元数据：{doc.metadata}\n"
            counter += 1

        result = self.chain.invoke(
            {
                "input": query,
                "context": context
            }
        )

        # ===== 写入 Redis 缓存 =====
        self._set_cache(query, result)
        return result

    # ==================== Redis 缓存辅助方法 ====================

    @staticmethod
    def _get_cache(query: str):
        """从 Redis 获取缓存（同步方法中调异步）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, rag_cache.get(query)).result()
            else:
                return loop.run_until_complete(rag_cache.get(query))
        except Exception:
            return None

    @staticmethod
    def _set_cache(query: str, result: str):
        """写入 Redis 缓存（同步方法中调异步，静默失败）"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, rag_cache.set(query, result)).result()
            else:
                loop.run_until_complete(rag_cache.set(query, result))
        except Exception:
            pass
