## AutoSafety-RAG

本地法规 RAG 问答（Windows 11 + 单张 A4000 16GB）。

### v0.2 功能更新
- **数据一致性**：Chroma 作为单一事实来源，启动时自动同步已索引文件列表，无需手动刷新。
- **上传去重与状态管理**：
  - 自动拦截已索引或已在队列中的同名文件。
  - 用户撤销上传时，实时清空待处理队列，修正页数统计问题。
  - 侧边栏实时展示「当前库文档数」与「待构建索引文档数」。
- **增量构建**：仅处理本次新增的有效文档，构建成功后自动合并索引并重置队列。
- **日志系统**：运行日志自动写入 `logs/app.log`，方便问题排查。

### 目录结构
- `app.py`：Streamlit 主入口（含会话状态管理）。
- `rag_engine.py`：RAG 核心引擎（Chroma 连接、混合检索、元数据管理）。
- `utils.py`：PDF/PPTX 解析与 Markdown 转换。
- `config.py`：环境配置与日志初始化。
- `data/docs/`：原始法规文件存档。
- `data/vector_store/`：Chroma 向量数据库持久化目录。
- `logs/`：运行时日志文件。

### 环境安装
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
# CUDA 版 torch 需按显卡 CUDA 版本单独安装，示例（cu121）：
pip uninstall -y torch
pip install --no-cache-dir --force-reinstall torch --index-url https://download.pytorch.org/whl/cu121
```

### 运行
```bash
streamlit run app.py
```

### 使用说明
1. 确保 Ollama 已运行并可用 `qwen3:8b`：`ollama run qwen3:8b "hello"`.
2. 上传 PDF/PPTX 到侧边栏（存入 `data/docs/`），点击“构建/更新索引”。
3. 在输入框提问，回答会附带文件名与页码引用。
4. 若显存不足，可将 `config.py` 中 `embedding_device` 设为 `"cpu"`。

### 进一步阅读
- 技术实现细节：`TECHNICAL.md`

### 备注
- 解析基于 PyMuPDF、python-pptx，输出 Markdown 以保留标题层级。
- Chroma 持久化在 `data/vector_store/`，删除该目录可清空索引。*** End Patch``

