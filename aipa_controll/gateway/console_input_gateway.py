import sys
import msvcrt
import time
from queue import Queue

from .input_gateway import InputGateway


class ConsoleInputGateway(InputGateway):
    """
    Receive commands from stdin (console).

    Uses blocking readline() inside a dedicated thread.
    This avoids Windows select() limitations.
    """

    def __init__(self, command_queue: Queue):
        super().__init__(command_queue)

    def _run(self):
        while self._running:
            try:
                if msvcrt.kbhit():
                    line = sys.stdin.readline()

                    if line:
                        self._push_command(line)

                time.sleep(0.05)

            except Exception:
                continue