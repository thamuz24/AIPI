import threading
import time
from queue import Queue

from aipa_controll.gateway.console_input_gateway import ConsoleInputGateway
from aipa_controll.parser.command_parser import CommandParser
from aipa_controll.controllers.mouse_keyboard_controller import MouseKeyboardController
from aipa_controll.executor.action_executor import ActionExecutor
from aipa_controll.overlay.grid_overlay import GridOverlayService
from aipa_controll.core.main_service import MainService


# =====================================================
# Shared Queue
# =====================================================

command_queue = Queue()

# =====================================================
# Input
# =====================================================

input_gateway = ConsoleInputGateway(command_queue)

# =====================================================
# Parser
# =====================================================

parser = CommandParser()

# =====================================================
# Controller
# =====================================================

controller = MouseKeyboardController()

# =====================================================
# Overlay (must live in main thread)
# =====================================================

overlay = GridOverlayService(rows=6, cols=6)

# =====================================================
# Executor
# =====================================================

executor = ActionExecutor(controller, overlay)

# =====================================================
# MainService
# =====================================================

service = MainService(
    input_gateway=input_gateway,
    command_parser=parser,
    action_executor=executor,
    command_queue=command_queue,
    grid_overlay=overlay,
)

# =====================================================
# Start MainService in worker thread
# =====================================================

service_thread = threading.Thread(
    target=service.start,
    daemon=True
)

service_thread.start()

print("System ready.")
print("Type commands:")
print("Examples:")
print("  type hello")
print("  press ctrl c")
print("  grid on")
print("  grid off")
print("  zoom a5")
print("CTRL+C to exit")

# =====================================================
# Overlay must run in main thread
# =====================================================

try:
    overlay.start()

except KeyboardInterrupt:
    print("Shutdown requested...")
    service.stop()