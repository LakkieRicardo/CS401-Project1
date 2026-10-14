import socket
from abc import ABC, abstractmethod
from collections.abc import Callable
from uuid import UUID


MessageCallback = Callable[[bytes], None]
ConnectionRequestCallback = Callable[[UUID, str, str], None]
ConnectionCancelledCallback = Callable[[UUID, str, str], None]
DisconnectCallback = Callable[[OSError | None], None]
CHAT_MESSAGE_TYPE = 0
HEALTH_UPDATE_TYPE = 1


def encode_chat_message(message: str) -> bytes:
    return bytes((CHAT_MESSAGE_TYPE,)) + message.encode("utf-8") + b"\n"


def decode_chat_message(message: bytes) -> str | None:
    if not message or message[0] != CHAT_MESSAGE_TYPE:
        return None
    return message[1:].rstrip(b"\r\n").decode("utf-8", errors="replace")


def encode_health_update(current_health: int, max_health: int) -> bytes:
    if (
        type(current_health) is not int
        or type(max_health) is not int
        or max_health <= 0
        or not 0 <= current_health <= max_health
        or max_health > 0xFFFFFFFF
    ):
        raise ValueError("Health values must fit in unsigned 32-bit fields.")
    return bytes((HEALTH_UPDATE_TYPE,)) + max_health.to_bytes(
        4, "big"
    ) + current_health.to_bytes(4, "big")


def decode_health_update(message: bytes) -> tuple[int, int] | None:
    if (
        len(message) != 9
        or message[0] != HEALTH_UPDATE_TYPE
    ):
        return None
    max_health = int.from_bytes(message[1:5], "big")
    current_health = int.from_bytes(message[5:9], "big")
    if max_health <= 0 or current_health < 0 or current_health > max_health:
        return None
    return current_health, max_health


def extract_complete_messages(pending: bytearray) -> tuple[bytes, ...]:
    messages = []
    while pending:
        if pending[0] == CHAT_MESSAGE_TYPE:
            line_end = pending.find(b"\n", 1)
            if line_end < 0:
                break
            messages.append(bytes(pending[: line_end + 1]))
            del pending[: line_end + 1]
        elif pending[0] == HEALTH_UPDATE_TYPE:
            if len(pending) < 9:
                break
            messages.append(bytes(pending[:9]))
            del pending[:9]
        else:
            del pending[0]
    return tuple(messages)


class NetworkInterface(ABC):
    def __init__(self) -> None:
        self._message_callback: MessageCallback | None = None
        self._connection_request_callback: ConnectionRequestCallback | None = None
        self._connection_cancelled_callback: ConnectionCancelledCallback | None = None
        self._disconnect_callback: DisconnectCallback | None = None

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

    def set_disconnect_callback(self, callback: DisconnectCallback) -> None:
        self._disconnect_callback = callback

    def _dispatch_disconnect(self, error: OSError | None) -> None:
        if self._disconnect_callback is not None:
            self._disconnect_callback(error)

    def accept_pending_connection(self) -> tuple[UUID, str, str] | None:
        return None

    def reject_pending_connection(self) -> tuple[UUID, str, str] | None:
        return None

    def kick_client(self, username: str) -> tuple[str, str] | None:
        return None

    def ban_ip(self, ip_address: str) -> tuple[tuple[str, str], ...] | None:
        return None

    def unban_ip(self, ip_address: str) -> bool | None:
        return None

    @property
    def accepted_players(self) -> tuple[tuple[UUID, str, int, int], ...]:
        return ()

    def set_player_health(
        self, client_id: UUID, current_health: int, max_health: int | None = None
    ) -> tuple[int, int] | None:
        return None

    def listen_for_messages(self) -> None:
        pending = bytearray()
        while True:
            try:
                chunk = self.receive_message()
            except OSError as error:
                if pending and pending[0] == CHAT_MESSAGE_TYPE:
                    self._dispatch_message(bytes(pending))
                self._dispatch_disconnect(error)
                return
            if not chunk:
                if pending and pending[0] == CHAT_MESSAGE_TYPE:
                    self._dispatch_message(bytes(pending))
                self._dispatch_disconnect(None)
                return
            pending.extend(chunk)
            for message in extract_complete_messages(pending):
                self._dispatch_message(message)

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