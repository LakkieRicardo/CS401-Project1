import pygame, pygame_gui
from typing import TYPE_CHECKING
from shared.ui_state import StateUI

if TYPE_CHECKING:
    from shared.game_state import GameState

class ClientStateUI(StateUI):

    def __init__(self, manager: pygame_gui.UIManager, game_state: "GameState"):
        super().__init__(manager, game_state)
        self.hello_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((350, 275), (100, 50)), text='YOU ARE THE CLIENT', manager=manager)

    def process_events(self, event) -> bool:
        event_handled = super().process_events(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.hello_button:
            print("hello button pressed")
        return event_handled

    def handle_message_sent(self, message: str) -> None:
        self.game_state.client_send_message(message)