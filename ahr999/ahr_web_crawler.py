import asyncio
import sys, os
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db_management import create_ahr999_db, save_ahr999, fetch_ahr999_by_ymd

def convert_to_float(text):
    """将文本转换为浮点数，处理可能的空格、$和逗号"""
    if not text or text.isspace() or text == '\xa0':
        return None
    return float(text.strip().replace('$', '').replace(',', ''))

def is_empty(text):
    """将文本转换为浮点数，处理可能的空格、$和逗号"""
    if not text or text.isspace() or text == '\xa0':
        return True
    return False

async def fetch_table_row_by_date(url, target_date):
    """
    从指定页面抓取表格数据，并提取目标日期的行。
    :param url: 页面 URL
    :param target_date: 目标日期，例如 '2025/11/18'
    :return: 包含目标日期行数据的字典，或 None 如果未找到
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        try:
            # 打开目标页面
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            print("页面加载完成")

            # 等待表格加载完成（根据页面实际情况调整选择器）
            await page.wait_for_selector("table", timeout=10000)

            # 提取表格内容
            rows = await page.query_selector_all("table tbody tr")
            for row in rows:
                # 提取每一行的单元格内容
                cells = await row.query_selector_all("td")
                cell_texts = [await cell.inner_text() for cell in cells]
                if is_empty(cell_texts[0]):
                    continue

                # 检查目标日期是否在第一列
                if cell_texts and (not target_date or cell_texts[0] == target_date):
                    ahr999 = convert_to_float(cell_texts[1])
                    btc_price = convert_to_float(cell_texts[2])
                    basis_200 = convert_to_float(cell_texts[3])
                    exp_growth_valuation = btc_price**2 / ahr999 / basis_200

                    # 返回目标行数据
                    await browser.close()
                    return cell_texts[0], round(ahr999, 4), int(btc_price), int(basis_200), int(exp_growth_valuation)

            print(f"未找到目标日期 {target_date} 的数据")
            await browser.close()
            return None

        except Exception as e:
            print(f"抓取失败: {e}")
            await browser.close()
            return None

async def fetch_ahr999_data(target_date=None):
    """
    从 AHR999 页面抓取目标日期的价格数据。
    :param target_date: 目标日期，例如 '2025/11/18'
    :return: 包含目标日期价格数据的字典，或 None 如果未找到
    """
    url = "https://www.coinglass.com/zh/pro/i/ahr999"
    # if not target_date:
    #     target_date = datetime.now().strftime("%Y/%m/%d")
    return await fetch_table_row_by_date(url, target_date)

async def save_ahr999_2_db():
    create_ahr999_db()
    """
    保存ahr999数据到数据库
    """
    ymd, ahr999, price, basis_200, exp_growth_val = await fetch_ahr999_data()
    if ymd:
        save_ahr999(ymd, ahr999, price, basis_200, exp_growth_val)

def fetch_ahr999(ymd=None):
    """
    获取ahr999数据
    """
    if not ymd:
        ymd = datetime.now().strftime("%Y/%m/%d")
    return fetch_ahr999_by_ymd(ymd)


if __name__ == "__main__":
    # 测试抓取逻辑
    # target_date = "2025/11/21"
    result = asyncio.run(fetch_ahr999_data())
    # result = asyncio.run(save_ahr999_2_db())

    # result = fetch_ahr999_data()
    print(result)