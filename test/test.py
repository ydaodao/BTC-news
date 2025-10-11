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

print([1,2,3,4][1:])

