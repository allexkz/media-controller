"""Envio de teclas para janelas (fallback para apps fora do SMTC, ex.: Stremio)."""
import ctypes
import time

import psutil
import win32api
import win32con
import win32gui
import win32process

VK = {
    "space": win32con.VK_SPACE,
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
    "media_play_pause": win32con.VK_MEDIA_PLAY_PAUSE,
    "f": ord("F"),
}

# teclas que também geram um caractere (WM_CHAR) quando postadas
_CHAR = {"space": " ", "f": "f"}

_EXTENDED = {win32con.VK_LEFT, win32con.VK_RIGHT}


def tap(vk):
    flags = win32con.KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED else 0
    win32api.keybd_event(vk, 0, flags, 0)
    win32api.keybd_event(vk, 0, flags | win32con.KEYEVENTF_KEYUP, 0)


def find_window(process_name):
    """Maior janela visível pertencente ao processo."""
    pids = {p.pid for p in psutil.process_iter(["name"]) if p.info["name"] and p.info["name"].lower() == process_name.lower()}
    best, best_area = None, 0
    def cb(hwnd, _):
        nonlocal best, best_area
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid in pids:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            area = (r - l) * (b - t)
            if area > best_area:
                best, best_area = hwnd, area
        return True
    win32gui.EnumWindows(cb, None)
    return best


def _focus(hwnd):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    # Windows bloqueia SetForegroundWindow de processos em segundo plano;
    # um toque em ALT libera a troca de foco.
    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
    time.sleep(0.08)


def _find_child(hwnd, class_name):
    found = []
    def cb(child, _):
        if win32gui.GetClassName(child) == class_name and win32gui.IsWindowVisible(child):
            found.append(child)
        return True
    win32gui.EnumChildWindows(hwnd, cb, None)
    return found[0] if found else None


def post_to(process_name, key, target_class="Chrome_WidgetWin_1"):
    """Posta a tecla direto na janela (sem roubar o foco)."""
    hwnd = find_window(process_name)
    if not hwnd:
        return False
    target = _find_child(hwnd, target_class) or hwnd
    vk = VK[key]
    scan = win32api.MapVirtualKey(vk, 0)
    lparam = 1 | (scan << 16) | ((1 << 24) if vk in _EXTENDED else 0)
    win32api.PostMessage(target, win32con.WM_KEYDOWN, vk, lparam)
    if key in _CHAR:
        win32api.PostMessage(target, win32con.WM_CHAR, ord(_CHAR[key]), lparam)
    win32api.PostMessage(target, win32con.WM_KEYUP, vk, lparam | (1 << 30) | (1 << 31))
    return True


def send_to(process_name, key, restore_focus=True):
    hwnd = find_window(process_name)
    if not hwnd:
        return False
    previous = win32gui.GetForegroundWindow()
    if previous != hwnd:
        _focus(hwnd)
    tap(VK[key])
    if restore_focus and previous and previous != hwnd:
        time.sleep(0.05)
        try:
            _focus(previous)
        except Exception:
            pass
    return True


def windows_with_title(text):
    """Janelas visíveis cujo título contém `text`: [(hwnd, título)]."""
    found = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if text in title:
                found.append((hwnd, title))
        return True
    win32gui.EnumWindows(cb, None)
    return found


def press_in(hwnd, key):
    """Traz a janela pra frente e aperta a tecla (sem devolver o foco)."""
    _focus(hwnd)
    tap(VK[key])
