## AutoSafety-RAG

本地法规 RAG 问答（Windows 11 + 单张 A4000 16GB）。

### v0.3 功能更新 (2025-12)
- **代码重构与模块化**：
  - 引入 `engines` 包管理核心引擎（如 OCR、VLM）。
  - 独立 `Visualize_parser_pdf` 模块，提供专门的 PDF解析可视化调试工具。
  - 修复了项目级导入路径，规范化包结构。
- **可视化调试看板**：
  - 新增基于 Gradio 的 PDF 解析调试界面，支持实时查看 Markdown 渲染结果、公式/表格提取效果及布局边框可视化。
- **功能优化**：
  - 优化了依赖管理与环境配置流程。

### v0.2 功能更新
- **数据一致性**：Chroma 作为单一事实来源，启动时自动同步已索引文件列表。
- **上传管理**：去重拦截、状态实时刷新。
- **日志系统**：运行日志自动写入 `logs/app.log`。

### 目录结构
- `app.py`：主应用入口（Streamlit）。
- `rag_engine.py`：RAG 核心服务（检索与生成）。
- `engines/`：核心算法引擎包。
  - `ocr_by_vlm/`：基于 MinerU 2.5 的视觉语言模型 PDF 解析器。
- `Visualize_parser_pdf/`：PDF 解析可视化调试工具包。
  - `gradio_app.py`：可视化看板启动入口。
- `utils.py`：通用工具函数。
- `config.py`：全局配置。
- `data/`：
  - `docs/`：原始法规文件。
  - `vector_store/`：向量数据库持久化文件。
- `logs/`：系统运行日志。

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

