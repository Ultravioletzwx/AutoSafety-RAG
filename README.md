## AutoSafety-RAG

本地法规 RAG 问答（Windows 11 + 单张 A4000 16GB）。

### 目录结构
- `app.py`：Streamlit 入口。
- `rag_engine.py`：LlamaIndex 混合检索封装（BM25 + 向量）。
- `utils.py`：上传、PDF/PPTX 解析为 Markdown。
- `config.py`：路径与模型配置。
- `data/docs/`：文件夹1，存放上传的法规 PDF/PPTX。
- `data/vector_store/`：文件夹2，存放 Chroma 向量化数据。

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

