import sys
import string
from typing import Optional

from PyQt6.QtCore import Qt, QRect, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QApplication, QWidget


# =========================================================
# Thread-safe signal bridge
# =========================================================

class OverlayController(QObject):
    show_grid_signal = pyqtSignal()
    hide_grid_signal = pyqtSignal()
    zoom_signal = pyqtSignal(str)
    reset_zoom_signal = pyqtSignal()
    stop_signal = pyqtSignal()


# =========================================================
# Grid Widget
# =========================================================

class GridOverlay(QWidget):

    def __init__(self, rows: int = 6, cols: int = 6):
        super().__init__()

        self.rows = rows
        self.cols = cols

        self.grid_visible = False
        self.zoom_cell: Optional[str] = None

        self._setup_window()
        self._setup_style()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def _setup_style(self):
        self.grid_pen = QPen(QColor(0, 255, 0, 180), 2)
        self.text_color = QColor(255, 255, 255)
        self.font = QFont("Consolas", 14)

    def show_grid(self):
        self.grid_visible = True
        self.show()
        self.update()

    def hide_grid(self):
        self.grid_visible = False
        self.zoom_cell = None
        self.update()

    def zoom_to(self, coord: str):
        self.zoom_cell = coord.lower()
        self.update()

    def reset_zoom(self):
        self.zoom_cell = None
        self.update()

    def paintEvent(self, event):
        if not self.grid_visible:
            return

        painter = QPainter(self)
        painter.setPen(self.grid_pen)
        painter.setFont(self.font)

        rect = self._get_active_rect()

        cell_w = rect.width() / self.cols
        cell_h = rect.height() / self.rows

        for r in range(self.rows):
            for c in range(self.cols):
                x = rect.left() + c * cell_w
                y = rect.top() + r * cell_h

                painter.drawRect(int(x), int(y), int(cell_w), int(cell_h))

                label = f"{string.ascii_lowercase[c]}{r+1}"

                painter.setPen(self.text_color)
                painter.drawText(int(x + 6), int(y + 18), label)
                painter.setPen(self.grid_pen)

    def _get_active_rect(self):
        if not self.zoom_cell:
            return self.rect()

        col_letter = self.zoom_cell[0]
        row_number = int(self.zoom_cell[1:])

        col = string.ascii_lowercase.index(col_letter)
        row = row_number - 1

        cell_w = self.width() / self.cols
        cell_h = self.height() / self.rows

        x = col * cell_w
        y = row * cell_h

        return QRect(int(x), int(y), int(cell_w), int(cell_h))


# =========================================================
# Service Wrapper
# =========================================================

class GridOverlayService:

    def __init__(self, rows=6, cols=6):
        self.rows = rows
        self.cols = cols

        self.app = None
        self.overlay = None

        self.controller = OverlayController()

    def start(self):
        self.app = QApplication(sys.argv)

        self.overlay = GridOverlay(self.rows, self.cols)

        self.controller.show_grid_signal.connect(self.overlay.show_grid)
        self.controller.hide_grid_signal.connect(self.overlay.hide_grid)
        self.controller.zoom_signal.connect(self.overlay.zoom_to)
        self.controller.reset_zoom_signal.connect(self.overlay.reset_zoom)
        self.controller.stop_signal.connect(self.app.quit)

        self.overlay.show()

        self.app.exec()

    def show_grid(self):
        self.controller.show_grid_signal.emit()

    def hide_grid(self):
        self.controller.hide_grid_signal.emit()

    def zoom(self, coord):
        self.controller.zoom_signal.emit(coord)

    def reset_zoom(self):
        self.controller.reset_zoom_signal.emit()

    def resize_grid(self, rows, cols):
        if self.overlay:
            self.overlay.rows = rows
            self.overlay.cols = cols
            self.overlay.update()

    def stop(self):
        self.hide_grid()

        if self.app:
            self.controller.stop_signal.emit()