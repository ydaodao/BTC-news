from datetime import date, datetime, timedelta, timezone

def days_between(start_date: date, end_date: date) -> int:
    """
    计算两个日期之间的天数差
    :param start_date: datetime.date 开始日期
    :param end_date: datetime.date 结束日期
    :return: 相差的天数（end_date - start_date）
    """
    return (end_date - start_date).days

def get_weekday(date_str = None) -> str:
    """
    根据日期字符串返回中文星期
    :param date_str: 日期字符串，例如 "2025-10-15"
    :return: 对应的中文星期，例如 "星期三"
    """
    # 解析日期
    if date_str:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        date_obj = datetime.now()
    
    # 映射表（weekday(): 0~6 -> 周一~周日）
    week_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    # 返回结果
    return week_map[date_obj.weekday()]


# 示例用法
if __name__ == "__main__":
    # today = date.today()
    # end_this_year = date(today.year, 12, 31)
    # end_2035 = date(2035, 12, 31)

    # # print(f"今天到2035年末还有 {days_between(today, end_2035)} 天")
    # print(f"今天是2024年{today.month}月{today.day}日")
    # print(f"距离2035年还有 {days_between(today, end_2035)} 天")
    # between_year = days_between(today, end_this_year)
    # print(f"距离2024年结束还有 {between_year} 天")

    # print(f"距离2035年还有 {days_between(today, end_2035) // 365} 年 {days_between(today, end_2035) % 365} 天")


    # between_days = days_between(date.today(), date(2035, 1, 1))
    # between_years = between_days // 365
    # end_this_year = date(date.today().year, 12, 31)
    
    # print(f'十年倒计时 — {between_days}天（距离2035年还有{between_years}年{days_between(date.today(), end_this_year)}天）')
    # print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 示例
    print(get_weekday())  # 输出：星期三
    print(get_weekday("2035-12-31"))  # 输出：星期一