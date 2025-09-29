import schedule
import time
from datetime import datetime, timedelta
import sys
import os
import asyncio
import pyautogui
import utils.powershell_utils as powershell_utils
from playwright.sync_api import sync_playwright
from main import main
from croniter import croniter
import threading
from utils.feishu_robot_utils import push_text_to_robot, push_wxqrcode_to_robot
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'

class CronScheduler:
    """支持 cron 语法的定时任务调度器"""
    
    def __init__(self):
        self.jobs = []
        self.running = False
        
    def add_cron_job(self, cron_expression, job_func, job_name=None, *args, **kwargs):
        """
        添加 cron 定时任务
        
        Args:
            cron_expression (str): cron 表达式，格式：分 时 日 月 周
                                  例如：'0 9 * * *' 表示每天9点执行
                                       '*/5 * * * *' 表示每5分钟执行
                                       '0 9,21 * * *' 表示每天9点和21点执行
            job_func (callable): 要执行的函数
            job_name (str): 任务名称（可选）
            *args, **kwargs: 传递给job_func的参数
        """
        try:
            # 验证 cron 表达式
            cron = croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
            
            job = {
                'cron_expression': cron_expression,
                'job_func': job_func,
                'job_name': job_name or job_func.__name__,
                'args': args,
                'kwargs': kwargs,
                'next_run': next_run,
                'cron_iter': croniter(cron_expression, datetime.now())
            }
            
            self.jobs.append(job)
            print(f"已添加 cron 任务: {job['job_name']} ({cron_expression})")
            print(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"添加 cron 任务失败: {e}")
            push_text_to_robot(f"添加 cron 任务失败: {e}")
    
    def remove_job(self, job_name):
        """移除指定名称的任务"""
        self.jobs = [job for job in self.jobs if job['job_name'] != job_name]
        print(f"已移除任务: {job_name}")
    
    def list_jobs(self):
        """列出所有任务"""
        if not self.jobs:
            print("当前没有定时任务")
            return
            
        print("\n当前定时任务列表:")
        print("-" * 80)
        for job in self.jobs:
            print(f"任务名称: {job['job_name']}")
            print(f"Cron表达式: {job['cron_expression']}")
            print(f"下次执行: {job['next_run'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
    
    def run_pending(self):
        """检查并执行到期的任务"""
        now = datetime.now()
        
        for job in self.jobs:
            if now >= job['next_run']:
                try:
                    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 执行 cron 任务: {job['job_name']}")
                    
                    # 执行任务
                    if asyncio.iscoroutinefunction(job['job_func']):
                        asyncio.run(job['job_func'](*job['args'], **job['kwargs']))
                    else:
                        job['job_func'](*job['args'], **job['kwargs'])
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务 {job['job_name']} 执行完成")
                    
                except Exception as e:
                    error_msg = f"执行 cron 任务 {job['job_name']} 失败: {e}"
                    print(error_msg)
                    push_text_to_robot(error_msg)
                
                # 修改这里：重新创建croniter对象，使用当前时间作为基准
                job['cron_iter'] = croniter(job['cron_expression'], datetime.now())
                # 计算下次执行时间
                job['next_run'] = job['cron_iter'].get_next(datetime)
                print(f"任务 {job['job_name']} 下次执行时间: {job['next_run'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    def start(self):
        """启动调度器"""
        self.running = True
        print("Cron 调度器已启动")
        
        try:
            while self.running:
                self.run_pending()
                time.sleep(30)  # 每30秒检查一次
        except KeyboardInterrupt:
            print("\nCron 调度器已停止")
        except Exception as e:
            error_msg = f"Cron 调度器运行出错: {e}"
            print(error_msg)
            push_text_to_robot(error_msg)
    
    def stop(self):
        """停止调度器"""
        self.running = False

# 创建全局 cron 调度器实例
cron_scheduler = CronScheduler()

def keep_gzh_online_task():
    """保持公众号在线任务"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行保持公众号在线任务")

    from send_to_weixin.to_gzh_with_pw import keep_gzh_online
    success, msg, qrcode_download_url = keep_gzh_online()
    if success:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    else:
        if qrcode_download_url:
            push_wxqrcode_to_robot("需重新登录公众号！", qrcode_download_url)
        else:
            push_text_to_robot(msg)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def screenshot_task():
    # 检查桌面是否还能截图的任务
    try:
        # 设置pyautogui
        pyautogui.FAILSAFE = False
        # 截图
        screenshot = pyautogui.screenshot()
        print(f"截图成功！尺寸：{screenshot.size}")
        if not screenshot:
            push_text_to_robot("截图失败！")
    except Exception as e:
        print(f"截图失败：{e}")
        print(f"错误类型：{type(e).__name__}")
        push_text_to_robot(f"截图失败！错误信息：{str(e)}")

def check_cdp_connection():
    """检查CDP连接状态，带重试机制"""
    max_retries = 3  # 最大重试次数
    retry_delay = 5  # 重试间隔（秒）
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"CDP连接尝试 {attempt}/{max_retries}")
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                context = browser.contexts[0]
                page = context.pages[0]
                title = page.title()
                print(f"CDP连接成功，页面标题: {title}")
                return True  # 连接成功，返回
        except Exception as e:
            print(f"CDP连接尝试 {attempt} 失败：{e}")
            print(f"错误类型：{type(e).__name__}")
            
            if attempt < max_retries:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                # 所有重试都失败了，发送通知
                error_msg = f"CDP连接失败（已重试{max_retries}次）！错误信息：{str(e)}"
                push_text_to_robot(error_msg)
                print(f"所有重试均失败: {error_msg}")
                return False

def run_main_task(task_name):
    """执行主定时任务"""
    print(f"\n[{datetime.now()}] 执行任务: {task_name}")
    result = powershell_utils.git_pull()
    if result['success']:
        asyncio.run(main(task_name))
        result = powershell_utils.git_commit(f"{task_name}")
        if result['success']:
            result = powershell_utils.git_push()
            if result['success']:
                print("git push 成功")
            else:
                push_text_to_robot(f"git push 失败！错误信息：{result['stderr']}")
                print(f"git push 失败！错误信息：{result['stderr']}")
        else:
            push_text_to_robot(f"git commit 失败！错误信息：{result['stderr']}")
            print(f"git commit 失败！错误信息：{result['stderr']}")
    else:
        push_text_to_robot(f"git pull 失败！错误信息：{result['stderr']}")
        print(f"git pull 失败！错误信息：{result['stderr']}")

def setup_cron_jobs():
    """设置 cron 定时任务"""
    
    # 使用 cron 语法设置任务
    # 格式：分 时 日 月 周 (0-59 0-23 1-31 1-12 0-7，其中0和7都表示周日)
    
    # 每天21:00执行截图任务
    cron_scheduler.add_cron_job('0 21 * * *', screenshot_task, '截图检查任务')
    
    # 每天21:05执行CDP连接检查
    cron_scheduler.add_cron_job('5 21 * * *', check_cdp_connection, 'CDP连接检查')
    
    # 每天7:00、12:00、21:00执行保持公众号在线任务
    cron_scheduler.add_cron_job('0 6,12,19 * * *', keep_gzh_online_task, '保持公众号在线')

    # 每周一、二、三、四、五的7:00执行 日报任务
    cron_scheduler.add_cron_job('0 7 * * 1,2,3,4,5', lambda: run_main_task("daily_news"), '日报任务')

    # 每周日的7:00执行 周报任务
    cron_scheduler.add_cron_job('0 7 * * 7', lambda: run_main_task("weekly_news"), '周报任务')

def start_cron_scheduler():
    """启动 cron 调度器"""
    setup_cron_jobs()
    cron_scheduler.list_jobs()
    cron_scheduler.start()

if __name__ == "__main__":
    if LOCAL_DEV:
        # powershell_utils.run_powershell_command("Get-Process")
        keep_gzh_online_task()
        # run_main_task('weekly_news')
    else:
        start_cron_scheduler()     # 使用新的 cron 调度器
