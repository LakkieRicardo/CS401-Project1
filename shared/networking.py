import socket
from abc import ABC, abstractmethod
from collections.abc import Callable


MessageCallback = Callable[[bytes], None]


class NetworkInterface(ABC):
    def __init__(self) -> None:
        self._message_callback: MessageCallback | None = None

    def set_message_callback(self, callback: MessageCallback) -> None:
        self._message_callback = callback

    def _dispatch_message(self, message: bytes) -> None:
        if self._message_callback is not None:
            self._message_callback(message)

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