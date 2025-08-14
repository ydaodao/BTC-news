import asyncio
import aiofiles
from crawl4ai import AsyncWebCrawler
import os

# 使用绝对路径
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output.html")
URL = "https://techcrunch.com/"
URL = 'https://www.google.com/url?rct=j&sa=t&url=https://www.binance.com/zh-CN/square/post/28212044130986&ct=ga&cd=CAIyIGQ0OGVkZDFmZDIyYTgzMGU6Y29tLmhrOnpoLUNOOkhL&usg=AOvVaw0HN7-5AB5B1hiihRGZZ7cB'

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=URL)  # 替换为目标网站
        print(result.markdown)  # 输出清洗后的Markdown内容
        # 只使用同步写入即可
        async with aiofiles.open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            await f.write(result.html)
        print(f"文件已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())