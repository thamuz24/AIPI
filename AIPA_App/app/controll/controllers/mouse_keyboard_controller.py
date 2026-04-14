import ctypes
from ctypes import wintypes
import os
import time
from threading import Lock, RLock
from typing import Optional, Tuple, List

from pynput.mouse import Controller as MouseControllerLib
from pynput.mouse import Button

from pynput.keyboard import Controller as KeyboardControllerLib
from pynput.keyboard import Key


if os.name == "nt":
    _CF_UNICODETEXT = 13
    _GMEM_MOVEABLE = 0x0002
    _GHND = 0x0042
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    _user32.OpenClipboard.argtypes = [wintypes.HWND]
    _user32.OpenClipboard.restype = wintypes.BOOL
    _user32.CloseClipboard.argtypes = []
    _user32.CloseClipboard.restype = wintypes.BOOL
    _user32.EmptyClipboard.argtypes = []
    _user32.EmptyClipboard.restype = wintypes.BOOL
    _user32.GetClipboardData.argtypes = [wintypes.UINT]
    _user32.GetClipboardData.restype = wintypes.HANDLE
    _user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    _user32.SetClipboardData.restype = wintypes.HANDLE

    _kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    _kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    _kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalLock.restype = wintypes.LPVOID
    _kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalUnlock.restype = wintypes.BOOL
    _kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalFree.restype = wintypes.HGLOBAL
else:
    _CF_UNICODETEXT = 13
    _GMEM_MOVEABLE = 0x0002
    _GHND = 0x0042
    _user32 = None
    _kernel32 = None


_MOUSE_MOVE_MIN_STEPS = 8
_MOUSE_MOVE_MAX_STEPS = 28
_MOUSE_MOVE_BASE_DURATION_SECONDS = 0.18
_MOUSE_DRAG_DURATION_SECONDS = 0.25


# =========================================================
# Mouse Controller
# =========================================================

class MouseController:
    """
    Mouse control layer.

    Responsibilities:
    - left click
    - right click
    - drag
    - scroll

    Thread-safe.
    """

    def __init__(self):
        self._mouse = MouseControllerLib()
        self._lock = Lock()

    def left_click(self, position: Tuple[int, int]):
        with self._lock:
            self._move_smoothly(position)
            self._mouse.click(Button.left, 1)

    def move_to(self, position: Tuple[int, int]):
        with self._lock:
            self._move_smoothly(position)
            return self._mouse.position

    def move_relative(self, delta: Tuple[int, int]):
        with self._lock:
            current_x, current_y = self._mouse.position
            next_position = (current_x + int(delta[0]), current_y + int(delta[1]))
            self._move_smoothly(next_position)
            return self._mouse.position

    def get_position(self):
        with self._lock:
            return self._mouse.position

    def right_click(self, position: Tuple[int, int]):
        with self._lock:
            self._move_smoothly(position)
            self._mouse.click(Button.right, 1)

    def drag(self, start: Tuple[int, int], end: Tuple[int, int]):
        with self._lock:
            self._move_smoothly(start)
            self._mouse.press(Button.left)
            try:
                self._move_smoothly(end, duration=_MOUSE_DRAG_DURATION_SECONDS)
            finally:
                self._mouse.release(Button.left)

    def scroll_up(self, amount: int = 2):
        with self._lock:
            self._mouse.scroll(0, amount)

    def scroll_down(self, amount: int = 2):
        with self._lock:
            self._mouse.scroll(0, -amount)

    def _move_smoothly(self, position: Tuple[int, int], duration: float = _MOUSE_MOVE_BASE_DURATION_SECONDS):
        target_x = int(position[0])
        target_y = int(position[1])
        current_x, current_y = self._mouse.position
        current_x = int(current_x)
        current_y = int(current_y)

        delta_x = target_x - current_x
        delta_y = target_y - current_y
        distance = max(abs(delta_x), abs(delta_y))
        if distance == 0:
            return

        steps = max(_MOUSE_MOVE_MIN_STEPS, min(_MOUSE_MOVE_MAX_STEPS, distance // 24))
        sleep_seconds = max(0.002, float(duration) / max(1, steps))
        for step in range(1, steps + 1):
            next_x = round(current_x + (delta_x * step / steps))
            next_y = round(current_y + (delta_y * step / steps))
            self._mouse.position = (next_x, next_y)
            time.sleep(sleep_seconds)

        self._mouse.position = (target_x, target_y)


# =========================================================
# Keyboard Controller
# =========================================================

class KeyboardController:
    """
    Keyboard control layer.

    Responsibilities:
    - type text
    - hotkeys

    Thread-safe.
    """

    KEY_MAP = {
        "ctrl": Key.ctrl,
        "alt": Key.alt,
        "shift": Key.shift,
        "tab": Key.tab,
        "enter": Key.enter,
        "esc": Key.esc,
        "space": Key.space,
        "backspace": Key.backspace,
        "delete": Key.delete,
    }

    def __init__(self):
        self._keyboard = KeyboardControllerLib()
        self._lock = RLock()

    def type_text(self, text: str):
        with self._lock:
            payload = str(text or "")
            if not payload:
                return

            if os.name == "nt" and self._paste_text_via_clipboard(payload):
                return

            self._keyboard.type(payload)

    def press_combination(self, keys: List[str]):
        """
        Example:
            ["ctrl", "c"]
            ["alt", "tab"]
        """

        with self._lock:
            resolved_keys = [self._resolve_key(k) for k in keys]

            for key in resolved_keys:
                self._keyboard.press(key)

            for key in reversed(resolved_keys):
                self._keyboard.release(key)

    def _resolve_key(self, key: str):
        key = key.lower()

        if key in self.KEY_MAP:
            return self.KEY_MAP[key]

        return key

    def _paste_text_via_clipboard(self, text: str) -> bool:
        original_clipboard = None
        had_clipboard_text = False
        try:
            original_clipboard = self._get_clipboard_text()
            had_clipboard_text = original_clipboard is not None
            self._set_clipboard_text(text)
            time.sleep(0.18)
            self.press_combination(["ctrl", "v"])
            time.sleep(0.08)
            return True
        except Exception:
            return False
        finally:
            if had_clipboard_text:
                try:
                    self._set_clipboard_text(original_clipboard or "")
                except Exception:
                    pass

    def _get_clipboard_text(self) -> Optional[str]:
        if os.name != "nt" or _user32 is None:
            return None

        for _ in range(5):
            if _user32.OpenClipboard(None):
                break
            time.sleep(0.02)
        else:
            raise RuntimeError("Không mở được clipboard.")

        try:
            handle = _user32.GetClipboardData(_CF_UNICODETEXT)
            if not handle:
                return None
            locked = _kernel32.GlobalLock(handle)
            if not locked:
                return None
            try:
                return ctypes.wstring_at(locked)
            finally:
                _kernel32.GlobalUnlock(handle)
        finally:
            _user32.CloseClipboard()

    def _set_clipboard_text(self, text: str):
        if os.name != "nt" or _user32 is None:
            raise RuntimeError("Clipboard Unicode hiện chỉ hỗ trợ trên Windows.")

        payload = str(text or "")
        data = payload.encode("utf-16-le") + b"\x00\x00"

        for _ in range(5):
            if _user32.OpenClipboard(None):
                break
            time.sleep(0.02)
        else:
            raise RuntimeError("Không mở được clipboard.")

        handle = None
        locked = None
        try:
            if not _user32.EmptyClipboard():
                raise RuntimeError("Không xóa được clipboard hiện tại.")
            handle = _kernel32.GlobalAlloc(_GHND, len(data))
            if not handle:
                raise MemoryError("Không cấp phát được bộ nhớ clipboard.")
            locked = _kernel32.GlobalLock(handle)
            if not locked:
                raise MemoryError("Không khóa được bộ nhớ clipboard.")
            ctypes.memmove(locked, data, len(data))
            _kernel32.GlobalUnlock(handle)
            locked = None
            if not _user32.SetClipboardData(_CF_UNICODETEXT, handle):
                raise RuntimeError("Không ghi được nội dung vào clipboard.")
            handle = None
        finally:
            if locked:
                _kernel32.GlobalUnlock(handle)
            if handle:
                _kernel32.GlobalFree(handle)
            _user32.CloseClipboard()


# =========================================================
# Unified Controller
# =========================================================

class MouseKeyboardController:
    """
    Unified facade for ActionExecutor.

    ActionExecutor chỉ cần gọi:
        controller.mouse.left_click(...)
        controller.keyboard.type_text(...)
    """

    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
