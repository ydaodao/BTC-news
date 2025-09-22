from playwright.sync_api import sync_playwright
from time import sleep
import pyperclip
import os
from dotenv import load_dotenv, find_dotenv

try:
    # 当作为模块被导入时
    from .to_gzh_with_ui import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix, open_preview_page, delete_exit_draft, find_icon_with_prefix
    from .play_write_utils import active_page, operate_element, find_element_by_css, scroll_page, scroll_bottom, open_new_page
except ImportError:
    # 当直接运行时
    from to_gzh_with_ui import push_feishu_docs_2_wxgzh, open_edit_page_and_get_url, choose_page_cover, choose_other_options_and_preview, wait_icon_dismiss_with_prefix, open_preview_page, delete_exit_draft, find_icon_with_prefix
    from play_write_utils import active_page, operate_element, find_element_by_css, scroll_page, scroll_bottom, open_new_page
    pass

# 加载环境变量 - 自动查找.env文件
load_dotenv(find_dotenv())
LOCAL_DEV = os.getenv('LOCAL_DEV')



content_management_selector = '#js_index_menu > ul > li.weui-desktop-menu__item.weui-desktop-menu_create.menu-fold > span'
draft_selector = '#js_level2_title > li > ul > li:nth-child(1) > a'

def keep_gzh_online():
    """保持公众号在线"""
    try:        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]

            # 公众号页面 或者 微信公众平台页面
            page = active_page(context, "公众号", "https://mp.weixin.qq.com/", new_url="https://mp.weixin.qq.com/")
            if not page:
                page = active_page(context, "微信公众平台", "https://mp.weixin.qq.com/", new_url="https://mp.weixin.qq.com/")
            
            if page.title() == "公众号":
                # 内容管理菜单
                if operate_element(page, content_management_selector):
                    # 草稿箱
                    if operate_element(page, draft_selector):
                        return True, "保持公众号在线成功", None
            elif page.title() == "微信公众平台":
                # # 如果二维码过期了，二维码刷新按钮
                # refresh_qrcode_selector = '#header > div.banner > div > div > div.login__type__container.login__type__container__scan > div.login__type__container__scan__info > div > div > div > p:nth-child(1)'
                # if find_element_by_css(page, refresh_qrcode_selector):
                #     print(f"找到刷新二维码按钮: {refresh_qrcode_selector}")
                #     operate_element(page, refresh_qrcode_selector, 'click')
                # 下载二维码图片
                qrcode_download_url, qr_img_src = download_qrcode_image(page)
                return False, "已获取登录二维码", qrcode_download_url
                    
            else:
                return False, "没有找到公众号页面！", None
    except Exception as e:
        return False, f"保持公众号在线任务失败！错误信息：{str(e)}", None

def download_qrcode_image(page=None):
    """下载登录二维码图片"""
    def get_qrcode_image(page):
        if not page:
            return None, None

        qrcode_selector = '#header > div.banner > div > div > div.login__type__container.login__type__container__scan > img'
        qrcode_download_url = os.path.join(os.path.dirname(__file__), "qrcode.jpg")
        print(f"二维码下载路径: {qrcode_download_url}")
        qr_img_src = operate_element(page, qrcode_selector, 'get_image_screenshot', download_path=qrcode_download_url)
        return qrcode_download_url, qr_img_src

    if page:
        return get_qrcode_image(page)
    else:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = active_page(context, "微信公众平台", "https://mp.weixin.qq.com/", new_url="https://mp.weixin.qq.com/")
            return get_qrcode_image(page)


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
            # 内容管理菜单
            if operate_element(main_page, content_management_selector):
                # 草稿箱
                if operate_element(main_page, draft_selector):
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

    print(download_qrcode_image())