from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import json
import os
import asyncio
from playwright.sync_api import sync_playwright
from datetime import datetime
import logging
from functools import wraps
from send_to_weixin.to_gzh_with_pw import send_feishu_docs_to_wxgzh, download_qrcode_image
from main import main
from web_templates.template_manager import template_manager

# 配置静态文件目录
current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'web_templates', 'templates', 'static')

# 创建Flask应用，配置静态文件
app = Flask(__name__, static_folder=static_folder, static_url_path='/static')
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

# 主页 - 返回HTML
@app.route('/', methods=['GET'])
def index():
    return jsonify({
                    'success': True
                }), 200

# 检查CDP连接
@app.route('/api/check_cdp', methods=['GET'])
def check_cdp_connection():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        print(page.title())
        return jsonify({
            'success': True,
            'title': page.title()
        })


# 启动主程序
@app.route('/api/main', methods=['GET'])
def start_main():
    try:
        mode = request.args.get('mode', '', type=str)
        if mode:
            asyncio.run(main(mode))
            return jsonify({
                    'success': True
                }), 200
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
            preview_page_title, preview_page_url =  send_feishu_docs_to_wxgzh(feishu_docx_title, feishu_docx_url)
            # preview_page_title, preview_page_url =  '百度', 'https://www.baidu.com/'
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

# 公众号登录二维码页面 - 返回HTML页面显示二维码
@app.route('/qrcode', methods=['GET'])
def qrcode_page():
    try:
        # 使用模板管理器渲染页面
        html_content = template_manager.get_qrcode_page()
        return html_content
    except Exception as e:
        logger.error(f"渲染二维码页面失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '页面加载失败'
        }), 500

# 返回公众号登录二维码图片的API接口
@app.route('/api/qrcode', methods=['GET'])
def get_qrcode_image():
    try:
        # 构建二维码图片路径
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # qrcode_path = os.path.join(current_dir, 'send_to_weixin', 'qrcode.jpg')
        qrcode_path, qrcode_url = download_qrcode_image()
        
        # 检查文件是否存在
        if not os.path.exists(qrcode_path):
            return jsonify({
                'success': False,
                'error': '二维码图片不存在'
            }), 404
        
        # 返回图片文件
        return send_file(qrcode_path, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"获取二维码图片失败: {str(e)}")
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