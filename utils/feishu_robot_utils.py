import os
import asyncio
import json
import requests
from requests_toolbelt import MultipartEncoder
from urllib.parse import quote, quote_plus, urlencode  # 添加URL编码支持
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
ALI_WEBSERVICE_URL = 'http://127.0.0.1:5000' if LOCAL_DEV else 'http://39.107.72.186:5000'

def url_encode_parameter(param_value, encoding='utf-8'):
    """
    对URL参数进行编码的通用方法
    
    Args:
        param_value: 需要编码的参数值（字符串或数字）
        encoding: 编码格式，默认utf-8
        
    Returns:
        str: 编码后的参数字符串
    """
    if param_value is None:
        return ''
    
    # 转换为字符串
    param_str = str(param_value)
    
    # 使用quote_plus进行编码，空格会被编码为+
    encoded = quote_plus(param_str, encoding=encoding)
    
    return encoded

def build_url_with_params(base_url, params_dict=None, **kwargs):
    """
    构建带参数的URL，自动对参数进行编码
    
    Args:
        base_url: 基础URL
        params_dict: 参数字典
        **kwargs: 额外的参数
        
    Returns:
        str: 完整的URL字符串
    """
    if not base_url:
        return ''
    
    # 合并参数
    all_params = {}
    if params_dict:
        all_params.update(params_dict)
    if kwargs:
        all_params.update(kwargs)
    
    # 如果没有参数，返回基础URL
    if not all_params:
        return base_url
    
    # 构建查询字符串
    query_parts = []
    for key, value in all_params.items():
        if value is not None:  # 跳过None值
            encoded_key = url_encode_parameter(key)
            encoded_value = url_encode_parameter(value)
            query_parts.append(f"{encoded_key}={encoded_value}")
    
    query_string = '&'.join(query_parts)
    
    # 组合URL
    separator = '&' if '?' in base_url else '?'
    full_url = f"{base_url}{separator}{query_string}"
    
    return full_url

class FeishuRobotAPI:
    def __init__(self, app_id=None, app_secret=None):
        """初始化飞书文档API客户端"""
        self.app_id = app_id or os.getenv('FEISHU_APP_ID')
        self.app_secret = app_secret or os.getenv('FEISHU_APP_SECRET')
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        
        if not self.app_id or not self.app_secret:
            raise ValueError("请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量")
    
    def get_tenant_access_token(self):
        """获取 tenant_access_token"""
        if self.access_token:
            return self.access_token
            
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"获取 tenant_access_token 失败: {result.get('msg')}")
        
        self.access_token = result['tenant_access_token']
        return self.access_token

    def upload_image_for_message(self, image_path):
        """
        上传图片，返回图片的Key
        参考doc：https://open.feishu.cn/document/server-docs/im-v1/image/create?appId=cli_a822ce94f622501c
        """
        url = f"{self.base_url}/im/v1/images"

        # 构造请求体
        form = {'image_type': 'message',
            'image': (open(image_path, 'rb'))}  # 需要替换具体的path 
        multi_form = MultipartEncoder(form)
        headers = {
            'Authorization': f'Bearer {self.get_tenant_access_token()}',  ## 获取tenant_access_token, 需要替换为实际的token
        }
        headers['Content-Type'] = multi_form.content_type

        response = requests.post(url, headers=headers, data=multi_form)
        result = response.json()
        if result.get('code') == 0:
            return result.get('data', {}).get('image_key')
        else:
            print(f"图片上传失败: {result.get('msg', '未知错误')}")
            return None


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
            print("消息推送到飞书成功！")
        else:
            print(f"推送失败: {result.get('msg', '未知错误')}")
    except requests.exceptions.RequestException as e:
        print(f"消息推送到飞书失败：{e}")

# ------------------------- 以上为基础方法 ----------------------------

def push_text_to_robot(text_content):
    # 文本
    message = {
        "msg_type": "text",
        "content": {
            "text": text_content
        }
    }
    send_to_robot(message)

def push_wxqrcode_to_robot(card_title, image_path):
    api = FeishuRobotAPI()
    # 图片
    message = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {
                "update_multi": True,
            },
            "body": {
                "direction": "vertical",
                "horizontal_spacing": "8px",
                "vertical_spacing": "20px",
                "horizontal_align": "left",
                "vertical_align": "top",
                "padding": "12px 12px 20px 12px",
                "elements": [
                    {
                        "tag": "column_set",
                        "flex_mode": "stretch",
                        "horizontal_spacing": "8px",
                        "horizontal_align": "left",
                        "columns": [
                            {
                                "tag": "column",
                                "width": "140px",
                                "elements": [
                                    {
                                        "tag": "img",
                                        "img_key": api.upload_image_for_message(image_path),
                                        "preview": True,
                                        "transparent": False,
                                        "scale_type": "crop_center",
                                        # "size": "16:5",
                                        "alt": {
                                            "tag": "plain_text",
                                            "content": ""
                                        },
                                        "corner_radius": "8px"
                                    }
                                ],
                                "vertical_spacing": "8px",
                                "horizontal_align": "left",
                                "vertical_align": "top"
                            },
                            {
                                "tag": "column",
                                "width": "weighted",
                                "elements": [
                                    {
                                        "tag": "button",
                                        "text": {
                                            "tag": "plain_text",
                                            "content": "请求登录二维码",
                                            "i18n_content": {
                                                "en_us": "View Tutorial"
                                            }
                                        },
                                        "type": "default",
                                        "width": "default",
                                        "size": "medium",
                                        "behaviors": [
                                            {
                                                "type": "open_url",
                                                "default_url": f"{ALI_WEBSERVICE_URL}/qrcode",
                                                "pc_url": "",
                                                "ios_url": "",
                                                "android_url": ""
                                            }
                                        ]
                                    }
                                ],
                                "direction": "horizontal",
                                "horizontal_spacing": "8px",
                                "vertical_spacing": "8px",
                                "horizontal_align": "left",
                                "vertical_align": "top",
                                "weight": 1
                            }
                        ],
                        "margin": "0px 0px 0px 0px"
                    }
                ]
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{card_title}"
                },
                "subtitle": {
                    "tag": "plain_text",
                    "content": ""
                },
                "template": "orange",
                "padding": "12px 12px 12px 12px"
            }
        }
    }
    send_to_robot(message)

def push_origin_weekly_news_to_robot(card_title, docs_title, docs_url):
    # 构建推送终版到公众号的URL
    push_url = build_url_with_params(
        f"{ALI_WEBSERVICE_URL}/api/push_final_weekly_news_and_push_robot",
        feishu_docx_url=docs_url
    )
    
    # 推送周报到机器人
    message = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": card_title,
                    "content": [
                        [{
                            "tag": "a",
                            "text": docs_title,
                            "href": docs_url
                        },{
                            "tag": "a",
                            "text": "-> 推送终版到公众号",
                            "href": push_url
                        }]
                    ]
                }
            }
        }
    }
    send_to_robot(message)

def push_final_weekly_news_to_robot(docs_url, wx_preview_page_url):
    # 读取飞书消息模板
    template_path = os.path.join(os.path.dirname(__file__), '..', 'send_to_weixin', 'templates', 'final_weekly_news_template.json')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 替换模板中的占位符
    data_str = template_content.replace('{title}', '周报推送到公众号成功！') \
                              .replace('{docs_url}', docs_url or '') \
                              .replace('{wx_preview_page_url}', wx_preview_page_url or '推送公众号失败！')

    data = json.loads(data_str)
    send_to_robot(data)

if __name__ == "__main__":
    # asyncio.run(push_richtext_to_feishu("这是一条测试消息"))
    api = FeishuRobotAPI()
    push_origin_weekly_news_to_robot('加密周报', '加密日报(09.22)：比特币盘整与机构布局凸显长期趋势', 'https://bj058omdwg.feishu.cn/docx/JN9od2Pt8okjF4x0cKscbNT9nWe')
    # image_key = api.upload_image_for_message('D:/Study2/BTC-news/send_to_weixin/qrcode.jpg')
    # print(image_key)
    # push_image_to_feishu("测试图片", 'D:/Study2/BTC-news/send_to_weixin/qrcode.jpg')