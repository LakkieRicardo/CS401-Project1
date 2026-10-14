import socket
from collections import deque
import time
from shared.networking import NetworkInterface, encode_chat_message

message_q = deque()


class ClientConnect(NetworkInterface):
    def __init__(self, host: str, port: int, username: str):
        super().__init__()
        self._host = host
        self._port = port
        self.username = username
        self._connection = socket.create_connection((host, port))
        self._connection.sendall(f"{username}\n".encode("utf-8"))

    def send_message(self, message: bytes) -> None:
        self._connection.sendall(message)

    def receive_message(self, buffer_size: int = 1024) -> bytes:
        return self._connection.recv(buffer_size)

    def close(self) -> None:
        try:
            self._connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._connection.close()

    def get_connection_addr(self) -> str:
        return f"{self._host}:{self._port}"


def queue_message(msg: str):
    message_q.append(msg)

def connect_to_server(host, port, username):
    client = ClientConnect(host, port, username)
    try:
        while True:
            if len(message_q) > 0:
                msg_to_send = message_q.popleft()
                client.send_message(encode_chat_message(msg_to_send))
            else:
                time.sleep(0.1)
    finally:
        client.close()

