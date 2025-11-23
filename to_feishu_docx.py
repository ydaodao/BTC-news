import json
import os
import requests
import webbrowser
from dotenv import load_dotenv
from utils.feishu_robot_utils import push_origin_weekly_news_to_robot
from utils.image_utils import save_text_image, merge_images
from utils.feishu_block_utils import FeishuBlockAPI
from utils.feishu_docs_utils import FeishuDocsAPI
import re
import time

import lark_oapi as lark
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.drive.v1 import *
from utils.date_utils import days_between
from datetime import date
from utils.feishu_block_utils import extract_block_content_by_type, replace_textblock_by_blocktype, create_text_block, create_callout_block, wrapper_block_for_desc
from utils.feishu_docs_utils import create_feishu_document, copy_feishu_document
from ahr999.ahr_web_crawler import fetch_ahr999

# 加载环境变量
load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
FEISHU_WEEKLY_FOLDER = 'I1nifXLCllLAu8dpnzTcHUGyngx' # BTC-周报
FEISHU_DAILY_FOLDER = 'MdSNf0W47lGdIidseGUceatlnsb' # BTC-日报
FEISHU_REFERENCE_DOCS_ID = 'MugEdoDduoEBZfxC5TocV65Nnhb' # 参考文章的地址
ALI_WEBSERVICE_URL = 'http://127.0.0.1:5000' if LOCAL_DEV else 'http://39.107.72.186:5000'

# 如果环境变量未设置，给出明确的错误提示
if not FEISHU_APP_ID:
    raise ValueError("请设置 FEISHU_APP_ID 环境变量")
if not FEISHU_APP_SECRET:
    raise ValueError("请设置 FEISHU_APP_SECRET 环境变量")


def clean_markdown_content_for_daily_docs(markdown_content):
    """
    检查markdown_content内容格式是否符合要求，并进行清理
    
    要求格式：
    ### 一、聚类标题
    **总结**：
    1. 
    2. 
    **参考**：
    - [原始新闻标题](url)
    - [原始新闻标题](url)
    ---
    
    清理规则：
    1. 去掉所有的 **参考**： 及其下面的链接内容
    2. 去掉 **总结**： 标题，但保留总结下的内容
    """
    
    # 按行分割内容
    lines = markdown_content.split('\n')
    cleaned_lines = []
    skip_references = False
    
    for line in lines:
        # 检查是否遇到参考部分
        if re.match(r'^\*\*参考\*\*.*?', line.strip()):
            skip_references = True
            continue
        
        # 检查是否遇到分隔符，结束参考部分跳过
        if line.strip() == '---':
            skip_references = False
            # cleaned_lines.append(line)
            continue
        
        # 检查是否遇到新的聚类标题，结束参考部分跳过
        if line.strip().startswith('###'):
            skip_references = False
            cleaned_lines.append(line)
            continue
        
        # 跳过参考部分的内容
        if skip_references:
            continue
        
        # 去掉 **总结**： 标题，但保留后面的内容
        if re.match(r'^\*\*总结.*?', line.strip()):
            continue
        
        # 保留其他内容
        cleaned_lines.append(line)
    
    cleaned_content = '\n'.join(cleaned_lines)
    
    # 保存响应内容到文件
    latest_summary_cleaned = os.path.join(os.path.dirname(__file__), "files", "latest_summary_cleaned.md")
    try:
        with open(latest_summary_cleaned, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        print(f"清理后摘要已保存到: {latest_summary_cleaned}")
    except Exception as e:
        print(f"保存清理后摘要失败: {e}")
    
    return cleaned_content

def format_string_with_line_breaks(text, max_chars=11, min_chars=5):
    """
    按照指定规则格式化字符串换行，智能处理中英文混合情况
    
    Args:
        text: 输入字符串
        max_chars: 每行最大字符数，默认11
        min_chars: 最小字符数，小于此数需要整合，默认5
    
    Returns:
        格式化后的字符串
    """
    import re
    
    # 特殊处理：对于常见的英文缩写，将其视为与后面的中文词组成一个整体
    text = re.sub(r'(ETF|BTC|NFT|DeFi|DAO|DEX|CEX)(\s*)(?=[\u4e00-\u9fff])', r'\1', text)
    
    # 将文本视为一个整体，按最大宽度进行分割
    result_lines = []
    remaining_text = text
    
    while remaining_text:
        # 计算当前可以放入一行的最佳切分点
        best_cut_point = find_best_cut_point(remaining_text, max_chars)
        
        if best_cut_point > 0:
            result_lines.append(remaining_text[:best_cut_point])
            remaining_text = remaining_text[best_cut_point:]
        else:
            # 如果找不到合适的切分点，强制切分
            result_lines.append(remaining_text[:max_chars])
            remaining_text = remaining_text[max_chars:]
    
    return '\n'.join(result_lines)

def find_best_cut_point(text, max_width):
    """
    找到最佳的切分点，使得切分后的文本不超过最大宽度
    优先在标点符号后切分，其次在词语边界切分
    """
    if not text:
        return 0
        
    # 计算文本的实际显示宽度
    def get_width(s):
        return sum(1.0 if '\u4e00' <= c <= '\u9fff' else 0.5 for c in s)
    
    # 如果整个文本宽度不超过最大宽度，直接返回全部
    if get_width(text) <= max_width:
        return len(text)
    
    # 寻找最佳切分点
    best_point = 0
    current_width = 0
    
    # 标点符号优先级
    punctuation = ['。', '！', '？', '；', '，', '.', '!', '?', ';', ',']
    
    # 首先尝试在标点符号处切分
    for i in range(len(text)):
        char = text[i]
        char_width = 1.0 if '\u4e00' <= char <= '\u9fff' else 0.5
        
        if current_width + char_width <= max_width:
            current_width += char_width
            
            # 如果当前字符是标点符号，记录为潜在切分点
            if char in punctuation:
                best_point = i + 1  # 包含标点符号
        else:
            break
    
    # 如果没有找到标点符号切分点，尝试在词语边界切分
    if best_point == 0:
        # 英文单词和中文词语的边界
        for i in range(len(text) - 1):
            if i >= max_width:
                break
                
            char = text[i]
            next_char = text[i + 1]
            
            # 英文和中文的边界
            is_boundary = (('\u4e00' <= char <= '\u9fff' and not '\u4e00' <= next_char <= '\u9fff') or
                          (not '\u4e00' <= char <= '\u9fff' and '\u4e00' <= next_char <= '\u9fff'))
            
            char_width = 1.0 if '\u4e00' <= char <= '\u9fff' else 0.5
            
            if current_width + char_width <= max_width:
                current_width += char_width
                
                if is_boundary:
                    best_point = i + 1
            else:
                break
    
    # 如果仍然没有找到合适的切分点，就在最大宽度处切分
    if best_point == 0:
        # 计算最大宽度对应的字符位置
        i = 0
        width = 0
        while i < len(text):
            char_width = 1.0 if '\u4e00' <= text[i] <= '\u9fff' else 0.5
            if width + char_width > max_width:
                break
            width += char_width
            i += 1
        best_point = i
    
    return best_point

def create_header_image(text, type='daily'):
    header_text_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_header_text.png")
    header_bg_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_background.png")
    header_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_header.png")
    save_text_image(
        text=text,
        output_path=header_text_image_path,
        width=480,
        height=300,
        line_spacing=18,
        support_markdown=True,
        font_size=38,
        font_color=(255, 255, 255) if type == 'daily' else (212,180,91),
        text_align='left',
        vertical_align='center'
    )       

    # 合并图片
    image_configs = [
        {'path': header_bg_image_path, 'position': 'center'},
        {'path': header_text_image_path, 'position': 'center-right'}
    ]
    if merge_images(image_configs, output_path=header_image_path):
        return header_image_path
    else:
        return None



async def write_to_daily_docx(news_content=None, title=None, summary=None, date_md=None):
    # 使用环境变量替代硬编码
    app_id = FEISHU_APP_ID
    app_secret = FEISHU_APP_SECRET
    folder_token = FEISHU_DAILY_FOLDER

    final_title = f"加密日报({date_md})：{title}"
    final_title_for_imageheader = f"**加密日报({date_md})**\n{format_string_with_line_breaks(title)}"
    
    # 去除内容中多余的部分
    cleaned_content = clean_markdown_content_for_daily_docs(news_content)

    # 生成头图，替换标题图片
    header_image_path = create_header_image(final_title_for_imageheader)
    if not header_image_path:
        print("创建头图失败")
        return
    
    # 新建日报飞书文档
    api = FeishuBlockAPI()
    document_id = create_feishu_document(final_title, app_id, app_secret, folder_token)
    if document_id:
        try:
            # 价格高亮块
            print(f"创建价格高亮块")
            _, ahr999, btc_price, _, _ = fetch_ahr999()
            data0 = wrapper_block_for_desc(create_text_block(f'AHR999：{ahr999}；价格：{btc_price}'), 'block_id0')
            callout0 = wrapper_block_for_desc(create_callout_block(), 'callout_id00', children=[data0['block_id']])
            # 创建块数据
            blocks0 = {
                'children_id': [callout0['block_id']],
                'index': -1,
                'descendants': [callout0, data0]
            }
            block_ids0 = api.insert_descendant_blocks_to_document(document_id, blocks0)
            print(f"创建成功")

            # 上传头图
            print(f"上传头图：{header_image_path}")
            image_block_id = api.insert_image_block_to_document(document_id, header_image_path)
            print(f"上传成功！图片文件token: {image_block_id}")

            # 倒计时高亮块
            print(f"创建倒计时高亮块")
            between_days = days_between(date.today(), date(2035, 1, 1))
            between_years = between_days // 365
            end_this_year = date(date.today().year, 12, 31)
            
            data1 = wrapper_block_for_desc(create_text_block(f'十年倒计时 — {between_days}天（距离2035年还有 {between_years} 年 {days_between(date.today(), end_this_year)} 天）'), 'block_id1')
            callout1 = wrapper_block_for_desc(create_callout_block(), 'callout_id11', children=[data1['block_id']])
            # 创建块数据
            blocks1 = {
                'children_id': [callout1['block_id']],
                'index': -1,
                'descendants': [callout1, data1]
            }
            block_ids1 = api.insert_descendant_blocks_to_document(document_id, blocks1)
            print(f"创建成功")
        except Exception as e:
            print(f"上传失败: {e}")
    
    # 调用convert接口将markdown转换为文档块
    ordered_blocks = api.convert_markdown_to_blocks(cleaned_content)
    
    # 插入文档块到文档中（分批处理）
    batch_size = 10
    for i in range(0, len(ordered_blocks), batch_size):
        batch_blocks = ordered_blocks[i:i + batch_size]
        try:
            block_ids = api.insert_blocks_to_document(document_id, batch_blocks)
            time.sleep(0.5)
            lark.logger.info(f"Batch {i//batch_size + 1} inserted successfully ({len(block_ids)} blocks)")
        except Exception as e:
            lark.logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
            return
    
    # 插入引用的文章
    api_docs = FeishuDocsAPI()
    blocks_for_desendent = api_docs.get_all_document_blocks_for_desendent(FEISHU_REFERENCE_DOCS_ID)
    block_ids = api.insert_descendant_blocks_to_document(document_id, blocks_for_desendent)
    lark.logger.info(f"插入的引用文章块ID：{len(block_ids)}")
    
    docs_url = f"https://bj058omdwg.feishu.cn/docx/{document_id}"
    lark.logger.info(f"创建的飞书文档链接：{docs_url}")
    if LOCAL_DEV:
        # 在浏览器打开链接
        webbrowser.open(docs_url)
    
    # 发送请求：将飞书文档推送到公众号
    try:
        lark.logger.info(f"发送请求{ALI_WEBSERVICE_URL}/api/push_daily_news。{final_title}，链接：{docs_url}")
        
        # 创建session并配置重试机制
        session = requests.Session()
        retry_strategy = requests.packages.urllib3.util.retry.Retry(
            total=3,  # 最多重试3次
            backoff_factor=1,  # 重试间隔时间将按1, 2, 4秒递增
            status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码会触发重试
            allowed_methods=["POST"]  # 允许POST方法重试
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 使用配置好的session发送请求
        response = session.post(
            url=f'{ALI_WEBSERVICE_URL}/api/push_daily_news', 
            json={"feishu_docx_title": final_title, "feishu_docx_url": docs_url},
            headers={'Content-Type': 'application/json'},
            proxies=None,
            timeout=600
        )
        response.raise_for_status()

        # 打印详细的响应信息
        result = response.json()
        print(f"飞书推送响应: {result}")
        
        if result.get('success'):
            print("推送到公众号成功！")
            result_data = result.get('data')
            preview_page_title = result_data.get('preview_page_title')
            preview_page_url = result_data.get('preview_page_url')

            return docs_url, preview_page_title, preview_page_url
        else:
            print(f"推送失败: {result.get('msg', '未知错误')}")
    except requests.exceptions.RequestException as e:
        print(f"消息推送到公众号失败：{e}")
    
    # 发送机器人预览内容：主体消息、推送到微信公众号用，超链接（指向阿里云）
    # 阿里云将文档推送到公众号后，返回公众号链接 至飞书消息、以及正式推送的超链接
    # 我打开后预览消息，并可以发起正式推送
    return None, None, None

async def write_to_weekly_docx(news_content=None, week_start_md='1.1', week_end_md='1.7'):
    """
    写入文档到飞书文档库
    """
    from llm_doubao import generate_title_and_summary_and_content
    title, summary= generate_title_and_summary_and_content(news_content, LOCAL_DEV=LOCAL_DEV)
    title = f"加密货币周报（{week_start_md}-{week_end_md}）：{title}"

    # 使用环境变量替代硬编码
    app_id = FEISHU_APP_ID
    app_secret = FEISHU_APP_SECRET
    folder_token = FEISHU_WEEKLY_FOLDER
    original_document_id = "FIqsdVXJfozn3ixLAfycCG8xnUc"
    
    # 复制飞书文档
    document_id = copy_feishu_document(title, app_id, app_secret, folder_token, original_document_id)
    if not document_id:
        lark.logger.error("Failed to copy Feishu document")
        return
    
    # 替换辅助内容（方便手动拉取OpenAI的信息）
    replace_textblock_by_blocktype(document_id, "最近01.01 ~ 01.01之间，加密货币领域有什么热点新闻？", f"最近{week_start_md} ~ {week_end_md}之间，加密货币领域有什么热点新闻？")
    
    # 调用convert接口将markdown转换为文档块
    api = FeishuBlockAPI()
    ordered_blocks = api.convert_markdown_to_blocks(f"{summary}\n---\n{news_content}")
    
    # 插入文档块到文档中（分批处理，每次最多5个块）
    batch_size = 10
    for i in range(0, len(ordered_blocks), batch_size):
        batch_blocks = ordered_blocks[i:i + batch_size]
        try:
            block_ids = api.insert_blocks_to_document(document_id, batch_blocks)
            time.sleep(0.5)
            lark.logger.info(f"Batch {i//batch_size + 1} inserted successfully ({len(block_ids)} blocks)")
        except Exception as e:
            lark.logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
            return
    # 更新一级标题，并加颜色
    replace_textblock_by_blocktype(document_id, "各国政策与监管变化", "一、政策与监管", "heading1", 5)
    replace_textblock_by_blocktype(document_id, "企业与机构的活动", "二、企业与机构", "heading1", 5)
    replace_textblock_by_blocktype(document_id, "价格波动与市场风险", "三、市场与风险（仅做观察）", "heading1", 5)
    replace_textblock_by_blocktype(document_id, "其它相关事件", "四、其它动态", "heading1", 5)

    # 插入引用的文章
    api_docs = FeishuDocsAPI()
    blocks_for_desendent = api_docs.get_all_document_blocks_for_desendent(FEISHU_REFERENCE_DOCS_ID)
    block_ids = api.insert_descendant_blocks_to_document(document_id, blocks_for_desendent)
    lark.logger.info(f"插入的引用文章块ID：{len(block_ids)}")

    # 推送飞书消息
    docs_url = f"https://bj058omdwg.feishu.cn/docx/{document_id}"
    push_origin_weekly_news_to_robot("加密周报", title, docs_url)

    lark.logger.info("Markdown content inserted into document successfully!")
    lark.logger.info(f"Document URL: {docs_url}")
    if LOCAL_DEV:
        # 在浏览器打开链接
        webbrowser.open(docs_url)

if __name__ == "__main__":

    # ### 测试生成周报：读取本地文件并保存到飞书文档中
    def test_write_to_docx():
        # 读取markdown文件内容
        markdown_content = ''
        # markdown_file_path = os.path.join(os.path.dirname(__file__), "test", "write_to_feishu", "test_latest_summary.md")
        markdown_file_path = os.path.join(os.path.dirname(__file__), "files", "latest_summary.md")

        try:
            with open(markdown_file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        except Exception as e:
            lark.logger.error(f"Failed to read markdown file: {e}")
        
        import asyncio
        global FEISHU_WEEKLY_FOLDER
        # FEISHU_WEEKLY_FOLDER = 'RS3DfGQETlGxpXdK3ZdcJHaVnRg' # 周报TEST文件夹
        # asyncio.run(write_to_weekly_docx(markdown_content))

        global FEISHU_DAILY_FOLDER
        FEISHU_DAILY_FOLDER = 'GqokfczlBl8lZLdwqJGcjw4inMc' # 日报TEST文件夹
        asyncio.run(write_to_daily_docx(markdown_content, title='比特币震荡盘整与机构持续吸筹', date_md='09.13'))
    test_write_to_docx()


    # asyncio.run(write_to_daily_docx(markdown_content, "机构增持与矿工抛售并存，AI支付生态初现"))

    # ### 测试生成周报：从OpenAI获取内容并保存到飞书文档中


    # 1. 测试标题分隔
    # test_string = "机构增持与矿工抛售并存，AI支付生态初现AI支付生态，AI，AI测试，AI"
    # result = format_string_with_line_breaks(test_string)
    # print("原字符串:", test_string)
    # print("格式化结果:")
    # print(result)
    # print("\n每行字符数:")
    # for i, line in enumerate(result.split('\n'), 1):
    #     print(f"第{i}行: {len(line)}字 - {line}")

    # 2. 测试发送service
    # try:
    #     response = requests.post(
    #         url=f'{ALI_WEBSERVICE_URL}/api/send_to_wx_gzh', 
    #         json={"feishu_docx_title": 'final_title', "feishu_docx_url": 'docs_url'},
    #         headers={'Content-Type': 'application/json'},
    #         timeout=10
    #     )
    #     response.raise_for_status()

    #     # 打印详细的响应信息
    #     result = response.json()
    #     print(f"飞书推送响应: {result}")
        
    #     if result.get('success'):
    #         print("消息直接推送到飞书成功！")
    #     else:
    #         print(f"推送失败: {result.get('msg', '未知错误')}")
    # except requests.exceptions.RequestException as e:
    #     print(f"消息直接推送到飞书失败：{e}")

    # print()

    # 3. 测试标题图片生成
    # def test_create_header_image():
    #     date_md = '09.13'
    #     title = '比特币突破12.5万美元，ETF资金流入与宏观避险需求推动上涨'
    #     final_title_for_imageheader = f"**加密日报({date_md})**\n{format_string_with_line_breaks(title)}"
    #     create_header_image(final_title_for_imageheader, type='daily')
    # test_create_header_image()
