import pyperclip

def string_to_bytes(string):
    # 计算字符串的字节数，以K为单位显示
    return round(len(string.encode('utf-8')) / 1024, 0)

def copy_to_clipboard(string):
    # 将字符串复制到剪贴板
    pyperclip.copy(string)
    print("已将字符串复制到剪贴板")