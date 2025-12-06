import win32gui
import win32con
import win32com.client

def activate_chrome_window(window_title_keyword="Chrome"):
    """
    激活包含关键字的 Chrome 窗口。
    默认关键字为 "Chrome"，也可以换成网站标题，比如 "CoinGlass"
    """

    shell = win32com.client.Dispatch("WScript.Shell")

    def enum_handler(hwnd, result_list):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if window_title_keyword.lower() in text.lower():
                result_list.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_handler, windows)

    if not windows:
        print(f"未找到包含关键字 '{window_title_keyword}' 的窗口")
        return False

    hwnd = windows[0]

    # 关键步骤！！需要先调用 "AppActivate"
    shell.AppActivate(win32gui.GetWindowText(hwnd))
    
    # 再调用 bring to front
    win32gui.SetForegroundWindow(hwnd)
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    print("已激活窗口:", win32gui.GetWindowText(hwnd))
    return True


# 调用示例
if __name__ == "__main__":
    activate_chrome_window("Edge")            # 激活任意 Chrome
    # activate_chrome_window("CoinGlass")       # 激活特定页面标题