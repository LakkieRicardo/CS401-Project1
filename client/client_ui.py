import pygame, pygame_gui
from typing import TYPE_CHECKING
from shared.ui_state import StateUI

if TYPE_CHECKING:
    from shared.game_state import GameState

class ClientStateUI(StateUI):

    def __init__(self, manager: pygame_gui.UIManager, game_state: "GameState"):
        super().__init__(manager, game_state)
        self.hello_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((350, 275), (100, 50)), text='YOU ARE THE CLIENT', manager=manager)
        self.health_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 320, 112),
            manager=manager,
            object_id="#health_panel",
        )
        self.health_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 8, 296, 26),
            text="YOUR HEALTH",
            manager=manager,
            container=self.health_panel,
        )
        self.health_value = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 36, 296, 22),
            text="",
            manager=manager,
            container=self.health_panel,
        )
        self.health_bar = pygame_gui.elements.UIProgressBar(
            relative_rect=pygame.Rect(12, 66, 296, 24),
            manager=manager,
            container=self.health_panel,
            object_id="#health_bar",
        )
        self.health_panel.hide()

    def update_own_health(self, current_health: int, max_health: int) -> None:
        self.health_value.set_text(f"{current_health} / {max_health} HP")
        self.health_bar.set_current_progress(current_health / max_health * 100)
        self.health_panel.show()

    def process_events(self, event) -> bool:
        event_handled = super().process_events(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.hello_button:
            print("hello button pressed")
        return event_handled

    def handle_message_sent(self, message: str) -> None:
        self.game_state.client_send_message(message)