from datetime import datetime, timezone, timedelta # 新增：用于处理时区


beijing_tz = timezone(timedelta(hours=8))
now = datetime.now(beijing_tz)

week_day_ago = now - timedelta(days=7)
week_start_md = week_day_ago.strftime('%m.%d')
week_end_md = now.strftime('%m.%d')

title = '【加密货币周报:xxxxx】'.replace("加密货币周报:", f"加密货币周报({week_start_md}-{week_end_md})：").strip('【】')

print(title)
