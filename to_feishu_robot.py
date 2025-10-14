import os
import pyperclip
from datetime import datetime

if __name__ == '__main__':
    # 读取飞书消息模板
    template_path = os.path.join(os.path.dirname(__file__), 'send_to_weixin', 'templates', 'daily_news_template.json')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 替换模板中的占位符
    now_md = datetime.now().strftime('%m.%d')
    data_str = template_content.replace('{title}', "title_escaped") \
                              .replace('{message_content}', "message_content_escaped") \
                              .replace('{now_md}', now_md or '') \
                              .replace('{docs_url}', "docs_url" or '') \
                              .replace('{wx_preview_page_url}', "wx_preview_page_url" or '推送公众号失败！') \
                              .replace('{regenerate_daily_url}', f"{"ALI_WEBSERVICE_URL"}/regenerate_daily_news" or '')

    pyperclip.copy(data_str)