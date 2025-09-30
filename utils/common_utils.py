import pyperclip
import os
import re

def string_to_bytes(string):
    # 计算字符串的字节数，以K为单位显示
    return round(len(string.encode('utf-8')) / 1024, 0)

def copy_to_clipboard(string):
    # 将字符串复制到剪贴板
    pyperclip.copy(string)
    print("已将字符串复制到剪贴板")

def read_file_safely(file_path, description):
    """安全读取文件内容"""
    try:
        if not os.path.exists(file_path):
            print(f"警告: {description}文件不存在: {file_path}")
            return ""
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        if not content:
            print(f"警告: {description}文件为空: {file_path}")
            return ""
        
        print(f"成功读取{description}: {file_path} (长度: {len(content)} 字符)")
        return content
    except Exception as e:
        print(f"读取{description}失败: {e}")
        return ""

def clean_zero_width_chars(text):
    """
    清理字符串中的零宽字符和其他不可见Unicode字符
    
    Args:
        text: 需要清理的字符串
        
    Returns:
        str: 清理后的字符串
    """
    if not text:
        return text
    
    # 定义需要清理的零宽字符范围
    zero_width_chars = [
        '\u200b',  # 零宽空格
        '\u200c',  # 零宽非连接符
        '\u200d',  # 零宽连接符
        '\ufeff',  # 零宽非断空格 (BOM)
        '\u2060',  # 零宽非断空格
        '\u2061',  # 函数应用
        '\u2062',  # 不可见乘号
        '\u2063',  # 不可见分隔符
        '\u2064',  # 不可见加号
        '\u206a',  # 不可见乘号
        '\u206b',  # 不可见分隔符
        '\u206c',  # 不可见分隔符
        '\u206d',  # 不可见分隔符
        '\u206e',  # 不可见分隔符
        '\u206f',  # 不可见分隔符
        '\u202a',  # 左到右嵌入
        '\u202b',  # 右到左嵌入
        '\u202c',  # 弹出方向格式化
        '\u202d',  # 左到右重写
        '\u202e',  # 右到左重写
    ]
    
    # 清理零宽字符
    for char in zero_width_chars:
        text = text.replace(char, '')
    
    # 清理其他常见的不可见字符
    # 清理控制字符（除了换行、回车、制表符）
    cleaned_text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # 去除前后空格和多余的空格
    cleaned_text = cleaned_text.strip()
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    return cleaned_text