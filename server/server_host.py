import socketserver
import socket
import select
import threading
from collections import deque
from dataclasses import dataclass, field
from queue import Queue
from threading import Thread
from typing import Literal
from uuid import UUID, uuid4

from shared.networking import NetworkInterface


@dataclass
class ClientConnection:
    client_id: UUID
    connection: socket.socket
    address: tuple[str, int]
    username: str
    decision: threading.Event = field(default_factory=threading.Event)
    connection_state: Literal["pending", "accepted"] = "pending"


class _MessageHandler(socketserver.BaseRequestHandler):
    def handle(self):
        host = self.server.network_interface
        client = None
        try:
            username = host._receive_username(self.request)
            client = host._queue_connection(
                self.request, self.client_address, username
            )
            if not host._wait_for_connection_decision(client):
                return
            while data := self.request.recv(1024):
                host._incoming_messages.put(data)
        except OSError:
            pass
        finally:
            if client is not None:
                host._remove_connection(client.client_id)


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
        self._client_conns: dict[UUID, ClientConnection] = {}
        self._pending_conn_order: deque[UUID] = deque()
        self._connections_lock = threading.Lock()
        self._serving = threading.Event()
        self._server = _ThreadedTCPServer((host, port), self)

    @property
    def address(self) -> tuple[str, int]:
        return self._server.server_address

    @property
    def client_connections(self) -> dict[UUID, ClientConnection]:
        with self._connections_lock:
            return dict(self._client_conns)

    @property
    def pending_connections(self) -> dict[UUID, ClientConnection]:
        with self._connections_lock:
            return {
                client_id: client
                for client_id, client in self._client_conns.items()
                if client.connection_state == "pending"
            }

    @staticmethod
    def _receive_username(connection: socket.socket) -> str:
        username = bytearray()
        while len(username) < 64:
            byte = connection.recv(1)
            if not byte:
                raise ConnectionError("Client disconnected before sending username")
            if byte == b"\n":
                decoded_username = username.decode("utf-8").strip()
                if decoded_username:
                    return decoded_username
                raise ValueError("Username cannot be empty")
            username.extend(byte)
        raise ValueError("Username must be 64 bytes or fewer")

    def _queue_connection(
        self, connection: socket.socket, address: tuple[str, int], username: str
    ) -> ClientConnection:
        client_id = uuid4()
        client = ClientConnection(client_id, connection, address, username)
        with self._connections_lock:
            self._client_conns[client_id] = client
            self._pending_conn_order.append(client_id)
            self._dispatch_connection_request(client_id, address[0], username)
        return client

    def _wait_for_connection_decision(self, client: ClientConnection) -> bool:
        while not client.decision.wait(0.1):
            if not self._has_client_disconnected(client.connection):
                continue

            with self._connections_lock:
                still_pending = (
                    self._client_conns.get(client.client_id) is client
                    and client.connection_state == "pending"
                )
            if still_pending:
                self._remove_connection(client.client_id)
                self._dispatch_connection_cancelled(
                    client.client_id, client.address[0], client.username
                )
            return False
        return client.connection_state == "accepted"

    @staticmethod
    def _has_client_disconnected(connection: socket.socket) -> bool:
        try:
            readable, _, _ = select.select([connection], [], [], 0)
            return bool(readable) and connection.recv(1, socket.MSG_PEEK) == b""
        except OSError:
            return True

    def accept_pending_connection(self) -> tuple[UUID, str, str] | None:
        with self._connections_lock:
            while self._pending_conn_order:
                client_id = self._pending_conn_order.popleft()
                client = self._client_conns.get(client_id)
                if client is None or client.connection_state != "pending":
                    continue
                client.connection_state = "accepted"
                client.decision.set()
                return client_id, client.username, client.address[0]
        return None

    def reject_pending_connection(self) -> tuple[UUID, str, str] | None:
        with self._connections_lock:
            while self._pending_conn_order:
                client_id = self._pending_conn_order.popleft()
                client = self._client_conns.get(client_id)
                if client is None or client.connection_state != "pending":
                    continue
                connection = client.connection
                username = client.username
                client_ip = client.address[0]
                break
            else:
                return None
        try:
            connection.sendall(b"Server rejected your connection.")
            connection.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        self._remove_connection(client_id)
        connection.close()
        return client_id, username, client_ip

    def _remove_connection(self, client_id: UUID) -> None:
        with self._connections_lock:
            client = self._client_conns.pop(client_id, None)
            if client is not None and client.connection_state == "pending":
                client.decision.set()

    def send_message(self, message: bytes) -> None:
        with self._connections_lock:
            connections = tuple(
                client.connection
                for client in self._client_conns.values()
                if client.connection_state == "accepted"
            )
        for connection in connections:
            try:
                connection.sendall(message)
            except OSError:
                with self._connections_lock:
                    stale_ids = [
                        client_id
                        for client_id, client in self._client_conns.items()
                        if client.connection is connection
                    ]
                for client_id in stale_ids:
                    self._remove_connection(client_id)

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
            clients = tuple(self._client_conns.values())
            self._client_conns.clear()
            self._pending_conn_order.clear()
            for client in clients:
                if client.connection_state == "pending":
                    client.decision.set()
        for client in clients:
            client.connection.close()
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