"""
Streamlit 入口：上传法规文件(PDF/PPTX)、构建/更新索引、聊天问答与引用溯源。
运行：
    streamlit run app.py
"""
from pathlib import Path
from typing import List

import streamlit as st
from llama_index.core import Document

import config
import rag_engine
import utils

st.set_page_config(page_title="AutoSafety-RAG", page_icon="🚗", layout="wide")


def init_state() -> None:
    """初始化会话状态。"""
    if "documents" not in st.session_state:
        st.session_state["documents"]: List[Document] = []
    if "index_ready" not in st.session_state:
        st.session_state["index_ready"] = False


def sidebar_upload() -> None:
    """侧边栏上传并解析文件。"""
    uploaded = st.sidebar.file_uploader(
        "上传法规文件（PDF/PPTX）",
        type=["pdf", "pptx"],
        accept_multiple_files=True,
    )
    if not uploaded:
        return

    st.sidebar.write("解析中...")
    for uf in uploaded:
        saved_path = utils.save_uploaded_file(uf, config.UPLOAD_DIR)
        docs = utils.file_to_documents(saved_path)
        st.session_state["documents"].extend(docs)
    st.sidebar.success(f"已解析文档数：{len(st.session_state['documents'])}")


def build_index_action() -> None:
    """构建或刷新向量索引。"""
    if not st.session_state["documents"]:
        st.warning("请先上传并解析文档。")
        return
    rag_engine.build_or_refresh_index(st.session_state["documents"])
    st.session_state["index_ready"] = True
    st.success("索引已更新，混合检索就绪。")


def chat_area() -> None:
    """聊天区域：提交问题并展示答案与引用。"""
    st.header("法规问答")
    query = st.text_area("输入你的问题", height=120, placeholder="例如：前排安全气囊展开条件？")
    if st.button("发送") and query:
        if not st.session_state["index_ready"]:
            st.warning("请先构建/更新索引。")
            return
        engine = rag_engine.as_query_engine(st.session_state["documents"])
        with st.spinner("检索与生成中..."):
            response = engine.query(query)
        st.markdown("### 回答")
        st.write(response.response)

        sources = rag_engine.extract_sources(response)
        if sources:
            st.markdown("### 引用溯源")
            for idx, src in enumerate(sources, start=1):
                st.write(f"{idx}. {src['file']} - 第 {src['page']} 页 (score: {src['score']})")
        else:
            st.info("未返回引用节点。")


def main() -> None:
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

