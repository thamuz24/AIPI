import argparse
import json
import os
import string
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


class GridOverlay(QWidget):
    def __init__(
        self,
        command_file: Path,
        status_file: Path,
        pid_file: Path,
        rows: int = 6,
        cols: int = 6,
    ) -> None:
        super().__init__()
        self.command_file = command_file
        self.status_file = status_file
        self.pid_file = pid_file
        self.rows = max(1, int(rows))
        self.cols = max(1, int(cols))
        self.grid_visible = False
        self.zoom_cell: Optional[str] = None
        self.last_request_id = ''
        self.last_command_mtime = 0.0
        self.last_error = ''
        self.last_action = 'boot'

        self._setup_window()
        self._setup_style()
        self._setup_timers()
        self._write_pid()
        self._write_status()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen()
        geometry = screen.geometry() if screen else None
        if geometry:
            self.setGeometry(geometry)
        else:
            self.setGeometry(0, 0, 1280, 720)

    def _setup_style(self) -> None:
        self.grid_pen = QPen(QColor(35, 214, 132, 205), 2)
        self.grid_fill = QColor(20, 112, 84, 28)
        self.text_color = QColor(248, 252, 255)
        self.subtext_color = QColor(218, 241, 255, 230)
        self.focus_fill = QColor(255, 196, 0, 55)
        self.header_fill = QColor(9, 29, 43, 180)
        self.header_border = QColor(90, 191, 233, 190)
        self.header_font = QFont('Segoe UI', 12)
        self.label_font = QFont('Consolas', 13)
        self.coord_font = QFont('Consolas', 9)

    def _setup_timers(self) -> None:
        self.command_timer = QTimer(self)
        self.command_timer.timeout.connect(self._poll_command_file)
        self.command_timer.start(180)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._write_status)
        self.status_timer.start(750)

    def _write_pid(self) -> None:
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()), encoding='utf-8')

    def _write_status(self) -> None:
        payload = {
            'running': True,
            'visible': bool(self.grid_visible),
            'zoom_cell': self.zoom_cell or '',
            'rows': self.rows,
            'cols': self.cols,
            'pid': os.getpid(),
            'last_request_id': self.last_request_id,
            'last_action': self.last_action,
            'last_error': self.last_error,
            'updated_at': time.time(),
            'screen_width': int(self.width()),
            'screen_height': int(self.height()),
        }
        _write_json(self.status_file, payload)

    def _apply_command(self, payload: Dict[str, Any]) -> None:
        action = str(payload.get('action') or '').strip().lower()
        if not action:
            return

        self.last_request_id = str(payload.get('request_id') or '')
        self.last_action = action
        self.last_error = ''

        rows = payload.get('rows')
        cols = payload.get('cols')
        if isinstance(rows, int) and rows > 0:
            self.rows = rows
        if isinstance(cols, int) and cols > 0:
            self.cols = cols

        focus = str(payload.get('focus') or '').strip().lower()

        if action == 'show':
            self.grid_visible = True
            self.zoom_cell = focus or None
            self.show()
            self.raise_()
            self.update()
            return

        if action == 'hide':
            self.grid_visible = False
            self.zoom_cell = None
            self.hide()
            self.update()
            return

        if action == 'zoom':
            self.grid_visible = True
            self.zoom_cell = focus or self.zoom_cell
            self.show()
            self.raise_()
            self.update()
            return

        if action == 'reset':
            self.zoom_cell = None
            self.update()
            return

        if action == 'stop':
            self.grid_visible = False
            self.hide()
            self._write_status()
            QApplication.instance().quit()
            return

        self.last_error = f'Unsupported action: {action}'

    def _poll_command_file(self) -> None:
        try:
            if not self.command_file.exists():
                return
            stat = self.command_file.stat()
            if stat.st_mtime <= self.last_command_mtime:
                return
            self.last_command_mtime = stat.st_mtime
            payload = _read_json(self.command_file)
            self._apply_command(payload)
            self._write_status()
        except Exception as exc:
            self.last_error = str(exc)
            self._write_status()

    def _get_active_rect(self) -> QRectF:
        base_rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        if not self.zoom_cell:
            return base_rect

        if len(self.zoom_cell) < 2:
            return base_rect

        col_letter = self.zoom_cell[0]
        if col_letter not in string.ascii_lowercase[: self.cols]:
            return base_rect
        try:
            row_number = int(self.zoom_cell[1:])
        except ValueError:
            return base_rect
        if row_number < 1 or row_number > self.rows:
            return base_rect

        cell_w = base_rect.width() / self.cols
        cell_h = base_rect.height() / self.rows
        col_index = string.ascii_lowercase.index(col_letter)
        row_index = row_number - 1
        return QRectF(
            col_index * cell_w,
            row_index * cell_h,
            cell_w,
            cell_h,
        )

    def _draw_header(self, painter: QPainter) -> None:
        header_rect = QRectF(22.0, 18.0, min(620.0, self.width() - 44.0), 78.0)
        painter.setPen(QPen(self.header_border, 1))
        painter.setBrush(self.header_fill)
        painter.drawRoundedRect(header_rect, 14.0, 14.0)

        painter.setPen(self.text_color)
        painter.setFont(self.header_font)
        painter.drawText(
            header_rect.adjusted(14.0, 12.0, -14.0, -34.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            'Luoi toa do chuot dang hien tren man hinh',
        )
        painter.setPen(self.subtext_color)
        painter.setFont(self.coord_font)
        subtitle = (
            f'Dung a1..f6 hoac toa do pixel. Vi du: '
            f'"keo chuot tu 100,200 den 300,400" | '
            f'{int(self.width())}x{int(self.height())} px'
        )
        painter.drawText(
            header_rect.adjusted(14.0, 36.0, -14.0, -10.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            subtitle,
        )

    def paintEvent(self, _event) -> None:
        if not self.grid_visible:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        active_rect = self._get_active_rect()

        self._draw_header(painter)

        cell_w = active_rect.width() / self.cols
        cell_h = active_rect.height() / self.rows

        for row_index in range(self.rows):
            for col_index in range(self.cols):
                left = active_rect.left() + col_index * cell_w
                top = active_rect.top() + row_index * cell_h
                rect = QRectF(left, top, cell_w, cell_h)
                label = f'{string.ascii_lowercase[col_index]}{row_index + 1}'
                center_x = int(round(rect.center().x()))
                center_y = int(round(rect.center().y()))

                if self.zoom_cell and label == self.zoom_cell:
                    painter.setBrush(self.focus_fill)
                else:
                    painter.setBrush(self.grid_fill)
                painter.setPen(self.grid_pen)
                painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), 10.0, 10.0)

                painter.setPen(self.text_color)
                painter.setFont(self.label_font)
                painter.drawText(
                    rect.adjusted(10.0, 8.0, -10.0, -28.0),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                    label.upper(),
                )

                painter.setPen(self.subtext_color)
                painter.setFont(self.coord_font)
                painter.drawText(
                    rect.adjusted(10.0, 28.0, -10.0, -8.0),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                    f'{center_x}, {center_y}',
                )

    def closeEvent(self, event) -> None:
        try:
            self._write_status()
        finally:
            try:
                if self.pid_file.exists():
                    self.pid_file.unlink()
            except Exception:
                pass
        super().closeEvent(event)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--command-file', required=True)
    parser.add_argument('--status-file', required=True)
    parser.add_argument('--pid-file', required=True)
    parser.add_argument('--rows', type=int, default=6)
    parser.add_argument('--cols', type=int, default=6)
    args = parser.parse_args()

    app = QApplication(sys.argv)
    overlay = GridOverlay(
        command_file=Path(args.command_file),
        status_file=Path(args.status_file),
        pid_file=Path(args.pid_file),
        rows=args.rows,
        cols=args.cols,
    )
    overlay.hide()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
