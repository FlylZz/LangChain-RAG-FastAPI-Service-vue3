
from langchain_chroma import Chroma
from utils.config_handler import chroma_conf
from model.factory import chat_model, embed_model
from utils.file_handler import txt_loader, pdf_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.retrievers import BM25Retriever
import os



class VectorStoreService(object):
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"],
        )
        # 使用语义切割器（余弦相似度），在语义断层处切分，保证每块语义完整
        self.spliter = SemanticChunker(
            embeddings=embed_model,
            breakpoint_threshold_type=chroma_conf["breakpoint_threshold_type"],
            breakpoint_threshold_amount=chroma_conf["breakpoint_threshold_amount"],
        )
        self._bm25_retriever = None  # BM25 检索器（懒加载）

    def get_retrieve(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def _get_all_documents(self) -> list:
        """获取向量库中的所有文档，用于构建 BM25 检索器"""
        try:
            all_docs = self.vector_store.get(include=["documents", "metadatas"])
            from langchain_core.documents import Document
            documents = []
            for i, doc in enumerate(all_docs["documents"]):
                metadata = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
                documents.append(Document(page_content=doc, metadata=metadata))
            return documents
        except Exception as e:
            logger.error(f"获取向量库文档失败: {e}")
            return []

    def _build_bm25_retriever(self):
        """构建 BM25 关键词检索器"""
        all_docs = self._get_all_documents()
        if all_docs:
            self._bm25_retriever = BM25Retriever.from_documents(
                documents=all_docs,
                k=chroma_conf["k"],
            )
            logger.info(f"【混合检索】BM25 检索器构建成功，共 {len(all_docs)} 个文档片段")
        else:
            self._bm25_retriever = None
            logger.warning("【混合检索】向量库无文档，BM25 检索器未构建")

    @staticmethod
    def _get_dynamic_weights(query: str = None) -> list:
        """
        根据查询特征动态调整向量检索与 BM25 检索的权重
        长查询更偏向语义（向量），短查询更偏向关键词（BM25）
        :return: [向量权重, BM25权重]
        """
        default_vector_weight = 0.5
        default_bm25_weight = 0.5

        if not query:
            return [default_vector_weight, default_bm25_weight]

        query_length = len(query)

        if query_length > 50:
            vector_weight, bm25_weight = 0.7, 0.3
        elif query_length < 20:
            vector_weight, bm25_weight = 0.3, 0.7
        else:
            vector_weight, bm25_weight = default_vector_weight, default_bm25_weight

        query_words = len(query.split())
        if query_words > 0:
            word_density = query_words / query_length
            if word_density > 0.1:
                bm25_weight = min(bm25_weight + 0.1, 0.7)
                vector_weight = max(vector_weight - 0.1, 0.3)

        logger.info(f"【混合检索】查询长度={query_length}, 权重分配: 向量={vector_weight}, BM25={bm25_weight}")
        return [vector_weight, bm25_weight]

    def hybrid_search(self, query: str) -> list:
        """
        混合检索：向量 + BM25，基于互惠排名融合（RRF）合并结果
        :param query: 用户查询
        :return: 合并后的文档列表
        """
        if self._bm25_retriever is None:
            self._build_bm25_retriever()

        # 向量检索
        vector_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": chroma_conf["k"]},
        )
        vector_docs = vector_retriever.invoke(query)

        # BM25 不可用时降级
        if self._bm25_retriever is None:
            logger.info("【混合检索】BM25 不可用，降级为纯向量检索")
            return vector_docs

        # BM25 检索
        bm25_docs = self._bm25_retriever.invoke(query)

        # 获取动态权重
        weights = self._get_dynamic_weights(query)
        vector_weight, bm25_weight = weights

        # 互惠排名融合（RRF）
        k = 60  # RRF 常数
        doc_scores = {}
        doc_contents = {}  # 用内容去重

        for rank, doc in enumerate(vector_docs):
            content_key = doc.page_content[:200]  # 用前200字符做去重键
            if content_key not in doc_contents:
                doc_scores[content_key] = 0.0
                doc_contents[content_key] = doc
            doc_scores[content_key] += vector_weight / (k + rank + 1)

        for rank, doc in enumerate(bm25_docs):
            content_key = doc.page_content[:200]
            if content_key not in doc_contents:
                doc_scores[content_key] = 0.0
                doc_contents[content_key] = doc
            doc_scores[content_key] += bm25_weight / (k + rank + 1)

        # 按融合分数排序
        sorted_keys = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
        result = [doc_contents[k] for k in sorted_keys[:chroma_conf["k"]]]

        logger.info(f"【混合检索】向量={len(vector_docs)}篇, BM25={len(bm25_docs)}篇, 合并={len(result)}篇")
        return result

    def load_document(self):
        """
        从数据文件夹内读取数据文件，转为向量存入向量库
        要计算文件的MD5做去重

        :return:None
        """


        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                # 创建文件
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False            #md5 没处理过

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True     #md5 处理过
            return False        #md5 不存在

        def save_md5_hex(md5_str: str):
            """将传入的md5字符串，记录到文件中保存"""

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_str + "\n")

        def get_file_document(read_path:str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)

            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return  []

        allowed_file_path:list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allowed_knowledge_file_type"]),
        )

        for path in allowed_file_path:
            # 获取文件的MD5
            md5_hex = get_file_md5_hex(path)

            if check_md5_hex(md5_hex):
                logger.info(f"加载知识库{path}内容已经存在知识库内，跳过")
                continue

            try:
                from langchain_core.documents import Document
                documents:list[Document] = get_file_document(path)

                if not documents:
                    logger.warning(f"加载知识库文件{path}内容为空，跳过")
                    continue

                split_documents = self.spliter.split_documents(documents)

                if not split_documents:
                    logger.warning(f"加载知识库文件{path}分片后没有有效文本内容，跳过")
                    continue

                # 将分片后的内容添加到向量库
                self.vector_store.add_documents(split_documents)

                # 记录这个已经处理好的文件的md5，避免下次重复加载
                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库{path} 内容加载成功]")
            except Exception as e:
                # exc_info=True 表示会记录详细的报错堆栈，如果为False则记录错误信息本身
                logger.error(f"加载知识库{path}加载失败：{str(e)},",exc_info=True)

        # 文档加载完毕后，重建 BM25 检索器
        self._build_bm25_retriever()


if __name__ == '__main__':
    vs = VectorStoreService()

    vs.load_document()

    # 测试纯向量检索
    print("=== 纯向量检索 ===")
    retriever = vs.get_retrieve()
    res = retriever.invoke("迷路")
    for r in res:
        print(r.page_content)

    # 测试混合检索
    print("\n=== 混合检索（BM25 + 向量） ===")
    res2 = vs.hybrid_search("迷路")
    for r in res2:
        print(r.page_content)