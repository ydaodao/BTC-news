import pyautogui
import time
import os
import sys

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
                # 可以尝试使用其他截图方法
                return False
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
    
    test_screenshot()