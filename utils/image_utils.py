from PIL import Image, ImageDraw, ImageFont
import os
import re

def parse_markdown_text(text):
    """
    解析简单的markdown格式文本
    支持：**粗体**、*斜体*、# 标题、- 列表
    
    Returns:
        list: [(text, style_dict), ...] 格式的列表
    """
    lines = text.split('\n')
    parsed_lines = []
    
    for line in lines:
        line = line.strip()
        style = {'bold': False, 'italic': False, 'is_title': False, 'is_list': False, 'font_size_multiplier': 1.0}
        
        # 处理标题 (# 开头)
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            line = line.lstrip('# ').strip()
            style['is_title'] = True
            style['bold'] = True
            # 根据标题级别调整字体大小
            style['font_size_multiplier'] = max(1.5 - (level - 1) * 0.2, 1.0)
        
        # 处理列表 (- 开头)
        elif line.startswith('-'):
            line = '• ' + line[1:].strip()  # 替换为圆点
            style['is_list'] = True
        
        # 处理粗体 **text**
        if '**' in line:
            if line.count('**') >= 2:
                style['bold'] = True
                line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
        
        # 处理斜体 *text*
        if '*' in line and not style['bold']:
            if line.count('*') >= 2:
                style['italic'] = True
                line = re.sub(r'\*(.*?)\*', r'\1', line)
        
        parsed_lines.append((line, style))
    
    return parsed_lines

def text_to_image(text, width=800, height=600, font_size=24, font_color=(0, 0, 0), 
                  font_path=None, text_align='center', vertical_align='center', 
                  line_spacing=5, support_markdown=False):
    """
    将文字生成指定尺寸的PNG图片
    
    Args:
        text (str): 要生成的文字内容
        width (int): 图片宽度，默认800
        height (int): 图片高度，默认600
        font_size (int): 字体大小，默认24
        font_color (tuple): 字体颜色RGB，默认黑色(0, 0, 0)
        font_path (str): 字体文件路径，None则使用默认字体
        text_align (str): 水平对齐方式：'left', 'center', 'right'
        vertical_align (str): 垂直对齐方式：'top', 'center', 'bottom'
        line_spacing (int): 行间距，默认5像素
        support_markdown (bool): 是否支持markdown格式，默认False
    
    Returns:
        PIL.Image: 生成的图片对象
    """
    # 创建透明背景的图片
    image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # 设置字体
    def get_font(size, bold=False, italic=False):
        try:
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            else:
                # 尝试使用系统默认字体
                try:
                    import platform
                    
                    system = platform.system()
                    
                    if system == "Windows":
                        # Windows字体路径
                        if bold:
                            return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", size)  # 微软雅黑粗体
                        else:
                            return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", size)
                    elif system == "Linux":
                        # Linux (Ubuntu)字体路径
                        font_paths = []
                        if bold:
                            font_paths = [
                                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
                            ]
                        else:
                            font_paths = [
                                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
                            ]
                        
                        for font_path in font_paths:
                            if os.path.exists(font_path):
                                return ImageFont.truetype(font_path, size)
                    
                    # 如果没有找到合适的字体，使用默认字体
                    return ImageFont.load_default()
                except:
                    try:
                        # 备用字体
                        font_name = "arialbd.ttf" if bold else "arial.ttf"
                        return ImageFont.truetype(font_name, size)
                    except:
                        # 使用PIL默认字体
                        return ImageFont.load_default()
        except Exception as e:
            print(f"字体加载失败，使用默认字体: {e}")
            return ImageFont.load_default()
    
    # 解析文本
    if support_markdown:
        parsed_lines = parse_markdown_text(text)
    else:
        lines = text.split('\n')
        parsed_lines = [(line, {'bold': False, 'italic': False, 'is_title': False, 'is_list': False, 'font_size_multiplier': 1.0}) for line in lines]
    
    # 计算文本总高度
    line_data = []
    total_text_height = 0
    
    for line_text, style in parsed_lines:
        current_font_size = int(font_size * style['font_size_multiplier'])
        font = get_font(current_font_size, style['bold'], style['italic'])
        
        bbox = draw.textbbox((0, 0), line_text, font=font)
        line_height = bbox[3] - bbox[1]
        
        line_data.append({
            'text': line_text,
            'font': font,
            'height': line_height,
            'style': style
        })
        
        total_text_height += line_height
    
    # 添加行间距
    if len(line_data) > 1:
        total_text_height += line_spacing * (len(line_data) - 1)

    # 计算起始Y坐标
    if vertical_align == 'top':
        start_y = 10
    elif vertical_align == 'bottom':
        start_y = height - total_text_height - 10
    else:  # center
        start_y = (height - total_text_height) / 2 - 10 # 使用浮点除法而不是整除
    
    # 绘制每一行文字
    current_y = start_y
    for i, line_info in enumerate(line_data):
        line_text = line_info['text']
        font = line_info['font']
        style = line_info['style']
        
        # 计算文本宽度
        bbox = draw.textbbox((0, 0), line_text, font=font)
        text_width = bbox[2] - bbox[0]
        
        # 计算X坐标
        if text_align == 'left' or style['is_list']:
            x = 10
            if style['is_list']:
                x += 20  # 列表项缩进
        elif text_align == 'right':
            x = width - text_width - 10
        else:  # center
            x = (width - text_width) // 2
        
        # 绘制文字
        draw.text((int(x), int(current_y)), line_text, fill=font_color, font=font)
        
        # 更新Y坐标（最后一行不加行间距）
        if i < len(line_data) - 1:
            current_y += line_info['height'] + line_spacing
        else:
            current_y += line_info['height']
    
    return image

def save_text_image(text, output_path, width=800, height=600, **kwargs):
    """
    将文字生成图片并保存为PNG文件
    
    Args:
        text (str): 要生成的文字内容
        output_path (str): 输出文件路径
        width (int): 图片宽度
        height (int): 图片高度
        **kwargs: 其他参数传递给text_to_image函数
    
    Returns:
        bool: 保存是否成功
    """
    try:
        image = text_to_image(text, width, height, **kwargs)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存为PNG格式
        image.save(output_path, 'PNG')
        print(f"图片已保存到: {output_path}")
        return True
    except Exception as e:
        print(f"保存图片失败: {e}")
        return False

def merge_images(image_configs, output_size=None, output_path=None):
    """
    将多张图片合并为一张图片
    
    Args:
        image_configs (list): 图片配置列表，每个元素为字典，格式：
                             [{'path': '图片路径', 'position': '位置'}, ...]
                             按层叠顺序排列（第一个在最下层）
                             position支持字符串或(x, y)坐标：
                             'top-left', 'top-center', 'top-right',
                             'center-left', 'center', 'center-right',
                             'bottom-left', 'bottom-center', 'bottom-right'
        output_size (tuple): 输出图片尺寸 (width, height)，None则使用第一张图片的尺寸
        output_path (str): 输出文件路径，None则返回PIL Image对象
    
    Returns:
        PIL.Image or bool: 如果指定output_path则返回保存成功状态，否则返回合并后的图片对象
    """
    if not image_configs:
        raise ValueError("图片配置列表不能为空")
    
    # 加载所有图片
    images = []
    positions = []
    
    for config in image_configs:
        try:
            # 支持两种格式：字典格式或直接路径
            if isinstance(config, dict):
                path = config.get('path')
                position = config.get('position', 'center')
            else:
                # 兼容旧格式
                path = config
                position = 'center'
            
            if isinstance(path, str):
                img = Image.open(path)
            else:
                img = path  # 直接传入PIL Image对象
            
            # 转换为RGBA模式以支持透明度
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            images.append(img)
            positions.append(position)
            
        except Exception as e:
            print(f"加载图片失败 {config}: {e}")
            continue
    
    if not images:
        raise ValueError("没有成功加载任何图片")
    
    # 确定输出尺寸 - 默认使用第一张图片的尺寸
    if output_size is None:
        output_size = images[0].size
    
    # 创建输出画布
    result = Image.new('RGBA', output_size, (255, 255, 255, 0))
    
    # 计算位置的辅助函数
    def calculate_position(img_size, canvas_size, position):
        img_w, img_h = img_size
        canvas_w, canvas_h = canvas_size
        
        if isinstance(position, tuple) and len(position) == 2:
            # 直接指定坐标
            return position
        
        # 字符串位置映射
        position_map = {
            'top-left': (0, 0),
            'top-center': ((canvas_w - img_w) // 2, 0),
            'top-right': (canvas_w - img_w, 0),
            'center-left': (0, (canvas_h - img_h) // 2),
            'center': ((canvas_w - img_w) // 2, (canvas_h - img_h) // 2),
            'center-right': (canvas_w - img_w, (canvas_h - img_h) // 2),
            'bottom-left': (0, canvas_h - img_h),
            'bottom-center': ((canvas_w - img_w) // 2, canvas_h - img_h),
            'bottom-right': (canvas_w - img_w, canvas_h - img_h)
        }
        
        return position_map.get(position, (0, 0))
    
    # 按顺序合并图片（第一个在最下层）
    for i, (img, position) in enumerate(zip(images, positions)):
        x, y = calculate_position(img.size, output_size, position)
        
        # 确保坐标不超出画布范围
        x = max(0, min(x, output_size[0] - img.size[0]))
        y = max(0, min(y, output_size[1] - img.size[1]))
        
        # 粘贴图片（支持透明度）
        result.paste(img, (x, y), img)
    
    # 保存或返回结果
    if output_path:
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result.save(output_path, 'PNG')
            print(f"合并图片已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存合并图片失败: {e}")
            return False
    else:
        return result

# 在使用示例部分添加新的示例
if __name__ == "__main__":
    save_text_image(
        text="**加密日报(09.10)**\n机构增持与矿工抛售并存\nAI支付生态初现",
        output_path="./test/image_utils/sample_text.png",
        width=1050,
        height=400,
        line_spacing=40,
        support_markdown=True,
        font_size=70,
        # font_color=(0, 0, 0),  # 黑色
        font_color=(255, 255, 255),  # 白色
        text_align='left',
        vertical_align='center'
    )

    # 合并图片
    image_configs = [
        {'path': './test/image_utils/background.png', 'position': 'center'},
        {'path': './test/image_utils/sample_text.png', 'position': 'center-right'}
    ]

    result = merge_images(image_configs, output_path='./test/image_utils/merged.png')