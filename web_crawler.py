import asyncio
import aiofiles
import os
from urllib.parse import urlparse, parse_qs
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright
from readability import Document
import html2text


# === 配置 ===
BASE_DIR = os.path.dirname(__file__)
HTML_FILE = os.path.join(BASE_DIR, "test/output.html")
MD_FILE = os.path.join(BASE_DIR, "test/output.md")
SH_PICTURE_FILE = os.path.join(BASE_DIR, "test/debug_screenshot.png")
WAIT_TIME = 15  # 可视化模式手动操作等待时间
# VPN 代理配置
PROXIES = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}


def resolve_google_redirect(url):
    """解析 Google 跳转 URL"""
    parsed = urlparse(url)
    if "google.com" in parsed.netloc and "url" in parsed.path:
        query = parse_qs(parsed.query)
        if "url" in query:
            return query["url"][0]
    return url


def is_challenge_page(html):
    """判断是否是反爬/验证码页面"""
    return any(
        keyword in html.lower()
        for keyword in ["javascript is disabled", "captcha", "cloudflare", "awswaf"]
    )


def extract_readable_content(html):
    """用 Readability 提取正文并转 Markdown"""
    doc = Document(html)
    title = doc.short_title()
    content_html = doc.summary(html_partial=True)

    md_converter = html2text.HTML2Text()
    md_converter.ignore_links = False
    md_text = md_converter.handle(content_html)
    return title, content_html, md_text


async def save_result(title, html, md_text, save_files=False):
    if not save_files:
        return
    """保存 HTML 和 Markdown"""
    async with aiofiles.open(HTML_FILE, "w", encoding="utf-8") as f:
        await f.write(html)
    async with aiofiles.open(MD_FILE, "w", encoding="utf-8") as f:
        await f.write(f"# {title}\n\n{md_text}")
    print(f"✅ HTML 保存到: {HTML_FILE}")
    print(f"✅ Markdown 保存到: {MD_FILE}")


async def try_crawl4ai(url):
    """第一阶段：直接用 crawl4ai 抓取"""
    try:
        async with AsyncWebCrawler(proxy=PROXIES['http'], max_concurrency=5) as crawler:
            result = await crawler.arun(url=url)
            if result and result.html and not is_challenge_page(result.html):
                return result.html
    except Exception as e:
        print(f"[crawl4ai 抓取失败] {e}")
    return None


async def try_playwright(url, headless=True, debug_mode=False):
    """第二阶段：使用 Playwright 抓取"""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=headless, 
                slow_mo=100,
                proxy={
                    "server": PROXIES['http'],
                }
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                # 添加持久化 Cookie 存储
                storage_state={
                    "cookies": [
                        {
                            "name": "cookie_consent",
                            "value": "accepted",
                            "domain": ".binance.com",
                            "path": "/"
                        }
                    ]
                }
            )
            
            page = await context.new_page()
            
            # 添加更多请求头
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })
            
            await page.goto(url, timeout=60000)
            
            # 等待页面加载
            await page.wait_for_load_state("domcontentloaded")
            
            # 尝试自动点击 Cookie 同意按钮
            try:
                # 等待并点击 Cookie 同意按钮（根据实际按钮选择器调整）
                accept_button = await page.wait_for_selector('button[id="onetrust-accept-btn-handler"]', timeout=5000)
                if accept_button:
                    await accept_button.click()
                    # 等待页面重新加载
                    await page.wait_for_load_state("networkidle")
            except Exception:
                print("未找到 Cookie 同意按钮或已经同意")
            
            # 等待主要内容加载
            await page.wait_for_load_state("load")
            await asyncio.sleep(5)
            
            content = await page.content()
            
            # 调试用：保存页面截图
            if debug_mode and (not content or "cookie" in content.lower()):
                await page.screenshot(path=SH_PICTURE_FILE)
                print("已保存调试截图到 debug_screenshot.png")
            
            await browser.close()
            return content
            
        except Exception as e:
            print(f"[Playwright 抓取失败] {e}")
            return None


async def multi_cralwer(target_url, save_files=False, debug_mode=True):
    url_input = target_url.strip()
    if not url_input.startswith(("http://", "https://")):
        print("❌ 无效的 URL，请确保以 http:// 或 https:// 开头。")
        return
    real_url = resolve_google_redirect(url_input)
    if real_url != url_input:
        print(f"已解析真实地址: {real_url}")

    # 第一阶段：crawl4ai
    print("🚀 第一阶段：尝试 crawl4ai 抓取...")
    html = await try_crawl4ai(real_url)
    if html:
        print("✅ crawl4ai 抓取成功")
        title, clean_html, md_text = extract_readable_content(html)
        await save_result(title, clean_html, md_text, save_files)
        return md_text, real_url

    # 第二阶段：Playwright 无头模式
    print("⚠️ 第二阶段：crawl4ai 抓取失败，尝试 Playwright 无头模式...")
    html = await try_playwright(real_url, headless=True, debug_mode=debug_mode)
    if html:
        print("✅ Playwright 无头模式抓取成功")
        title, clean_html, md_text = extract_readable_content(html)
        await save_result(title, clean_html, md_text, save_files)
        return md_text, real_url

    # 第三阶段：如果无头模式失败，尝试可见浏览器
    if debug_mode:
        print("⚠️ 第三阶段：无头模式失败，启动可见浏览器，请手动过验证...")
        html = await try_playwright(real_url, headless=False, debug_mode=debug_mode)
        if html:
            print("✅ 手动操作后抓取成功")
            title, clean_html, md_text = extract_readable_content(html)
            await save_result(title, clean_html, md_text, save_files)
            return md_text, real_url
        else:
            print("❌ 仍然无法抓取该页面")


if __name__ == "__main__":
    BASE_DIR = os.path.join(os.path.dirname(__file__), "test")

    url = 'https://www.google.com/url?rct=j&sa=t&url=https://www.fx168news.com/article/%25E6%25AF%2594%25E7%2589%25B9%25E5%25B8%2581-930071&ct=ga&cd=CAIyIGQ0OGVkZDFmZDIyYTgzMGU6Y29tLmhrOnpoLUNOOkhL&usg=AOvVaw1pY9U2l1FepoUqeYekeLDE'
    asyncio.run(multi_cralwer(url, save_files=True, debug_mode=True))