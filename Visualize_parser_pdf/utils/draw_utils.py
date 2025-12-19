
import io
import copy
from loguru import logger
from pypdf import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas

# 块类型定义
class BlockType:
    TEXT = "text"
    TITLE = "title"
    INTERLINE_EQUATION = "interline_equation"
    EQUATION = "equation"
    IMAGE = "image"
    TABLE = "table"
    LIST = "list"
    INDEX = "index"
    ABANDON = "abandon" # 废弃/忽略的块
    PAGE_NUMBER = "page_number"
    TABLE_CAPTION = "table_caption"
    IMAGE_CAPTION = "image_caption"
    # 对应 minueru 的命名
    # 来自 chunk.txt: title, text, list, page_number, table_caption, table, image, image_caption, equation

# 颜色配置 (RGB 0-255)
# 基于 mineru/utils/draw_bbox.py 和通用默认值
COLOR_MAP = {
    BlockType.IMAGE: [153, 255, 51],           # 绿色系
    BlockType.IMAGE_CAPTION: [102, 178, 255],  # 浅蓝色
    BlockType.TABLE: [204, 204, 0],            #黄色系
    BlockType.TABLE_CAPTION: [255, 255, 102],  # 浅黄色
    BlockType.TITLE: [102, 102, 255],          # 蓝色
    BlockType.TEXT: [153, 0, 76],              # 深红/紫色
    BlockType.EQUATION: [0, 255, 0],           # 绿色
    BlockType.INTERLINE_EQUATION: [0, 255, 0],
    BlockType.LIST: [40, 169, 92],             # 森林绿
    BlockType.INDEX: [40, 169, 92],
    BlockType.PAGE_NUMBER: [255, 0, 255],      # 洋红色
    "default": [255, 0, 0]                     # 默认红色
}

def cal_canvas_rect(page, bbox):
    """
    根据原始PDF页面和边界框计算画布上的矩形坐标。
    """
    # 获取页面尺寸 (优先使用 cropbox 或 mediabox)
    cropbox = page.cropbox
    page_width = float(cropbox[2]) - float(cropbox[0])
    page_height = float(cropbox[3]) - float(cropbox[1])
    
    actual_width = page_width
    actual_height = page_height
    
    rotation_obj = page.get("/Rotate", 0)
    try:
        rotation = int(rotation_obj) % 360
    except (ValueError, TypeError) as e:
        logger.warning(f"页面 /Rotate 值 {rotation_obj!r} 无效; 默认为 0. 错误: {e}")
        rotation = 0
    
    # 如果旋转了90或270度，交换宽高
    if rotation in [90, 270]:
        actual_width, actual_height = actual_height, actual_width
        
    x0, y0, x1, y1 = bbox
    
    # extracted_blocks 返回归一化坐标 [x1, y1, x2, y2]
    # 我们需要将其按页面尺寸缩放
    
    x0 = x0 * actual_width
    x1 = x1 * actual_width
    y0 = y0 * actual_height
    y1 = y1 * actual_height

    rect_w = abs(x1 - x0)
    rect_h = abs(y1 - y0)
    
    # PDF坐标转换 (0,0 在左下角)
    # 归一化坐标通常以左上角为 (0,0) (图片坐标系)
    
    pdf_x0 = x0
    pdf_y0 = page_height - y1  # 底部 y (top-down坐标系中 y1 更大)
    pdf_x1 = x1
    pdf_y1 = page_height - y0  # 顶部 y (top-down坐标系中 y0 更小)
    
    rect_x = pdf_x0
    rect_y = pdf_y0
    rect_w = pdf_x1 - pdf_x0
    rect_h = pdf_y1 - pdf_y0
    
    if rotation == 0:
        rect = [rect_x, rect_y, rect_w, rect_h]
    elif rotation == 90:
        # TODO: 如果需要处理旋转的PDF，这里需要更复杂的逻辑
         pass
    
    return [rect_x, rect_y, rect_w, rect_h]

def draw_bbox_with_number(page_blocks, page, c, fill_config=False):
    # 确保获取正确的宽高
    cropbox = page.cropbox
    page_width = float(cropbox[2]) - float(cropbox[0])
    page_height = float(cropbox[3]) - float(cropbox[1])
    
    for i, block in enumerate(page_blocks):
        bbox = block.get('bbox')
        block_type = block.get('type', 'default')
        
        if not bbox or len(bbox) != 4:
            continue
            
        rgb = COLOR_MAP.get(block_type, COLOR_MAP["default"])
        new_rgb = [float(color) / 255 for color in rgb]
            
        x0_n, y0_n, x1_n, y1_n = bbox
        
        # 从归一化坐标 (左上角原点) 转换为 PDF 坐标 (左下角原点)
        x = x0_n * page_width
        y = page_height - (y1_n * page_height)
        w = (x1_n - x0_n) * page_width
        h = (y1_n - y0_n) * page_height
        
        rect = [x, y, w, h]
        
        # 绘制矩形
        if fill_config:
            c.setFillColorRGB(*new_rgb, 0.3)
            c.rect(rect[0], rect[1], rect[2], rect[3], stroke=0, fill=1)
        else:
            c.setStrokeColorRGB(*new_rgb)
            c.rect(rect[0], rect[1], rect[2], rect[3], stroke=1, fill=0)

        # 在框外绘制序号
        # Mineru 原始风格逻辑参考
        
        c.setFillColorRGB(*new_rgb, 1.0)
        c.setFontSize(size=10)
        
        c.saveState()
        # 位置: 框的右侧，靠近顶部
        number_x = rect[0] + rect[2] + 2
        number_y = rect[1] + rect[3] - 10
        
        # 边界检查：如果超出页面右边缘，画在左侧
        if number_x > page_width - 15:
            number_x = rect[0] - 15
            
        c.translate(number_x, number_y)
        c.drawString(0, 0, str(i + 1))
        c.restoreState()
        
    return c

def draw_layout_bbox(page_blocks_list, pdf_path, output_path):
    """
    在PDF上绘制布局边界框。
    
    Args:
        page_blocks_list: 字典列表，每个字典包含一页的 'blocks'。
                          预期格式来自 local_parser.py: 
                          {'page_num': 1, 'blocks': [...], ...}
        pdf_path: 原始PDF路径
        output_path: 保存标注后PDF的路径
    """
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # 按页码排序以确保对齐
        sorted_page_blocks = sorted(page_blocks_list, key=lambda x: x['page_num'])
        
        # 映射页码到块列表以便访问
        blocks_map = {item['page_num'] - 1: item['blocks'] for item in sorted_page_blocks} # page_num 是 1-based
        
        for i, page in enumerate(reader.pages):
            # 获取当前页的块
            blocks = blocks_map.get(i, [])
            
            # 过滤出有 bbox 的有效块，并排除 LIST 类型以避免重叠
            # 排除 ABANDON 类型
            # 排除 LIST 类型 (通常包含其他文本块，导致视觉重叠和重复计数)
            valid_blocks = [
                b for b in blocks 
                if 'bbox' in b 
                and b.get('type') not in [BlockType.LIST, BlockType.ABANDON]
            ]
            
            if not valid_blocks:
                writer.add_page(page)
                continue
            
            cropbox = page.cropbox
            page_width = float(cropbox[2]) - float(cropbox[0])
            page_height = float(cropbox[3]) - float(cropbox[1])
            
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))
            
            c = draw_bbox_with_number(valid_blocks, page, c, fill_config=False)
            
            c.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            
            if len(overlay_pdf.pages) > 0:
                page.merge_page(overlay_pdf.pages[0])
            
            writer.add_page(page)
            
        with open(output_path, "wb") as f:
            writer.write(f)
            
        return output_path
        
    except Exception as e:
        logger.error(f"绘制布局bbox失败: {e}")
        return None
