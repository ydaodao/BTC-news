from playwright.sync_api import sync_playwright
from time import sleep
import pyperclip
try:
    # 当作为模块被导入时
    from .to_gzh_with_ui import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix, open_preview_page
except ImportError:
    # 当直接运行时
    from to_gzh_with_ui import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix, open_preview_page
    pass

# def init_browser():
#     """初始化浏览器连接"""
#     global BROWSER, PLAYWRIGHT_INSTANCE
    
#     if BROWSER is None:
#         PLAYWRIGHT_INSTANCE = sync_playwright().start()
#         BROWSER = PLAYWRIGHT_INSTANCE.chromium.connect_over_cdp("http://127.0.0.1:9222")
#         print("浏览器连接已初始化")
    
#     return BROWSER

# def get_browser():
#     """获取浏览器实例"""
#     if BROWSER is None:
#         return init_browser()
#     return BROWSER

# def close_browser():
#     """关闭浏览器连接"""
#     global BROWSER, PLAYWRIGHT_INSTANCE
    
#     if BROWSER:
#         BROWSER.close()
#         BROWSER = None
    
#     if PLAYWRIGHT_INSTANCE:
#         PLAYWRIGHT_INSTANCE.stop()
#         PLAYWRIGHT_INSTANCE = None
#         print("浏览器连接已关闭")

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
            page.wait_for_load_state('domcontentloaded', timeout=20000)  # 20秒超时
            
            # 尝试等待网络空闲，但设置较短的超时时间
            try:
                page.wait_for_load_state('networkidle', timeout=10000)  # 10秒超时
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
    page.wait_for_load_state('domcontentloaded', timeout=20000)  # 20秒超时
    # 尝试等待网络空闲，但设置较短的超时时间
    try:
        page.wait_for_load_state('networkidle', timeout=10000)  # 10秒超时
    except Exception:
        # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
        pass
    print(f"页面加载完成: {page.title()}")
    return page

def active_page(context, target_page_title, target_page_url, refresh=False):
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
            page.wait_for_load_state('domcontentloaded', timeout=20000)  # 20秒超时
            
            # 尝试等待网络空闲，但设置较短的超时时间
            try:
                page.wait_for_load_state('networkidle', timeout=10000)  # 10秒超时
            except Exception:
                # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
                pass
            
            print(f"页面刷新完成: {page.title()}")
            return page
        except Exception as e:
            print(f"页面刷新失败: {e}")
            return None
    sleep(2)
    page.title()
    return page

def switch_to_page_and_change_url(context, target_page_title, new_url):
    """切换到指定的tab页并改变URL"""
    # 查找匹配的tab页   
    page = active_page(context, target_page_title, None)
    if page:
        page.goto(new_url)
        print(f"已改变URL为: {new_url}")
        # 先等待 domcontentloaded，然后等待较短时间的 networkidle
        page.wait_for_load_state('domcontentloaded', timeout=20000)  # 20秒超时
        
        # 尝试等待网络空闲，但设置较短的超时时间
        try:
            page.wait_for_load_state('networkidle', timeout=10000)  # 10秒超时
        except Exception:
            # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
            pass
        
        print(f"页面加载完成: {page.title()}")
        return page
    return None

# def active_page_and_scroll(context, target_page_url, scroll_to_bottom=False):
#     """激活指定的tab页并滚动到页面底部"""
#     # 查找匹配的tab页
#     page = active_page(context, None, target_page_url)
#     if page:
#         if scroll_to_bottom:
#             page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
#             # 等待滚动完成
#             page.wait_for_timeout(1000)
#             print("已滚动到页面底部")
#         return page
#     return None

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

def send_feishu_docs_to_wxgzh(feishu_docs_url, target_page_title=None):
    # 主程序
    with sync_playwright() as p:
        def begin_send(context, feishu_docs_page):
            if push_feishu_docs_2_wxgzh():
                # 切换到已登录的公众号页面，并重置到首页
                main_page = switch_to_page_and_change_url(context, "公众号", "https://mp.weixin.qq.com/")
                # 打开文章编辑页面并获取URL
                edit_page_url = open_edit_page_and_get_url(feishu_docs_page)                
                # 激活编辑页面
                edit_page = active_page(context, None, edit_page_url, True)
                if edit_page:
                    if scroll_bottom(edit_page):
                        scroll_page(edit_page, -100)
                        sleep(2)
                        # 选择文章封面
                        choose_page_cover()
                        # 选择其他选项并 发送到公众号预览
                        if choose_other_options_and_preview():
                            # 回到主页，打开编辑页面
                            if open_preview_page(main_page):
                                # 聚焦到文章预览页面
                                preview_page = active_page(context, target_page_title, "https://mp.weixin.qq.com/")

                                preview_page_title = preview_page.title()
                                preview_page_url = preview_page.url
                                return preview_page_title, preview_page_url


        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]

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
    feishu_docs_url = "https://bj058omdwg.feishu.cn/docx/NUi8dqEugoIB4xxIFjWc6uJMnSe"
    # # target_page_title = pyperclip.paste().strip()
    target_page_title = "加密货币周报（8.24-9.7）：监管动态与机构持仓双线并进"

    preview_page_title, preview_page_url = send_feishu_docs_to_wxgzh(feishu_docs_url, target_page_title)
    print(preview_page_title)
    print(preview_page_url)