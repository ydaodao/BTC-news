import pyautogui
import time
import os

def test_screenshot():
    try:
        # print("尝试截图...")
        
        # 设置pyautogui
        pyautogui.FAILSAFE = False
        
        # 截图
        screenshot = pyautogui.screenshot()
        # print(f"截图成功！尺寸：{screenshot.size}")
        
        # 保存截图
        screenshot_path = "C:\\Users\\Administrator\\Desktop\\test_screenshot.png"
        screenshot.save(screenshot_path)
        # print(f"截图已保存到：{screenshot_path}")
        
        return True
    except Exception as e:
        print(f"截图失败：{e}")
        print(f"错误类型：{type(e).__name__}")
        return False

if __name__ == "__main__":
    # 等待几秒让服务启动
    time.sleep(3)
    
    start_time = time.time()
    print(f"程序开始时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    while True:
        success = test_screenshot()
        if success:
            time.sleep(600)
        else:
            # 计算运行时间
            elapsed_time = time.time() - start_time
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            seconds = int(elapsed_time % 60)
            print(f"截图测试失败！程序运行了：{hours}小时{minutes}分钟{seconds}秒")
            break
        
    
    