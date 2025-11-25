import asyncio
import sys, os
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db_management import create_ahr999_db, save_ahr999, fetch_ahr999_by_ymd
from ahr999.ahr999_utils import forecast_price

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

async def crawler_table_row_by_date(url, target_date):
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
            # 尝试等待网络空闲，但设置较短的超时时间
            try:
                await page.wait_for_load_state('networkidle', timeout=20000)  # 10秒超时
            except Exception:
                # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
                pass
            print("AHR999 页面加载完成")

            # 等待表格加载完成（根据页面实际情况调整选择器）
            await page.wait_for_selector("table", timeout=10000)

            # 提取表格内容
            rows = await page.query_selector_all("table tbody tr")
            for row in rows:
                # 提取每一行的单元格内容
                cells = await row.query_selector_all("td")
                cell_texts = [await cell.inner_text() for cell in cells]
                print(cell_texts)
                if is_empty(cell_texts[0]):
                    continue

                # 检查目标日期是否在第一列，或者就取第一行不为空的数据
                if cell_texts and (not target_date or cell_texts[0] == target_date):
                    ahr999 = convert_to_float(cell_texts[1])
                    btc_price = convert_to_float(cell_texts[2])
                    basis_200 = convert_to_float(cell_texts[3])
                    exp_growth_val = btc_price**2 / ahr999 / basis_200

                    # 返回目标行数据
                    await browser.close()
                    return cell_texts[0], ahr999, btc_price, basis_200, exp_growth_val

            print(f"未找到目标日期 {target_date} 的数据")
            await browser.close()
            return None, None, None, None, None

        except Exception as e:
            print(f"抓取失败: {e}")
            await browser.close()
            return None, None, None, None, None

async def crawler_ahr999_data(target_date=None):
    """
    从 AHR999 页面抓取目标日期的价格数据。
    :param target_date: 目标日期，例如 '2025/11/18'
    :return: 包含目标日期价格数据的字典，或 None 如果未找到
    """
    url = "https://www.coinglass.com/zh/pro/i/ahr999"
    # if not target_date:
    #     target_date = datetime.now().strftime("%Y/%m/%d")
    return await crawler_table_row_by_date(url, target_date)

async def crawler_and_save_ahr999_data():
    create_ahr999_db()
    """
    保存ahr999数据到数据库
    """
    ymd, ahr999, price, basis_200, exp_growth_val = await crawler_ahr999_data()
    if ymd:
        save_ahr999(ymd, ahr999, price, basis_200, exp_growth_val)

def fetch_ahr999_data(ymd=None):
    """
    获取ahr999数据
    """
    ahr999_data = fetch_ahr999_by_ymd(ymd)
    if not ahr999_data:
        return None
    
    date_str = ahr999_data.get("ymd")
    date_obj = datetime.strptime(date_str, "%Y/%m/%d")

    ahr999 = ahr999_data.get("ahr999")
    btc_price = ahr999_data.get("price")
    basis_200 = ahr999_data.get("basis_200")
    exp_growth_val = ahr999_data.get("exp_growth_val")

    exp_growth_val_new = forecast_price(year=date_obj.year, month=date_obj.month, day=date_obj.day, version='new')
    ahr999_new = btc_price**2 / basis_200 / exp_growth_val_new

    return date_str, round(ahr999, 2), int(btc_price), int(basis_200), int(exp_growth_val), round(ahr999_new, 2), int(exp_growth_val_new)


if __name__ == "__main__":
    # 测试抓取逻辑
    # target_date = "2025/11/21"
    result = asyncio.run(crawler_ahr999_data())
    # result = asyncio.run(crawler_and_save_ahr999_data())
    # result = asyncio.run(fetch_ahr999_data())

    # result = fetch_ahr999_data()
    print(result)