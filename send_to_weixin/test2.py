import time
from playwright.sync_api import sync_playwright
from to_gzh_with_pw import refresh_page
from to_gzh_with_ui import find_icon_with_prefix, hover_icon_with_prefix

with sync_playwright() as p:
    time.sleep(3)
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    start_time = time.time()
    print(f"程序开始时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    while True:
        if refresh_page(context, "公众号"):
            if hover_icon_with_prefix("wx_content_management", 3):
                time.sleep(60*60*6)
            else:
                # 计算运行时间
                elapsed_time = time.time() - start_time
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)
                print(f"公众号保持登录失败！程序运行了：{hours}小时{minutes}分钟{seconds}秒")
                break
