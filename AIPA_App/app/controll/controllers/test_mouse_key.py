from mouse_keyboard_controller import MouseKeyboardController

controller = MouseKeyboardController()

controller.mouse.left_click((500, 300))
controller.mouse.right_click((600, 400))
controller.mouse.drag((300, 300), (800, 600))
controller.mouse.scroll_up()
controller.mouse.scroll_down()