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
    today = date.today()
    end_2035 = date(2035, 12, 31)

    print(f"今天到2035年末还有 {days_between(today, end_2035)} 天")
