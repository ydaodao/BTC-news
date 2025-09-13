import os
import asyncio
import requests
from dotenv import load_dotenv
# 加载环境变量
load_dotenv()

def send_to_robot(message):
    """
    直接推送内容到飞书机器人（不依赖pushplus）
    """
    webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
    if not webhook_url:
        print("错误：请设置 FEISHU_WEBHOOK_URL 环境变量或传入webhook_url参数")
        return
    
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

async def push_richtext_to_feishu(card_title, text_content, text_url):
    # 富文本
    message = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": card_title,
                    "content": [
                        [{
                            "tag": "a",
                            "text": text_content,
                            "href": text_url
                        }]
                    ]
                }
            }
        }
    }
    send_to_robot(message)

async def push_text_to_feishu(text_content):
    # 文本
    message = {
        "msg_type": "text",
        "content": {
            "text": text_content
        }
    }
    send_to_robot(message)

if __name__ == "__main__":
    asyncio.run(push_richtext_to_feishu("这是一条测试消息"))