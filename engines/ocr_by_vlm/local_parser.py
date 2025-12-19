#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinerU 2.5 PDF解析器

依赖安装:
pip install transformers torch pdf2image pillow pymupdf mineru-vl-utils

模型使用方式:
1. 默认从本地路径加载: 从config.py中读取mineru_model_path配置
2. 或通过Hugging Face Hub加载: 传入模型名称如 "opendatalab/MinerU2.5-2509-1.2B"

功能: 使用MinerU 2.5模型将PDF转换为Markdown格式，支持文字、表格、公式、图片提取
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List

import torch
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
from PIL import Image
from pdf2image import convert_from_path

# 导入配置模块
from config import model_config

# 需要安装 mineru_vl_utils
# pip install "mineru-vl-utils[transformers]"
from mineru_vl_utils import MinerUClient
from Visualize_parser_pdf.utils.draw_utils import draw_layout_bbox



class MinerUParser:
    """MinerU PDF解析器封装"""
    
    def __init__(self, model_name: str = None):
        """初始化解析器
        
        Args:
            model_name: 模型名称或路径，如果为None则使用config中的默认路径
        """
        # 使用config中的默认路径或用户提供的路径
        self.model_name = model_name or model_config.mineru_model_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.client = None
        
    def load_model(self) -> None:
        """加载模型到内存"""
        if self.model is None:
            print(f"正在加载模型到 {self.device}...")
            
            # 加载模型和处理器
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_name,
                dtype="auto",  # 使用 torch_dtype 替代 dtype 当 transformers < 4.56.0
                device_map="auto"
            )
            
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                use_fast=True
            )
            
            # 创建 MinerU 客户端
            self.client = MinerUClient(
                backend="transformers",
                model=self.model,
                processor=self.processor
            )
            
            print("模型加载完成!")
    
    def _extract_images_from_pdf(self, pdf_path: str, output_dir: str) -> Dict[int, List[str]]:
        """从PDF中提取图片
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 图片输出目录
            
        Returns:
            图片路径字典，键为页码，值为图片路径列表
        """
        os.makedirs(output_dir, exist_ok=True)
        images = convert_from_path(pdf_path)
        
        page_images = {}
        for page_idx, image in enumerate(images):
            img_path = os.path.join(output_dir, f"page_{page_idx+1}.jpg")
            image.save(img_path, "JPEG")
            page_images[page_idx+1] = [img_path]
            
        return page_images
    

    def _blocks_to_markdown(self, blocks: List[Dict], image_path: str, output_dir: str, page_num: int, img_counter: Dict[str, int]) -> str:
        """将提取的块转换为Markdown格式
        
        Args:
            blocks: 提取的块列表
            image_path: 原始页面图片路径
            output_dir: 输出目录
            page_num: 页码
            img_counter: 图片计数器字典
            
        Returns:
            Markdown格式的文本
        """
        md_content = ""
        
        for block in blocks:
            block_type = block.get("type", "")
            content = block.get("content", "")
            
            if block_type == "text":
                if content:
                    md_content += content + "\n"
            elif block_type == "table":
                if content:
                    md_content += content + "\n" # 原生输出html表格
            elif block_type == "image": # mineru 提取的图片 type是image
                bbox = block.get("bbox", None)
                if bbox and len(bbox) == 4:
                    cropped_img_name = self._crop_and_save_image(
                        image_path, bbox, output_dir, page_num, img_counter
                    )
                    if cropped_img_name:
                        md_content += f"![图片](images/{cropped_img_name})\n"
            elif block_type == "equation": # mineru 提取的公式 type是equation
                if content:
                    md_content += f"$$\n{content}\n$$\n"
            else:
                if content:
                    md_content += content + "\n"
        
        return md_content.strip()
    
    def _crop_and_save_image(self, image_path: str, bbox: List[float], output_dir: str, page_num: int, img_counter: Dict[str, int]) -> Optional[str]:
        """根据bbox裁剪图片并保存
        
        Args:
            image_path: 原始页面图片路径
            bbox: 边界框坐标 [x1, y1, x2, y2]，归一化坐标(0-1)
            output_dir: 输出目录
            page_num: 页码
            img_counter: 图片计数器字典
            
        Returns:
            裁剪后的图片文件名，失败返回None
        """
        try:
            page_image = Image.open(image_path)
            width, height = page_image.size
            
            x1, y1, x2, y2 = bbox
            left = int(x1 * width)
            top = int(y1 * height)
            right = int(x2 * width)
            bottom = int(y2 * height)
            
            cropped_image = page_image.crop((left, top, right, bottom))
            
            img_counter['count'] += 1
            cropped_img_name = f"page_{page_num}_img_{img_counter['count']}.jpg"
            
            images_dir = os.path.join(output_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            cropped_img_path = os.path.join(images_dir, cropped_img_name)
            
            cropped_image.save(cropped_img_path, "JPEG")
            
            return cropped_img_name
        except Exception as e:
            print(f"裁剪图片失败: {e}")
            return None
    
    
    def _merge_cross_page_tables(self, page_blocks: List[Dict]) -> None:
        """
        检测并合并跨页表格
        
        Args:
            page_blocks: 包含所有页面块信息的列表
        """
        if len(page_blocks) < 2:
            return  # 至少需要两页才可能有跨页表格
            
        # 遍历所有页面，除了最后一页
        for i in range(len(page_blocks) - 1):
            current_page = page_blocks[i]
            next_page = page_blocks[i + 1]
            
            current_blocks = current_page['blocks']
            next_blocks = next_page['blocks']
            
            if not current_blocks or not next_blocks:
                continue
            
            # 检查当前页的最后一个块是否是表格
            current_last_block = current_blocks[-1]
            if current_last_block.get('type') != 'table':
                continue
            
            # 检查下一页的第一个块是否是表格
            next_first_block = next_blocks[0]
            if next_first_block.get('type') != 'table':
                continue
            
            # 判断是否为跨页表格（简单规则：当前页最后一个和下一页第一个都是表格）
            # 这里可以添加更复杂的判断逻辑，比如表格结构匹配、行数/列数等
            print(f"检测到跨页表格: 第{current_page['page_num']}页结束，第{next_page['page_num']}页开始")
            
            # 合并表格：将下一页的表格内容追加到当前页的表格内容中
            # 假设表格内容是HTML格式
            merged_content = current_last_block.get('content', '') + next_first_block.get('content', '')
            current_last_block['content'] = merged_content
            
            # 标记跨页表格
            current_last_block['is_cross_page'] = True
            
            # 从下一页移除已合并的表格
            next_blocks.pop(0)
            
            print("跨页表格合并完成")
    
    def parse_pdf_to_markdown(self, pdf_path: str, output_dir: str) -> str:
        """
        将PDF转换为Markdown格式
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录，将包含markdown文件和images子目录
            
        Returns:
            生成的Markdown文件绝对路径
        """
        # 验证输入
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建images子目录
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # 加载模型
        self.load_model()
        
        # 从PDF中提取图片
        print(f"正在从PDF中提取图片...")
        page_images = self._extract_images_from_pdf(pdf_path, images_dir)
        
        # 处理每一页图片并收集结果
        total_pages = len(page_images)
        page_blocks = []  # 存储每一页的提取块
        
        for page_num, img_paths in sorted(page_images.items()):
            print(f"正在处理第 {page_num}/{total_pages} 页...")
            
            if img_paths:
                img_path = img_paths[0]  # 每页只有一张图片
                
                # 打开图片
                image = Image.open(img_path)
                
                # 使用MinerU客户端进行两阶段提取
                extracted_blocks = self.client.two_step_extract(image)
                
                # 保存当前页的块信息
                page_blocks.append({
                    'page_num': page_num,
                    'blocks': extracted_blocks,
                    'image_path': img_path
                })
        
        # 检测并合并跨页表格
        print("正在检测跨页表格...")
        self._merge_cross_page_tables(page_blocks)
        
        # 将所有页面的块转换为Markdown
        full_md_content = ""
        img_counter = {'count': 0}
        
        for page_data in page_blocks:
            page_num = page_data['page_num']
            blocks = page_data['blocks']
            image_path = page_data['image_path']
            
            # 将提取的块转换为Markdown格式
            page_md = self._blocks_to_markdown(blocks, image_path, output_dir, page_num, img_counter)
            
            # 添加到完整内容
            full_md_content += f"\n\n---\n\n# 第 {page_num} 页\n\n{page_md}"
        
        # 保存Markdown文件
        md_filename = os.path.splitext(os.path.basename(pdf_path))[0] + ".md"
        md_path = os.path.join(output_dir, md_filename)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_md_content.strip())
        
        print(f"PDF解析完成! 输出文件: {md_path}")
        
        # Draw layout bbox on PDF
        layout_pdf_name = os.path.splitext(os.path.basename(pdf_path))[0] + "_layout.pdf"
        layout_pdf_path = os.path.join(output_dir, layout_pdf_name)
        print(f"正在生成布局可视化PDF...")
        draw_layout_bbox(page_blocks, pdf_path, layout_pdf_path)
        print(f"布局可视化PDF生成完成: {layout_pdf_path}")

        return os.path.abspath(md_path), os.path.abspath(layout_pdf_path)


# 全局解析器实例，确保模型只加载一次
_global_parser = None

# 便捷函数
def parse_pdf_to_markdown(pdf_path: str, output_dir: str):
    """
    将PDF转换为Markdown格式的便捷函数
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        
    Returns:
        生成的Markdown文件绝对路径, 布局可视化PDF文件绝对路径
    """
    global _global_parser
    if _global_parser is None:
        _global_parser = MinerUParser()
    return _global_parser.parse_pdf_to_markdown(pdf_path, output_dir)


if __name__ == "__main__":
    # 示例用法
    # import argparse
    
    # parser = argparse.ArgumentParser(description="使用MinerU 2.5将PDF转换为Markdown")
    # parser.add_argument("pdf_path", help="PDF文件路径")
    # parser.add_argument("output_dir", help="输出目录")
    
    # args = parser.parse_args()
    pdf_path = r"C:\Users\14724\PycharmProjects\pythonProject\small_cases\Rag_in_passive_safety_regulations\data\docs\附录A正面100%重叠刚性壁障碰撞试验规程.pdf"
    output_dir = r"C:\Users\14724\PycharmProjects\pythonProject\small_cases\Rag_in_passive_safety_regulations\data\test"
    
    # md_path = parse_pdf_to_markdown(args.pdf_path, args.output_dir)
    md_path, layout_pdf_path = parse_pdf_to_markdown(pdf_path, output_dir)
    print(f"生成的Markdown文件: {md_path}")
    print(f"生成的布局PDF文件: {layout_pdf_path}")
