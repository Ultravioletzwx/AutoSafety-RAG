import io
from io import BytesIO
import os
import re
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


pdf_suffixes = ['pdf']
image_suffixes = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'jp2', 'webp', 'gif']


def guess_suffix_by_bytes(file_bytes, path):
    """根据文件字节和路径猜测文件后缀"""
    if path and hasattr(path, 'suffix'):
        suffix = path.suffix.lower().lstrip('.')
        if suffix in pdf_suffixes + image_suffixes:
            return suffix
    
    # 简单的文件头检查
    if file_bytes.startswith(b'%PDF'):
        return 'pdf'
    elif file_bytes.startswith(b'\xff\xd8'):
        return 'jpg'
    elif file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    elif file_bytes.startswith(b'GIF8'):
        return 'gif'
    elif file_bytes.startswith(b'BM'):
        return 'bmp'
    elif file_bytes.startswith(b'II*') or file_bytes.startswith(b'MM*'):
        return 'tiff'
    else:
        return ''


def images_bytes_to_pdf_bytes(image_bytes):
    """将图片字节转换为PDF字节"""
    try:
        # 使用PIL打开图片
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # 使用pypdfium2创建PDF
        pdf = pdfium.PdfDocument.new()
        width, height = image.size
        page = pdf.new_page(width, height)
        
        # 将图片插入到PDF页面
        with pdfium.PdfImage.new(pdf, image_bytes) as pdf_image:
            page.insert_image(pdf_image, pdfium.PdfImagePosition(x=0, y=0, width=width, height=height))
        
        # 保存PDF到内存缓冲区
        output_buffer = io.BytesIO()
        pdf.save(output_buffer)
        pdf_bytes = output_buffer.getvalue()
        
        pdf.close()
        return pdf_bytes
    except Exception as e:
        print(f"pypdfium2转换失败，使用PIL fallback: {e}")
        # PIL fallback
        try:
            pdf_buffer = io.BytesIO()
            image.save(pdf_buffer, format='PDF')
            return pdf_buffer.getvalue()
        except Exception as fallback_e:
            print(f"PIL转换失败: {fallback_e}")
            raise


def read_fn(path):
    """读取文件并根据文件类型进行转换"""
    if not isinstance(path, Path):
        path = Path(path)
    with open(str(path), "rb") as input_file:
        file_bytes = input_file.read()
        file_suffix = guess_suffix_by_bytes(file_bytes, path)
        if file_suffix in image_suffixes:
            return images_bytes_to_pdf_bytes(file_bytes)
        elif file_suffix in pdf_suffixes:
            return file_bytes
        else:
            raise Exception(f"不支持的文件类型: {file_suffix}")


def safe_stem(file_path):
    """安全地获取文件名（只保留字母、数字、下划线和点）"""
    stem = Path(file_path).stem
    return re.sub(r'[^\w.]', '_', stem)


def to_pdf(file_path):
    """将文件转换为PDF格式"""
    if file_path is None:
        return None

    try:
        pdf_bytes = read_fn(file_path)
        
        # 生成安全的文件名
        unique_filename = f'{safe_stem(file_path)}.pdf'
        
        # 构建完整的文件路径
        tmp_file_path = os.path.join(os.path.dirname(file_path), unique_filename)
        
        # 将字节数据写入文件
        with open(tmp_file_path, 'wb') as tmp_pdf_file:
            tmp_pdf_file.write(pdf_bytes)
        
        return tmp_file_path
    except Exception as e:
        print(f"转换为PDF失败: {e}")
        return None

