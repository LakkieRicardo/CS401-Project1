import socket
from collections import deque
import time
from shared.networking import NetworkInterface

message_q = deque()


class ClientConnect(NetworkInterface):
    def __init__(self, host: str, port: int):
        super().__init__()
        self._connection = socket.create_connection((host, port))

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


def queue_message(msg: str):
    message_q.append(msg)

def connect_to_server(host, port):
    client = ClientConnect(host, port)
    try:
        while True:
            if len(message_q) > 0:
                msg_to_send = message_q.popleft()
                client.send_message(msg_to_send.encode("utf-8"))
            else:
                time.sleep(0.1)
    finally:
        client.close()

