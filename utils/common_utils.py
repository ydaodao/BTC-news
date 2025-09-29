import pyperclip
import os

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