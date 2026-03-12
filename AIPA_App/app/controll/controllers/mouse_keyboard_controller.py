from threading import Lock
from typing import Tuple, List

from pynput.mouse import Controller as MouseControllerLib
from pynput.mouse import Button

from pynput.keyboard import Controller as KeyboardControllerLib
from pynput.keyboard import Key


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
            self._mouse.position = position
            self._mouse.click(Button.left, 1)

    def right_click(self, position: Tuple[int, int]):
        with self._lock:
            self._mouse.position = position
            self._mouse.click(Button.right, 1)

    def drag(self, start: Tuple[int, int], end: Tuple[int, int]):
        with self._lock:
            self._mouse.position = start
            self._mouse.press(Button.left)
            self._mouse.position = end
            self._mouse.release(Button.left)

    def scroll_up(self, amount: int = 2):
        with self._lock:
            self._mouse.scroll(0, amount)

    def scroll_down(self, amount: int = 2):
        with self._lock:
            self._mouse.scroll(0, -amount)


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
        self._lock = Lock()

    def type_text(self, text: str):
        with self._lock:
            self._keyboard.type(text)

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