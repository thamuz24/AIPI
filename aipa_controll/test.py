import threading
import time

from overlay.grid_overlay import GridOverlayService

overlay = GridOverlayService(rows=6, cols=6)

ui_thread = threading.Thread(target=overlay.start, daemon=True)
ui_thread.start()

time.sleep(2)
overlay.show_grid()

time.sleep(2)
overlay.zoom("c3")

time.sleep(3)
overlay.reset_zoom()

time.sleep(2)
overlay.hide_grid()

ui_thread.join()