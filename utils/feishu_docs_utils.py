import requests
import json
import os
import lark_oapi as lark
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.drive.v1 import *

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class FeishuDocsAPI:
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