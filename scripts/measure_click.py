"""
measure_click.py - Find where a button sits inside a window, as a fraction of the window's client area.

Usage:
  1. Open the window (e.g. the Blue Archive JP launcher) and make sure the button is visible.
  2. Run this script, hover the mouse over the centre of the button, and press Enter here
     without moving the mouse.
  3. Copy the printed tuple into BA_START_BUTTON in pagent.py.
"""

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()

user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.restype = wintypes.HWND

input("Hover over the button, then press Enter here (keep the mouse still)...")

cursor = wintypes.POINT()
user32.GetCursorPos(ctypes.byref(cursor))
hwnd = user32.GetAncestor(user32.WindowFromPoint(cursor), 2)  # GA_ROOT: the top-level window

title = ctypes.create_unicode_buffer(256)
user32.GetWindowTextW(hwnd, title, 256)
rect = wintypes.RECT()
user32.GetClientRect(hwnd, ctypes.byref(rect))
local = wintypes.POINT(cursor.x, cursor.y)
user32.ScreenToClient(hwnd, ctypes.byref(local))

print(f"Window: {title.value!r}, client size {rect.right}x{rect.bottom}")
print(f"BA_START_BUTTON = ({local.x / rect.right:.3f}, {local.y / rect.bottom:.3f})")