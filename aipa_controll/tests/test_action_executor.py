
from dataclasses import dataclass, field


# ============================================
# Fake Action
# ============================================

@dataclass
class Action:
    type: str
    target: any = None
    params: dict = field(default_factory=dict)


# ============================================
# Fake MouseKeyboardController
# ============================================

class FakeMouse:
    def left_click(self, pos):
        print("Mouse left click:", pos)

    def right_click(self, pos):
        print("Mouse right click:", pos)

    def drag(self, start, end):
        print("Mouse drag:", start, "->", end)

    def scroll_up(self):
        print("Mouse scroll up")

    def scroll_down(self):
        print("Mouse scroll down")


class FakeKeyboard:
    def type_text(self, text):
        print("Keyboard type:", text)

    def press_combination(self, keys):
        print("Keyboard press:", keys)


class FakeMouseKeyboardController:
    def __init__(self):
        self.mouse = FakeMouse()
        self.keyboard = FakeKeyboard()


# ============================================
# Fake GridOverlay
# ============================================

class FakeGridOverlay:
    def show_grid(self):
        print("Grid ON")

    def hide_grid(self):
        print("Grid OFF")

    def zoom(self, cell):
        print("Zoom:", cell)

    def resize_grid(self, rows, cols):
        print("Resize grid:", rows, cols)


# ============================================
# Run test
# ============================================

from aipa_controll.executor.action_executor import ActionExecutor

controller = FakeMouseKeyboardController()
overlay = FakeGridOverlay()

executor = ActionExecutor(controller, overlay)

tests = [
    Action(type="click", target=(500, 300)),
    Action(type="right_click", target=(600, 400)),
    Action(type="drag", target=((100, 100), (700, 700))),
    Action(type="scroll", target="up"),
    Action(type="type", target="hello world"),
    Action(type="press", target=["ctrl", "c"]),
    Action(type="grid_on"),
    Action(type="grid_off"),
    Action(type="grid_resize", params={"rows": 6, "cols": 6}),
    Action(type="zoom", target="a5"),
    Action(type="find", target="login"),
]

for action in tests:
    executor.execute(action)