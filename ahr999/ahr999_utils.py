import numpy as np
from datetime import datetime, timedelta, date

# 预测某一天的价格
def forecast_price(year=None, month=None, day=None, version='old'):
    # 计算某一天到2009年1月3日的间隔天数
    target_dt = datetime.now()
    if year:
        target_dt = datetime(year, month, day)
    delta = target_dt - datetime(2009, 1, 3)

    # ahr999的函数式
    price = 0
    if version == 'old':
        price = 10**(5.84*np.log10(delta.days) - 17.01)
    elif version == 'new':
        price = 10**(5.418*np.log10(delta.days) - 15.54)

    # 预测价格
    return round(price, 4)