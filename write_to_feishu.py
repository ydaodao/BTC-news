import json
import os
import requests
import webbrowser
from dotenv import load_dotenv

import lark_oapi as lark
from lark_oapi.api.docx.v1 import *

# 加载环境变量
load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
FEISHU_FOLDER = 'RS3DfGQETlGxpXdK3ZdcJHaVnRg'

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


def insert_blocks_to_document(document_id, ordered_blocks, app_id, app_secret, start_index=0):
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
        
        # 根据块类型添加相应的内容 - 根据官方文档修正块类型映射
        if block.get('block_type') == 2:  # 文本块
            descendant["text"] = block.get('text', {})
        elif block.get('block_type') == 3:  # 标题1块
            descendant["heading1"] = block.get('heading1', {})
        elif block.get('block_type') == 4:  # 标题2块
            descendant["heading2"] = block.get('heading2', {})
        elif block.get('block_type') == 5:  # 标题3块
            descendant["heading3"] = block.get('heading3', {})
        elif block.get('block_type') == 6:  # 标题4块
            descendant["heading4"] = block.get('heading4', {})
        elif block.get('block_type') == 7:  # 标题5块
            descendant["heading5"] = block.get('heading5', {})
        elif block.get('block_type') == 8:  # 标题6块
            descendant["heading6"] = block.get('heading6', {})
        elif block.get('block_type') == 9:  # 标题7块
            descendant["heading7"] = block.get('heading7', {})
        elif block.get('block_type') == 10:  # 标题8块
            descendant["heading8"] = block.get('heading8', {})
        elif block.get('block_type') == 11:  # 标题9块
            descendant["heading9"] = block.get('heading9', {})
        elif block.get('block_type') == 12:  # 无序列表块
            descendant["bullet"] = block.get('bullet', {})
        elif block.get('block_type') == 13:  # 有序列表块
            descendant["ordered"] = block.get('ordered', {})
        elif block.get('block_type') == 14:  # 代码块
            descendant["code"] = block.get('code', {})
        elif block.get('block_type') == 15:  # 引用块
            descendant["quote"] = block.get('quote', {})
        elif block.get('block_type') == 17:  # 待办事项块
            descendant["todo"] = block.get('todo', {})
        elif block.get('block_type') == 18:  # 多维表格块
            descendant["bitable"] = block.get('bitable', {})
        elif block.get('block_type') == 19:  # 高亮块
            descendant["callout"] = block.get('callout', {})
        elif block.get('block_type') == 20:  # 会话卡片块
            descendant["chat_card"] = block.get('chat_card', {})
        elif block.get('block_type') == 21:  # 流程图 & UML块
            descendant["diagram"] = block.get('diagram', {})
        elif block.get('block_type') == 22:  # 分割线块
            descendant["divider"] = {}
        elif block.get('block_type') == 23:  # 文件块
            descendant["file"] = block.get('file', {})
        elif block.get('block_type') == 24:  # 分栏块
            descendant["grid"] = block.get('grid', {})
        elif block.get('block_type') == 25:  # 分栏列块
            descendant["grid_column"] = block.get('grid_column', {})
        elif block.get('block_type') == 26:  # 内嵌网页块
            descendant["iframe"] = block.get('iframe', {})
        elif block.get('block_type') == 27:  # 图片块
            descendant["image"] = block.get('image', {})
        elif block.get('block_type') == 28:  # 开放平台小组件块
            descendant["isv"] = block.get('isv', {})
        elif block.get('block_type') == 29:  # 思维笔记块
            descendant["mindnote"] = block.get('mindnote', {})
        elif block.get('block_type') == 30:  # 电子表格块
            descendant["sheet"] = block.get('sheet', {})
        elif block.get('block_type') == 31:  # 表格块
            table_data = block.get('table', {})
            # 移除只读字段
            if 'merge_info' in table_data:
                del table_data['merge_info']
            descendant["table"] = table_data
        elif block.get('block_type') == 32:  # 表格单元格块
            descendant["table_cell"] = block.get('table_cell', {})
        elif block.get('block_type') == 33:  # 视图块
            descendant["view"] = block.get('view', {})
        elif block.get('block_type') == 34:  # 引用容器块
            descendant["quote_container"] = {}
        elif block.get('block_type') == 35:  # 任务块
            descendant["task"] = block.get('task', {})
        elif block.get('block_type') == 36:  # OKR块
            descendant["okr"] = block.get('okr', {})
        elif block.get('block_type') == 37:  # OKR Objective块
            descendant["okr_objective"] = block.get('okr_objective', {})
        elif block.get('block_type') == 38:  # OKR Key Result块
            descendant["okr_key_result"] = block.get('okr_key_result', {})
        elif block.get('block_type') == 39:  # OKR进展块
            descendant["okr_progress"] = block.get('okr_progress', {})
        elif block.get('block_type') == 40:  # 文档小组件块
            descendant["add_ons"] = block.get('add_ons', {})
        elif block.get('block_type') == 41:  # Jira问题块
            descendant["jira_issue"] = block.get('jira_issue', {})
        elif block.get('block_type') == 42:  # Wiki子目录块
            descendant["wiki_catalog"] = block.get('wiki_catalog', {})
        elif block.get('block_type') == 43:  # 画板块
            descendant["board"] = block.get('board', {})
        elif block.get('block_type') == 44:  # 议程块
            descendant["agenda"] = block.get('agenda', {})
        elif block.get('block_type') == 45:  # 议程项块
            descendant["agenda_item"] = block.get('agenda_item', {})
        elif block.get('block_type') == 46:  # 议程项标题块
            descendant["agenda_item_title"] = block.get('agenda_item_title', {})
        elif block.get('block_type') == 47:  # 议程项内容块
            descendant["agenda_item_content"] = block.get('agenda_item_content', {})
        elif block.get('block_type') == 48:  # 链接预览块
            descendant["link_preview"] = block.get('link_preview', {})
        else:
            # 对于其他类型，直接复制所有字段（除了 block_id）
            for key, value in block.items():
                if key not in ['block_id', 'block_type', 'children', 'parent_id']:
                    descendant[key] = value
        
        descendants.append(descendant)
    
    # 调用创建嵌套块接口 - 尝试逐个插入而不是批量插入
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/descendant?document_revision_id=-1"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    import time
    
    # 逐个插入块以保持顺序
    for i, (child_id, descendant) in enumerate(zip(children_ids, descendants)):
        data = {
            "index": start_index + i,  # 使用全局递增的索引
            "children_id": [child_id],
            "descendants": [descendant]
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"Insert block {start_index + i} failed: {result.get('msg')} - {result}")
        
        print(f"Successfully inserted block {start_index + i + 1}")
        
        # 控制API调用频率：每秒最多2次，即每次调用间隔0.5秒
        time.sleep(0.5)
    
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

async def write_to_docx(markdown_content=None, week_start_md='01.01', week_end_md='01.07'):
    """
    写入文档到飞书文档库
    """
    from main import generate_title_and_summary_and_content
    title, summary= generate_title_and_summary_and_content(markdown_content)
    title = f"加密货币周报（{week_start_md}-{week_end_md}）：{title}"

    # 使用环境变量替代硬编码
    app_id = FEISHU_APP_ID
    app_secret = FEISHU_APP_SECRET
    
    # 创建client
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    # 构造请求对象
    request: CreateDocumentRequest = CreateDocumentRequest.builder() \
        .request_body(CreateDocumentRequestBody.builder()
            .folder_token(FEISHU_FOLDER)
            .title(title)
            .build()) \
        .build()

    # 发起请求 - 创建文档
    response: CreateDocumentResponse = client.docx.v1.document.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.docx.v1.document.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 获取文档ID
    document_id = response.data.document.document_id
    lark.logger.info(f"Document created successfully, document_id: {document_id}")
        

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
    batch_size = 5
    total_inserted = 0  # 跟踪已插入的块数量
    
    for i in range(0, len(ordered_blocks), batch_size):
        batch_blocks = ordered_blocks[i:i + batch_size]
        
        try:
            result = insert_blocks_to_document(document_id, batch_blocks, app_id, app_secret, total_inserted)
            total_inserted += len(batch_blocks)  # 更新已插入的块数量
            lark.logger.info(f"Batch {i//batch_size + 1} inserted successfully ({len(batch_blocks)} blocks)")
        except Exception as e:
            lark.logger.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
            return
    
    lark.logger.info("Markdown content inserted into document successfully!")
    lark.logger.info(f"Document URL: https://bj058omdwg.feishu.cn/docx/{document_id}")

    if LOCAL_DEV:
        # 在浏览器打开链接
        webbrowser.open(f"https://bj058omdwg.feishu.cn/docx/{document_id}")


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

    write_to_docx(markdown_content)