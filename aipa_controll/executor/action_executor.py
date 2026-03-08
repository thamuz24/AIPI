import logging
from threading import Lock
from typing import Callable, Dict, Any


class ActionExecutor:
    """
    Dispatch Action object tới controller tương ứng.

    Dependencies injected:
    - mouse_keyboard_controller
    - grid_overlay

    Thread-safe.
    """

    def __init__(self, mouse_keyboard_controller, grid_overlay):
        self.mouse_keyboard_controller = mouse_keyboard_controller
        self.grid_overlay = grid_overlay

        self._lock = Lock()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ActionExecutor")

        self._dispatch_table: Dict[str, Callable] = {
            "click": self._execute_click,
            "right_click": self._execute_right_click,
            "drag": self._execute_drag,
            "scroll": self._execute_scroll,
            "type": self._execute_type,
            "press": self._execute_press,
            "grid_on": self._execute_grid_on,
            "grid_off": self._execute_grid_off,
            "grid_resize": self._execute_grid_resize,
            "zoom": self._execute_zoom,
            "find": self._execute_find,
            "grid": self._execute_grid_legacy,
        }

    def execute(self, action):
        """
        Execute Action safely.
        """

        with self._lock:
            if action.type not in self._dispatch_table:
                raise ValueError(f"Unsupported action type: {action.type}")

            self.logger.info(f"Executing action: {action}")

            handler = self._dispatch_table[action.type]
            handler(action)

    # =====================================================
    # Mouse
    # =====================================================

    def _execute_click(self, action):
        self.mouse_keyboard_controller.mouse.left_click(action.target)

    def _execute_right_click(self, action):
        self.mouse_keyboard_controller.mouse.right_click(action.target)

    def _execute_drag(self, action):
        start, end = action.target
        self.mouse_keyboard_controller.mouse.drag(start, end)

    def _execute_scroll(self, action):
        if action.target == "up":
            self.mouse_keyboard_controller.mouse.scroll_up()
        elif action.target == "down":
            self.mouse_keyboard_controller.mouse.scroll_down()
        else:
            raise ValueError(f"Invalid scroll direction: {action.target}")

    # =====================================================
    # Keyboard
    # =====================================================

    def _execute_type(self, action):
        self.mouse_keyboard_controller.keyboard.type_text(action.target)

    def _execute_press(self, action):
        self.mouse_keyboard_controller.keyboard.press_combination(action.target)

    # =====================================================
    # Grid
    # =====================================================

    def _execute_grid_on(self, action):
        self.grid_overlay.show_grid()

    def _execute_grid_off(self, action):
        self.grid_overlay.hide_grid()

    def _execute_grid_resize(self, action):
        rows = action.params["rows"]
        cols = action.params["cols"]

        if hasattr(self.grid_overlay, "resize_grid"):
            self.grid_overlay.resize_grid(rows, cols)
        else:
            self.logger.warning("GridOverlay does not implement resize_grid()")

    def _execute_zoom(self, action):
        self.grid_overlay.zoom(action.target)

    def _execute_grid_legacy(self, action):
        """
        Compatibility for parser returning:
            type='grid', target='on/off'
        """

        if action.target == "on":
            self.grid_overlay.show_grid()
        elif action.target == "off":
            self.grid_overlay.hide_grid()
        else:
            raise ValueError(f"Invalid grid target: {action.target}")

    # =====================================================
    # OCR placeholder
    # =====================================================

    def _execute_find(self, action):
        self.logger.info(f"OCR placeholder search for text: {action.target}")