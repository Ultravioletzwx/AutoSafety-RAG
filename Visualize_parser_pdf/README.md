# Visualize Parser PDF - MinerU 可视化调试看板

这是一个基于 Gradio 开发的 PDF 解析可视化工具，专门用于测试和验证 MinerU 2.5 模型的解析效果。它允许开发者上传 PDF 或图片，实时预览 Markdown 转换结果，并直观地检查公式、表格的识别情况以及版面分析的准确性。

## 主要功能

*   **PDF/图片转 Markdown**：使用本地部署的 MinerU 2.5 模型将文档转换为高质量 Markdown。
*   **多模态识别**：支持复杂的数学公式（LaTeX 格式）和表格结构识别。
*   **布局可视化**：自动生成带有布局边框（Layout BBox）的 PDF，方便通过边框颜色和编号检查版面分析结果。
*   **交互式预览**：提供 Markdown 渲染视图和源码视图，支持双向对照。
*   **本地资源渲染**：智能处理图片路径，确保解析后的图片能在 Web 界面正常显示。
*   **结果导出**：支持一键下载包含 Markdown 和提取图片的 ZIP 压缩包。

## 目录结构

```text
Visualize_parser_pdf/
├── gradio_app.py      # Gradio 应用启动入口
├── utils/
│   ├── common.py      # 通用文件处理工具
│   └── draw_utils.py  # 布局绘制工具（绘制 BBox）
└── README.md          # 本说明文档
```

## 快速开始

### 1. 环境准备
请确保已安装项目根目录下的 `requirements.txt` 以及 MinerU 相关依赖：

```bash
# 根目录下执行
pip install -r requirements.txt
pip install "mineru-vl-utils[transformers]"
```

### 2. 启动应用
在项目**根目录**下运行以下命令（请勿进入子目录运行，以免路径错误）：

```bash
python Visualize_parser_pdf/gradio_app.py
```

### 3. 使用说明
1.  打开浏览器访问显示的本地链接（通常为 `http://127.0.0.1:7860`）。
2.  在左侧配置栏：
    *   **上传文件**：选择要测试的 PDF 或图片。
    *   **最大转换页数**：设置解析的页数上限，避免超长文档耗时过久。
    *   **识别选项**：勾选是否启用公式识别和表格识别。
3.  点击 **“转换”** 按钮。
4.  等待解析完成后，右侧面板将展示：
    *   **Markdown 渲染**：可视化的文档效果。
    *   **Markdown 文本**：源代码。
    *   **PDF 预览**：带有布局边框标注的 PDF 文件。
    *   **转换结果**：可下载的 ZIP 包。

## 技术细节

此模块调用了 `engines.ocr_by_vlm.local_parser` 中的解析逻辑。Gradio 应用通过修补 `sys.path` 确保可以从项目根目录正确导入核心引擎模块。可视化部分利用 `reportlab` 和 `pypdf` 在原始 PDF 上层绘制半透明的彩色矩形框，不同颜色代表不同的区域类型（如：图片、表格、公式、文本等）。
