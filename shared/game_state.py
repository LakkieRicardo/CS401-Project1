from server.server_ui import ServerStateUI
from client.client_ui import ClientStateUI
from .networking import NetworkInterface
from queue import Empty, SimpleQueue
from collections.abc import Callable
from threading import Thread
from uuid import UUID

class GameState():

    def __init__(
        self,
        exec_mode,
        pygame_ui_manager,
        network_interface: NetworkInterface | None = None,
        client_connection_factory: Callable[[str], NetworkInterface] | None = None,
    ):
        self.exec_mode = exec_mode
        self.pygame_ui_manager = pygame_ui_manager
        self._client_connection_factory = client_connection_factory
        self.message_history: list[str] = []
        self._incoming_network_messages: SimpleQueue[bytes] = SimpleQueue()
        self._incoming_connection_requests: SimpleQueue[tuple[UUID, str, str]] = SimpleQueue()
        self._incoming_connection_cancellations: SimpleQueue[tuple[UUID, str, str]] = SimpleQueue()
        if exec_mode == "server":
            self.ui_state = ServerStateUI(pygame_ui_manager, self)
        elif exec_mode == "connect":
            self.ui_state = ClientStateUI(pygame_ui_manager, self)
            self.ui_state.show_user_message("Enter your username in chat to connect.")
        self.network_interface = None
        if network_interface is not None:
            self.set_network_interface(network_interface)

    def set_network_interface(self, network_interface: NetworkInterface) -> None:
        self.network_interface = network_interface
        self.network_interface.set_message_callback(self.handle_network_message)
        self.network_interface.set_connection_request_callback(
            self.handle_connection_request
        )
        self.network_interface.set_connection_cancelled_callback(
            self.handle_connection_cancelled
        )

    def handle_connection_request(
        self, client_id: UUID, client_ip: str, username: str
    ) -> None:
        self._incoming_connection_requests.put((client_id, client_ip, username))

    def handle_connection_cancelled(
        self, client_id: UUID, client_ip: str, username: str
    ) -> None:
        self._incoming_connection_cancellations.put((client_id, client_ip, username))

    def handle_network_message(self, message: bytes) -> None:
        if self.exec_mode == "server" and self.network_interface is not None:
            self.network_interface.send_message(message)
        self._incoming_network_messages.put(message)

    def process_network_messages(self) -> None:
        history_changed = False
        while True:
            try:
                _, client_ip, username = self._incoming_connection_requests.get_nowait()
            except Empty:
                break
            self.message_history.append(
                f"User {username} from {client_ip} is requesting to join. Use /accept or /reject to decide."
            )
            history_changed = True
        while True:
            try:
                _, client_ip, username = self._incoming_connection_cancellations.get_nowait()
            except Empty:
                break
            self.message_history.append(
                f"User {username} from {client_ip} canceled their request to join."
            )
            history_changed = True
        while True:
            try:
                message = self._incoming_network_messages.get_nowait()
            except Empty:
                break
            self.message_history.append(message.decode("utf-8", errors="replace"))
            history_changed = True
        if history_changed:
            self.ui_state.show_message_history(self.message_history)

    def process_command(self, command: str) -> None:
        if self.exec_mode != "server" or self.network_interface is None:
            self.ui_state.show_user_message("Only the server can accept or reject clients.")
            return

        if command == "/accept":
            result = self.network_interface.accept_pending_connection()
            response = (
                f"Accepted {result[1]} from {result[2]}"
                if result is not None
                else "There are no pending connections to accept."
            )
        elif command == "/reject":
            result = self.network_interface.reject_pending_connection()
            response = (
                f"Rejected {result[1]} from {result[2]}"
                if result is not None
                else "There are no pending connections to reject."
            )
        else:
            return
        self.ui_state.show_user_message(response)

    def process_events(self, event) -> bool:
        return self.ui_state.process_events(event)

    def client_send_message(self, message: str):
        if self.network_interface is None:
            if self._client_connection_factory is None:
                self.ui_state.show_user_message("Client connection is not configured.")
                return
            username = message.strip()
            if not username:
                self.ui_state.show_user_message("Username cannot be empty.")
                return
            try:
                network_interface = self._client_connection_factory(username)
                self.set_network_interface(network_interface)
            except OSError as error:
                self.ui_state.show_user_message(f"Connection failed: {error}")
                return
            Thread(
                target=network_interface.listen_for_messages,
                daemon=True,
            ).start()
            self.ui_state.show_user_message(f"Connecting to {self.network_interface.get_connection_addr()} as {username}...")
            return
        self.network_interface.send_message(message.encode())