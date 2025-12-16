import feedparser
import requests
import json
import os
import asyncio
from crawl4ai import AsyncWebCrawler
from openai import OpenAI  # 火山引擎的客户端基于 OpenAI 库
from utils import date_utils
from web_crawler import multi_cralwer
import sqlite3  # 新增：用于数据库操作
from datetime import datetime, timezone, timedelta # 新增：用于处理时区
import utils.feishu_robot_utils as feishu_robot_utils  # 新增：飞书机器人工具
from dotenv import load_dotenv
from llm_doubao import generate_news_summary, generate_news_summary_chunked, generate_title_and_summary_and_content
from db_management import open_or_create_rss_db, save_rss, fetch_news_by_published, update_news_content
from ahr999.ahr_web_crawler import crawler_and_save_ahr999_data

# 加载环境变量
load_dotenv()

# --- 配置部分 ---
# 替换为您的谷歌快讯RSS源链接
RSS_URL = "https://www.google.com.hk/alerts/feeds/08373742189599090702/14816707195864267476"

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
VOLCENGINE_API_KEY = os.getenv('VOLCENGINE_API_KEY')
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN')
LOCAL_DEV = os.getenv('LOCAL_DEV')
ALI_WEBSERVICE_URL = 'http://127.0.0.1:5000' if LOCAL_DEV else 'http://39.107.72.186:5000'

# 如果环境变量未设置，给出明确的错误提示
if not VOLCENGINE_API_KEY:
    raise ValueError("请设置 VOLCENGINE_API_KEY 环境变量")
if not PUSHPLUS_TOKEN:
    raise ValueError("请设置 PUSHPLUS_TOKEN 环境变量")

# VPN 代理配置：本地开发时使用代理，GitHub Actions 中不使用
PROXIES = None
if os.getenv('LOCAL_DEV'):  # 本地开发环境标志
    PROXIES = {
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890'
    }

async def fetch_rss_news():
    """从 RSS 源抓取新闻并存储到数据库"""
    print("开始抓取谷歌快讯...")
    open_or_create_rss_db()
    
    try:
        # 根据环境决定是否使用代理
        response = requests.get(RSS_URL, proxies=PROXIES if PROXIES else None)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        
        if not feed.entries:
            print("RSS源中没有新内容。")
            return 0
            
        for entry in feed.entries:
            save_rss(entry)
        
        print(f"成功抓取 {len(feed.entries)} 条新闻并存入数据库。")
        return len(feed.entries)
        
    except Exception as e:
        print(f"抓取RSS源或数据库操作失败：{e}")
        return 0

async def fetch_news_content(start_date: str, end_date: str):
    """
    处理指定时间范围内的新闻正文
    """
    print("开始从数据库中读取新闻...")
    news_list = fetch_news_by_published(start_date, end_date)
    
    if not news_list:
        print("指定日期范围内没有找到新闻。")
        return False

    print(f"成功从数据库中读取 {len(news_list)} 条新闻。")

    print("开始异步提取新闻正文...")
    for item in news_list:
        print(f"正在处理新闻：{item['id']} {item['title']}")
        result = await multi_cralwer(item['link'])
        if result:
            md_text, real_url = result
            # 无论是否抓取到内容，只要有 real_url 就更新数据库
            news_id = update_news_content(item['link'], md_text, real_url)
            if md_text:
                print(f"已更新新闻内容：(ID: {news_id}) Title：{item['title']}")
            if real_url:
                print(f"已更新真实URL：(ID: {news_id}) Real_URL：{real_url}")

        else:
            print(f"无法抓取新闻内容：{item['id']} {item['title']}")
    
    return True

async def push_daily_news_to_feishu(content=None, title=None, summary=None, daily_end_md=None, docs_url=None, wx_preview_page_url=None):
    """
    直接推送内容到飞书机器人（不依赖pushplus）
    """
    if not title:
        print("错误：标题不能为空")
        return
    if not content:
        print("错误：内容不能为空")
        return
    
    # 对内容进行JSON转义处理
    import json as json_module
    title_escaped = json_module.dumps(f"加密日报({daily_end_md})：{title}")[1:-1]  # 去掉首尾引号
    message_content_escaped = json_module.dumps(content)[1:-1]  # 去掉首尾引号

    if not title_escaped:
        print("错误：提取标题失败")
        return
    if not message_content_escaped:
        print("错误：提取内容失败")
        return

    print("开始推送消息到飞书机器人...")
    # 读取飞书消息模板
    template_path = os.path.join(os.path.dirname(__file__), 'send_to_weixin', 'templates', 'daily_news_template.json')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 替换模板中的占位符
    now_md = datetime.now().strftime('%m.%d')
    weekday = date_utils.get_weekday()
    data_str = template_content.replace('{title}', title_escaped) \
                              .replace('{message_content}', message_content_escaped) \
                              .replace('{now_md}', now_md or '') \
                              .replace('{weekday}', weekday or '') \
                              .replace('{docs_url}', docs_url or '') \
                              .replace('{wx_preview_page_url}', wx_preview_page_url or '') \
                              .replace('{regenerate_daily_url}', f"{ALI_WEBSERVICE_URL}/regenerate_daily_news" or '') \
                              .replace('{push_daily_url}', f"{ALI_WEBSERVICE_URL}/push_daily_news?feishu_docx_url={docs_url}" or '')
    data = json.loads(data_str)
    feishu_robot_utils.send_to_robot(data)

async def push_to_wechat(content=None, feishu_mode=True):
    """
    使用 pushplus 服务将内容推送到微信
    如果 content 为空，则尝试从本地文件读取
    """
    if not content:
        # 尝试从本地文件读取内容
        summary_file = os.path.join(os.path.dirname(__file__), "process_files", "latest_summary.md")
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"已从本地文件读取内容: {summary_file}")
        except Exception as e:
            print(f"读取本地文件失败: {e}")
            return

    if not content:
        print("错误：没有可推送的内容")
        return

    print("开始推送消息...")
    # 从内容中提取第一行作为标题
    title = "每日新闻摘要"  # 默认标题
    if content:
        # 按行分割内容
        lines = content.strip().split('\n')
        if lines:
            # 获取第一行并去掉 Markdown 标题符号
            first_line = lines[0].strip()
            if first_line.startswith('# '):
                title = first_line[2:].strip()
                # 将第一行从content中移除
                content = '\n'.join(lines[1:]).strip()
    print(f"使用标题: {title}")

    url = "http://www.pushplus.plus/send"
    
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "markdown"
    }
    
    # 通过pushplus推送到飞书
    if feishu_mode:
        data["channel"] = "webhook"
        data["webhook"] = "feishu001"
        print("将通过pushplus推送到飞书机器人")
    else:
        print("将通过pushplus推送到微信")
    
    try:
        response = requests.post(
            url, 
            json=data,
            headers={'Content-Type': 'application/json'}, 
            # proxies=PROXIES if PROXIES else None,  # 根据环境决定是否使用代理
            timeout=10
        )
        response.raise_for_status()

        # 打印详细的响应信息
        result = response.json()
        print(f"推送响应: {result}")
        
        if result['code'] == 200:
            print("消息推送成功！")
        else:
            print(f"推送失败: {result.get('msg', '未知错误')}")
    except requests.exceptions.RequestException as e:
        print(f"消息推送失败：{e}")

async def main(mode="all"):
    """
    主函数，根据模式执行不同的任务
    :param mode: 执行模式
        - "rss": 抓取RSS并获取内容
        - "daily_news": 生成日报
        - "all": 执行所有步骤
    """
    if not VOLCENGINE_API_KEY:
        print("错误：请先设置环境变量 'ARK_API_KEY' 或在代码中配置您的密钥。")
        return

    # 使用东八区时间，确保与数据库存储的时间一致
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    yesterday = now - timedelta(days=1)
    start_date = yesterday.strftime('%Y-%m-%d %H:%M:%S')
    end_date = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # 为摘要生成设置2天的时间范围
    one_day_ago = now - timedelta(days=1)
    daily_start_date = one_day_ago.strftime('%Y-%m-%d %H:%M:%S')
    daily_end_date = now.strftime('%Y-%m-%d %H:%M:%S')
    daily_end_md = now.strftime('%m.%d')

    # 为摘要生成设置7天的时间范围
    week_day_ago = now - timedelta(days=14)
    week_start_date = week_day_ago.strftime('%Y-%m-%d %H:%M:%S')
    week_end_date = now.strftime('%Y-%m-%d %H:%M:%S')
    week_start_md = f"{week_day_ago.month}.{week_day_ago.day}"
    week_end_md = f"{now.month}.{now.day}"
    
    news_content = None

    if mode in ["rss", "all"]:
        print("\n=== 执行RSS抓取任务 ===")
        # 1. 抓取RSS
        await fetch_rss_news()
        # 2. 获取内容
        await fetch_news_content(start_date, end_date)
        # 3. 更新ahr999
        await crawler_and_save_ahr999_data()

    if mode in ["daily_news", "all"]:
        print("\n=== 生成日报 ===")
        # 1. 生成文章内容
        news_content = await generate_news_summary(daily_start_date, daily_end_date, VOLCENGINE_API_KEY)
        # 2. 生成标题摘要
        # 从内容中提取标题和主体内容
        title, summary = generate_title_and_summary_and_content(news_content)
        if title:
            # 3. 生成飞书文档，生成公众号链接
            from to_feishu_docx import write_to_daily_docx
            docs_url, preview_page_title, preview_page_url = await write_to_daily_docx(news_content, title, summary, daily_end_md)
            if preview_page_url:
                # 4. 推送消息（自动根据环境变量选择推送到微信或飞书）
                # await push_to_wechat(summary)
                await push_daily_news_to_feishu(news_content, title, summary, daily_end_md, docs_url, preview_page_url)
        else:
            print("标题为空，不生成文档")
    
    if mode in ["weekly_news", "all"]:
        print("\n=== 生成周报 ===")
        # 1. 生成摘要（使用分块处理版本）
        news_content = await generate_news_summary_chunked(week_start_date, week_end_date, VOLCENGINE_API_KEY)
        # 延迟导入，避免循环依赖
        from to_feishu_docx import write_to_weekly_docx
        await write_to_weekly_docx(news_content, week_start_md, week_end_md)
        
# --- 主程序入口 ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='新闻处理工具')
    parser.add_argument('--mode', 
                      choices=['rss', 'daily_news', 'weekly_news', 'all'],
                      default='all',
                      help='执行模式: rss=RSS抓取, daily_news=生成日报, weekly_news=生成周报, all=全部')
    args = parser.parse_args()
    
    asyncio.run(main(args.mode))
