from datetime import datetime, timezone, timedelta # 新增：用于处理时区
import re


# beijing_tz = timezone(timedelta(hours=8))
# now = datetime.now(beijing_tz)

# week_day_ago = now - timedelta(days=7)
# week_start_md = f"{week_day_ago.month}.{week_day_ago.day}"
# week_end_md = f"{now.month}.{now.day}"

# title = '【加密货币周报:xxxxx】'.replace("加密货币周报:", f"加密货币周报({week_start_md}-{week_end_md})：").strip('【】')

# print(title)

# print(week_start_md)

# print(re.match(r'^\*\*参考\*\*.*?', '**参考**；'))
# print(re.match(r'^\*\*参考\*\*.*?', '**参考**；；；；'))
# print(re.match(r'^\*\*参考\*\*.*?', '**参考**'))

# Python 示例 (需要安装 pycryptodome)
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64

encrypted_data = "3WNC2/SIZwZbm+gt9z244QV5uBNvdLmD8h5T7mtFZUi8dFPzTnc1UMT3ZIfD/i0yPpccs4XK5Ld/49kLLh6S0D5P6HeXPT7REy/3Hl28NYnwRKFdUYCDqhVcNIayDG0zrZGqhjXX+22QKNNVNVhMHUgudf9ikgts8q2fOfqrLX/AtI6o3TD45XUo7qcrlRMUJHtxBsUEF0FFQ4clbC9/4ITgRLhcB4zUKjBuPMOUegk="
key_hex = "1f68efd73f8d4921acc0dead41dd39bc"
iv_hex = "d7667823f95b498f80459586111f1854"

# 1. Base64 解码
ciphertext = base64.b64decode(encrypted_data)

# 2. 转换为字节数组
key = bytes.fromhex(key_hex)
iv = bytes.fromhex(iv_hex)

# 3. 创建解密器
cipher = AES.new(key, AES.MODE_CBC, iv)

# 4. 解密并移除填充
decrypted_bytes = cipher.decrypt(ciphertext)
plaintext = unpad(decrypted_bytes, AES.block_size).decode('utf-8')

# 5. 打印结果
print(plaintext)

