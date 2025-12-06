import pyautogui
import pyperclip
import cv2
import numpy as np
import os
import re
import sys
from time import sleep
import ctypes
from ctypes import wintypes
import time
from dotenv import load_dotenv, find_dotenv
# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from send_to_weixin.playwright_utils import operate_element

# 加载环境变量 - 自动查找.env文件
load_dotenv(find_dotenv())
LOCAL_DEV = os.getenv('LOCAL_DEV')

# 0.83 = 1.2 / 1.5
# 0.66 = 1 / 1.5    阿里云/本地1.5
# 1.5 = 2.25 / 1.5  本地大屏/本地1.5
PYAUTOGUI_SCALES = [1]
if LOCAL_DEV:
    PYAUTOGUI_SCALES = [1, 1.2, 0.8333333333333333, 0.6666666666666666, 0.8, 1.5]

def windows_api_click(x, y):
    """使用Windows API发送鼠标点击事件"""
    try:
        # 获取窗口句柄
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # 将屏幕坐标转换为客户端坐标
        point = wintypes.POINT()
        point.x = x
        point.y = y
        ctypes.windll.user32.ScreenToClient(hwnd, ctypes.byref(point))
        
        # 发送鼠标按下和释放消息
        WM_LBUTTONDOWN = 0x0201
        WM_LBUTTONUP = 0x0202
        
        lParam = (point.y << 16) | point.x
        
        ctypes.windll.user32.SendMessageW(hwnd, WM_LBUTTONDOWN, 0, lParam)
        sleep(0.05)
        ctypes.windll.user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lParam)
        
        return True
    except Exception as e:
        print(f"Windows API点击失败: {e}")
        return False

script_dir = os.path.dirname(os.path.abspath(__file__))

# 动态计算适合的scales列表
def get_adaptive_scales(original_scale, target_scale):
    base_ratio = target_scale / original_scale
    return base_ratio

def find_icon_multi_scale(image_name, position='center', scales=PYAUTOGUI_SCALES):
    """多尺度模板匹配查找图标
    
    Args:
        image_name: 图片文件名
        scales: 缩放比例列表
        position: 点击位置，支持以下选项：
                 'center' - 中心（默认）
                 'top-left' - 左上角
                 'top-center' - 上方中心
                 'top-right' - 右上角
                 'left-center' - 左侧中心
                 'right-center' - 右侧中心
                 'bottom-left' - 左下角
                 'bottom-center' - 下方中心
                 'bottom-right' - 右下角
    
    Returns:
        tuple: (confidence, scale, click_x, click_y)
    """
    icon_path = os.path.join(script_dir, "images", image_name)
    
    # 获取屏幕截图
    screenshot = pyautogui.screenshot()
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    # 读取模板图像
    template = cv2.imread(icon_path)
    if template is None:
        print(f"无法读取图像文件: {image_name}")
        return False
    
    best_match = None
    best_confidence = 0
    
    # 尝试不同的缩放比例
    for scale in scales:
        # 缩放模板
        width = int(template.shape[1] * scale)
        height = int(template.shape[0] * scale)
        scaled_template = cv2.resize(template, (width, height))
        
        # 模板匹配
        result = cv2.matchTemplate(screenshot_cv, scaled_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        # 记录最佳匹配
        if max_val > best_confidence:
            best_confidence = max_val
            best_match = {
                'location': max_loc,
                'size': (width, height),
                'confidence': max_val,
                'scale': scale
            }
    
    # 如果找到足够好的匹配（阈值可调整）
    if best_match and best_confidence > 0.7:
        # 根据position参数计算点击位置
        location_x = best_match['location'][0]
        location_y = best_match['location'][1]
        width = best_match['size'][0]
        height = best_match['size'][1]
        
        # 计算不同位置的坐标
        if position == 'center':
            click_x = location_x + width // 2
            click_y = location_y + height // 2
        elif position == 'top-left':
            click_x = location_x
            click_y = location_y
        elif position == 'top-center':
            click_x = location_x + width // 2
            click_y = location_y
        elif position == 'top-right':
            click_x = location_x + width
            click_y = location_y
        elif position == 'left-center':
            click_x = location_x
            click_y = location_y + height // 2
        elif position == 'right-center':
            click_x = location_x + width
            click_y = location_y + height // 2
        elif position == 'bottom-left':
            click_x = location_x
            click_y = location_y + height
        elif position == 'bottom-center':
            click_x = location_x + width // 2
            click_y = location_y + height
        elif position == 'bottom-right':
            click_x = location_x + width
            click_y = location_y + height
        else:
            # 默认使用中心位置
            click_x = location_x + width // 2
            click_y = location_y + height // 2
            print(f"未知的位置参数: {position}，使用默认中心位置")

        return best_confidence, best_match['scale'], click_x, click_y
    else:
        print(f"未找到{image_name}，最高匹配度: {best_confidence:.2f}")
        return best_confidence, None, None, None

def find_icon_once(prefix, position='center'):
    """扫描所有符合前缀的图片，返回第一个匹配的图片文件"""
    images_dir = os.path.join(script_dir, "images")
    
    # 获取所有图片文件
    all_files = os.listdir(images_dir)
    
    # 筛选符合前缀的图片文件
    matching_files = []
    for file in all_files:
        if file.endswith('.png'):
            # 严格按照 prefix_数字.png 格式匹配
            name_without_ext = os.path.splitext(file)[0]
            # 使用正则表达式严格匹配 prefix_数字 格式
            pattern = rf'^{re.escape(prefix)}_\d+$'
            if re.match(pattern, name_without_ext):
                matching_files.append(file)
    
    if not matching_files:
        print(f"未找到以 '{prefix}' 开头的图片文件")
        return None, None, None, None, None
    
    # 按数字后缀排序
    def get_suffix_number(filename):
        # 提取文件名（不含扩展名）
        name_without_ext = os.path.splitext(filename)[0]
        # 使用正则表达式提取后缀数字
        match = re.search(r'_(\d+)$', name_without_ext)
        if match:
            return int(match.group(1))
        else:
            return 0  # 没有后缀的按0排序
    
    # 排序
    matching_files.sort(key=get_suffix_number)
    
    print(f"找到符合前缀 '{prefix}' 的图片: {matching_files}")
    
    # 依次尝试点击
    for image_file in matching_files:
        print(f"尝试定位: {image_file}")
        best_confidence, scale, click_x, click_y = find_icon_multi_scale(image_file, position)
        if click_x:
            print(f"找到{image_file}，匹配度: {best_confidence:.2f}，缩放：{scale}")
            return image_file, best_confidence, scale, click_x, click_y
    
    print(f"没有找到符合前缀 '{prefix}' 的图片")
    return None, None, None, None, None

def find_icon_with_prefix(prefix, max_try_times=20, sleep_time=0.2):
    """查找图标，返回图标文件路径、匹配度、缩放比例、点击坐标"""
    for i in range(max_try_times):
        sleep(sleep_time)
        _, _, _, click_x, click_y = find_icon_once(prefix)
        if click_x:
            return True
    return False

def wait_icon_dismiss_with_prefix(prefix, max_wait_seconds=10):
    sleep(0.5)
    image_file, best_confidence, scale, click_x, click_y = find_icon_once(prefix)
    if not click_x:
        return False
    
    """等待图标消失，如果指定次数内图标仍存在则返回False"""
    for i in range(max_wait_seconds):
        sleep(1)  # 等待1秒后再找图像
        image_file, best_confidence, scale, click_x, click_y = find_icon_once(prefix)
        if click_x:  # 如果找到了图标
            if i == max_wait_seconds - 1:  # 最后一次尝试
                print(f"等待了{i+1}次，{image_file}依然存在，匹配度: {best_confidence:.2f}，缩放：{scale}")
                return False
        else:  # 没找到图标（图标已消失）
            print(f"等待了{i+1}秒，{prefix}已经消失")
            return True
    return False

def click_icon_with_prefix(prefix, position='center', max_try_times=20, duration=0.5):
    """点击最高匹配度的图片，返回点击状态
    
    Args:
        prefix: 图片文件名前缀
        position: 点击位置，支持以下选项：
                 'center' - 中心（默认）
                 'top-left' - 左上角
                 'top-center' - 上方中心
                 'top-right' - 右上角
                 'left-center' - 左侧中心
                 'right-center' - 右侧中心
                 'bottom-left' - 左下角
                 'bottom-center' - 下方中心
                 'bottom-right' - 右下角
    """
    for i in range(max_try_times):
        sleep(0.2)
        image_file, best_confidence, scale, click_x, click_y = find_icon_once(prefix, position)
        if click_x:
            if duration:
                pyautogui.moveTo(click_x, click_y, duration=duration) # 平滑移动
                pyautogui.click()
            else:
                pyautogui.click(click_x, click_y)
            print(f"点击了{image_file}，匹配度: {best_confidence:.2f}，缩放：{scale}")
            return True
        else:
            continue
    return False

def hover_icon_with_prefix(prefix, position='center', max_try_times=20):
    """悬停最高匹配度的图片，返回悬停状态
    
    Args:
        prefix: 图片文件名前缀
        position: 点击位置，支持以下选项：
                 'center' - 中心（默认）
                 'top-left' - 左上角
                 'top-center' - 上方中心
                 'top-right' - 右上角
                 'left-center' - 左侧中心
                 'right-center' - 右侧中心
                 'bottom-left' - 左下角
                 'bottom-center' - 下方中心
                 'bottom-right' - 右下角
    """
    for i in range(max_try_times):
        sleep(0.3)
        image_file, best_confidence, scale, click_x, click_y = find_icon_once(prefix, position)
        if click_x:
            pyautogui.moveTo(click_x, click_y, duration=0.5)  # 0.5秒内平滑移动
            print(f"悬停在{image_file}，匹配度: {best_confidence:.2f}，缩放：{scale}")
            return True
        else:
            continue
    return False

def scroll_with_windows_api(clicks, x=None, y=None):
    """使用Windows API发送滚轮消息
    
    Args:
        clicks: 滚轮滚动次数，正数向上，负数向下
        x, y: 滚动位置坐标，如果不提供则使用当前鼠标位置
    """
    try:
        # 获取当前鼠标位置（如果未指定）
        if x is None or y is None:
            current_x, current_y = pyautogui.position()
            if x is None:
                x = current_x
            if y is None:
                y = current_y
        
        # Windows API常量
        WM_MOUSEWHEEL = 0x020A
        WHEEL_DELTA = 120
        
        # 获取窗口句柄
        hwnd = ctypes.windll.user32.WindowFromPoint(wintypes.POINT(x, y))
        
        # 计算滚轮数据
        wheel_data = clicks * WHEEL_DELTA
        wparam = (wheel_data << 16)
        lparam = (y << 16) | (x & 0xFFFF)
        
        # 发送滚轮消息
        result = ctypes.windll.user32.SendMessageW(hwnd, WM_MOUSEWHEEL, wparam, lparam)
        
        direction = "向上" if clicks > 0 else "向下"
        print(f"使用Windows API在位置({x}, {y}){direction}滚动{abs(clicks)}次")
        return result != 0
        
    except Exception as e:
        print(f"Windows API滚动时出错: {e}")
        return False

def send_keys_to_visible_window(key_combination):
    """发送按键组合到当前活动窗口
    
    Args:
        key_combination: 按键组合，支持格式：
                        - 单个按键: 'a', 'enter', 'space'
                        - 组合键: 'ctrl+a', 'ctrl+c', 'ctrl+v', 'alt+tab'
                        - 功能键: 'f1', 'f2', etc.
    """
    try:
        # 获取当前活动窗口的句柄
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # 按键码映射
        key_codes = {
            # 修饰键
            'ctrl': 0x11,
            'alt': 0x12,
            'shift': 0x10,
            'win': 0x5B,
            
            # 字母键
            'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
            'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
            'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
            'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
            'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
            'z': 0x5A,
            
            # 数字键
            '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
            '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
            
            # 功能键
            'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
            'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
            'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
            
            # 特殊键
            'enter': 0x0D,
            'space': 0x20,
            'tab': 0x09,
            'esc': 0x1B,
            'backspace': 0x08,
            'delete': 0x2E,
            'home': 0x24,
            'end': 0x23,
            'pageup': 0x21,
            'pagedown': 0x22,
            'up': 0x26,
            'down': 0x28,
            'left': 0x25,
            'right': 0x27,
        }
        
        # 解析按键组合
        keys = key_combination.lower().split('+')
        modifier_keys = []
        main_key = None
        
        for key in keys:
            key = key.strip()
            if key in ['ctrl', 'alt', 'shift', 'win']:
                modifier_keys.append(key)
            else:
                main_key = key
        
        if main_key is None:
            print(f"无效的按键组合: {key_combination}")
            return False
        
        if main_key not in key_codes:
            print(f"不支持的按键: {main_key}")
            return False
        
        # 按下修饰键
        for modifier in modifier_keys:
            if modifier in key_codes:
                ctypes.windll.user32.keybd_event(key_codes[modifier], 0, 0, 0)
        
        # 按下主键
        ctypes.windll.user32.keybd_event(key_codes[main_key], 0, 0, 0)
        
        # 释放主键
        ctypes.windll.user32.keybd_event(key_codes[main_key], 0, 2, 0)
        
        # 释放修饰键（逆序释放）
        for modifier in reversed(modifier_keys):
            if modifier in key_codes:
                ctypes.windll.user32.keybd_event(key_codes[modifier], 0, 2, 0)
        
        print(f"发送按键组合: {key_combination}")
        return True
        
    except Exception as e:
        print(f"发送按键时出错: {e}")
        return False

def send_hotkey(key_combination):
    """发送快捷键的简化版本
    
    Args:
        key_combination: 快捷键组合，如 'ctrl+a', 'ctrl+c', 'alt+tab'
    """
    sleep(0.3)
    return send_keys_to_visible_window(key_combination)

def send_text_to_window(text):
    """发送文本到当前活动窗口
    
    Args:
        text: 要发送的文本内容
    """
    try:
        for char in text:
            if char.isalpha():
                send_keys_to_visible_window(char)
            elif char == ' ':
                send_keys_to_visible_window('space')
            elif char == '\n':
                send_keys_to_visible_window('enter')
            # 可以根据需要添加更多字符处理
            sleep(0.05)  # 短暂延迟避免输入过快
        
        print(f"发送文本: {text}")
        return True
        
    except Exception as e:
        print(f"发送文本时出错: {e}")
        return False

# ---------------- 微信公众号操作 ---------------- 

def bring_chrome_to_front():
    pyautogui.moveTo(150, 20, duration=0.5) # 平滑移动
    pyautogui.click()

def active_chrome_window():
    # 激活 Chrome 窗口
    pyautogui.moveTo(150, 20, duration=0.5) # 平滑移动
    pyautogui.click()

def push_feishu_docs_2_wxgzh():
    # 通过壹伴推送到公众号
    if click_icon_with_prefix("yiban_icon"):
        if click_icon_with_prefix("yiban_caijiwenzhang"):
            if click_icon_with_prefix("yiban_choose_gzh"):
                if click_icon_with_prefix("yiban_choose_snxc"):
                    if click_icon_with_prefix("yiban_caiji_done"):
                        sleep_time = 0.2 if LOCAL_DEV else 0.1
                        if find_icon_with_prefix("yiban_caiji_success", 60, sleep_time):
                            print("采集成功")
                            return True
                        else:
                            print(f"等待了60秒，采集失败")
                            return False
    return False

def delete_exit_draft(feishu_docs_page=None):
    time.sleep(5)
    feishu_docs_page.title() # 通过一个固定不变的页面来更新context内容
    while hover_icon_with_prefix("wx_content_draft_btc_title", max_try_times=3):
        if click_icon_with_prefix("wx_content_delete"):
            if click_icon_with_prefix("wx_edit_common_deletebtn"):
                print("删除了已有的草稿")
                return True
            else:
                print("删除草稿失败")
                return False
        else:
            print("删除草稿失败")
            return False
    
    print("没有找到草稿，不需要删除")
    return True

def open_edit_page_and_get_url(feishu_docs_page=None):
    # 打开微信文章编辑页面，并获得页面链接
    if click_icon_with_prefix("wx_content_management"):
        if click_icon_with_prefix("wx_content_draft"): # 点击后，页面的URL改变了
            time.sleep(5)
            feishu_docs_page.title() # 通过一个固定不变的页面来更新context内容

            if hover_icon_with_prefix("wx_content_draft_btc_title"):
                if click_icon_with_prefix("wx_content_edit"):
                    print("打开了文章编辑页面")
                    sleep(10) # 等待足够的时间
                    feishu_docs_page.title() # 通过一个页面来更新context内容，因为有新页面打开了

                    # 获取当前页面的URL
                    if click_icon_with_prefix("wx_edit_url_prefix"):
                        send_hotkey("ctrl+a")
                        sleep(0.5)
                        send_hotkey("ctrl+c")
                        sleep(0.5)
                        wx_url = pyperclip.paste().strip()
                        print(f"编辑页面链接：{wx_url}")
                        return wx_url
    return None

def choose_page_cover(edit_page=None, try_once=True):
    # 选择文章封面图片
    if hover_icon_with_prefix("wx_edit_changecover_nocover_icon"):
        if hover_icon_with_prefix("wx_edit_changecover_icon"):
            if click_icon_with_prefix("wx_edit_changecover_frompage_icon", duration=None):
                wx_edit_changecover_pickimage = '#vue_app > mp-image-product-dialog > div > div.weui-desktop-dialog__wrp.weui-desktop-dialog_img-picker > div > div.weui-desktop-dialog__bd > div.img_crop_panel > div > ul > li:nth-child(1) > div'
                if operate_element(edit_page, '选择封面图片', wx_edit_changecover_pickimage, 'hover'):
                    sleep(1)
                    if operate_element(edit_page, '', wx_edit_changecover_pickimage, 'click'):
                        if click_icon_with_prefix("wx_edit_common_nextbtn"):
                            sleep(2)
                            scroll_with_windows_api(-5) ## 滚动到底部出现确认按钮
                            if click_icon_with_prefix("wx_edit_common_querenbtn"):
                                print("选择了封面")
                                # 有可能选择封面报错，所以再尝试一次
                                sleep(2)
                                # 如果没有选上，则再试一次
                                if find_icon_with_prefix("wx_edit_changecover_nocover_icon", max_try_times=1):
                                    if try_once:
                                        return choose_page_cover(edit_page, False)
                                    else:
                                        return False
                                else:
                                    return True
    return False

def choose_other_options_and_preview():
    flag_yuanchuang, flag_zanshang, flag_liuyan, flag_heji, flag_save_draft = False, False, False, False, False

    # 选择其它文章的选项
    if click_icon_with_prefix("wx_edit_choose_yuanchuang"):
        if click_icon_with_prefix("wx_edit_common_quedingbtn"):
            print("选择了原创")
    if click_icon_with_prefix("wx_edit_choose_zanshang"):
        if click_icon_with_prefix("wx_edit_common_quedingbtn"):
            print("选择了赞赏")
    if click_icon_with_prefix("wx_edit_choose_liuyan"):
        if click_icon_with_prefix("wx_edit_common_quedingbtn"):
            print("选择了留言")
    if click_icon_with_prefix("wx_edit_choose_heji", "right-center"):
        if click_icon_with_prefix("wx_edit_choose_heji_select"):
            if click_icon_with_prefix("wx_edit_choose_heji_select_zhoubao"):
                if click_icon_with_prefix("wx_edit_common_querenbtn"):
                    print("选择了合集")
    # if click_icon_with_prefix("wx_edit_save_draft"):
    #     if find_icon_with_prefix("wx_edit_save_draft_success"):
    #         print("保存了草稿")
    if click_icon_with_prefix("wx_edit_choose_preview"):
        if click_icon_with_prefix("wx_edit_common_quedingbtn"):
            # if find_icon_with_prefix("wx_edit_choose_preview_success"):
            print("发送到微信公众号预览")
            return True
                
def open_preview_page(page = None):
    page.bring_to_front()
    if click_icon_with_prefix("wx_content_draft_btc_title"):
        print("打开了文章编辑页面")
        if LOCAL_DEV:
            sleep(8) # 至少进入到了新页面中
        else:
            sleep(20) # 至少进入到了新页面中
        page.title() # 更新context，并取消页面加载的阻塞
        return True
    return None



if __name__ == "__main__":
    # sleep(3)
    # 从您提到的两种配置计算scale
    # scale_value = calculate_icon_scale(S
    #     (2240, 1400), 1.5,    # 电脑1: 2240×1400 150%
    #     (3840, 2160), 2.25    # 电脑2: 3840×2160 225%
    # )
    # print(f"需要的scale值: {scale_value:.2f}")

    sleep(3)

    # click_icon_with_prefix("test")
    # print(click_icon_with_prefix("wx_edit_changecover_pickimage"))
    bring_chrome_to_front()


    

