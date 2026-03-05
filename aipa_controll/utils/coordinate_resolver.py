import re
from typing import Optional, Tuple


class CoordinateResolver:
    """
    Resolve grid coordinate (a1, b3, h10) -> pixel center.

    Supports:
    - dynamic grid size
    - optional zoom region
    """

    GRID_PATTERN = r"^([a-z])([0-9]+)$"

    def __init__(
        self,
        rows: int,
        cols: int,
        screen_width: int,
        screen_height: int,
    ):
        self.rows = rows
        self.cols = cols
        self.screen_width = screen_width
        self.screen_height = screen_height

        # zoom region = (x, y, width, height)
        self.zoom_region: Optional[Tuple[int, int, int, int]] = None

    # =====================================================
    # Public API
    # =====================================================

    def resolve(self, coordinate: str) -> tuple[int, int]:
        """
        Convert grid coordinate -> pixel center.
        """

        coordinate = coordinate.strip().lower()

        match = re.match(self.GRID_PATTERN, coordinate)
        if not match:
            raise ValueError(f"Invalid coordinate format: {coordinate}")

        col_letter, row_str = match.groups()

        col = ord(col_letter) - ord("a")
        row = int(row_str) - 1

        if col < 0 or col >= self.cols:
            raise ValueError(f"Column out of range: {coordinate}")

        if row < 0 or row >= self.rows:
            raise ValueError(f"Row out of range: {coordinate}")

        active_x, active_y, active_w, active_h = self._get_active_region()

        cell_w = active_w / self.cols
        cell_h = active_h / self.rows

        x = active_x + (col * cell_w) + (cell_w / 2)
        y = active_y + (row * cell_h) + (cell_h / 2)

        return int(x), int(y)

    # =====================================================
    # Zoom support
    # =====================================================

    def set_zoom_region(self, x: int, y: int, width: int, height: int):
        """
        Zoom region defines active grid area.
        """

        self.zoom_region = (x, y, width, height)

    def clear_zoom(self):
        self.zoom_region = None

    # =====================================================
    # Internal
    # =====================================================

    def _get_active_region(self):
        if self.zoom_region:
            return self.zoom_region

        return (
            0,
            0,
            self.screen_width,
            self.screen_height,
        )