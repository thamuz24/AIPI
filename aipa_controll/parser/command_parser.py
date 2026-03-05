import re
from typing import List
from .action import Action


class CommandParser:
    GRID_PATTERN = r"^[a-z][0-9]+$"

    def parse(self, command: str) -> Action:
        command = command.strip().lower()

        if not command:
            raise ValueError("Empty command")

        tokens = command.split()

        if tokens[0] == "click":
            return self._parse_click(tokens)

        if tokens[0] == "right":
            return self._parse_right_click(tokens)

        if tokens[0] == "drag":
            return self._parse_drag(tokens)

        if tokens[0] == "scroll":
            return self._parse_scroll(tokens)

        if tokens[0] == "type":
            return self._parse_type(command)

        if tokens[0] == "press":
            return self._parse_press(tokens)

        if tokens[0] == "grid":
            return self._parse_grid(tokens)

        if tokens[0] == "zoom":
            return self._parse_zoom(tokens)

        raise ValueError(f"Unknown command: {command}")

    def _parse_click(self, tokens: List[str]) -> Action:
        if len(tokens) != 2:
            raise ValueError("Invalid click syntax")

        self._validate_grid(tokens[1])

        return Action(type="click", target=tokens[1])

    def _parse_right_click(self, tokens: List[str]) -> Action:
        if len(tokens) != 3 or tokens[1] != "click":
            raise ValueError("Invalid right click syntax")

        self._validate_grid(tokens[2])

        return Action(type="right_click", target=tokens[2])

    def _parse_drag(self, tokens: List[str]) -> Action:
        if len(tokens) != 3:
            raise ValueError("Invalid drag syntax")

        self._validate_grid(tokens[1])
        self._validate_grid(tokens[2])

        return Action(type="drag", target=(tokens[1], tokens[2]))

    def _parse_scroll(self, tokens: List[str]) -> Action:
        if len(tokens) != 2:
            raise ValueError("Invalid scroll syntax")

        if tokens[1] not in ("up", "down"):
            raise ValueError("Scroll must be up/down")

        return Action(type="scroll", target=tokens[1])

    def _parse_type(self, command: str) -> Action:
        text = command[5:].strip()

        if not text:
            raise ValueError("Type requires text")

        return Action(type="type", target=text)

    def _parse_press(self, tokens: List[str]) -> Action:
        if len(tokens) < 2:
            raise ValueError("Invalid press syntax")

        return Action(type="press", target=tokens[1:])

    def _parse_grid(self, tokens: List[str]) -> Action:
        """
        Supported:
            grid on
            grid off
            grid 6 6
        """
        if len(tokens) == 2:
            if tokens[1] == "on":
                return Action(type="grid_on")

            if tokens[1] == "off":
                return Action(type="grid_off")

            raise ValueError("grid command must be 'on' or 'off'")

        if len(tokens) == 3:
            try:
                rows = int(tokens[1])
                cols = int(tokens[2])
            except ValueError:
                raise ValueError("grid size must be integers")

            if rows <= 0 or cols <= 0:
                raise ValueError("grid size must be > 0")

            return Action(
                type="grid_resize",
                params={
                    "rows": rows,
                    "cols": cols
                }
            )

        raise ValueError("Invalid grid syntax")

    def _parse_zoom(self, tokens: List[str]) -> Action:
        if len(tokens) != 2:
            raise ValueError("Invalid zoom syntax")

        self._validate_grid(tokens[1])

        return Action(type="zoom", target=tokens[1])

    def _validate_grid(self, token: str):
        if not re.match(self.GRID_PATTERN, token):
            raise ValueError(f"Invalid grid coordinate: {token}")