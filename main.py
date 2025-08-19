import feedparser
import requests
import json
import os
import asyncio
from crawl4ai import AsyncWebCrawler
from openai import OpenAI  # 火山引擎的客户端基于 OpenAI 库
from web_crawler import multi_cralwer
import sqlite3  # 新增：用于数据库操作
from datetime import datetime, timezone, timedelta # 新增：用于处理时区
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# --- 配置部分 ---
# 替换为您的谷歌快讯RSS源链接
RSS_URL = "https://www.google.com.hk/alerts/feeds/08373742189599090702/14816707195864267476"

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
VOLCENGINE_API_KEY = os.getenv('VOLCENGINE_API_KEY')
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN')
print(VOLCENGINE_API_KEY)
print(PUSHPLUS_TOKEN)

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

# --- 数据库函数 ---
def open_or_create_db():
    """
    连接到 SQLite 数据库，创建带自增主键的表
    """
    # 使用项目根目录的相对路径
    db_path = os.path.join(os.path.dirname(__file__), 'ssr_list.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建新表，添加 id 自增主键，link 设为唯一索引
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS ssr_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT UNIQUE,
        real_url TEXT,
        title TEXT,
        summary TEXT,
        published TEXT,
        updated TEXT,
        content TEXT,
        content_updated TEXT
    )
    '''
    cursor.execute(create_table_sql)
    
    # 为已存在的表添加content_updated字段（如果不存在）
    try:
        cursor.execute('ALTER TABLE ssr_list ADD COLUMN content_updated TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        # 字段已存在，忽略错误
        pass
    
    # 分别创建每个索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_published ON ssr_list(published)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_link ON ssr_list(link)')
    
    conn.commit()
    return conn, cursor

def save_to_db(conn, cursor, entry):
    """
    将单个新闻条目存储到数据库中。
    使用 INSERT OR IGNORE 处理重复的 link。
    """
    try:
        # 定义东八区时区对象
        local_timezone = timezone(timedelta(hours=8))
        
        # 将原始的 UTC 时间字符串转换为 datetime 对象
        published_dt_utc = datetime.fromisoformat(entry.published.replace('Z', '+00:00'))
        updated_dt_utc = datetime.fromisoformat(entry.updated.replace('Z', '+00:00'))
        
        # 将 UTC 时间转换为东八区时间
        published_dt_local = published_dt_utc.astimezone(local_timezone)
        updated_dt_local = updated_dt_utc.astimezone(local_timezone)
        
        # 格式化为所需的字符串格式
        formatted_published = published_dt_local.strftime('%Y-%m-%d %H:%M:%S')
        formatted_updated = updated_dt_local.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError) as e:
        print(f"日期格式转换失败，使用原始字符串。错误: {e}")
        formatted_published = entry.published
        formatted_updated = entry.updated

    # 使用 INSERT OR IGNORE 来处理重复的 link
    insert_sql = """
    INSERT OR IGNORE INTO ssr_list 
    (link, title, summary, published, updated) 
    VALUES (?, ?, ?, ?, ?)
    """
    data = (entry.link, entry.title, entry.summary, formatted_published, formatted_updated)
    cursor.execute(insert_sql, data)
    
    if cursor.rowcount == 0:
        print(f"新闻已存在: {entry.title}")
    else:
        print(f"新闻已保存 (ID: {cursor.lastrowid}): {entry.title}")
    
    conn.commit()

def fetch_news_by_date_range(start_date: str, end_date: str):
    """
    从数据库中读取指定日期范围的新闻数据。
    :param start_date: 开始日期字符串 (格式: 'YYYY-MM-DD HH:MM:SS')
    :param end_date: 结束日期字符串 (格式: 'YYYY-MM-DD HH:MM:SS')
    :return: 包含新闻链接和标题的列表，例如 [{'link': '...', 'title': '...'}]
    """
    conn = None
    try:
        conn = sqlite3.connect('ssr_list.db')
        cursor = conn.cursor()
        query = "SELECT id, link, title FROM ssr_list WHERE published BETWEEN ? AND ? AND (content IS NULL OR content = '') ORDER BY id ASC"
        cursor.execute(query, (start_date, end_date))
        
        results = cursor.fetchall()
        news_list = [{"id": row[0], "link": row[1], "title": row[2]} for row in results]
        return news_list
    except sqlite3.Error as e:
        print(f"数据库查询失败: {e}")
        return []
    finally:
        if conn:
            conn.close()

def fetch_news_with_content(start_date: str, end_date: str):
    """
    从数据库中读取指定日期范围的新闻数据，包括正文内容
    """
    conn = None
    try:
        conn = sqlite3.connect('ssr_list.db')
        cursor = conn.cursor()
        query = """
            SELECT link, real_url, title, content 
            FROM ssr_list 
            WHERE content_updated BETWEEN ? AND ?
            AND content IS NOT NULL
            ORDER BY id ASC
        """
        cursor.execute(query, (start_date, end_date))
        
        results = cursor.fetchall()
        news_list = [{
            "link": row[0],
            "real_url": row[1],
            "title": row[2], 
            "content": row[3]
        } for row in results]
        return news_list
    except sqlite3.Error as e:
        print(f"数据库查询失败: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_news_content(conn, cursor, link: str, content: str, real_url: str):
    """
    更新指定新闻链接的正文内容和真实URL
    返回：被更新记录的id
    """
    # 获取当前UTC北京时区时间
    beijing_tz = timezone(timedelta(hours=8))
    current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    update_sql = "UPDATE ssr_list SET content = ?, real_url = ?, content_updated = ? WHERE link = ?"
    cursor.execute(update_sql, (content, real_url, current_time, link))
    conn.commit()
    
    # 查询被更新记录的id
    query_id_sql = "SELECT id FROM ssr_list WHERE link = ?"
    cursor.execute(query_id_sql, (link,))
    result = cursor.fetchone()
    return result[0] if result else None

async def fetch_rss_news():
    """从 RSS 源抓取新闻并存储到数据库"""
    print("开始抓取谷歌快讯...")
    conn, cursor = open_or_create_db()
    
    try:
        # 根据环境决定是否使用代理
        response = requests.get(RSS_URL, proxies=PROXIES if PROXIES else None)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        
        if not feed.entries:
            print("RSS源中没有新内容。")
            return 0
            
        for entry in feed.entries:
            save_to_db(conn, cursor, entry)
        
        print(f"成功抓取 {len(feed.entries)} 条新闻并存入数据库。")
        return len(feed.entries)
        
    except Exception as e:
        print(f"抓取RSS源或数据库操作失败：{e}")
        return 0
    finally:
        cursor.close()
        conn.close()

async def fetch_news_content(start_date: str, end_date: str):
    """
    处理指定时间范围内的新闻正文
    """
    print("开始从数据库中读取新闻...")
    news_list = fetch_news_by_date_range(start_date, end_date)
    
    if not news_list:
        print("指定日期范围内没有找到新闻。")
        return False

    print(f"成功从数据库中读取 {len(news_list)} 条新闻。")

    print("开始异步提取新闻正文...")
    conn, cursor = open_or_create_db()
    try:
        for item in news_list:
            print(f"正在处理新闻：{item['id']} {item['title']}")
            result = await multi_cralwer(item['link'])
            if result:
                md_text, real_url = result
                # 无论是否抓取到内容，只要有 real_url 就更新数据库
                news_id = update_news_content(conn, cursor, item['link'], md_text, real_url)
                if md_text:
                    print(f"已更新新闻内容：(ID: {news_id}) Title：{item['title']}")
                if real_url:
                    print(f"已更新真实URL：(ID: {news_id}) Real_URL：{real_url}")

            else:
                print(f"无法抓取新闻内容：{item['id']} {item['title']}")
    finally:
        cursor.close()
        conn.close()
    
    return True

async def generate_news_summary(start_date: str, end_date: str):
    """
    生成新闻摘要并调用大模型处理
    """
    processed_news = fetch_news_with_content(start_date, end_date)
    if not processed_news:
        print("没有找到包含正文内容的新闻。")
        return None

    print(f"成功读取 {len(processed_news)} 条新闻内容。")
    print("构建大模型API的Prompt...")
    
    all_content = "\n\n-----\n\n".join([
        f"标题: {n['title']}\n"
        f"真实链接: {n['real_url']}\n"
        f"正文: {n['content']}" 
        for n in processed_news
    ])

    prompt_text = f"""你是一名资深的新闻编辑，请对以下新闻进行处理。你的任务是：

    1. 全文以markdown格式输出
    2. 将所有新闻进行主题聚类，每个聚类需要一个简洁的主题标题。要求：用###开头，序号用一、二、三……来标注，聚类之间用 --- 分隔开
    3. 总结每个聚类的主旨，风格要求公正、客观、简洁。要求：用 **总结** 开头，内容用有序列表呈现
    4. 在每个聚类下，用无序列表列出原始新闻的标题和链接，符合markdown格式[标题](url)。要求：用 **参考** 开头
    5. 最后输出一个总标题，放在第一行，要求：内容仅与BTC有关。举例：BTC监管收紧，稳定币重塑市场格局

    以下是新闻内容：

    -----

    {all_content}
    """

    # 保存 prompt 到文件
    prompt_file = os.path.join(os.path.dirname(__file__), "latest_prompt.txt")
    try:
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        print(f"Prompt 已保存到: {prompt_file}")
        
        # 可选：自动打开文件
        # os.startfile(prompt_file)
    except Exception as e:
        print(f"保存 Prompt 失败: {e}")


    print("开始调用火山引擎API生成摘要...")
    try:
        # # 根据环境设置代理
        # if PROXIES:
        #     os.environ['HTTP_PROXY'] = PROXIES['http']
        #     os.environ['HTTPS_PROXY'] = PROXIES['https']

        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=VOLCENGINE_API_KEY,
        )

        response = client.chat.completions.create(
            model="doubao-seed-1-6-thinking-250715",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.3,
        )

        summary_content = response.choices[0].message.content

        # 保存响应内容到文件
        summary_file = os.path.join(os.path.dirname(__file__), f"latest_summary.md")
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary_content)
            print(f"摘要已保存到: {summary_file}")
            
            # 可选：自动打开文件
            # os.startfile(summary_file)
        except Exception as e:
            print(f"保存摘要失败: {e}")

        return summary_content

    except Exception as e:
        print(f"调用火山引擎API失败：{e}")
        return None
    finally:
        # 清理代理环境变量
        if 'HTTP_PROXY' in os.environ:
            del os.environ['HTTP_PROXY']
            del os.environ['HTTPS_PROXY']

async def push_to_feishu_direct(content=None, webhook_url=None):
    """
    直接推送内容到飞书机器人（不依赖pushplus）
    如果 content 为空，则尝试从本地文件读取
    """
    if not webhook_url:
        webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
        if not webhook_url:
            print("错误：请设置 FEISHU_WEBHOOK_URL 环境变量或传入webhook_url参数")
            return
    
    if not content:
        # 尝试从本地文件读取内容
        summary_file = os.path.join(os.path.dirname(__file__), "latest_summary.md")
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

    print("开始直接推送消息到飞书机器人...")
    
    # 从内容中提取第一行作为标题
    title = "每日新闻摘要"  # 默认标题
    message_content = content
    if content:
        # 按行分割内容
        lines = content.strip().split('\n')
        if lines:
            # 获取第一行并去掉 Markdown 标题符号
            first_line = lines[0].strip()
            if first_line.startswith('# '):
                title = first_line[2:].strip()
                # 将第一行从content中移除
                message_content = '\n'.join(lines[1:]).strip()
    print(f"使用标题: {title}")

    # 飞书机器人富文本消息格式
    # 读取飞书消息模板
    template_path = os.path.join(os.path.dirname(__file__), 'feishu_message_template.json')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 对内容进行JSON转义处理
    import json as json_module
    title_escaped = json_module.dumps(title)[1:-1]  # 去掉首尾引号
    message_content_escaped = json_module.dumps(message_content)[1:-1]  # 去掉首尾引号
    
    # 替换模板中的占位符
    data_str = template_content.replace('{title}', title_escaped).replace('{message_content}', message_content_escaped)
    data = json.loads(data_str)
    
    try:
        response = requests.post(
            webhook_url, 
            json=data,
            headers={'Content-Type': 'application/json'}, 
            timeout=10
        )
        response.raise_for_status()

        # 打印详细的响应信息
        result = response.json()
        print(f"飞书推送响应: {result}")
        
        if result.get('StatusCode') == 0:
            print("消息直接推送到飞书成功！")
        else:
            print(f"推送失败: {result.get('msg', '未知错误')}")
    except requests.exceptions.RequestException as e:
        print(f"消息直接推送到飞书失败：{e}")

async def push_to_wechat(content=None, feishu_mode=True):
    """
    使用 pushplus 服务将内容推送到微信
    如果 content 为空，则尝试从本地文件读取
    """
    if not content:
        # 尝试从本地文件读取内容
        summary_file = os.path.join(os.path.dirname(__file__), "latest_summary.md")
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
        - "summary_push": 只执行摘要生成和推送
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
    
    # 为摘要生成设置1天的时间范围
    one_day_ago = now - timedelta(days=1)
    summary_start_date = one_day_ago.strftime('%Y-%m-%d %H:%M:%S')
    summary_end_date = now.strftime('%Y-%m-%d %H:%M:%S')
    
    summary = None

    if mode in ["rss", "all"]:
        print("\n=== 执行RSS抓取任务 ===")
        # 1. 抓取RSS
        await fetch_rss_news()
        # 2. 获取内容
        await fetch_news_content(start_date, end_date)

    if mode in ["summary_push", "all"]:
        print("\n=== 执行摘要生成和推送任务 ===")
        # 1. 生成摘要
        summary = await generate_news_summary(summary_start_date, summary_end_date)
        # 2. 推送消息（自动根据环境变量选择推送到微信或飞书）
        # await push_to_wechat(summary)
        await push_to_feishu_direct(summary)
            
# --- 主程序入口 ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='新闻处理工具')
    parser.add_argument('--mode', 
                      choices=['rss', 'summary_push', 'all'],
                      default='all',
                      help='执行模式: rss=RSS抓取, summary_push=摘要推送, all=全部')
    args = parser.parse_args()
    
    asyncio.run(main(args.mode))
