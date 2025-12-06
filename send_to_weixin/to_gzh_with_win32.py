import win32gui
import win32con
import win32com.client
import pythoncom

def activate_chrome_window(window_title_keyword="Chrome"):
    pythoncom.CoInitialize()

    try:
        shell = win32com.client.Dispatch("WScript.Shell")

        def enum_handler(hwnd, result_list):
            if win32gui.IsWindowVisible(hwnd):
                text = win32gui.GetWindowText(hwnd)
                if window_title_keyword.lower() in text.lower():
                    result_list.append(hwnd)

        windows = []
        win32gui.EnumWindows(enum_handler, windows)

        if not windows:
            print("未找到 Chrome 窗口")
            return False

        hwnd = windows[0]

        # 获取当前窗口状态
        placement = win32gui.GetWindowPlacement(hwnd)
        show_cmd = placement[1]   # 1=Normal, 2=Minimized, 3=Maximized

        # 先激活窗口（必要）
        shell.AppActivate(win32gui.GetWindowText(hwnd))

        # 如果原来是最大化，则保持最大化
        if show_cmd == win32con.SW_SHOWMAXIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        print("激活成功，保持最大化状态:", show_cmd == win32con.SW_SHOWMAXIMIZED)
        return True

    finally:
        pythoncom.CoUninitialize()


# 调用示例
if __name__ == "__main__":
    activate_chrome_window("Edge")            # 激活任意 Chrome
    # activate_chrome_window("CoinGlass")       # 激活特定页面标题