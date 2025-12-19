import sys
from pathlib import Path
# Add project root to sys.path to allow imports from other directories
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import base64
import os
import re
import time
import zipfile

import gradio as gr
from gradio_pdf import PDF

from engines.ocr_by_vlm.local_parser import parse_pdf_to_markdown
from Visualize_parser_pdf.utils.common import read_fn, to_pdf, safe_stem


async def parse_pdf(doc_path, output_dir, end_page_id, formula_enable=True, table_enable=True):
    os.makedirs(output_dir, exist_ok=True)

    try:
        file_name = f'{safe_stem(Path(doc_path).stem)}_{time.strftime("%y%m%d_%H%M%S")}'
        
        # 创建独立的输出目录，避免多请求冲突
        unique_output_dir = os.path.join(output_dir, file_name)
        os.makedirs(unique_output_dir, exist_ok=True)
        
        # 调用用户的local_parser进行PDF解析
        md_path, layout_pdf_path = parse_pdf_to_markdown(doc_path, unique_output_dir)
        
        return unique_output_dir, file_name, layout_pdf_path
    except Exception as e:
        print(f"解析错误: {e}")
        return None


def compress_directory_to_zip(directory_path, output_zip_path):
    """压缩指定目录到一个 ZIP 文件。

    :param directory_path: 要压缩的目录路径
    :param output_zip_path: 输出的 ZIP 文件路径
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历目录中的所有文件和子目录
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    # 构建完整的文件路径
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, directory_path)
                    # 添加文件到 ZIP 文件
                    zipf.write(file_path, arcname)
        return 0
    except Exception as e:
        print(f"压缩错误: {e}")
        return -1


def image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def replace_image_with_local_url(markdown_text, image_dir_path):
    # 匹配Markdown中的图片标签
    pattern = r'\!\[(?:[^\]]*)\]\(([^)]+)\)'
    
    # 获取绝对路径，用于 Gradio 服务
    abs_image_dir = os.path.abspath(image_dir_path)

    # 替换图片链接
    def replace(match):
        relative_path = match.group(1).strip()
        
        # 尝试查找图片
        full_path = None
        
        # 尝试直接拼接
        potential_path = os.path.join(abs_image_dir, relative_path)
        
        if os.path.exists(potential_path):
            full_path = potential_path
        elif relative_path.startswith('images/'):
            # 有时可能路径拼接问题，再次尝试
            # 这里的 relative_path 应该是 images/xxx.jpg
            full_path = os.path.join(abs_image_dir, relative_path)
            
        if full_path and os.path.exists(full_path):
            # 将 Windows 路径分隔符转换为 /
            normalized_path = full_path.replace('\\', '/')
            # 使用 Gradio 的 /file= 路由服务本地文件
            # 这样避免了 Base64 过大的问题
            return f'![image](/file={normalized_path})'
        else:
            return match.group(0)
            
    # 应用替换
    return re.sub(pattern, replace, markdown_text)


async def to_markdown(file_path, end_pages=10, formula_enable=True, table_enable=True, progress=gr.Progress()):
    if file_path is None:
        return None, None, None, None
        
    file_path = to_pdf(file_path)
    if file_path is None:
        return None, None, None, None
        
    try:
        # 更新进度
        progress(0.1, desc="开始处理文件...")
        
        # 调用local_parser进行PDF解析
        output_dir = './output'
        # 调用local_parser进行PDF解析
        output_dir = './output'
        local_md_dir, file_name, layout_pdf_path_from_parser = await parse_pdf(file_path, output_dir, end_pages - 1, formula_enable, table_enable)
        
        if local_md_dir is None:
            return None, None, None, None
        
        # 更新进度
        progress(0.5, desc="文件解析完成，正在处理结果...")
        
        # 压缩结果
        archive_zip_path = os.path.join('./output', f'{file_name}.zip')
        zip_archive_success = compress_directory_to_zip(local_md_dir, archive_zip_path)
        if zip_archive_success == 0:
            print('压缩成功')
        else:
            print('压缩失败')
        
        # 更新进度
        progress(0.7, desc="正在读取Markdown内容...")
        
        # 读取Markdown内容
        md_filename = os.path.splitext(os.path.basename(file_path))[0] + '.md'
        md_path = os.path.join(local_md_dir, md_filename)
        
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()
            
            # 更新进度
            progress(0.8, desc="正在处理图片...")
            
            # 将图片链接替换为 /file= 本地链接，供前端渲染
            md_content = replace_image_with_local_url(txt_content, local_md_dir)
            
            # 返回转换后的PDF路径（使用带布局的可视化文件）
            if layout_pdf_path_from_parser and os.path.exists(layout_pdf_path_from_parser):
                new_pdf_path = layout_pdf_path_from_parser
            else:
                new_pdf_path = file_path # Fallback to original if generation failed
            
            # 更新进度
            progress(1.0, desc="完成!")
            
            return md_content, txt_content, archive_zip_path, new_pdf_path
        else:
            return None, None, None, None
    except Exception as e:
        print(f"处理错误: {e}")
        return None, None, None, None


# LaTeX分隔符配置
latex_delimiters_type_a = [
    {'left': '$$', 'right': '$$', 'display': True},
    {'left': '$', 'right': '$', 'display': False},
]
latex_delimiters_type_b = [
    {'left': '\\(', 'right': '\\)', 'display': False},
    {'left': '\\[', 'right': '\\]', 'display': True},
]
latex_delimiters = latex_delimiters_type_a + latex_delimiters_type_b


# 创建WebUI界面
def main():
    # 支持的文件格式
    pdf_suffixes = ['pdf']
    image_suffixes = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif']
    suffixes = [f".{suffix}" for suffix in pdf_suffixes + image_suffixes]
    
    with gr.Blocks(title="MinerU Demo") as demo:
        gr.Markdown("# MinerU PDF解析器")
        gr.Markdown("将PDF或图片转换为Markdown格式，支持公式和表格识别")
        gr.Markdown("**注意:** PDF解析可能需要较长时间(1-5分钟/页)，请耐心等待")
        
        with gr.Row():
            with gr.Column(variant='panel', scale=5):
                with gr.Row():
                    input_file = gr.File(label='请上传PDF或图片文件', file_types=suffixes)
                with gr.Row():
                    max_pages = gr.Slider(1, 100, 10, step=1, label='最大转换页数')
                with gr.Row(equal_height=True):
                    with gr.Column():
                        gr.Markdown("**识别选项:**")
                        formula_enable = gr.Checkbox(label='启用公式识别', value=True)
                        table_enable = gr.Checkbox(label='启用表格识别', value=True)
                with gr.Row():
                    convert_btn = gr.Button('转换', variant='primary')
                    clear_btn = gr.ClearButton(value='清除')
                with gr.Row():
                    progress = gr.Progress()  # 添加进度条
                pdf_show = PDF(label='PDF预览', interactive=False, visible=True, height=600)

            with gr.Column(variant='panel', scale=5):
                output_file = gr.File(label='转换结果', interactive=False)
                with gr.Tabs():
                    with gr.Tab('Markdown渲染'):
                        md = gr.Markdown(label='Markdown渲染', height=1000,
                                         latex_delimiters=latex_delimiters,
                                         line_breaks=True)
                    with gr.Tab('Markdown文本'):
                        md_text = gr.TextArea(lines=45)

        # 添加事件处理
        input_file.change(fn=to_pdf, inputs=input_file, outputs=pdf_show, api_name=False)
        
        convert_btn.click(
            fn=to_markdown,
            inputs=[input_file, max_pages, formula_enable, table_enable],
            outputs=[md, md_text, output_file, pdf_show],
            api_name=False
        )
        
        clear_btn.add([input_file, md, pdf_show, md_text, output_file])

    # 允许访问 output 目录以渲染图片
    allowed_paths = [os.path.abspath('./output')]
    demo.launch(server_name='0.0.0.0', server_port=7860, share=False, allowed_paths=allowed_paths)


if __name__ == '__main__':
    main()