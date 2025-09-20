from playwright.sync_api import sync_playwright
from time import sleep
import pyperclip
import os
from dotenv import load_dotenv, find_dotenv

try:
    # 当作为模块被导入时
    from .to_gzh_with_ui import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix, open_preview_page, delete_exit_draft, find_icon_with_prefix
except ImportError:
    # 当直接运行时
    from to_gzh_with_ui import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix, open_preview_page, delete_exit_draft, find_icon_with_prefix
    pass

# 加载环境变量 - 自动查找.env文件
load_dotenv(find_dotenv())
LOCAL_DEV = os.getenv('LOCAL_DEV')
PAGELOAD_TIMEOUT = 30000
if LOCAL_DEV:
    print("本地开发环境")
    PAGELOAD_TIMEOUT = 10000

# --------------  以上为实例化代码 -----------------

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

def refresh_page_by_title(context, target_page_title):
    """刷新页面并等待页面刷新完成，返回True"""
    # 查找匹配的tab页
    page = active_page(context, target_page_title, None, refresh=True)        
    return refresh_page(page)

def refresh_page(page):
    if page:
        try:
            print(f"刷新页面: {page.title()}, {page.url}")
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
            return True
        except Exception as e:
            print(f"页面刷新失败: {e}")
            return False
    else:
        print("页面不存在")
        return False

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

def active_page(context, target_page_title, target_page_url, refresh=False, new_url=None):
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

def find_element_by_css(page, css_selector, timeout=10000, wait_for_visible=True):
    """
    通过CSS选择器查找页面元素
    
    Args:
        page: Playwright页面对象
        css_selector: CSS选择器字符串
        timeout: 等待超时时间（毫秒），默认10秒
        wait_for_visible: 是否等待元素可见，默认True
    
    Returns:
        element: 找到的元素对象，如果未找到返回None
    """
    try:
        print(f"正在查找元素: {css_selector}")
        
        if wait_for_visible:
            # 等待元素可见
            element = page.wait_for_selector(css_selector, timeout=timeout, state='visible')
        else:
            # 只等待元素存在于DOM中
            element = page.wait_for_selector(css_selector, timeout=timeout, state='attached')
        
        if element:
            print(f"成功找到元素: {css_selector}")
            return element
        else:
            print(f"未找到元素: {css_selector}")
            return None
            
    except Exception as e:
        print(f"查找元素失败 {css_selector}: {e}")
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

def operate_element(page, css_selector, operation='click', text_content=None, timeout=10000, wait_for_visible=True, download_path=None):
    """
    对页面元素执行各种操作
    
    Args:
        page: Playwright页面对象
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
        element = find_element_by_css(page, css_selector, timeout, wait_for_visible)
        if not element:
            return None
        
        print(f"对元素 {css_selector} 执行操作: {operation}")
        
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
        print(f"操作元素失败 {css_selector} ({operation}): {e}")
        return None



# --------------  操作页面元素 ↑↑↑ -----------------

def keep_gzh_online():
    """保持公众号在线"""
    try:        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]

            # 公众号页面 或者 微信公众平台页面
            page = active_page(context, "公众号", "https://mp.weixin.qq.com/", refresh=True, new_url="https://mp.weixin.qq.com/")
            
            if page.title() == "公众号":
                # 内容管理菜单
                if operate_element(page, '#js_index_menu > ul > li.weui-desktop-menu__item.weui-desktop-menu_create.menu-fold > span', 'click'):
                    # 草稿箱
                    if operate_element(page, '#js_level2_title > li > ul > li:nth-child(1) > a', 'click'):
                        return True, "保持公众号在线成功", None
            elif page.title() == "微信公众平台":
                # 如果二维码过期了，二维码刷新按钮
                    refresh_qrcode_selector = '#header > div.banner > div > div > div.login__type__container.login__type__container__scan > div.login__type__container__scan__info > div > div > div > p:nth-child(1)'
                    if find_element_by_css(page, refresh_qrcode_selector):
                        print(f"找到刷新二维码按钮: {refresh_qrcode_selector}")
                        operate_element(page, refresh_qrcode_selector, 'click')
                    # 下载二维码图片
                    qrcode_selector = '#header > div.banner > div > div > div.login__type__container.login__type__container__scan > img'
                    qrcode_download_url = os.path.join(os.path.dirname(__file__), "qrcode.jpg")
                    print(f"二维码下载路径: {qrcode_download_url}")
                    operate_element(page, qrcode_selector, 'get_image', download_path=qrcode_download_url)
                    return False, "需扫描二维码登录", qrcode_download_url
                    
            else:
                return False, "没有找到公众号页面！", None
    except Exception as e:
        return False, f"保持公众号在线任务失败！错误信息：{str(e)}", None


def send_feishu_docs_to_wxgzh(target_page_title=None, feishu_docs_url=None):
    # 主程序
    with sync_playwright() as p:
        def begin_send(context, feishu_docs_page):
            # 通过壹伴将文档推送到公众号
            if push_feishu_docs_2_wxgzh():
                # 切换到已登录的公众号页面，并重置到首页
                main_page = active_page(context, "公众号", None, new_url="https://mp.weixin.qq.com/")
                # 打开文章编辑页面并获取URL
                edit_page_url = open_edit_page_and_get_url(feishu_docs_page)
                if not LOCAL_DEV:
                    feishu_docs_page.close()
                # 激活编辑页面
                edit_page = active_page(context, None, edit_page_url, False)
                if edit_page:
                    if scroll_bottom(edit_page):
                        scroll_page(edit_page, -100)
                        sleep(2)
                        # 选择文章封面
                        if choose_page_cover():
                            # 选择其他选项并 发送到公众号预览
                            if choose_other_options_and_preview():
                                if not LOCAL_DEV:
                                    edit_page.close()
                                # 回到主页，打开编辑页面
                                if open_preview_page(main_page):
                                    # 聚焦到文章预览页面
                                    preview_page = active_page(context, target_page_title, "https://mp.weixin.qq.com/")

                                    preview_page_title = preview_page.title()
                                    preview_page_url = preview_page.url
                                    if not LOCAL_DEV:
                                        preview_page.close()
                                    return preview_page_title, preview_page_url
                                else:
                                    print("打开预览页面失败")
                                    return None, None
                            else:
                                print("选择其他选项并发送到公众号预览失败")
                                return None, None
                        else:
                            print("选择文章封面失败")
                            return None, None
                    else:
                        print("滚动到页面底部失败")
                        return None, None
                else:
                    print("激活编辑页面失败")
                    return None, None
            else:
                print("推送飞书文档到公众号失败")
                return None, None


        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]

        # 切换到已登录的公众号页面，并重置到首页
        main_page = active_page(context, "公众号", None, new_url="https://mp.weixin.qq.com/")
        if main_page:
            # 删除已经存在的草稿
            if delete_exit_draft(main_page):
                # 打开目标飞书文档
                feishu_docs_page = active_page(context, target_page_title, feishu_docs_url, refresh=True)
                if feishu_docs_page:
                    return begin_send(context, feishu_docs_page)
                else:
                    if feishu_docs_url:
                        print(f"打开飞书文档页面: {feishu_docs_url}")
                        feishu_docs_page = open_new_page(context, feishu_docs_url)
                        if feishu_docs_page:
                            return begin_send(context, feishu_docs_page)

if __name__ == "__main__":
    # feishu_docs_url = "https://bj058omdwg.feishu.cn/docx/NUi8dqEugoIB4xxIFjWc6uJMnSe"
    # # # target_page_title = pyperclip.paste().strip()
    # target_page_title = "加密货币周报（8.24-9.7）：监管动态与机构持仓双线并进"


    # preview_page_title, preview_page_url = send_feishu_docs_to_wxgzh(target_page_title, feishu_docs_url)
    # print(preview_page_title)
    # print(preview_page_url)

    print(keep_gzh_online())