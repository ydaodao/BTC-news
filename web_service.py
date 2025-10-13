# 顶部导入区域（module top-level）
from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import json
import os
import asyncio
import time
import threading
import sys
from integrated_scheduler import run_main_task
from playwright.sync_api import sync_playwright
from datetime import datetime
import logging
from functools import wraps
from send_to_weixin.to_gzh_with_pw import send_feishu_docs_to_wxgzh, download_qrcode_image
from main import main
from web_templates.template_manager import template_manager
import utils.powershell_utils as powershell_utils
from concurrent.futures import ThreadPoolExecutor
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'
ALI_WEBSERVICE_URL = 'http://127.0.0.1:5000' if LOCAL_DEV else 'http://39.107.72.186:5000'

# 配置静态文件目录
current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, 'web_templates', 'templates', 'static')

# 创建Flask应用，配置静态文件
app = Flask(__name__, static_folder=static_folder, static_url_path='/static')
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('web_service')

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
    mode = request.args.get('mode', '', type=str)

    # 启动后台线程
    thread = threading.Thread(target=run_main_task, args=(mode,))
    thread.start()

    # 立即返回成功响应
    return jsonify({
        'success': True,
        'message': f'/api/main?mode={mode} 任务已提交，正在后台处理'
    }), 200

# 将飞书文档发送到公众号
@app.route('/api/push_daily_news', methods=['POST'])
def push_daily_news():
    try:
        # 获取JSON数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        feishu_docx_url = data.get('feishu_docx_url', '')
        if feishu_docx_url:
            # 在当前的浏览器中打开这个链接
            preview_page_title, preview_page_url =  send_feishu_docs_to_wxgzh(None, feishu_docx_url)
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

@app.route('/api/push_final_weekly_news_and_push_robot', methods=['GET'])
def push_final_weekly_news_and_push_robot():
    feishu_docx_url = request.args.get('feishu_docx_url', '')
    # 定义后台推送函数
    def background_push(feishu_docx_url):
        try:
            if LOCAL_DEV:
                preview_page_url = 'https://mp.weixin.qq.com/s/1D6SeMRtDDTkOBW2jsldsg'
                time.sleep(10)
            else:
                _, preview_page_url = send_feishu_docs_to_wxgzh(None, feishu_docx_url)
            
            if preview_page_url:
                # 推送消息到飞书机器人
                from utils.feishu_robot_utils import push_final_weekly_news_to_robot
                push_final_weekly_news_to_robot(feishu_docx_url, preview_page_url)
                logger.info(f"后台推送成功: {preview_page_url}")
            else:
                logger.error("微信公众号推送失败")
        except Exception as e:
            logger.error(f"后台推送异常: {str(e)}")
    
    # 启动后台线程
    thread = threading.Thread(target=background_push, args=(feishu_docx_url,))
    thread.start()
    
    # 立即返回成功响应
    return jsonify({
        'success': True,
        'message': f'/api/push_final_weekly_news_and_push_robot?feishu_docx_url={feishu_docx_url} 任务已提交，正在后台处理'
    }), 200

# 返回公众号登录二维码图片的API接口
@app.route('/api/qrcode', methods=['GET'])
def get_qrcode_image():
    try:
        result = powershell_utils.git_pull()
        if result['success']:
            qrcode_path, qrcode_url = download_qrcode_image()
            # 路径健壮性校验，避免 NoneType 传入 send_file
            if not qrcode_path or not isinstance(qrcode_path, (str, bytes, os.PathLike)) or not os.path.exists(qrcode_path):
                return jsonify({
                    'success': False,
                    'error': '二维码图片不存在或生成失败'
                }), 500

            result = powershell_utils.git_commit(f"Add qrcode image")
            if result['success']:
                result = powershell_utils.git_push()
        # 返回图片文件
        return send_file(qrcode_path, mimetype='image/jpeg')

    except Exception as e:
        logger.error(f"获取二维码图片失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# -------------------------以下都是页面-----------------------------

# 测试页面
@app.route('/test_element_plus', methods=['GET'])
def test_element_plus_page():
    try:
        # 使用模板管理器渲染Vue页面
        html_content = template_manager.get_test_element_plus_page()
        return html_content
    except Exception as e:
        logger.error(f"渲染测试页面失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '页面加载失败'
        }), 500

# 公众号登录二维码页面 - 返回HTML页面显示二维码
@app.route('/qrcode', methods=['GET'])
def qrcode_page():
    try:
        # 使用模板管理器渲染Vue页面
        html_content = template_manager.get_qrcode_page()
        return html_content
    except Exception as e:
        logger.error(f"渲染二维码页面失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '页面加载失败'
        }), 500

# 重新生成日报页面 - 返回HTML页面显示二维码
@app.route('/regenerate_daily_news', methods=['GET'])
def regenerate_daily_news_page():
    try:
        # 使用模板管理器渲染Vue页面
        html_content = template_manager.get_regenerate_daily_news_page()
        return html_content
    except Exception as e:
        logger.error(f"渲染重新生成日报页面失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '页面加载失败'
        }), 500

# 模块主入口（if __name__ == "__main__":）
if __name__ == "__main__":
    # 开发环境配置
    if not LOCAL_DEV:
        try:
            from livereload import Server
            # 用 livereload 包裹 WSGI 应用
            server = Server(app.wsgi_app)

            # 监听模板与静态资源目录
            server.watch(r"d:\Study2\BTC-news\web_templates\templates\*.html")
            server.watch(r"d:\Study2\BTC-news\web_templates\templates\static\css\*.css")
            server.watch(r"d:\Study2\BTC-news\web_templates\templates\static\js\*.js")
            
            server.serve(host="127.0.0.1", port=5000, debug=True)
        except ImportError:
            app.run(host="127.0.0.1", port=5000, debug=True)
    else:
        app.run(
            host='0.0.0.0',  # 允许外部访问
            port=5000,       # 端口号
            debug=True       # 开启调试模式
        )