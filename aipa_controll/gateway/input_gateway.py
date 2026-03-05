from abc import ABC, abstractmethod
import threading
from queue import Queue
from typing import Optional


class InputGateway(ABC):
    """
    Abstract base class for all input gateways.

    Responsibilities:
    - Receive text commands from external systems
    - Push commands into a shared thread-safe queue
    - Run in its own thread
    """

    def __init__(self, command_queue: Queue):
        self._command_queue = command_queue
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start the gateway in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False

    @abstractmethod
    def _run(self):
        """
        Main loop implemented by subclasses.
        Must push text commands into queue.
        """
        pass

    def _push_command(self, command: str):
        """Push command into thread-safe queue."""
        command = command.strip()

        if not command:
            return

        self._command_queue.put(command)