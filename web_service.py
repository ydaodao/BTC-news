from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import json
import os
from datetime import datetime
import logging
from functools import wraps
from send_to_weixin.to_gzh_with_pw import send_feishu_docs_to_wxgzh

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# 将飞书文档发送到公众号
@app.route('/api/send_to_wx_gzh', methods=['POST'])
def send_to_wx_gzh():
    try:
        # 获取JSON数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        feishu_docx_url = data.get('feishu_docx_url', '')
        feishu_docx_title = data.get('feishu_docx_title', '')
        if feishu_docx_url and feishu_docx_title:
            # 在当前的浏览器中打开这个链接
            # preview_page_title, preview_page_url =  send_feishu_docs_to_wxgzh(feishu_docx_url, feishu_docx_title)
            preview_page_title, preview_page_url =  '百度', 'https://www.baidu.com/'
            if preview_page_url:
                data = {
                    'preview_page_title': preview_page_title,
                    'preview_page_url': preview_page_url
                }
                return jsonify({
                    'success': True,
                    'data': data
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': '微信公众号推送失败'
                }), 400

        return jsonify({
            'success': False,
            'error': '入参为空'
        }), 400
    except Exception as e:
        logger.error(f"错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # 开发环境配置
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,       # 端口号
        debug=True       # 开启调试模式
    )