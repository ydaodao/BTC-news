from playwright.sync_api import sync_playwright
from time import sleep
import pyperclip
from to_wx_gzh import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix

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

def refresh_page(context, target_page_title):
    """刷新页面并等待页面刷新完成，返回True"""
    # 查找匹配的tab页
    matching_tabs = find_tabs_by_title(context, target_page_title)
    if not matching_tabs:
        print(f"未找到标题包含'{target_page_title}'的tab页")
        return False
    
    page = matching_tabs[0]['page']
    page.bring_to_front()
    print(f"已激活tab页: {page.title()}")

    try:
        # 刷新页面
        page.reload()
        
        # 等待页面加载完成，使用更宽松的等待策略
        # 先等待 domcontentloaded，然后等待较短时间的 networkidle
        page.wait_for_load_state('domcontentloaded', timeout=10000)  # 10秒超时
        
        # 尝试等待网络空闲，但设置较短的超时时间
        try:
            page.wait_for_load_state('networkidle', timeout=5000)  # 5秒超时
        except Exception:
            # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
            pass
        
        print(f"页面刷新完成: {page.title()}")
        return True
    except Exception as e:
        print(f"页面刷新失败: {e}")
        return False

def switch_to_page_and_change_url(context, target_page_title, new_url):
    """切换到指定的tab页并改变URL"""
    # 查找匹配的tab页
    matching_tabs = find_tabs_by_title(context, target_page_title)
    if not matching_tabs:
        print(f"未找到标题包含'{target_page_title}'的tab页")
        return False
    
    page = matching_tabs[0]['page']
    page.bring_to_front()
    print(f"已激活tab页: {page.title()}")
    page.goto(new_url)
    print(f"已改变URL为: {new_url}")
    # 先等待 domcontentloaded，然后等待较短时间的 networkidle
    page.wait_for_load_state('domcontentloaded', timeout=10000)  # 10秒超时
    
    # 尝试等待网络空闲，但设置较短的超时时间
    try:
        page.wait_for_load_state('networkidle', timeout=5000)  # 5秒超时
    except Exception:
        # 如果网络空闲等待超时，继续执行，因为DOM已经加载完成
        pass
    
    print(f"页面加载完成: {page.title()}")
    return page

def active_page_and_scroll(context, target_page_url, scroll_to_bottom=False):
    """激活指定的tab页并滚动到页面底部"""
    # 查找匹配的tab页
    matching_tabs = find_tabs_by_url(context, target_page_url)
    if not matching_tabs:
        print(f"未找到URL包含'{target_page_url}'的tab页")
        return None
    
    page = matching_tabs[0]['page']
    page.bring_to_front()
    print(f"已激活tab页: {page.title()}")
    if scroll_to_bottom:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        # 等待滚动完成
        page.wait_for_timeout(1000)
        print("已滚动到页面底部")
    return page

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
        page.wait_for_timeout(500)
        
        print(f"从位置 {current_scroll} 滚动到位置 {new_scroll_position}，滚动距离: {scroll_height}")
        return True
        
    except Exception as e:
        print(f"滚动页面时出错: {e}")
        return False

# 主程序
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    #刷新飞书文档
    target_page_title = pyperclip.paste().strip()
    if target_page_title.startswith('加密货币'):
        if refresh_page(context, target_page_title):
            sleep(0.1)
            if push_feishu_docs_2_wxgzh():
                # 切换到已登录的公众号页面，并重置到首页
                page = switch_to_page_and_change_url(context, "公众号", "https://mp.weixin.qq.com/")
                # 打开文章编辑页面并获取URL
                edit_page_url = open_edit_page_and_get_url(page)
                page.title() # 更新context，并取消页面加载的阻塞

                # 等待新打开的页面加载完成
                if wait_icon_dismiss_with_prefix("chrome_page_loading", 10):
                    if edit_page_url:
                        # 聚焦到文章编辑页面的底部
                        page = active_page_and_scroll(context, edit_page_url, scroll_to_bottom=True)
                        if page:
                            scroll_page(page, -100)
                            # 选择文章封面
                            choose_page_cover()
                            # 选择其他选项并预览
                            choose_other_options_and_preview()