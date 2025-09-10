import pyautogui
import time
import os
import sys

def test_screenshot_win32():
    """使用Windows API进行截图"""
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        from PIL import Image
        
        print("尝试使用Win32 API截图...")
        
        # 获取桌面窗口
        hdesktop = win32gui.GetDesktopWindow()
        
        # 获取桌面的设备上下文
        desktop_dc = win32gui.GetWindowDC(hdesktop)
        img_dc = win32ui.CreateDCFromHandle(desktop_dc)
        mem_dc = img_dc.CreateCompatibleDC()
        
        # 获取屏幕尺寸
        width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        print(f"屏幕尺寸：{width}x{height}")
        
        # 创建bitmap
        screenshot = win32ui.CreateBitmap()
        screenshot.CreateCompatibleBitmap(img_dc, width, height)
        mem_dc.SelectObject(screenshot)
        
        # 复制屏幕到bitmap
        mem_dc.BitBlt((0, 0), (width, height), img_dc, (0, 0), win32con.SRCCOPY)
        
        # 转换为PIL Image
        bmpinfo = screenshot.GetInfo()
        bmpstr = screenshot.GetBitmapBits(True)
        img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
        
        # 保存
        screenshot_path = "C:\\Users\\Administrator\\Desktop\\test_screenshot_win32.png"
        img.save(screenshot_path)
        print(f"Win32 API截图成功，保存到：{screenshot_path}")
        
        # 清理资源
        mem_dc.DeleteDC()
        win32gui.ReleaseDC(hdesktop, desktop_dc)
        
        return True
    except ImportError as e:
        print(f"缺少Win32库：{e}")
        print("请安装：pip install pywin32")
        return False
    except Exception as e:
        print(f"Win32 API截图失败：{e}")
        return False

def test_screenshot():
    try:
        print("尝试截图...")
        
        # 在无桌面环境下，可能需要设置显示
        if os.name == 'nt':  # Windows
            # 尝试连接到TightVNC提供的虚拟显示
            try:
                # 设置pyautogui在无GUI环境下的行为
                pyautogui.FAILSAFE = False
                screenshot = pyautogui.screenshot()
            except Exception as e:
                print(f"直接截图失败，尝试其他方法：{e}")
                # 尝试使用Win32 API
                return test_screenshot_win32()
        else:
            screenshot = pyautogui.screenshot()
            
        print(f"截图成功！尺寸：{screenshot.size}")
        
        # 保存截图到项目目录
        screenshot_path = "C:\\Users\\Administrator\\Desktop\\test_screenshot.png"
        screenshot.save(screenshot_path)
        print(f"截图已保存到：{screenshot_path}")
        
        return True
    except Exception as e:
        print(f"截图失败：{e}")
        print(f"错误类型：{type(e).__name__}")
        return False

if __name__ == "__main__":
    # 等待几秒让服务启动
    time.sleep(3)
    
    # 检查是否有显示环境
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口
        print("检测到GUI环境")
        root.destroy()
    except Exception as e:
        print(f"无GUI环境：{e}")
    
    success = test_screenshot()
    if success:
        print("截图测试成功！")
    else:
        print("截图测试失败！")