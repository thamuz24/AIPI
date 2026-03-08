import time

from aipa_controll.controllers.mouse_keyboard_controller import MouseKeyboardController


def test_mouse():
    controller = MouseKeyboardController()

    print("Test left click sau 3 giây...")
    time.sleep(3)
    controller.mouse.left_click((500, 500))

    print("Test right click sau 2 giây...")
    time.sleep(2)
    controller.mouse.right_click((600, 500))

    print("Test drag sau 2 giây...")
    time.sleep(2)
    controller.mouse.drag((400, 400), (800, 400))

    print("Test scroll up...")
    time.sleep(2)
    controller.mouse.scroll_up()

    print("Test scroll down...")
    time.sleep(2)
    controller.mouse.scroll_down()


def test_keyboard():
    controller = MouseKeyboardController()

    print("Gõ text sau 3 giây...")
    time.sleep(3)
    controller.keyboard.type_text("hello world")

    print("Ctrl+C sau 2 giây...")
    time.sleep(2)
    controller.keyboard.press_combination(["ctrl", "c"])

    print("Alt+Tab sau 2 giây...")
    time.sleep(2)
    controller.keyboard.press_combination(["alt", "tab"])


if __name__ == "__main__":
    # Chạy từng phần để dễ quan sát
    test_mouse()
    test_keyboard()