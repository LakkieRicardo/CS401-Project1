import socketserver
import socket
import threading
from queue import Queue
from threading import Thread

from shared.networking import NetworkInterface


class _MessageHandler(socketserver.BaseRequestHandler):
    def handle(self):
        host = self.server.network_interface
        host._add_connection(self.request)
        try:
            while data := self.request.recv(1024):
                host._incoming_messages.put(data)
        except OSError:
            pass
        finally:
            host._remove_connection(self.request)


class _ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, network_interface):
        self.network_interface = network_interface
        super().__init__(server_address, _MessageHandler)


class ServerHost(NetworkInterface):
    def __init__(self, port: int, host: str = "0.0.0.0"):
        super().__init__()
        self._incoming_messages: Queue[bytes] = Queue()
        self._connections: set[socket.socket] = set()
        self._connections_lock = threading.Lock()
        self._serving = threading.Event()
        self._server = _ThreadedTCPServer((host, port), self)

    @property
    def address(self) -> tuple[str, int]:
        return self._server.server_address

    def _add_connection(self, connection: socket.socket) -> None:
        with self._connections_lock:
            self._connections.add(connection)

    def _remove_connection(self, connection: socket.socket) -> None:
        with self._connections_lock:
            self._connections.discard(connection)

    def send_message(self, message: bytes) -> None:
        with self._connections_lock:
            connections = tuple(self._connections)
        for connection in connections:
            try:
                connection.sendall(message)
            except OSError:
                self._remove_connection(connection)

    def receive_message(self, buffer_size: int = 1024) -> bytes:
        return self._incoming_messages.get()

    def serve_forever(self) -> None:
        self._serving.set()
        try:
            self._server.serve_forever()
        finally:
            self._serving.clear()

    def close(self) -> None:
        if self._serving.is_set():
            self._server.shutdown()
        self._server.server_close()
        with self._connections_lock:
            connections = tuple(self._connections)
            self._connections.clear()
        for connection in connections:
            connection.close()
        self._incoming_messages.put(b"")

def host_server(port):
    server = ServerHost(port)
    server.set_message_callback(
        lambda message: print(message.decode("utf-8", errors="replace"))
    )
    message_listener = Thread(target=server.listen_for_messages, daemon=True)
    message_listener.start()
    print(f"Listening on 127.0.0.1:{port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    finally:
        server.close()