import os
import asyncio
import requests
from dotenv import load_dotenv
# 加载环境变量
load_dotenv()

async def push_richtext_to_feishu(title, url):
    """
    直接推送富文本内容到飞书机器人（不依赖pushplus）
    """
    webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
    if not webhook_url:
        print("错误：请设置 FEISHU_WEBHOOK_URL 环境变量或传入webhook_url参数")
        return
    
    # 构建飞书机器人消息格式
    message = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "一周总结",
                    "content": [
                        [{
                            "tag": "a",
                            "text": title,
                            "href": url
                        }]
                    ]
                }
            }
        }
    }

    try:
        response = requests.post(
            webhook_url, 
            json=message,
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

if __name__ == "__main__":
    asyncio.run(push_richtext_to_feishu("这是一条测试消息"))