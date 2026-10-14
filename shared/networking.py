import socket
from abc import ABC, abstractmethod
from collections.abc import Callable
from uuid import UUID


MessageCallback = Callable[[bytes], None]
ConnectionRequestCallback = Callable[[UUID, str, str], None]
ConnectionCancelledCallback = Callable[[UUID, str, str], None]


class NetworkInterface(ABC):
    def __init__(self) -> None:
        self._message_callback: MessageCallback | None = None
        self._connection_request_callback: ConnectionRequestCallback | None = None
        self._connection_cancelled_callback: ConnectionCancelledCallback | None = None

    def set_message_callback(self, callback: MessageCallback) -> None:
        self._message_callback = callback

    def _dispatch_message(self, message: bytes) -> None:
        if self._message_callback is not None:
            self._message_callback(message)

    def set_connection_request_callback(
        self, callback: ConnectionRequestCallback
    ) -> None:
        self._connection_request_callback = callback

    def _dispatch_connection_request(
        self, client_id: UUID, client_ip: str, username: str
    ) -> None:
        if self._connection_request_callback is not None:
            self._connection_request_callback(client_id, client_ip, username)

    def set_connection_cancelled_callback(
        self, callback: ConnectionCancelledCallback
    ) -> None:
        self._connection_cancelled_callback = callback

    def _dispatch_connection_cancelled(
        self, client_id: UUID, client_ip: str, username: str
    ) -> None:
        if self._connection_cancelled_callback is not None:
            self._connection_cancelled_callback(client_id, client_ip, username)

    def accept_pending_connection(self) -> tuple[UUID, str, str] | None:
        return None

    def reject_pending_connection(self) -> tuple[UUID, str, str] | None:
        return None

    def listen_for_messages(self) -> None:
        try:
            while message := self.receive_message():
                self._dispatch_message(message)
        except OSError:
            return

    @abstractmethod
    def send_message(self, message: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def receive_message(self, buffer_size: int = 1024) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class SocketNetworkInterface(NetworkInterface):
    def __init__(self, connection: socket.socket) -> None:
        super().__init__()
        self._connection = connection

    def send_message(self, message: bytes) -> None:
        self._connection.sendall(message)

    def receive_message(self, buffer_size: int = 1024) -> bytes:
        return self._connection.recv(buffer_size)

    def close(self) -> None:
        self._connection.close()