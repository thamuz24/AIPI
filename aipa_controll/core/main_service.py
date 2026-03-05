import logging
import threading
from queue import Queue, Empty


class MainService:
    """
    Orchestrates full control engine pipeline.

    Flow:
        InputGateway -> Queue -> Parser -> Executor
    """

    def __init__(
            self,
            input_gateway,
            command_parser,
            action_executor,
            command_queue,
            grid_overlay=None,
    ):
        self.input_gateway = input_gateway
        self.command_parser = command_parser
        self.action_executor = action_executor
        self.command_queue = command_queue
        self.grid_overlay = grid_overlay

        self._running = False
        self._worker_thread = None

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("MainService")

    # =====================================================
    # Public lifecycle
    # =====================================================

    def start(self):
        """
        Start gateway + processing thread.
        """
        if self._running:
            return

        self.logger.info("Starting MainService")

        self._running = True

        self.input_gateway.start()

        self._worker_thread = threading.Thread(
            target=self._main_loop,
            daemon=True
        )
        self._worker_thread.start()

    def stop(self):
        self.logger.info("Stopping MainService")

        self._running = False

        self.input_gateway.stop()

        if self.grid_overlay:
            self.grid_overlay.stop()

        if self._worker_thread and threading.current_thread() != self._worker_thread:
            self._worker_thread.join(timeout=2)

        self.logger.info("MainService stopped")

    # =====================================================
    # Internal loop
    # =====================================================

    def _main_loop(self):
        while self._running:
            try:
                command = self.command_queue.get(timeout=0.2)

                command = command.strip().lower()

                if command in ("exit", "quit"):
                    self.logger.info("Shutdown command received")
                    self.stop()
                    break

                self.logger.info(f"Received command: {command}")

                action = self.command_parser.parse(command)

                self.logger.info(f"Parsed action: {action}")

                self.action_executor.execute(action)

                self.logger.info("Action executed successfully")

            except Empty:
                continue

            except Exception as e:
                self.logger.error(f"Pipeline error: {e}")