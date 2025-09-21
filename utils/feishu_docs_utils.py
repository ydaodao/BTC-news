import requests
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 飞书文档块类型映射
BLOCK_TYPE_MAPPING = {
    2: 'text',           # 文本块
    3: 'heading1',       # 标题1块
    4: 'heading2',       # 标题2块
    5: 'heading3',       # 标题3块
    6: 'heading4',       # 标题4块
    7: 'heading5',       # 标题5块
    8: 'heading6',       # 标题6块
    9: 'heading7',       # 标题7块
    10: 'heading8',      # 标题8块
    11: 'heading9',      # 标题9块
    12: 'bullet',        # 无序列表块
    13: 'ordered',       # 有序列表块
    14: 'code',          # 代码块
    15: 'quote',         # 引用块
    17: 'todo',          # 待办事项块
    18: 'bitable',       # 多维表格块
    19: 'callout',       # 高亮块
    20: 'chat_card',     # 会话卡片块
    21: 'diagram',       # 流程图 & UML块
    22: 'divider',       # 分割线块
    23: 'file',          # 文件块
    24: 'grid',          # 分栏块
    25: 'grid_column',   # 分栏列块
    26: 'iframe',        # 内嵌网页块
    27: 'image',         # 图片块
    28: 'isv',           # 开放平台小组件块
    29: 'mindnote',      # 思维笔记块
    30: 'sheet',         # 电子表格块
    31: 'table',         # 表格块
    32: 'table_cell',    # 表格单元格块
    33: 'view',          # 视图块
    34: 'quote_container', # 引用容器块
    35: 'task',          # 任务块
    36: 'okr',           # OKR块
    37: 'okr_objective', # OKR Objective块
    38: 'okr_key_result', # OKR Key Result块
    39: 'okr_progress',  # OKR进展块
    40: 'add_ons',       # 文档小组件块
    41: 'jira_issue',    # Jira问题块
    42: 'wiki_catalog',  # Wiki子目录块
    43: 'board',         # 画板块
    44: 'agenda',        # 议程块
    45: 'agenda_item',   # 议程项块
    46: 'agenda_item_title', # 议程项标题块
    47: 'agenda_item_content', # 议程项内容块
    48: 'link_preview',  # 链接预览块
}

# 反向映射：从字符串类型到数值类型
BLOCK_TYPE_REVERSE_MAPPING = {v: k for k, v in BLOCK_TYPE_MAPPING.items()}

def get_block_type_name(block_type_num):
    """根据数值获取块类型名称
    
    Args:
        block_type_num (int): 块类型数值
        
    Returns:
        str: 块类型名称，如果未找到返回 'unknown'
    """
    return BLOCK_TYPE_MAPPING.get(block_type_num, 'unknown')

def get_block_type_number(block_type_name):
    """根据块类型名称获取数值
    
    Args:
        block_type_name (str): 块类型名称
        
    Returns:
        int: 块类型数值，如果未找到返回 None
    """
    return BLOCK_TYPE_REVERSE_MAPPING.get(block_type_name)

def extract_block_content_by_type(block):
    """根据块类型提取块的内容数据
    
    Args:
        block (dict): 文档块数据
        
    Returns:
        dict: 提取的块内容，包含 type_name 和 content
    """
    block_type_num = block.get('block_type')
    block_type_name = get_block_type_name(block_type_num)
    
    # 特殊处理的块类型
    if block_type_name == 'divider' or block_type_name == 'quote_container':
        return {
            'type_name': block_type_name,
            'content': {}
        }
    elif block_type_name == 'table':
        # 表格块需要移除只读字段
        table_data = block.get('table', {})
        if 'merge_info' in table_data:
            table_data = table_data.copy()
            del table_data['merge_info']
        return {
            'type_name': block_type_name,
            'content': table_data
        }
    elif block_type_name != 'unknown':
        # 标准块类型
        return {
            'type_name': block_type_name,
            'content': block.get(block_type_name, {})
        }
    else:
        # 未知类型，返回所有非系统字段
        content = {}
        for key, value in block.items():
            if key not in ['block_id', 'block_type', 'children', 'parent_id']:
                content[key] = value
        return {
            'type_name': 'unknown',
            'content': content
        }

def create_block_data(block_type_name, content):
    """根据块类型名称和内容创建块数据
    
    Args:
        block_type_name (str): 块类型名称
        content (dict): 块内容
        
    Returns:
        dict: 创建的块数据
    """
    block_data = {
        'block_type': get_block_type_number(block_type_name)
    }
    
    if block_type_name in ['divider', 'quote_container']:
        # 这些类型不需要额外内容
        pass
    else:
        block_data[block_type_name] = content
    
    return block_data

class FeishuDocumentAPI:
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
    
    def _upload_image_to_document(self, image_block_id, image_path):
        """
        上传图片到指定的飞书文档中
        
        Args:
            document_id (str): 目标文档ID
            image_path (str): 本地图片文件路径
            
        Returns:
            dict: 包含上传结果的字典，包含file_token和block_id等信息
            
        Raises:
            Exception: 当上传失败时抛出异常
        """
        import mimetypes
        from requests_toolbelt import MultipartEncoder
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 获取文件信息
        file_name = os.path.basename(image_path)
        file_size = os.path.getsize(image_path)
        mime_type, _ = mimetypes.guess_type(image_path)
        
        if not mime_type or not mime_type.startswith('image/'):
            raise ValueError(f"文件不是有效的图片格式: {image_path}")
        
        access_token = self.get_tenant_access_token()
        
        # 第一步：使用MultipartEncoder上传图片文件到飞书云盘
        upload_url = f"{self.base_url}/drive/v1/medias/upload_all"
        
        # 按照官方文档示例使用MultipartEncoder
        form = {
            'file_name': file_name,
            'parent_type': 'docx_image',  # 新版文档图片
            'parent_node': image_block_id,   # 文档token
            'size': str(file_size),
            'file': (open(image_path, 'rb'))
        }
        
        multi_form = MultipartEncoder(form)
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        headers['Content-Type'] = multi_form.content_type
        
        response = requests.post(upload_url, headers=headers, data=multi_form)
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"上传图片到块失败: {result.get('msg')} - {result}")
        
        file_token = result.get('data', {}).get('file_token')
        if not file_token:
            raise Exception("上传成功但未获取到file_token")
        
        print(f"图片上传到块成功，file_token: {file_token}")
        
        return file_token
    
    def insert_image_block_to_document(self, document_id, image_path, insert_position=-1, parent_block_id=None):
        """
        将图片插入到文档中作为图片块（按照飞书官方三步流程）
        
        Args:
            document_id (str): 目标文档ID
            file_token (str): 图片文件token
            insert_position (int): 插入位置，默认为0（开头）
            parent_block_id (str): 父块ID，如果为None则使用document_id作为父块
            
        Returns:
            str: 插入的图片块的block_id
            
        Raises:
            Exception: 当插入失败时抛出异常
        """
        access_token = self.get_tenant_access_token()
        
        # 如果没有指定父块ID，使用文档ID作为父块
        if parent_block_id is None:
            parent_block_id = document_id
        
        # 第一步：创建空的图片块
        create_url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 创建空的图片块数据
        create_block_data = {
            "index": insert_position,
            "children": [
                {
                    "block_type": 27,  # 图片块类型
                    "image": {}  # 空的图片对象
                }
            ]
        }
        
        response = requests.post(create_url, headers=headers, json=create_block_data)
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"创建图片块失败: {result.get('msg')} - {result}")
        
        # 获取创建的图片块ID
        children = result.get('data', {}).get('children', [])
        if not children:
            raise Exception("创建图片块成功但未获取到block_id")
        
        image_block_id = children[0].get('block_id')
        print(f"图片块创建成功，block_id: {image_block_id}")

        # 第二步：上传图片
        image_file_token = self._upload_image_to_document(image_block_id, image_path)
        
        # 第三步：更新图片块设置素材
        update_url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{image_block_id}"
        
        update_data = {
            "replace_image": {
                "token": image_file_token
            }
        }
        
        update_response = requests.patch(update_url, headers=headers, json=update_data)
        update_result = update_response.json()
        
        if update_result.get('code') != 0:
            raise Exception(f"设置图片块素材失败: {update_result.get('msg')} - {update_result}")
        
        print(f"图片插入完成，block_id: {image_block_id}")
        return image_block_id
    
    def get_all_block_ids(self, document_id, filter_block_type=None, page_size=500):
        """获取文档的所有 block_id
        
        Args:
            document_id (str): 文档ID
            page_size (int): 每页返回的块数量，默认500
            
        Returns:
            list: 包含所有block_id的列表
        """
        access_token = self.get_tenant_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        all_block_ids = []
        page_token = None
        
        while True:
            params = {
                "page_size": page_size
            }
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"获取文档块失败: {result.get('msg')}")
            
            # 提取当前页的所有block_id
            blocks = result.get('data', {}).get('items', [])
            for block in blocks:
                block_id = block.get('block_id')
                if filter_block_type:
                    block_type = block.get('block_type')
                    if block_type == filter_block_type:
                        all_block_ids.append(block_id)
                else:
                    all_block_ids.append(block_id)
            
            # 检查是否还有下一页
            page_token = result.get('data', {}).get('page_token')
            if not page_token:
                break
        
        return all_block_ids
    
    def find_block_id_by_text(self, document_id, search_text, page_size=500):
        """根据特定字符串查找对应的 block_id
        
        Args:
            document_id (str): 文档ID
            search_text (str): 要搜索的文本内容
            page_size (int): 每页返回的块数量，默认500
            
        Returns:
            list: 包含匹配文本的block信息列表，每个元素包含block_id和匹配的文本内容
        """
        access_token = self.get_tenant_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        matched_blocks = []
        page_token = None
        
        while True:
            params = {
                "page_size": page_size
            }
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"获取文档块失败: {result.get('msg')}")
            
            # 检查当前页的所有块
            blocks = result.get('data', {}).get('items', [])
            for block in blocks:
                block_id = block.get('block_id')
                block_type_num = block.get('block_type')
                block_type_name = get_block_type_name(block_type_num)
                
                # 检查不同类型的块中的文本内容
                text_content = self._extract_text_from_block(block)
                
                if text_content and search_text in text_content:
                    matched_blocks.append({
                        'block_id': block_id,
                        'block_type': block_type_num,
                        'block_type_name': block_type_name,
                        'matched_text': text_content,
                        'full_block': block
                    })
            
            # 检查是否还有下一页
            page_token = result.get('data', {}).get('page_token')
            if not page_token:
                break
        
        return matched_blocks
    
    def _extract_text_from_block(self, block):
        """从块中提取文本内容
        
        Args:
            block (dict): 文档块数据
            
        Returns:
            str: 提取的文本内容
        """
        block_type_num = block.get('block_type')
        block_type_name = get_block_type_name(block_type_num)
        
        # 处理包含文本元素的块类型
        text_containing_types = [
            'text', 'heading1', 'heading2', 'heading3', 'heading4', 'heading5',
            'heading6', 'heading7', 'heading8', 'heading9', 'bullet', 'ordered',
            'quote', 'todo', 'callout'
        ]
        
        if block_type_name in text_containing_types:
            block_data = block.get(block_type_name, {})
            text_elements = block_data.get('elements', [])
            text_parts = []
            for element in text_elements:
                if element.get('text_run'):
                    text_parts.append(element['text_run'].get('content', ''))
            return ''.join(text_parts)
        
        # 可以根据需要添加更多块类型的处理
        return ''
    
    def replace_block_content(self, document_id, block_id, new_content, text_color=None):
        """替换指定 block_id 的内容
        
        Args:
            document_id (str): 文档ID
            block_id (str): 要替换的块ID
            new_content (str): 新的文本内容
            
        Returns:
            bool: 替换是否成功
        """
        access_token = self.get_tenant_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{block_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 根据飞书官方文档，使用 update_text_elements 格式
        update_data = {
            "update_text_elements": {
                "elements": [
                    {
                        "text_run": {
                            "content": new_content,
                        }
                    }
                ]
            }
        }
        if text_color:
            update_data['update_text_elements']['elements'][0]['text_run']['text_element_style'] = {
                'text_color': text_color
            }
        
        # 添加调试输出
        print(f"请求URL: {url}")
        # print(f"请求数据: {json.dumps(update_data, ensure_ascii=False, indent=2)}")
        
        response = requests.patch(url, headers=headers, json=update_data)
        result = response.json()
        
        # 添加详细的错误信息
        print(f"响应状态码: {response.status_code}")
        # print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get('code') != 0:
            error_msg = result.get('msg', '未知错误')
            error_details = result.get('data', {})
            raise Exception(f"替换块内容失败: {error_msg}, 详细信息: {error_details}")
        
        return True
    

# 便捷函数，使用环境变量中的配置
def get_document_blocks(document_id, filter_block_type=None, page_size=500):
    """获取文档的所有 block_id（便捷函数）"""
    api = FeishuDocumentAPI()
    return api.get_all_block_ids(document_id, filter_block_type, page_size)

def find_blocks_by_text(document_id, search_text, page_size=500):
    """根据文本查找 block_id（便捷函数）"""
    api = FeishuDocumentAPI()
    return api.find_block_id_by_text(document_id, search_text, page_size)

# def replace_block_text(document_id, block_id, new_content, block_type_name='text'):
#     """替换块内容（便捷函数）"""
#     api = FeishuDocumentAPI()
#     return api.replace_block_content(document_id, block_id, new_content, block_type_name)

def replace_textblock_by_blocktype(document_id, search_text, new_content, search_block_type='text', text_color=None):
    """根据文本查找并替换块内容（便捷函数）"""
    api = FeishuDocumentAPI()
    matched_blocks = api.find_block_id_by_text(document_id, search_text)
    if matched_blocks:
        for block in matched_blocks:
            if block['block_type_name'] == search_block_type:
                api.replace_block_content(document_id, block['block_id'], new_content, text_color)
                return True
    return False


# 使用示例
if __name__ == "__main__":
    # 示例用法
    document_id = "D4wBdMNVwoMstRxdWiTcZd2XnNf"
    
    try:
        # 1. 获取文档的所有 block_id
        # print("获取文档所有块ID...")
        # all_blocks = get_document_blocks(document_id, 27)
        # print(f"文档共有 {len(all_blocks)} 个块")

        # 1. 上传图片
        document_id = "D4wBdMNVwoMstRxdWiTcZd2XnNf"
        image_path = "D:\\Study2\\BTC-news\\test\\image_utils\\merged.png"

        try:
            api = FeishuDocumentAPI()
            image_file_token = api.insert_image_block_to_document(document_id, image_path)
            print(f"上传成功！图片文件token: {image_file_token}")
        except Exception as e:
            print(f"上传失败: {e}")

        # replace_block_text_by_text_and_type(document_id, "最近8.22 ~ 8.25之间，加密货币领域有什么热点新闻？", "最近8.22 ~ 8.25之间，加密货币领域有什么热点新闻？哈哈哈哈")
        
        # # 2. 根据文本查找特定的 block_id
        # print("\n查找包含特定文本的块...")
        # search_text = "最近8.22 ~ 8.25之间，加密货币领域有什么热点新闻？"
        # matched_blocks = find_blocks_by_text(document_id, search_text)
        # print(f"找到 {len(matched_blocks)} 个匹配的块")
        
        # for block_info in matched_blocks:
        #     print(f"块ID: {block_info['block_id']}, 类型: {block_info['block_type_name']} ({block_info['block_type']})")
        #     print(f"匹配文本: {block_info['matched_text'][:100]}...")  # 只显示前100个字符
        
        # # 3. 替换指定块的内容
        # if matched_blocks:
        #     print("\n替换第一个匹配块的内容...")
        #     first_block = matched_blocks[0]
        #     success = replace_block_text(
        #         document_id, 
        #         first_block['block_id'], 
        #         "最近8.22 ~ 8.25之间，加密货币领域有什么热点新闻？哈哈哈哈", 
        #         first_block['block_type_name']
        #     )
        #     print(f"替换结果: {'成功' if success else '失败'}")
            
    except Exception as e:
        print(f"操作失败: {e}")