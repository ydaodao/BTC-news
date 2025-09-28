from datetime import date

def days_between(start_date: date, end_date: date) -> int:
    """
    计算两个日期之间的天数差
    :param start_date: datetime.date 开始日期
    :param end_date: datetime.date 结束日期
    :return: 相差的天数（end_date - start_date）
    """
    return (end_date - start_date).days


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


    between_days = days_between(date.today(), date(2035, 1, 1))
    between_years = between_days // 365
    end_this_year = date(date.today().year, 12, 31)
    
    print(f'十年倒计时 — {between_days}天（距离2035年还有{between_years}年{days_between(date.today(), end_this_year)}天）')
