"""
LlamaIndex 核心封装：混合检索 (BM25 + 向量)、索引管理、查询引擎。
显存提示：BAAI/bge-m3 在 CUDA 上约占用 4~6GB，A4000(16GB) 需预留显存给 Ollama。
"""
from typing import List, Dict, Any, Set

import chromadb
import logging
import streamlit as st
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import (
    Document,
    VectorStoreIndex,
    StorageContext,
    get_response_synthesizer,
    Settings,
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever

import config

import os

# 强行设置环境变量，让 Python 忽略系统代理
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

logger = logging.getLogger("autosafety")

# @st.cache_resource作用是缓存资源，避免每次都重新创建，提高性能
@st.cache_resource(show_spinner=False)
def get_embedding_model() -> HuggingFaceEmbedding:
    """加载 HuggingFace 向量模型到指定设备。"""
    device = config.model_config.embedding_device
    logger.info("加载嵌入模型: %s, device=%s", config.model_config.embedding_model_name, device)
    return HuggingFaceEmbedding(
        model_name=config.model_config.embedding_model_name,
        device=device,
        embed_batch_size=config.model_config.embedding_batch_size,
        # 强制使用 Safetensors，避开 PyTorch 2.6 版本检查
        model_kwargs={"use_safetensors": True},
    )


@st.cache_resource(show_spinner=False)
def get_llm() -> Ollama:
    """Ollama LLM 客户端。"""
    logger.info("初始化 Ollama LLM: %s @ %s", config.model_config.ollama_model, config.model_config.ollama_base_url)
    return Ollama(
        model=config.model_config.ollama_model,
        base_url=config.model_config.ollama_base_url,
        request_timeout=120.0,
        # 避免在初始化时请求 /api/show 失败导致崩溃，可显式给出上下文窗口 注意
        context_window=8192,
    )


@st.cache_resource(show_spinner=False)
def get_vector_store() -> ChromaVectorStore:
    """初始化或连接本地 Chroma 持久化集合。"""
    config.ensure_dirs()
    client = chromadb.PersistentClient(path=str(config.CHROMA_PATH))
    collection = client.get_or_create_collection("autosafety_rag")
    logger.info("连接 Chroma collection=autosafety_rag, path=%s", config.CHROMA_PATH)
    return ChromaVectorStore(chroma_collection=collection)


def get_collection_count() -> int:
    """返回 Chroma 当前已存节点数量。"""
    vector_store = get_vector_store()
    collection = getattr(vector_store, "_collection", None)
    if collection is None:
        return 0
    try:
        count = collection.count()
        logger.info("Chroma collection 当前节点数: %s", count)
        return count
    except Exception:
        return 0


def get_exist_file_names() -> Set[str]:
    """
    从持久化 Chroma 中读取已索引的文件名集合。
    说明：当前场景数据量有限，直接全量获取 metadatas。
    """
    vector_store = get_vector_store()
    collection = getattr(vector_store, "_collection", None)
    if collection is None:
        return set()
    try:
        res = collection.get(include=["metadatas"])
        metadatas = res.get("metadatas") or []
        names: Set[str] = set()
        for meta in metadatas:
            if not meta:
                continue
            # chroma 返回可能是列表（batched），也可能是字典
            if isinstance(meta, list):
                metas = meta
            else:
                metas = [meta]
            for m in metas:
                if isinstance(m, dict):
                    name = m.get("file_name")
                    if name:
                        names.add(name)
        logger.info("已索引文件数: %s", len(names))
        return names
    except Exception as exc:
        logger.warning("读取已索引文件名失败: %s", exc)
        return set()


@st.cache_resource(show_spinner=False)
def init_global_settings() -> None:
    """统一配置全局 Settings，避免每次重复设定。"""
    Settings.llm = get_llm()
    Settings.embed_model = get_embedding_model()
    Settings.chunk_size = 1024
    Settings.chunk_overlap = 100


def build_or_refresh_index(documents: List[Document]) -> VectorStoreIndex:
    """向量化文档并写入 Chroma，返回索引实例。"""
    init_global_settings()
    logger.info("开始构建/刷新索引，文档数: %s", len(documents))
    storage_context = StorageContext.from_defaults(vector_store=get_vector_store())
    return VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
    )


def load_index() -> VectorStoreIndex:
    """从已有 Chroma 集合恢复索引。"""
    init_global_settings()
    logger.info("从持久化向量库加载索引")
    return VectorStoreIndex.from_vector_store(
        vector_store=get_vector_store(),
    )


def get_hybrid_retriever(
    index: VectorStoreIndex,
    documents: List[Document],
    bm25_top_k: int = 4,
    vector_top_k: int = 4,
) -> QueryFusionRetriever | Any:
    """
    构造 BM25 + 向量的混合检索。
    BM25 使用原始文档（适合专有名词），向量检索来自 Chroma。
    """
    retrievers = []
    if documents:
        bm25 = BM25Retriever.from_defaults(
            nodes=documents,
            similarity_top_k=bm25_top_k,
            language="zh",
        )
        retrievers.append(bm25)

    vector_retriever = index.as_retriever(similarity_top_k=vector_top_k)
    retrievers.append(vector_retriever)

    if len(retrievers) == 1:
        # 仅向量检索（无 BM25 文档时）
        return vector_retriever

    return QueryFusionRetriever(
        retrievers=retrievers,
        similarity_top_k=max(bm25_top_k, vector_top_k),
        num_queries=1,
        mode="reciprocal_rerank",
        use_async=False,
    )


def as_query_engine(
    documents: List[Document],
    bm25_top_k: int = 4,
    vector_top_k: int = 4,
) -> RetrieverQueryEngine:
    """构建带混合检索的 QueryEngine。"""
    index = load_index()
    retriever = get_hybrid_retriever(index, documents, bm25_top_k, vector_top_k)
    response_synthesizer = get_response_synthesizer(streaming=False)
    return RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )


def extract_sources(response) -> List[Dict[str, Any]]:
    """从响应中提取引用溯源信息。"""
    sources = []
    for node in response.source_nodes:
        sources.append(
            {
                "file": node.metadata.get("file_name", "unknown"),
                "page": node.metadata.get("page_number", "?"),
                "score": getattr(node, "score", None),
            }
        )
    return sources


if __name__ == "__main__":
    # 最简 CLI 演示
    from utils import file_to_documents

    config.ensure_dirs()
    sample = config.UPLOAD_DIR / "sample.pdf"
    if sample.exists():
        docs = file_to_documents(sample)
        build_or_refresh_index(docs)
        engine = as_query_engine(docs)
        ans = engine.query("这份文档主要讲什么？")
        print(ans)
        print("sources:", extract_sources(ans))
    else:
        print("请放置 sample.pdf 到 storage/uploads 后重试。")

