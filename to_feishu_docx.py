import json
import os
import requests
import webbrowser
from dotenv import load_dotenv
from to_feishu_robot import push_richtext_to_feishu

import lark_oapi as lark
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.drive.v1 import *
from utils.feishu_utils import extract_block_content_by_type, replace_block_text_by_text_and_type

# 加载环境变量
load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
FEISHU_FOLDER = 'I1nifXLCllLAu8dpnzTcHUGyngx' # BTC-周报

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
        
        # 使用 feishu_utils 中的通用函数处理块类型映射
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

async def write_to_docx(markdown_content=None, week_start_md='1.1', week_end_md='1.7'):
    """
    写入文档到飞书文档库
    """
    from llm_doubao import generate_title_and_summary_and_content
    title, summary= generate_title_and_summary_and_content(markdown_content, LOCAL_DEV=LOCAL_DEV)
    title = f"加密货币周报（{week_start_md}-{week_end_md}）：{title}"

    # 使用环境变量替代硬编码
    app_id = FEISHU_APP_ID
    app_secret = FEISHU_APP_SECRET
    folder_token = FEISHU_FOLDER
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
    
    # 替换辅助内容
    replace_block_text_by_text_and_type(document_id, "最近01.01 ~ 01.01之间，加密货币领域有什么热点新闻？", f"最近{week_start_md} ~ {week_end_md}之间，加密货币领域有什么热点新闻？")
    
    # 预处理markdown内容
    processed_markdown_content = preprocess_markdown_content(f"{summary}\n---\n{markdown_content}")
    
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
    await push_richtext_to_feishu(title, docs_url)

    lark.logger.info("Markdown content inserted into document successfully!")
    lark.logger.info(f"Document URL: {docs_url}")

    # 更新一级标题，并加颜色
    replace_block_text_by_text_and_type(document_id, "各国政策与监管变化", "一、政策与监管", "heading1", 5)
    replace_block_text_by_text_and_type(document_id, "企业与机构的活动", "二、企业与机构", "heading1", 5)
    replace_block_text_by_text_and_type(document_id, "价格波动与市场风险", "三、市场与风险（仅做观察）", "heading1", 5)
    replace_block_text_by_text_and_type(document_id, "其它相关事件", "四、其它动态", "heading1", 5)

    if LOCAL_DEV:
        # 在浏览器打开链接
        webbrowser.open(docs_url)


if __name__ == "__main__":
    # 读取markdown文件内容
    markdown_content = ''
    # markdown_file_path = os.path.join(os.path.dirname(__file__), "test", "write_to_feishu", "test_latest_summary.md")
    markdown_file_path = os.path.join(os.path.dirname(__file__), "latest_summary.md")

    try:
        with open(markdown_file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except Exception as e:
        lark.logger.error(f"Failed to read markdown file: {e}")
    
    FEISHU_FOLDER = 'RS3DfGQETlGxpXdK3ZdcJHaVnRg' # 周报TEST文件夹

    # 修复异步函数调用
    import asyncio
    asyncio.run(write_to_docx(markdown_content))