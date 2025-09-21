import os
from string import Template
from datetime import datetime
import json

class TemplateManager:
    """Web服务模板管理器"""
    
    def __init__(self, template_dir=None):
        if template_dir is None:
            # 默认模板目录为当前文件所在目录下的templates
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.join(current_dir, 'templates')
        
        self.template_dir = template_dir
        self._ensure_template_dir()
    
    def _ensure_template_dir(self):
        """确保模板目录存在"""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
        
        # 确保静态文件目录存在
        static_dir = os.path.join(self.template_dir, 'static')
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
    
    def load_template(self, template_name):
        """加载模板文件"""
        template_path = os.path.join(self.template_dir, template_name)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def render_template(self, template_name, **kwargs):
        """渲染模板"""
        template_content = self.load_template(template_name)
        template = Template(template_content)
        
        # 添加默认变量
        default_vars = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp_unix': int(datetime.now().timestamp())
        }
        default_vars.update(kwargs)
        
        return template.safe_substitute(default_vars)
    
    def list_templates(self):
        """列出所有可用模板"""
        templates = []
        for file in os.listdir(self.template_dir):
            if file.endswith('.html'):
                templates.append(file)
        return templates
    
    def template_exists(self, template_name):
        """检查模板是否存在"""
        template_path = os.path.join(self.template_dir, template_name)
        return os.path.exists(template_path)

    
    def get_qrcode_page(self, **kwargs):
        """获取二维码页面HTML"""
        return self.render_template('qrcode.html', **kwargs)

# 创建全局模板管理器实例
template_manager = TemplateManager()

# 模板配置
TEMPLATE_CONFIG = {
    'qrcode': {
        'template': 'qrcode.html',
        'description': '二维码显示页面',
        'variables': ['timestamp']
    },
    'qrcode_with_css': {
        'template': 'qrcode_with_css.html', 
        'description': '带外部CSS的二维码页面',
        'variables': ['timestamp']
    }
}