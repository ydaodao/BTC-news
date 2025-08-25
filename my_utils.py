


def string_to_bytes(string):
    # 计算字符串的字节数，以K为单位显示
    return round(len(string.encode('utf-8')) / 1024, 0)