import schedule
import time
from datetime import datetime
import sys
import os
import asyncio
import pyautogui
import utils.powershell_utils
from playwright.sync_api import sync_playwright
from main import main
# 添加项目路径
sys.path.append(os.path.dirname(__file__))
from to_feishu_robot import push_text_to_feishu

def keep_gzh_online_task():
    """保持公众号在线任务"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行保持公众号在线任务")
        # 导入并执行keep_gzh_online.py的逻辑
        from send_to_weixin.to_gzh_with_pw import active_page
        from send_to_weixin.to_gzh_with_ui import find_icon_with_prefix
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            if active_page(context, "公众号", "https://mp.weixin.qq.com/", refresh=True):
                if find_icon_with_prefix("wx_content_management"):
                    print("保持公众号在线成功")
                    return True
                else:
                    push_text_to_feishu("保持公众号在线失败！未找到内容管理图标")
                    print("保持公众号在线失败！未找到内容管理图标")
                    return False
            else:
                push_text_to_feishu("公众号页面刷新失败！")
                print("公众号页面刷新失败！")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务完成")
    except Exception as e:
        push_text_to_feishu(f"保持公众号在线任务失败！错误信息：{str(e)}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务失败: {str(e)}")

def screenshot_task():
    # 检查桌面是否还能截图的任务
    try:
        # 设置pyautogui
        pyautogui.FAILSAFE = False
        # 截图
        screenshot = pyautogui.screenshot()
        print(f"截图成功！尺寸：{screenshot.size}")
        if not screenshot:
            push_text_to_feishu("截图失败！")
    except Exception as e:
        print(f"截图失败：{e}")
        print(f"错误类型：{type(e).__name__}")
        push_text_to_feishu(f"截图失败！错误信息：{str(e)}")

def check_cdp_connection():
    """检查CDP连接状态"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            print(page.title())
    except Exception as e:
        print(f"CDP连接检查失败：{e}")
        print(f"错误类型：{type(e).__name__}")
        push_text_to_feishu(f"CDP连接失败！错误信息：{str(e)}")

def run_main_task(task_name):
    """执行定时任务"""
    print(f"\n[{datetime.now()}] 执行任务: {task_name}")
    asyncio.run(main(task_name))

def start_local_scheduler():
    """启动本地定时任务"""

    # 设置定时任务
    schedule.every().day.at("21:00").do(screenshot_task)
    schedule.every().day.at("21:05").do(check_cdp_connection)
    schedule.every().day.at("07:30").do(keep_gzh_online_task)
    schedule.every().day.at("21:30").do(keep_gzh_online_task)



    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n定时任务已停止")
    except Exception as e:
        print(f"定时任务运行出错：{e}")
        push_text_to_feishu(f"定时任务运行出错！错误信息：{str(e)}")

if __name__ == "__main__":
    # start_local_scheduler()
    powershell_utils.run_powershell_command("Get-Process")