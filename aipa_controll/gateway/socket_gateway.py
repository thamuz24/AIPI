import socket
import threading
from queue import Queue

from .input_gateway import InputGateway


class SocketInputGateway(InputGateway):
    """
    Receive commands via TCP socket.

    Each line = one command.

    Example client input:
        click left
        drag a1 b2
        find login
    """

    def __init__(self, command_queue: Queue, host="127.0.0.1", port=5555):
        super().__init__(command_queue)
        self.host = host
        self.port = port
        self._server_socket = None

    def _run(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen()

        while self._running:
            try:
                self._server_socket.settimeout(1.0)
                client_socket, _ = self._server_socket.accept()

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                client_thread.start()

            except socket.timeout:
                continue

    def _handle_client(self, client_socket: socket.socket):
        with client_socket:
            buffer = ""

            while self._running:
                try:
                    data = client_socket.recv(1024)

                    if not data:
                        break

                    buffer += data.decode("utf-8")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        self._push_command(line)

                except ConnectionResetError:
                    break