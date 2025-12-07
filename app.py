"""
Streamlit 入口：上传法规文件(PDF/PPTX)、构建/更新索引、聊天问答与引用溯源。
运行：
    streamlit run app.py
"""
import logging
from pathlib import Path
from typing import List, Set

import streamlit as st
from llama_index.core import Document

import config
import rag_engine
import utils

st.set_page_config(page_title="AutoSafety-RAG", page_icon="🚗", layout="wide")
logger = logging.getLogger("autosafety")


def init_state() -> None:
    """初始化会话状态，Chroma 为真值来源。"""
    logger.info("初始化会话状态")
    # 已索引文件集合（来自 Chroma）
    indexed_files: Set[str] = rag_engine.get_exist_file_names()
    st.session_state["indexed_files"] = indexed_files
    # 待入库的增量文档（本次上传未入库）
    st.session_state["pending_docs"]: List[Document] = st.session_state.get("pending_docs", [])
    # 查询就绪标记与已存文档数
    st.session_state["stored_count"] = rag_engine.get_collection_count()
    st.session_state["index_ready"] = len(indexed_files) > 0 or st.session_state["stored_count"] > 0
    logger.info(
        "持久化文档数: %s, indexed_files=%s, index_ready=%s",
        st.session_state["stored_count"],
        len(indexed_files),
        st.session_state["index_ready"],
    )


def sidebar_upload() -> None:
    """侧边栏上传并解析文件。"""
    # 使用最新持久化数量，确保按钮后也实时刷新
    stored_count = rag_engine.get_collection_count()
    st.session_state["stored_count"] = stored_count
    indexed_files = st.session_state["indexed_files"]
    pending_docs = st.session_state["pending_docs"]

    uploaded = st.sidebar.file_uploader(
        "上传法规文件（PDF/PPTX）",
        type=["pdf", "pptx"],
        accept_multiple_files=True,
    )

    # 若用户清空选择，则同步清空 pending
    if not uploaded:
        st.session_state["pending_docs"] = []
        pending_count = 0
        st.sidebar.markdown(f"**当前库文档数：{stored_count}**")
        st.sidebar.markdown(f"**待构建索引文档数：{pending_count}**")
        return

    # 只保留当前仍在上传列表中的 pending 文档（避免已取消的文件残留）
    current_names = {uf.name for uf in uploaded}
    print("current_names:", current_names)
    pending_docs = [doc for doc in pending_docs if doc.metadata.get("file_name") in current_names]
    print("pending_docs:", pending_docs)
    st.session_state["pending_docs"] = pending_docs

    st.sidebar.write("解析中...")
    new_pages = 0
    for uf in uploaded:
        if uf.name in indexed_files:
            st.sidebar.info(f"📄 {uf.name} 已存在于库中，自动跳过")
            logger.info("跳过已索引文件: %s", uf.name)
            continue
        # 检查是否已在待处理列表（通过 metadata 的 file_name 比较）
        already_pending = any(doc.metadata.get("file_name") == uf.name for doc in pending_docs)
        if already_pending:
            st.sidebar.info(f"📄 {uf.name} 已在待构建队列，跳过")
            logger.info("跳过已在待构建队列文件: %s", uf.name)
            continue

        saved_path = utils.save_uploaded_file(uf, config.UPLOAD_DIR)
        docs = utils.file_to_documents(saved_path)
        pending_docs.extend(docs)
        new_pages += len(docs)
        logger.info("解析完成: %s, 新增页数=%s", uf.name, len(docs))

    pending_count = len(pending_docs)
    st.sidebar.markdown(f"**当前库文档数：{stored_count}**")
    st.sidebar.markdown(f"**待构建索引文档数：{pending_count}**")
    st.sidebar.success(f"新增页数：{new_pages}，待索引总计：{pending_count}")


def build_index_action() -> None:
    """构建或刷新向量索引。"""
    pending_docs = st.session_state["pending_docs"]
    indexed_files = st.session_state["indexed_files"]

    if not pending_docs:
        if indexed_files:
            st.info("当前所有上传文档均已索引，无需更新。")
        else:
            st.warning("请先上传新文档。")
        return

    logger.info("开始构建增量索引，待索引页数=%s", len(pending_docs))
    rag_engine.build_or_refresh_index(pending_docs)
    # 成功后合并文件名记录
    new_files = {doc.metadata.get("file_name") for doc in pending_docs if doc.metadata.get("file_name")}
    indexed_files.update(new_files)
    st.session_state["pending_docs"] = []
    st.session_state["stored_count"] = rag_engine.get_collection_count()
    st.session_state["index_ready"] = True
    st.success("✅ 增量索引构建完成！")
    logger.info("索引更新完成，当前库文档数=%s，新增文件数=%s", st.session_state["stored_count"], len(new_files))


def chat_area() -> None:
    """聊天区域：提交问题并展示答案与引用。"""
    st.header("法规问答")
    query = st.text_area("输入你的问题", height=120, placeholder="例如：前排安全气囊展开条件？")
    if st.button("发送") and query:
        if not st.session_state["index_ready"]:
            st.warning("请先构建/更新索引。")
            return
        logger.info("收到查询: %s", query)
        # 查询时无需 pending 文档；BM25 若需要可传空列表
        engine = rag_engine.as_query_engine([])
        with st.spinner("检索与生成中..."):
            response = engine.query(query)
        st.markdown("### 回答")
        st.write(response.response)

        sources = rag_engine.extract_sources(response)
        if sources:
            st.markdown("### 引用溯源")
            for idx, src in enumerate(sources, start=1):
                st.write(f"{idx}. {src['file']} - 第 {src['page']} 页 (score: {src['score']})")
            logger.info("返回溯源节点数: %s", len(sources))
        else:
            st.info("未返回引用节点。")
            logger.info("未返回引用节点")


def main() -> None:
    config.setup_logging()
    logger.info("应用启动")
    config.ensure_dirs()
    init_state()
    st.title("AutoSafety-RAG 🚗")
    st.caption("本地混合检索：BM25 + 向量 (Chroma) + Ollama(qwen3:8b)")
    st.sidebar.header("文件上传与索引")
    sidebar_upload()
    if st.sidebar.button("构建/更新索引"):
        build_index_action()

    with st.expander("环境提示", expanded=False):
        st.write(
            "嵌入模型默认使用 GPU，A4000 显存 16GB，需为 Ollama 预留显存。如显存不足，可在 config.py 中将 embedding_device 改为 cpu。"
        )
    chat_area()


if __name__ == "__main__":
    # 直接运行示例：仅打印目录，实际交互请使用 streamlit run app.py
    # config.ensure_dirs()
    main()
    # print("启动命令：streamlit run app.py")
    # print(f"上传目录（docs）：{Path(config.UPLOAD_DIR).resolve()}")
    # print(f"向量库目录（vector_store）：{Path(config.CHROMA_PATH).resolve()}")

