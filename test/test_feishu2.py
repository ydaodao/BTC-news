import json

import lark_oapi as lark
from lark_oapi.api.docx.v1 import *


def main():
    # 创建client
    client = lark.Client.builder() \
        .app_id("cli_a822ce94f622501c") \
        .app_secret("gvaDluGS9P0LJnR6m21gsgXxjYVyHOql") \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    # 构造请求对象（不指定 folder_token）
    request: CreateDocumentRequest = CreateDocumentRequest.builder() \
        .request_body(CreateDocumentRequestBody.builder()
            .title("测试文档 - 应用默认空间")
            .build()) \
        .build()

    # 发起请求
    response: CreateDocumentResponse = client.docx.v1.document.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.docx.v1.document.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))
    
    # 打印文档链接，方便查看
    if response.data and response.data.document:
        doc_token = response.data.document.document_id
        print(f"文档创建成功！")
        print(f"文档 ID: {doc_token}")
        print(f"文档链接: https://your-domain.feishu.cn/docx/{doc_token}")


if __name__ == "__main__":
    main()