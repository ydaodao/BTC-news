"""
chrome_wakeup_helper.py

用途：
  - 安全激活（唤醒）Chrome 主窗口，保持最大化状态（如果原来是最大化）
  - 通过 WM_NULL 检测窗口响应性，必要时做轻量模拟输入（微移鼠标）以解除 Chrome freeze
  - 在单独 STA 线程中进行 COM 操作，避免 "尚未调用 CoInitialize" 错误
  - 提供定时守护接口（periodic_wakeup）

主要接口：
  - safe_activate_chrome(window_title_keyword='Chrome', simulate_input=True, timeout_ms=2000)
  - periodic_wakeup(interval_seconds, ... )  # 返回 threading.Timer 对象
  - connect_cdp_with_wakeup(... )  # Playwright + 激活 的示例组合
"""

import time
import threading
import logging
import ctypes
from ctypes import wintypes

import win32gui
import win32con
import win32com.client
import pythoncom
import psutil

# pyautogui 可选（用于微量鼠标移动）
try:
    import pyautogui
    PY_AUTO_AVAILABLE = True
except Exception:
    PY_AUTO_AVAILABLE = False

# Setup logging
logger = logging.getLogger("ChromeWakeupHelper")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(ch)

# ctypes for SendMessageTimeout
user32 = ctypes.windll.user32
SendMessageTimeout = user32.SendMessageTimeoutW
SendMessageTimeout.restype = wintypes.LPARAM
SendMessageTimeout.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(wintypes.LPARAM)
]

# Constants
SMTO_ABORTIFHUNG = 0x0002
WM_NULL = 0x0000

def _find_chrome_hwnds_by_proc_name(keyword="chrome"):
    """
    返回匹配关键词的 top-level 窗口句柄列表（优先使用进程名过滤）
    """
    hwnds = []

    # 首先通过 psutil 找 chrome 进程列表，获取其 pid set
    chrome_pids = set()
    for proc in psutil.process_iter(['name', 'exe', 'cmdline', 'pid']):
        try:
            name = (proc.info.get('name') or "").lower()
            cmd = " ".join(proc.info.get('cmdline') or []).lower()
            if "chrome.exe" in name or "chrome" in cmd:
                chrome_pids.add(proc.info['pid'])
        except Exception:
            continue

    def enum_handler(hwnd, lParam):
        if not win32gui.IsWindowVisible(hwnd):
            return
        text = win32gui.GetWindowText(hwnd) or ""
        # 部分窗口没有标题，跳过
        if not text:
            return
        # 过滤关键字
        if keyword.lower() in text.lower():
            # 检查窗口所属进程 pid 是否属于 chrome_pids（如果我们找到了）
            try:
                _, pid = win32gui.GetWindowThreadProcessId(hwnd)
                if chrome_pids and pid not in chrome_pids:
                    return
            except Exception:
                pass
            lParam.append(hwnd)

    win32gui.EnumWindows(lambda h, p: enum_handler(h, p), hwnds)
    return hwnds

def _is_window_responsive(hwnd, timeout_ms=1000):
    """
    使用 SendMessageTimeout(WM_NULL) 来检测窗口是否响应。
    返回 True = 响应；False = 无响应/挂起
    """
    result = wintypes.LPARAM()
    try:
        r = SendMessageTimeout(hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG, int(timeout_ms), ctypes.byref(result))
        return bool(r)
    except Exception as e:
        logger.debug("SendMessageTimeout error: %s", e)
        return False

def _small_mouse_nudge():
    """
    轻量模拟鼠标移动：向右1像素再回退（使用 pyautogui if available, otherwise produce a WM_MOUSEMOVE)
    目的是产生 minimal user input，唤醒/解除 throttle，但避免剧烈移动或聚焦问题。
    """
    try:
        if PY_AUTO_AVAILABLE:
            x, y = pyautogui.position()
            pyautogui.moveTo(x+1, y, duration=0)
            pyautogui.moveTo(x, y, duration=0)
            logger.debug("pyautogui nudge done")
            return True
        else:
            # Fallback: PostMessage WM_MOUSEMOVE (may not always work)
            # We'll get cursor position and post a message to the window under cursor.
            x = wintypes.DWORD()
            y = wintypes.DWORD()
            if user32.GetCursorPos(ctypes.byref(x)):  # not ideal binding, use simple approach below
                pass
            # Simpler: just call mouse_event (but it moves system cursor)
            # ctypes.windll.user32.mouse_event(1, 1, 0, 0, 0)  # MOUSEEVENTF_MOVE = 0x0001
            try:
                import win32api
                win32api.mouse_event(1, 1, 0, 0)  # tiny move
                win32api.mouse_event(1, -1, 0, 0)
                return True
            except Exception:
                return False
    except Exception as e:
        logger.debug("small nudge failed: %s", e)
        return False

def _get_window_show_cmd(hwnd):
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        # placement[1] is showCmd: 1 normal, 2 minimized, 3 maximized
        return placement[1]
    except Exception:
        return None

def _show_window_preserve_state(hwnd):
    """
    如果窗口是最大化的，调用 SW_SHOWMAXIMIZED，否则调用 SW_RESTORE (但在我们避免破坏最大化的目标下，我们会细化)
    """
    show_cmd = _get_window_show_cmd(hwnd)
    if show_cmd == win32con.SW_SHOWMAXIMIZED or show_cmd == 3:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
    else:
        # 若最小化，优先还原；若普通，则仅 SetForeground
        if show_cmd == win32con.SW_MINIMIZE or show_cmd == 2:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            # 用 ShowWindow(SW_SHOW) 更少副作用
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

def _app_activate_by_title(hwnd):
    """
    使用 WScript.Shell.AppActivate + SetForegroundWindow 的组合，保证尽量激活目标窗口
    """
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        title = win32gui.GetWindowText(hwnd)
        shell.AppActivate(title)
    except Exception as e:
        logger.debug("AppActivate error: %s", e)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        logger.debug("SetForegroundWindow error: %s", e)

# ---- 主接口 ----
def safe_activate_chrome(window_title_keyword="Chrome", simulate_input=True, responsiveness_timeout_ms=1000, max_retries=3):
    """
    安全激活 Chrome 窗口：
      - 在 STA 线程里调用 COM
      - 检测目标窗口是否响应（SendMessageTimeout）
      - 若不响应：尝试轻量 simulate_input（微量鼠标移动），再检测
      - 保持最大化状态（不破坏原来最大化）
    返回： (True, hwnd) 或 (False, None)
    """
    result = {"ok": False, "hwnd": None, "reason": None}

    def worker():
        pythoncom.CoInitialize()
        try:
            # 1) 找到候选 hwnd 列表
            hwnds = _find_chrome_hwnds_by_proc_name(window_title_keyword)
            if not hwnds:
                result["reason"] = "no_hwnd_found"
                logger.warning("safe_activate_chrome: no chrome hwnd found for keyword '%s'", window_title_keyword)
                return

            # 2) 选第一个最可能的主窗口（通常 index 0）
            hwnd = hwnds[0]
            result["hwnd"] = hwnd

            for attempt in range(1, max_retries + 1):
                logger.info("Attempt %d to activate hwnd %s", attempt, hwnd)
                # use AppActivate + SetForeground
                _app_activate_by_title(hwnd)

                # preserve show state
                _show_window_preserve_state(hwnd)

                # small sleep to let OS update
                time.sleep(0.25)

                # check responsiveness
                ok = _is_window_responsive(hwnd, timeout_ms=responsiveness_timeout_ms)
                if ok:
                    logger.info("Window responsive after activation (hwnd=%s)", hwnd)
                    result["ok"] = True
                    return
                else:
                    logger.warning("Window not responsive after activation (attempt %d)", attempt)
                    # try lightweight nudge if allowed
                    if simulate_input:
                        nudge_ok = _small_mouse_nudge()
                        logger.info("simulate_input nudge result: %s", nudge_ok)
                    # wait a bit and retry
                    time.sleep(0.5)

            # give up after retries
            logger.error("safe_activate_chrome: all retries failed for hwnd=%s", hwnd)
            result["reason"] = "not_responsive"
        finally:
            pythoncom.CoUninitialize()

    # Run worker in separate thread (STA)
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=10)  # join short time; worker handles timeout internally
    return (result["ok"], result["hwnd"], result["reason"])

# ---- 定时守护 ----
def periodic_wakeup(interval_seconds=600, window_title_keyword="Chrome", simulate_input=True, stop_event=None):
    """
    每 interval_seconds 调用一次 safe_activate_chrome。
    返回一个函数 cancel() 用于停止。
    stop_event: 若传入 threading.Event，则在 stop_event.set() 时停止。
    """
    stop_event_local = stop_event or threading.Event()
    timer_holder = {"timer": None}

    def _run_once():
        if stop_event_local.is_set():
            logger.info("periodic_wakeup stopping due to stop_event")
            return
        ok, hwnd, reason = safe_activate_chrome(window_title_keyword, simulate_input=simulate_input)
        logger.info("periodic_wakeup: activation result: ok=%s hwnd=%s reason=%s", ok, hwnd, reason)
        # schedule next
        timer_holder["timer"] = threading.Timer(interval_seconds, _run_once)
        timer_holder["timer"].daemon = True
        timer_holder["timer"].start()

    # start first run immediately in a background thread to avoid blocking
    threading.Thread(target=_run_once, daemon=True).start()

    def cancel():
        stop_event_local.set()
        t = timer_holder.get("timer")
        if t:
            t.cancel()

    return cancel

# ---- Playwright 集成示例 ----
def connect_cdp_with_wakeup(cdp_url="http://127.0.0.1:9222", window_title_keyword="Chrome", retries=5, delay=1.0):
    """
    在尝试 connect_over_cdp 前，先调用 safe_activate_chrome；
    若失败则继续重试。返回已经连接的 browser 对象或 raise Exception。
    注意：此函数只做示例，实际应在主调用处按你的 Playwright 使用习惯封装。
    """
    from playwright.sync_api import sync_playwright
    import time

    for i in range(retries):
        # wakeup
        ok, hwnd, reason = safe_activate_chrome(window_title_keyword, simulate_input=True)
        if ok:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp(cdp_url)
                    logger.info("connect_over_cdp success")
                    return browser
            except Exception as e:
                logger.warning("connect_over_cdp attempt failed: %s", e)
        else:
            logger.warning("wakeup failed before connect, reason=%s", reason)
        time.sleep(delay)

    raise RuntimeError("connect_cdp_with_wakeup: failed after retries")

# If run as script, demonstrate simple wakeup + periodic example
if __name__ == "__main__":
    logger.info("Demo: single activation")
    ok, hwnd, reason = safe_activate_chrome("Edge", simulate_input=True)
    logger.info("Result: ok=%s hwnd=%s reason=%s", ok, hwnd, reason)

    connect_cdp_with_wakeup(cdp_url="http://127.0.0.1:9222", window_title_keyword="Edge")

    # demo periodic wakeup every 10 minutes
    # cancel = periodic_wakeup(interval_seconds=600, window_title_keyword="Chrome")
    # logger.info("Started periodic wakeup every 600 seconds. Press Ctrl+C to stop.")
    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     cancel()
    #     logger.info("Stopped periodic wakeup.")