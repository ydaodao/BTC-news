import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta # 新增：用于处理时区
import sqlite3  # 新增：用于数据库操作

load_dotenv()
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
ALI_WEBSERVICE_URL = 'http://127.0.0.1:5000' if LOCAL_DEV else 'http://39.107.72.186:5000'

def _exec_remote_sql(sql, params=None):
    url = f"{ALI_WEBSERVICE_URL}/api/execute_sql"
    payload = {"sql": sql, "params": params or []}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(data.get("error") or "Unknown SQL execution error")
        return data.get("result")
    except Exception as e:
        raise RuntimeError(f"Remote SQL failed: {e}")

def open_or_create_rss_db():
    """
    通过远程接口执行建表与索引创建
    """
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
    _exec_remote_sql(create_table_sql)

    # 分别创建每个索引
    _exec_remote_sql('CREATE INDEX IF NOT EXISTS idx_published ON ssr_list(published)')
    _exec_remote_sql('CREATE INDEX IF NOT EXISTS idx_link ON ssr_list(link)')

    # 返回远程执行成功的标记
    return True

def save_rss(entry):
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

    # 使用 INSERT OR IGNORE 来处理重复的 link（远程调用）
    insert_sql = """
    INSERT OR IGNORE INTO ssr_list 
    (link, title, summary, published, updated) 
    VALUES (?, ?, ?, ?, ?)
    """
    params = [entry.link, entry.title, entry.summary, formatted_published, formatted_updated]
    try:
        result = _exec_remote_sql(insert_sql, params)
        rows_affected = result.get("rows_affected", 0) if isinstance(result, dict) else 0
        last_row_id = result.get("last_row_id") if isinstance(result, dict) else None
    except Exception as e:
        print(f"远程插入失败: {e}")
        return
    
    if rows_affected == 0:
        print(f"新闻已存在: {entry.title}")
    else:
        print(f"新闻已保存 (ID: {last_row_id}): {entry.title}")

def fetch_news_by_published(start_date: str, end_date: str):
    """
    从数据库中读取指定日期范围的新闻数据。
    :param start_date: 开始日期字符串 (格式: 'YYYY-MM-DD HH:MM:SS')
    :param end_date: 结束日期字符串 (格式: 'YYYY-MM-DD HH:MM:SS')
    :return: 包含新闻链接和标题的列表，例如 [{'id': 1, 'link': '...', 'title': '...'}]
    """
    query = ("SELECT id, link, title FROM ssr_list "
             "WHERE published BETWEEN ? AND ? "
             "AND (content IS NULL OR content = '') "
             "ORDER BY id ASC")
    try:
        result = _exec_remote_sql(query, [start_date, end_date])
        if isinstance(result, list):
            news_list = [{"id": row.get("id"), "link": row.get("link"), "title": row.get("title")} for row in result]
            return news_list
        return []
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return []

def fetch_news_by_content_updated(start_date: str, end_date: str):
    """
    从数据库中读取指定日期范围的新闻数据，包括正文内容
    """
    query = """
        SELECT link, real_url, title, content 
        FROM ssr_list 
        WHERE content_updated BETWEEN ? AND ?
        AND content IS NOT NULL
        ORDER BY id ASC
    """
    try:
        result = _exec_remote_sql(query, [start_date, end_date])
        if isinstance(result, list):
            news_list = [{
                "link": row.get("link"),
                "real_url": row.get("real_url"),
                "title": row.get("title"),
                "content": row.get("content")
            } for row in result]
            return news_list
        return []
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return []

def update_news_content(link: str, content: str, real_url: str):
    """
    更新指定新闻链接的正文内容和真实URL
    返回：被更新记录的id
    """
    # 获取当前UTC北京时区时间
    beijing_tz = timezone(timedelta(hours=8))
    current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    
    update_sql = "UPDATE ssr_list SET content = ?, real_url = ?, content_updated = ? WHERE link = ?"
    try:
        _exec_remote_sql(update_sql, [content, real_url, current_time, link])
        rows = _exec_remote_sql("SELECT id FROM ssr_list WHERE link = ?", [link])
        return rows[0].get("id") if rows else None
    except Exception as e:
        print(f"远程更新或查询失败: {e}")
        return None

# ------------------------- ahr999 ---------------------------
def drop_ahr999_db():
    create_table_sql = '''
    DROP TABLE IF EXISTS ahr999_list
    '''
    _exec_remote_sql(create_table_sql)

def create_ahr999_db():
    """
    通过远程接口执行建表与索引创建
    """
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS ahr999_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ymd TEXT UNIQUE,
        ahr999 REAL NOT NULL,
        price REAL NOT NULL,
        basis_200 REAL NOT NULL,
        exp_growth_val REAL NOT NULL
    )
    '''
    _exec_remote_sql(create_table_sql)

    # 分别创建每个索引
    _exec_remote_sql('CREATE INDEX IF NOT EXISTS idx_ymd ON ahr999_list(ymd)')

    # 返回远程执行成功的标记
    return True

def save_ahr999(ymd: str, ahr999: float, price: float, basis_200: float, exp_growth_val: float):
    insert_sql = """
    INSERT INTO ahr999_list (ymd, ahr999, price, basis_200, exp_growth_val)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(ymd) DO UPDATE SET
        ahr999 = excluded.ahr999,
        price = excluded.price,
        basis_200 = excluded.basis_200,
        exp_growth_val = excluded.exp_growth_val;
    """
    params = [ymd, ahr999, price, basis_200, exp_growth_val]
    try:
        result = _exec_remote_sql(insert_sql, params)
        rows_affected = result.get("rows_affected", 0) if isinstance(result, dict) else 0
        last_row_id = result.get("last_row_id") if isinstance(result, dict) else None
    except Exception as e:
        print(f"远程插入失败: {e}")
        return

def fetch_ahr999_by_ymd(ymd: str):
    query = ("SELECT ymd, ahr999, price, basis_200, exp_growth_val FROM ahr999_list WHERE ymd = ?")
    try:
        result = _exec_remote_sql(query, [ymd])
        if isinstance(result, list):
            row = result[0]
            return row.get("ymd"), row.get("ahr999"), row.get("price"), row.get("basis_200"), row.get("exp_growth_val")
        return []
    except Exception as e:
        print(f"数据库查询失败: {e}")
        return []

# ------------------------- ahr999 ---------------------------

if __name__ == '__main__':
    create_ahr999_db()
    # drop_ahr999_db()
