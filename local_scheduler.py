import asyncio
import schedule
import time
from datetime import datetime
from main import main

def run_task(task_name):
    """执行定时任务"""
    print(f"\n[{datetime.now()}] 执行任务: {task_name}")
    asyncio.run(main(task_name))

def start_local_scheduler():
    """启动本地定时任务"""
    # RSS抓取时间点
    schedule.every().day.at("02:00").do(run_task, "rss")
    schedule.every().day.at("10:00").do(run_task, "rss")
    schedule.every().day.at("18:00").do(run_task, "rss")
    
    # 摘要推送时间点
    schedule.every().day.at("20:00").do(run_task, "summary_push")
    
    print("本地定时任务已启动...")
    print("定时任务配置:")
    print("- RSS抓取和内容更新：每天 02:00, 10:00, 18:00")
    print("- 摘要生成和推送：每天 20:00")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n定时任务已停止")

if __name__ == "__main__":
    start_local_scheduler()