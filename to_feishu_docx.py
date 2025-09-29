import json
import os
import requests
import webbrowser
from dotenv import load_dotenv
from utils.feishu_robot_utils import push_origin_weekly_news_to_robot
from utils.image_utils import save_text_image, merge_images
from utils.feishu_docs_utils import FeishuDocumentAPI
import re

import lark_oapi as lark
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.drive.v1 import *
from utils.date_utils import days_between
from datetime import date
from utils.feishu_docs_utils import extract_block_content_by_type, replace_textblock_by_blocktype, create_text_block, create_callout_block, wrapper_block_for_desc

# 加载环境变量
load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
FEISHU_WEEKLY_FOLDER = 'I1nifXLCllLAu8dpnzTcHUGyngx' # BTC-周报
FEISHU_DAILY_FOLDER = 'MdSNf0W47lGdIidseGUceatlnsb' # BTC-日报
ALI_WEBSERVICE_URL = 'http://127.0.0.1:5000' if LOCAL_DEV else 'http://39.107.72.186:5000'

# 如果环境变量未设置，给出明确的错误提示
if not FEISHU_APP_ID:
    raise ValueError("请设置 FEISHU_APP_ID 环境变量")
if not FEISHU_APP_SECRET:
    raise ValueError("请设置 FEISHU_APP_SECRET 环境变量")


def get_tenant_access_token(app_id, app_secret):
    """获取 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if result.get('code') != 0:
        raise Exception(f"Failed to get tenant_access_token: {result.get('msg')}")
    
    return result['tenant_access_token']

def convert_markdown_to_blocks(app_id, app_secret, markdown_content):
    """将 Markdown 内容转换为飞书文档块"""
    # 获取 tenant_access_token
    tenant_access_token = get_tenant_access_token(app_id, app_secret)
    
    # 调用转换接口
    url = "https://open.feishu.cn/open-apis/docx/v1/documents/blocks/convert"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    data = {
        "content_type": "markdown",
        "content": markdown_content
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if result.get('code') != 0:
        raise Exception(f"Convert failed: {result.get('msg')}")
    
    # 获取原始blocks和排序ID列表
    original_blocks = result['data']['blocks']
    first_level_block_ids = result['data']['first_level_block_ids']
    
    # 创建block_id到block的映射
    block_map = {block['block_id']: block for block in original_blocks}
    
    # 按照first_level_block_ids的顺序重新排序blocks
    ordered_blocks = []
    for block_id in first_level_block_ids:
        if block_id in block_map:
            ordered_blocks.append(block_map[block_id])
    
    if LOCAL_DEV:
        # 将result['data']内容写入到test目录下的文件中
        output_file = os.path.join(os.path.dirname(__file__), "test", "write_to_feishu", "test_blocks_output.json")

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(ordered_blocks, f, indent=2, ensure_ascii=False)
            print(f"Blocks data saved to: {output_file}")
        except Exception as e:
            print(f"Failed to save blocks data: {e}")
    
    return ordered_blocks

def insert_blocks_to_document(document_id, ordered_blocks, app_id, app_secret):
    tenant_access_token = get_tenant_access_token(app_id, app_secret)
    
    # 为每个块生成临时ID并构建 descendants 数组
    children_ids = []
    descendants = []
    
    # 按照 ordered_blocks 的顺序处理
    for i, block in enumerate(ordered_blocks):
        temp_id = f"temp_block_{i:03d}"  # 使用三位数字确保排序
        children_ids.append(temp_id)
        
        # 构建 descendant 对象
        descendant = {
            "block_id": temp_id,
            "block_type": block.get('block_type'),
            "children": []
        }
        
        # 使用 feishu_docs_utils 中的通用函数处理块类型映射
        block_content = extract_block_content_by_type(block)
        # 直接使用提取的内容，无需额外特殊处理
        if block_content['type_name'] != 'unknown':
            descendant[block_content['type_name']] = block_content['content']
        else:
            # 对于未知类型，直接复制所有字段（除了 block_id）
            for key, value in block.items():
                if key not in ['block_id', 'block_type', 'children', 'parent_id']:
                    descendant[key] = value
        
        descendants.append(descendant)
    
    # 调用创建嵌套块接口 - 批量插入所有块
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/descendant?document_revision_id=-1"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # 批量插入所有块，保持 children_id 和 descendants 的顺序一致
    data = {
        "index": -1,
        "children_id": children_ids,  # 所有子块ID的列表
        "descendants": descendants    # 所有后代块的列表
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if result.get('code') != 0:
        raise Exception(f"Batch insert blocks failed: {result.get('msg')} - {result}")
    
    print(f"Successfully inserted {len(children_ids)} blocks in batch")
    
    return True

def preprocess_markdown_content(content):
    """预处理Markdown内容，将链接文本中的$符号替换为HTML实体"""
    # 先提取所有链接，替换其中的$符号，然后放回原文
    import re
    
    def replace_dollar_in_links(content):
        def replace_dollars_in_match(match):
            link_text = match.group(1)
            link_url = match.group(2)
            # 替换链接文本中的所有$符号
            processed_text = link_text.replace('$', '&#36;')
            return f'[{processed_text}]({link_url})'
        
        # 匹配所有Markdown链接格式并替换其中的$符号
        processed_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_dollars_in_match, content)
        return processed_content
    
    processed_content = replace_dollar_in_links(content)

    if LOCAL_DEV:
        # 保存处理后的markdown内容到同级目录
        processed_file_path = os.path.join(os.path.dirname(__file__), "test", "write_to_feishu", "test_latest_summary_processed.md")
        try:
            with open(processed_file_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            lark.logger.info(f"Processed markdown saved to: {processed_file_path}")
        except Exception as e:
            lark.logger.error(f"Failed to save processed markdown: {e}")
            return

    return processed_content

def create_feishu_document(title, app_id, app_secret, folder_token):
    """
    创建飞书文档
    
    Args:
        title (str): 文档标题
        app_id (str): 飞书应用ID
        app_secret (str): 飞书应用密钥
        folder_token (str): 飞书文件夹token
    
    Returns:
        str: 文档ID，如果创建失败返回None
    """
    # 创建client
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    # 构造请求对象
    request: CreateDocumentRequest = CreateDocumentRequest.builder() \
        .request_body(CreateDocumentRequestBody.builder()
            .folder_token(folder_token)
            .title(title)
            .build()) \
        .build()

    # 发起请求 - 创建文档
    response: CreateDocumentResponse = client.docx.v1.document.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.docx.v1.document.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return None

    # 获取文档ID
    document_id = response.data.document.document_id
    lark.logger.info(f"Document created successfully, document_id: {document_id}")
    return document_id

def copy_feishu_document(title, app_id, app_secret, folder_token, original_document_id):
    """
    复制飞书文档
    
    Args:
        title (str): 新文档标题
        app_id (str): 飞书应用ID
        app_secret (str): 飞书应用密钥
        folder_token (str): 飞书文件夹token
        original_document_id (str): 原始文档ID
    
    Returns:
        str: 新文档ID，如果复制失败返回None
    """
    # 创建client
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    # 构造请求对象
    request: CopyFileRequest = CopyFileRequest.builder() \
        .file_token(original_document_id) \
        .user_id_type("open_id") \
        .request_body(CopyFileRequestBody.builder()
            .name(title)
            .type("docx")
            .folder_token(folder_token)
            .build()) \
        .build()

    # 发起请求
    response: CopyFileResponse = client.drive.v1.file.copy(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.drive.v1.file.copy failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 获取文档ID
    document_id = response.data.file.token
    lark.logger.info(f"Document copied successfully, document_id: {document_id}")
    return document_id

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
    import re
    
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
        if line.strip() == '**总结**：' or line.strip() == '**总结**:':
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
    按照指定规则格式化字符串换行
    
    Args:
        text: 输入字符串
        max_chars: 每行最大字符数，默认10
        min_chars: 最小字符数，小于此数需要整合，默认5
    
    Returns:
        格式化后的字符串
    """
    # 首先按逗号分隔
    import re
    
    # 分割字符串，保留分隔符
    parts = re.split(r'([，,])', text)
    
    lines = []
    current_line = ""
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        # 如果是逗号分隔符，添加到当前行
        if part in ['，', ',']:
            current_line += part
            i += 1
            continue
            
        # 检查添加当前部分后是否超过最大字符数
        if len(current_line + part) <= max_chars:
            current_line += part
        else:
            # 如果当前行不为空，先保存当前行
            if current_line:
                lines.append(current_line)
                current_line = ""
            
            # 处理当前部分
            while len(part) > max_chars:
                # 强制在第10个字后换行
                lines.append(part[:max_chars])
                part = part[max_chars:]
            
            current_line = part
        
        i += 1
    
    # 添加最后一行
    if current_line:
        lines.append(current_line)
    
    # 处理短行整合 - 修复递归问题
    # final_lines = []
    # i = 0
    
    # while i < len(lines):
    #     current = lines[i]
        
    #     # 如果当前行字数小于最小字符数，尝试与下一行整合
    #     if len(current) < min_chars and i + 1 < len(lines):
    #         next_line = lines[i + 1]
            
    #         # 添加逗号连接
    #         if not current.endswith(('，', ',')):
    #             current += '，'
            
    #         combined = current + next_line
            
    #         # 如果整合后不超过最大字符数，则整合
    #         if len(combined) <= max_chars:
    #             final_lines.append(combined)
    #             i += 2  # 跳过下一行
    #         else:
    #             # 如果整合后超过最大字符数，直接强制分割，避免递归
    #             # 将combined按max_chars强制分割
    #             while len(combined) > max_chars:
    #                 final_lines.append(combined[:max_chars])
    #                 combined = combined[max_chars:]
                
    #             # 添加剩余部分
    #             if combined:
    #                 final_lines.append(combined)
                
    #             i += 2
    #     else:
    #         final_lines.append(current)
    #         i += 1
    
    return '\n'.join(lines)

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
    header_text_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_header_text.png")
    header_bg_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_background.png")
    header_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_header.png")
    save_text_image(
        text=final_title_for_imageheader,
        output_path=header_text_image_path,
        width=480,
        height=300,
        line_spacing=18,
        support_markdown=True,
        font_size=38,
        # font_color=(0, 0, 0),  # 黑色
        font_color=(255, 255, 255),  # 白色
        text_align='left',
        vertical_align='center'
    )

    # 合并图片
    image_configs = [
        {'path': header_bg_image_path, 'position': 'center'},
        {'path': header_text_image_path, 'position': 'center-right'}
    ]
    if merge_images(image_configs, output_path=header_image_path):
        # 新建日报飞书文档
        document_id = create_feishu_document(final_title, app_id, app_secret, folder_token)
        if document_id:
            try:
                api = FeishuDocumentAPI()
                print(f"上传头图：{header_image_path}")
                image_block_id = api.insert_image_block_to_document(document_id, header_image_path)
                print(f"上传成功！图片文件token: {image_block_id}")

                print(f"创建倒计时高亮块")
                between_days = days_between(date.today(), date(2035, 1, 1))
                between_years = between_days // 365
                end_this_year = date(date.today().year, 12, 31)
                
                data1 = wrapper_block_for_desc(create_text_block(f'十年倒计时 — {between_days}天（距离2035年还有 {between_years} 年 {days_between(date.today(), end_this_year)} 天）'), 'block_id1')
                callout = wrapper_block_for_desc(create_callout_block(), 'callout_id11', children=[data1['block_id']])
                # 创建块数据
                blocks = {
                    'children_id': [callout['block_id']],
                    'index': -1,
                    'descendants': [callout, data1]
                }
                block_ids = api.insert_descendant_blocks_to_document(document_id, blocks)
                print(f"创建成功")
            except Exception as e:
                print(f"上传失败: {e}")
        
        # 调用convert接口将markdown转换为文档块
        try:
            ordered_blocks = convert_markdown_to_blocks(app_id, app_secret, cleaned_content)
            lark.logger.info(f"Markdown converted successfully, got {len(ordered_blocks)} blocks")
        except Exception as e:
            lark.logger.error(f"Failed to convert markdown: {e}")
            return
        
        # 插入文档块到文档中（分批处理，每次最多5个块）
        batch_size = 10
        
        for i in range(0, len(ordered_blocks), batch_size):
            batch_blocks = ordered_blocks[i:i + batch_size]
            
            try:
                result = insert_blocks_to_document(document_id, batch_blocks, app_id, app_secret)
                lark.logger.info(f"Batch {i//batch_size + 1} inserted successfully ({len(batch_blocks)} blocks)")
            except Exception as e:
                lark.logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
                return
        
        docs_url = f"https://bj058omdwg.feishu.cn/docx/{document_id}"
        print(docs_url)
        if LOCAL_DEV:
            # 在浏览器打开链接
            webbrowser.open(docs_url)
        
        # 发送请求：将飞书文档推送到公众号
        try:
            print(f"发送请求{ALI_WEBSERVICE_URL}/api/push_daily_news。{final_title}，链接：{docs_url}")
            
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
    # 正式推送发起后，把二维截图给我，并附带再次请求二维码的链接（打开后就是二维码）
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
    
    # # 创建飞书文档
    # document_id = create_feishu_document(title, app_id, app_secret, folder_token)
    # if not document_id:
    #     lark.logger.error("Failed to create Feishu document")
    #     return
    # 复制飞书文档
    document_id = copy_feishu_document(title, app_id, app_secret, folder_token, original_document_id)
    if not document_id:
        lark.logger.error("Failed to copy Feishu document")
        return
    
    # 替换辅助内容（方便手动拉取OpenAI的信息）
    replace_textblock_by_blocktype(document_id, "最近01.01 ~ 01.01之间，加密货币领域有什么热点新闻？", f"最近{week_start_md} ~ {week_end_md}之间，加密货币领域有什么热点新闻？")
    
    # 预处理markdown内容
    processed_markdown_content = preprocess_markdown_content(f"{summary}\n---\n{news_content}")
    
    # 调用convert接口将markdown转换为文档块
    try:
        ordered_blocks = convert_markdown_to_blocks(app_id, app_secret, processed_markdown_content)
        lark.logger.info(f"Markdown converted successfully, got {len(ordered_blocks)} blocks")
    except Exception as e:
        lark.logger.error(f"Failed to convert markdown: {e}")
        return
    
    # 插入文档块到文档中（分批处理，每次最多5个块）
    batch_size = 10
    
    for i in range(0, len(ordered_blocks), batch_size):
        batch_blocks = ordered_blocks[i:i + batch_size]
        
        try:
            result = insert_blocks_to_document(document_id, batch_blocks, app_id, app_secret)
            lark.logger.info(f"Batch {i//batch_size + 1} inserted successfully ({len(batch_blocks)} blocks)")
        except Exception as e:
            lark.logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
            return
    
    docs_url = f"https://bj058omdwg.feishu.cn/docx/{document_id}"
    push_origin_weekly_news_to_robot("加密周报", title, docs_url)

    lark.logger.info("Markdown content inserted into document successfully!")
    lark.logger.info(f"Document URL: {docs_url}")

    # 更新一级标题，并加颜色
    replace_textblock_by_blocktype(document_id, "各国政策与监管变化", "一、政策与监管", "heading1", 5)
    replace_textblock_by_blocktype(document_id, "企业与机构的活动", "二、企业与机构", "heading1", 5)
    replace_textblock_by_blocktype(document_id, "价格波动与市场风险", "三、市场与风险（仅做观察）", "heading1", 5)
    replace_textblock_by_blocktype(document_id, "其它相关事件", "四、其它动态", "heading1", 5)

    if LOCAL_DEV:
        # 在浏览器打开链接
        webbrowser.open(docs_url)


if __name__ == "__main__":

    # ### 测试生成周报：读取本地文件并保存到飞书文档中

    # 读取markdown文件内容
    markdown_content = ''
    # markdown_file_path = os.path.join(os.path.dirname(__file__), "test", "write_to_feishu", "test_latest_summary.md")
    markdown_file_path = os.path.join(os.path.dirname(__file__), "files", "latest_summary.md")

    # try:
    #     with open(markdown_file_path, 'r', encoding='utf-8') as f:
    #         markdown_content = f.read()
    # except Exception as e:
    #     lark.logger.error(f"Failed to read markdown file: {e}")
    
    import asyncio
    # 修复异步函数调用
    # FEISHU_WEEKLY_FOLDER = 'RS3DfGQETlGxpXdK3ZdcJHaVnRg' # 周报TEST文件夹
    # asyncio.run(write_to_weekly_docx(markdown_content))

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
    date_md = '09.13'
    title = '比特币盘整蓄势，机构增持与宏观利好推动市场'
    final_title_for_imageheader = f"**加密日报({date_md})**\n{format_string_with_line_breaks(title)}"
    # 生成头图，替换标题图片
    header_text_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_header_text.png")
    header_bg_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_background.png")
    header_image_path = os.path.join(os.path.dirname(__file__), "feishu_docs", "daily_header.png")
    save_text_image(
        text=final_title_for_imageheader,
        output_path=header_text_image_path,
        width=480,
        height=300,
        line_spacing=20,
        support_markdown=True,
        font_size=40,
        # font_color=(0, 0, 0),  # 黑色
        font_color=(255, 255, 255),  # 白色
        text_align='left',
        vertical_align='center'
    )

    # 合并图片
    image_configs = [
        {'path': header_bg_image_path, 'position': 'center'},
        {'path': header_text_image_path, 'position': 'center-right'}
    ]
    merge_images(image_configs, output_path=header_image_path)