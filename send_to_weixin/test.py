import pyautogui
import time
import os

def test_screenshot():
    try:
        print("尝试截图...")
        screenshot = pyautogui.screenshot()
        print(f"截图成功！尺寸：{screenshot.size}")
        
        # 保存截图到项目目录
        screenshot_path = "C:\\Users\\Administrator\\Desktop\\test_screenshot.png"
        screenshot.save(screenshot_path)
        print(f"截图已保存到：{screenshot_path}")
        
        return True
    except Exception as e:
        print(f"截图失败：{e}")
        return False

if __name__ == "__main__":
    # 等待几秒让服务启动
    time.sleep(3)
    test_screenshot()


