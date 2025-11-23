import feedparser
import requests
import json
import os
import asyncio
from crawl4ai import AsyncWebCrawler
from openai import OpenAI  # 火山引擎的客户端基于 OpenAI 库
from ahr999 import multi_cralwer

# --- 配置部分 ---
# 替换为您的谷歌快讯RSS源链接
RSS_URL = "https://www.google.com.hk/alerts/feeds/08373742189599090702/14816707195864267476"

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中，例如：
# export ARK_API_KEY="sk-..."
# 或者直接在这里赋值（不推荐，出于安全考虑）
# VOLCENGINE_API_KEY = os.environ.get("ARK_API_KEY")
VOLCENGINE_API_KEY = "bf027b0a-f1ad-42d1-a3f1-30295a401ece"

# pushplus的token，用于推送微信消息
PUSHPLUS_TOKEN = "eb18ea921a7649cfae51c6cb66367a2a"

# --- 异步主函数 ---
async def main():
    # 假设文件路径
    file_path = "D:\BaiduSyncdisk\Study\BTC-news\\test\output.md"

    # 读取整个文件为一个字符串
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(content)  # content 现在是一个完整的字符串


    processed_news = []
    processed_news.append({
        "title": "测试标题",
        "link": "https://techcrunch.com/",
        "content": content
    })

    if not processed_news:
        print("未能提取任何新闻的正文。")
        return

    print(f"成功提取 {len(processed_news)} 条新闻正文。")

    # 构建大模型API的Prompt
    all_content = "\n\n---\n\n".join([f"标题: {n['title']}\n正文: {n['content']}" for n in processed_news])

    prompt_text = (
        "你是一名资深的新闻编辑，请对以下新闻进行处理。你的任务是：\n"
        "1. 将所有新闻进行主题聚类，每个聚类需要一个简洁的主题标题。\n"
        "2. 对每个聚类中的新闻，提取3-5个核心关键词，作为摘要。\n"
        "3. 总结每个聚类的主旨，风格要求公正、客观、简洁。\n"
        "4. 在每个聚类下，列出原始新闻的标题和链接，以便用户查看。\n"
        "请以清晰的Markdown格式输出结果。\n\n"
        f"以下是新闻内容：\n{all_content}"
    )

    # 调用火山引擎大模型API
    print("开始调用火山引擎大模型进行处理...")
    try:
        # # 通过设置环境变量来让 requests 自动使用代理。
        # os.environ['HTTP_PROXY'] = PROXIES['http']
        # os.environ['HTTPS_PROXY'] = PROXIES['https']
        
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=VOLCENGINE_API_KEY,
        )

        response = client.chat.completions.create(
            model="doubao-seed-1-6-thinking-250715",
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
            temperature=0.3, # 较低的温度值有助于生成更客观、稳定的结果
        )

        llm_result = response.choices[0].message.content
        print("大模型处理完成。")
        
        # # 完成 API 调用后，清除代理环境变量
        # del os.environ['HTTP_PROXY']
        # del os.environ['HTTPS_PROXY']

    except Exception as e:
        print(f"调用火山引擎API失败：{e}")
        return
    print(llm_result)

    # 推送至微信
    await push_to_wechat(llm_result)

async def push_to_wechat(content):
    """
    使用 pushplus 服务将内容推送到微信，这里也需要设置代理
    """
    print("开始推送微信消息...")
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "每日新闻摘要",
        "content": content,
        "template": "markdown" # 使用Markdown格式以获得更好的显示效果
    }
    try:
        # 使用 requests 库发送请求，并设置代理
        response = requests.post(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print("微信消息推送成功！")
    except requests.exceptions.RequestException as e:
        print(f"推送微信失败：{e}")

# --- 主程序入口 ---
if __name__ == "__main__":
    # 检查API密钥是否已配置
    if not VOLCENGINE_API_KEY:
        print("错误：请先设置环境变量 'ARK_API_KEY' 或在代码中配置您的密钥。")
    else:
        # 使用 asyncio.run() 运行异步主函数
        asyncio.run(main())
