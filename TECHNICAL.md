## AutoSafety-RAG 技术说明

### 目录与数据
- `data/docs/`：上传的法规 PDF/PPTX。
- `data/vector_store/`：Chroma 持久化向量库。

### 核心流程 (v0.2)

#### 1. 初始化与状态同步
- 应用启动时，通过 `rag_engine.get_exist_file_names()` 从 Chroma 全量获取已索引文件名集合，存入 `st.session_state["indexed_files"]`。
- 获取 Chroma 文档总数，若大于 0 则自动标记 `index_ready=True`，允许直接问答。

#### 2. 上传与去重
- 用户上传文件时，`sidebar_upload` 实时比对文件名：
  - 若在 `indexed_files`：提示已存在，跳过。
  - 若已在 `pending_docs`（待处理队列）：提示已在队列，跳过。
- 仅通过校验的文件会被解析（`utils.file_to_documents`）并加入 `pending_docs`。
- **撤销处理**：若用户清空上传组件，`pending_docs` 同步清空，保证计数准确。

#### 3. 增量索引构建
- 点击构建按钮后，`rag_engine.build_or_refresh_index` 仅处理 `pending_docs`。
- 构建成功后：
  - 将新文件名合并入 `indexed_files`。
  - 清空 `pending_docs`。
  - 更新 `stored_count`，界面即时反馈最新库容量。

#### 4. 混合检索与生成
- **检索**：`rag_engine.get_hybrid_retriever` 动态组合 BM25 与 Vector 检索器。若无待检索文档（如仅查库），自动降级为纯向量检索。
- **生成**：`Ollama(qwen3:8b)` 接收检索上下文生成回答，`extract_sources` 提取元数据中的文件名与页码用于溯源展示。

### 关键组件
- **状态管理**：Streamlit `session_state` 负责 UI 交互状态，Chroma DB 负责数据持久化真值。
- **缓存机制**：`st.cache_resource` 缓存 LLM、Embedding 模型与 Chroma 客户端连接。
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

