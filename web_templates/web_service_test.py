from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import json
import os
from datetime import datetime
import logging
from functools import wraps

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 简单的API密钥验证装饰器
# def require_api_key(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
#         # 这里可以设置你的API密钥验证逻辑
#         # if api_key != 'your_secret_key':
#         #     return jsonify({'error': 'Invalid API key'}), 401
#         return f(*args, **kwargs)
#     return decorated_function

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
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BTC News API Service</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            .put { background: #fca130; }
            .delete { background: #f93e3e; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>BTC News API Service</h1>
            <p>服务状态: <strong style="color: green;">运行中</strong></p>
            <p>当前时间: {{ current_time }}</p>
            
            <h2>API 接口文档</h2>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/status</h3>
                <p>获取服务状态信息</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/news</h3>
                <p>获取最新新闻摘要</p>
                <p>参数: limit (可选, 默认10)</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/process</h3>
                <p>处理文本内容</p>
                <p>请求体: {"text": "要处理的文本", "action": "处理类型"}</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method post">POST</span> /api/feishu/create</h3>
                <p>创建飞书文档</p>
                <p>请求体: {"title": "标题", "content": "内容"}</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method get">GET</span> /api/download/<filename></h3>
                <p>下载文件</p>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# API状态接口 - 返回JSON
@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'endpoints': [
            '/api/status',
            '/api/news',
            '/api/process',
            '/api/feishu/create'
        ]
    })

# 获取新闻接口 - GET请求
@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        # 获取查询参数
        limit = request.args.get('limit', 10, type=int)
        category = request.args.get('category', 'all')
        
        # 这里可以调用你的新闻获取逻辑
        # 示例数据
        news_data = {
            'success': True,
            'data': [
                {
                    'id': 1,
                    'title': 'BTC价格分析',
                    'summary': '比特币价格今日上涨...',
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'id': 2,
                    'title': '市场动态',
                    'summary': '加密货币市场整体表现...',
                    'timestamp': datetime.now().isoformat()
                }
            ][:limit],
            'total': 2,
            'category': category
        }
        
        return jsonify(news_data)
    
    except Exception as e:
        logger.error(f"获取新闻失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 文本处理接口 - POST请求
@app.route('/api/process', methods=['POST'])
def process_text():
    try:
        # 获取JSON数据
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        text = data.get('text', '')
        action = data.get('action', 'default')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'text参数不能为空'
            }), 400
        
        # 这里可以调用你的文本处理逻辑
        processed_result = {
            'original_text': text,
            'action': action,
            'processed_text': f"已处理: {text}",
            'word_count': len(text),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': processed_result
        })
    
    except Exception as e:
        logger.error(f"文本处理失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 创建飞书文档接口 - POST请求
@app.route('/api/feishu/create', methods=['POST'])
@require_api_key
def create_feishu_doc():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        title = data.get('title', '')
        content = data.get('content', '')
        
        if not title or not content:
            return jsonify({
                'success': False,
                'error': 'title和content参数不能为空'
            }), 400
        
        # 这里可以调用你的飞书文档创建逻辑
        # 例如: from to_feishu_docx import write_to_daily_docx
        # result = await write_to_daily_docx(content, title)
        
        # 示例返回
        doc_result = {
            'document_id': 'doc_123456789',
            'title': title,
            'url': 'https://feishu.cn/docx/doc_123456789',
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': doc_result
        })
    
    except Exception as e:
        logger.error(f"创建飞书文档失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 文件上传接口 - POST请求
@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有文件被上传'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件'
            }), 400
        
        # 保存文件
        upload_dir = 'uploads'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'upload_time': datetime.now().isoformat()
            }
        })
    
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 文件下载接口 - GET请求
@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_path = os.path.join('uploads', filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 健康检查接口
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# 支持PUT和DELETE请求的示例
@app.route('/api/data/<int:data_id>', methods=['PUT', 'DELETE'])
def handle_data(data_id):
    if request.method == 'PUT':
        data = request.get_json()
        return jsonify({
            'success': True,
            'message': f'数据 {data_id} 已更新',
            'data': data
        })
    
    elif request.method == 'DELETE':
        return jsonify({
            'success': True,
            'message': f'数据 {data_id} 已删除'
        })

if __name__ == '__main__':
    # 开发环境配置
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,       # 端口号
        debug=True       # 开启调试模式
    )