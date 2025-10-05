from playwright.sync_api import sync_playwright
from time import sleep
import pyperclip
import os
from dotenv import load_dotenv, find_dotenv

# 加载环境变量 - 自动查找.env文件
load_dotenv(find_dotenv())
LOCAL_DEV = os.getenv('LOCAL_DEV')
PAGELOAD_TIMEOUT = 40000 if not LOCAL_DEV else 10000

def list_all_tabs(context):
    """列出所有打开的tab页"""
    print(f"\n当前共有 {len(context.pages)} 个tab页:")
    for i, page in enumerate(context.pages):
        try:
            title = page.title()
            url = page.url
            print(f"{i+1}. 标题: {title}")
            print(f"   URL: {url}")
            print()
        except Exception as e:
            print(f"{i+1}. 获取页面信息失败: {e}")

def find_tabs_by_title(context, title_keyword):
    """根据标题关键词查找匹配的tab页"""
    matching_pages = []
    for page in context.pages:
        try:
            page_title = page.title()
            if title_keyword.lower() in page_title.lower():
                matching_pages.append({
                    'page': page,
                    'title': page_title,
                    'url': page.url
                })
        except Exception as e:
            print(f"获取页面标题失败: {e}")
            continue
    return matching_pages

def find_tabs_by_url(context, url_keyword):
    """根据URL关键词查找匹配的tab页"""
    matching_pages = []
    for page in context.pages:
        try:
            page_url = page.url
            if url_keyword.lower() in page_url.lower():
                matching_pages.append({
                    'page': page,
                    'title': page.title(),
                    'url': page_url
                })
        except Exception as e:
            print(f"获取页面信息失败: {e}")
            continue
    return matching_pages

def open_new_page(context, page_url):
    """打开新页面"""
    page = context.new_page()
    page.goto(page_url)
    page.bring_to_front()

    # 先等待 domcontentloaded，然后等待较短时间的 networkidle
    page.wait_for_load_state('domcontentloaded', timeout=PAGELOAD_TIMEOUT)  # 20秒超时
    # 尝试等待网络空闲，但设置较短的超时时间
    try:
        page.wait_for_load_state('networkidle', timeout=PAGELOAD_TIMEOUT)  # 10秒超时
    except Exception:
        # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
        pass
    print(f"页面加载完成: {page.title()}")
    return page

def active_page(context, target_page_title, target_page_url, refresh=False, new_url=None, close_other_tabs=False):
    if not target_page_title and not target_page_url:
        print("未提供标题或URL")
        return None

    """激活指定的tab页"""
    matching_tabs, matching_tabs_by_title, matching_tabs_by_url = [], [], []
    # 查找匹配的tab页
    if target_page_title:
        matching_tabs_by_title = find_tabs_by_title(context, target_page_title)
    if target_page_url:
        matching_tabs_by_url = find_tabs_by_url(context, target_page_url)
    # 如果两个都有，则取交集
    if target_page_title and target_page_url:
        # 修复：基于页面URL进行交集运算
        title_urls = {tab['url'] for tab in matching_tabs_by_title}
        url_urls = {tab['url'] for tab in matching_tabs_by_url}
        common_urls = title_urls & url_urls
        matching_tabs = [tab for tab in matching_tabs_by_title if tab['url'] in common_urls]
        if not matching_tabs:
            print(f"未找到标题包含'{target_page_title}'且URL包含'{target_page_url}'的tab页")
            return None
    elif target_page_title:
        matching_tabs = matching_tabs_by_title
        if not matching_tabs:
            print(f"未找到标题包含'{target_page_title}'的tab页")
            return None
    elif target_page_url:
        matching_tabs = matching_tabs_by_url
        if not matching_tabs:
            print(f"未找到URL包含'{target_page_url}'的tab页")
            return None
    
    # 是否关闭其它tab页
    if close_other_tabs and len(matching_tabs) > 1:
        for index, tab in enumerate(matching_tabs):
            if index == 0:
                continue
            if close_other_tabs:
                tab['page'].close()
    
    # 激活第一个tab页
    page = matching_tabs[0]['page']
    page.bring_to_front()
    print(f"已激活tab页: {page.title()}: {page.url}")
    if refresh:
        try:
            # 刷新页面
            page.reload()
            
            # 等待页面加载完成，使用更宽松的等待策略
            # 先等待 domcontentloaded，然后等待较短时间的 networkidle
            page.wait_for_load_state('domcontentloaded', timeout=PAGELOAD_TIMEOUT)  # 20秒超时
            
            # 尝试等待网络空闲，但设置较短的超时时间
            try:
                page.wait_for_load_state('networkidle', timeout=PAGELOAD_TIMEOUT)  # 10秒超时
            except Exception:
                # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
                pass
            
            print(f"页面刷新完成: {page.title()}")
        except Exception as e:
            print(f"页面刷新失败: {e}")
            return None

    if new_url:
        page.goto(new_url)
        print(f"已改变URL为: {new_url}")
        # 先等待 domcontentloaded，然后等待较短时间的 networkidle
        page.wait_for_load_state('domcontentloaded', timeout=PAGELOAD_TIMEOUT)  # 20秒超时
        
        # 尝试等待网络空闲，但设置较短的超时时间
        try:
            page.wait_for_load_state('networkidle', timeout=PAGELOAD_TIMEOUT)  # 10秒超时
        except Exception:
            # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
            pass
        
        print(f"页面加载完成: {page.title()}")
        return page
    
    return page

def scroll_bottom(page):
    if page:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        # 等待滚动完成
        page.wait_for_timeout(5000)
        print("已滚动到页面底部")
        return True
    return None

def scroll_page(page, scroll_height):
    """根据当前页面位置向上或向下滚动指定距离
    
    Args:
        page: Playwright页面对象
        scroll_height: 滚动距离，正数向下滚动，负数向上滚动
    """
    try:
        # 获取当前滚动位置
        current_scroll = page.evaluate("window.pageYOffset || document.documentElement.scrollTop")
        
        # 计算新的滚动位置
        new_scroll_position = current_scroll + scroll_height
        
        # 确保滚动位置不小于0
        new_scroll_position = max(0, new_scroll_position)
        
        # 获取页面最大可滚动高度
        max_scroll_height = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight) - window.innerHeight")
        
        # 确保滚动位置不超过最大高度
        new_scroll_position = min(new_scroll_position, max_scroll_height)
        
        # 执行滚动
        page.evaluate(f"window.scrollTo(0, {new_scroll_position});")
        
        # 等待滚动完成
        page.wait_for_timeout(2000)
        
        print(f"从位置 {current_scroll} 滚动到位置 {new_scroll_position}，滚动距离: {scroll_height}")
        return True
        
    except Exception as e:
        print(f"滚动页面时出错: {e}")
        return False

# --------------  操作页面元素↓↓↓ -----------------

def find_element_by_css(page, css_selector_name, css_selector, timeout=10000, wait_for_visible=True, hover=False):
    """
    通过CSS选择器查找页面元素
    
    Args:
        page: Playwright页面对象
        css_selector_name: 元素名称，用于日志输出
        css_selector: CSS选择器字符串
        timeout: 等待超时时间（毫秒），默认10秒
        wait_for_visible: 是否等待元素可见，默认True
        hover: 是否在找到元素后将鼠标悬停在元素上，默认False
    
    Returns:
        element: 找到的元素对象，如果未找到返回None
    """
    try:
        print(f"正在查找元素: {css_selector_name} ({css_selector})")
        
        if wait_for_visible:
            # 等待元素可见
            element = page.wait_for_selector(css_selector, timeout=timeout, state='visible')
        else:
            # 只等待元素存在于DOM中
            element = page.wait_for_selector(css_selector, timeout=timeout, state='attached')
        
        if element:
            print(f"成功找到元素: {css_selector_name} ({css_selector})")
            
            # 如果需要悬停，则将鼠标移动到元素上
            if hover:
                element.hover()
                print(f"已将鼠标悬停在元素上: {css_selector_name} ({css_selector})")
                
            return element
        else:
            print(f"未找到元素: {css_selector_name} ({css_selector})")
            return None
            
    except Exception as e:
        print(f"查找元素失败 {css_selector_name} ({css_selector}): {e}")
        return None

def convert_relative_url_to_absolute(page, relative_url):
    """
    将相对URL转换为绝对URL
    
    Args:
        page: Playwright页面对象
        relative_url: 相对URL或绝对URL
    
    Returns:
        str: 绝对URL
    """
    if not relative_url:
        return relative_url
    
    # 如果已经是绝对URL（包含协议）或者是data URL，直接返回
    if relative_url.startswith(('http://', 'https://', 'data:', 'blob:')):
        return relative_url
    
    page_url = page.url
    
    if relative_url.startswith('/'):
        # 相对于根域名的路径，需要添加协议和域名
        from urllib.parse import urlparse
        parsed_url = urlparse(page_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        absolute_url = base_url + relative_url
        print(f"转换根相对路径: {relative_url} -> {absolute_url}")
        return absolute_url
    else:
        # 相对于当前页面的路径
        from urllib.parse import urljoin
        absolute_url = urljoin(page_url, relative_url)
        print(f"转换相对路径: {relative_url} -> {absolute_url}")
        return absolute_url

def operate_element(page, css_selector_name, css_selector, operation='click', text_content=None, timeout=10000, wait_for_visible=True, download_path=None):
    """
    对页面元素执行各种操作
    
    Args:
        page: Playwright页面对象
        css_selector_name: 元素名称，用于日志输出
        css_selector: CSS选择器字符串
        operation: 操作类型，支持：
            - 'click': 点击元素
            - 'get_text': 获取元素文本内容
            - 'get_inner_text': 获取元素内部文本（不包含HTML标签）
            - 'get_inner_html': 获取元素内部HTML
            - 'get_attribute': 获取元素属性值（需要配合text_content参数指定属性名）
            - 'input_text': 输入文本（需要配合text_content参数）
            - 'clear_input': 清空输入框
            - 'get_image': 获取图片（如果是img元素）
            - 'hover': 鼠标悬停
            - 'double_click': 双击
            - 'right_click': 右键点击
            - 'scroll_into_view': 滚动到元素可见位置
            - 'is_visible': 检查元素是否可见
            - 'is_enabled': 检查元素是否可用
        text_content: 文本内容（用于input_text操作）或属性名（用于get_attribute操作）
        timeout: 等待超时时间（毫秒），默认10秒
        wait_for_visible: 是否等待元素可见，默认True
        download_path: 图片下载路径（用于get_image操作）
    
    Returns:
        根据操作类型返回不同结果：
        - click/input_text/clear_input/hover/double_click/right_click/scroll_into_view: 返回True/False
        - get_text/get_inner_text/get_inner_html/get_attribute: 返回字符串内容
        - get_image: 返回图片保存路径或None
        - is_visible/is_enabled: 返回True/False
    """
    try:
        # 查找元素
        element = find_element_by_css(page, css_selector_name, css_selector, timeout, wait_for_visible)
        if not element:
            return None
        
        print(f"对元素 {css_selector_name} ({css_selector}) 执行操作: {operation}")
        
        # 根据操作类型执行相应操作
        if operation == 'click':
            element.click()
            print(f"已点击元素: {css_selector}")
            return True
            
        elif operation == 'get_text':
            text = element.text_content()
            print(f"获取到文本内容: {text}")
            return text
            
        elif operation == 'get_inner_text':
            text = element.inner_text()
            print(f"获取到内部文本: {text}")
            return text
            
        elif operation == 'get_inner_html':
            html = element.inner_html()
            print(f"获取到内部HTML: {html[:100]}...")
            return html
            
        elif operation == 'get_attribute':
            if not text_content:
                print("获取属性值需要指定属性名")
                return None
            attr_value = element.get_attribute(text_content)
            print(f"获取到属性 {text_content} 的值: {attr_value}")
            return attr_value
            
        elif operation == 'input_text':
            if text_content is None:
                print("输入文本操作需要指定文本内容")
                return False
            element.fill(text_content)
            print(f"已输入文本: {text_content}")
            return True
            
        elif operation == 'clear_input':
            element.fill('')
            print(f"已清空输入框: {css_selector}")
            return True
            
        elif operation == 'get_image':
            # 检查是否是img元素
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name != 'img':
                print(f"元素不是img标签，而是: {tag_name}")
                return None
            
            # 获取图片URL
            img_src = element.get_attribute('src')
            if not img_src:
                print("图片元素没有src属性")
                return None
            
            # 转换为绝对URL
            img_src = convert_relative_url_to_absolute(page, img_src)
            print(f"最终图片URL: {img_src}")
            
            # 如果指定了下载路径，则下载图片
            if download_path:
                try:
                    import requests
                    import os
                    
                    # 确保下载目录存在
                    os.makedirs(os.path.dirname(download_path), exist_ok=True)
                    
                    # 下载图片
                    response = requests.get(img_src)
                    response.raise_for_status()
                    
                    with open(download_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"图片已下载到: {download_path}")
                    return download_path
                    
                except Exception as e:
                    print(f"下载图片失败: {e}")
                    return img_src
            else:
                return img_src

        elif operation == 'get_image_screenshot':
            # 检查是否是img元素
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name != 'img':
                print(f"元素不是img标签，而是: {tag_name}")
                return None
            
            # 如果指定了下载路径，则截图保存图片元素
            if download_path:
                try:
                    import os
                    
                    # 确保下载目录存在
                    os.makedirs(os.path.dirname(download_path), exist_ok=True)
                    
                    # 等待图片加载完成
                    element.wait_for_element_state("stable")
                    
                    # 截图保存图片元素（获取浏览器中实际显示的图片）
                    element.screenshot(path=download_path)
                    
                    print(f"图片已截图保存到: {download_path}")
                    return download_path
                    
                except Exception as e:
                    print(f"截图保存图片失败: {e}")
                    # 如果截图失败，回退到获取src属性
                    img_src = element.get_attribute('src')
                    if img_src:
                        img_src = convert_relative_url_to_absolute(page, img_src)
                        print(f"回退到图片URL: {img_src}")
                        return img_src
                    return None
            else:
                # 如果没有指定下载路径，返回图片URL
                img_src = element.get_attribute('src')
                if not img_src:
                    print("图片元素没有src属性")
                    return None
                
                # 转换为绝对URL
                img_src = convert_relative_url_to_absolute(page, img_src)
                print(f"图片URL: {img_src}")
                return img_src

        elif operation == 'hover':
            element.hover()
            print(f"已悬停在元素: {css_selector}")
            return True
            
        elif operation == 'double_click':
            element.dblclick()
            print(f"已双击元素: {css_selector}")
            return True
            
        elif operation == 'right_click':
            element.click(button='right')
            print(f"已右键点击元素: {css_selector}")
            return True
            
        elif operation == 'scroll_into_view':
            element.scroll_into_view_if_needed()
            print(f"已滚动到元素可见位置: {css_selector}")
            return True
            
        elif operation == 'is_visible':
            visible = element.is_visible()
            print(f"元素可见性: {visible}")
            return visible
            
        elif operation == 'is_enabled':
            enabled = element.is_enabled()
            print(f"元素可用性: {enabled}")
            return enabled
            
        else:
            print(f"不支持的操作类型: {operation}")
            return None
            
    except Exception as e:
        print(f"操作元素失败 {css_selector_name} ({css_selector}) ({operation}): {e}")
        return None

# --------------  操作页面元素 ↑↑↑ -----------------

if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        # page = active_page(context, "公众号", None, refresh=False, new_url=None)

