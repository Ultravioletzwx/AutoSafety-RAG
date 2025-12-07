## AutoSafety-RAG 技术说明

### 目录与数据
- `data/docs/`：上传的法规 PDF/PPTX。
- `data/vector_store/`：Chroma 持久化向量库。

### 流程概览
1. 上传：Streamlit 将文件保存至 `data/docs/`（`utils.save_uploaded_file`）。
2. 解析：`utils.file_to_documents` 调度 PDF/PPTX 解析为 Markdown，按页切分，写入 `metadata`（文件名、页码）。
3. 向量化与存储：`rag_engine.build_or_refresh_index` 使用 HuggingFace `BAAI/bge-m3` 生成向量，写入 Chroma。
4. 混合检索：`rag_engine.get_hybrid_retriever` 组合 BM25（稀疏）+ Chroma 向量检索，`QueryFusionRetriever` 使用 reciprocal_rerank。
5. 生成：`Ollama(qwen3:8b)` 负责回答，`extract_sources` 返回溯源的文件名与页码。

### 关键组件
- 缓存：`st.cache_resource` 复用 LLM、Embedding、VectorStore、ServiceContext，避免重复加载。
- GPU/显存：`config.model_config.embedding_device` 默认为 `cuda`。若显存紧张（A4000 需为 Ollama 预留显存），可改为 `"cpu"`。
- 路径：统一 `pathlib`，便于 Windows 兼容。

### 依赖与部署
- 统一依赖：`pip install -r requirements.txt`
- torch（CUDA）需按显卡 CUDA 版本单独安装示例：`pip install torch --index-url https://download.pytorch.org/whl/cu121`

### 运行
- 开发模式：`streamlit run app.py`
- 首次运行需上传文档并点击“构建/更新索引”以写入 Chroma。

### 可扩展点
- 解析增强：可替换/补充 LlamaParse 处理表格与版面。
- 索引策略：可调 BM25/vector top_k，或改用 rerank 模型。
- 安全与多租：可在 metadata 加入用户/租户标识并在检索时做过滤。

