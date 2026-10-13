from server.server_ui import ServerStateUI
from client.client_ui import ClientStateUI
from .networking import NetworkInterface
from queue import Empty, SimpleQueue

class GameState():

    def __init__(self, exec_mode, pygame_ui_manager, network_interface: NetworkInterface | None = None):
        self.exec_mode = exec_mode
        self.pygame_ui_manager = pygame_ui_manager
        self._incoming_network_messages: SimpleQueue[bytes] = SimpleQueue()
        if exec_mode == "server":
            self.ui_state = ServerStateUI(pygame_ui_manager, self)
        elif exec_mode == "connect":
            self.ui_state = ClientStateUI(pygame_ui_manager, self)
            self.ui_state.show_user_message("Connecting to {addr}")
        self.network_interface = None
        if network_interface is not None:
            self.set_network_interface(network_interface)

    def set_network_interface(self, network_interface: NetworkInterface) -> None:
        self.network_interface = network_interface
        self.network_interface.set_message_callback(self.handle_network_message)

    def handle_network_message(self, message: bytes) -> None:
        self._incoming_network_messages.put(message)

    def process_network_messages(self) -> None:
        while True:
            try:
                message = self._incoming_network_messages.get_nowait()
            except Empty:
                break
            self.ui_state.show_user_message(message.decode("utf-8", errors="replace"))

    def process_events(self, event) -> bool:
        return self.ui_state.process_events(event)

    def client_send_message(self, message: str):
        self.network_interface.send_message(message.encode())