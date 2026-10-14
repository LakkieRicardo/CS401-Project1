import pygame, pygame_gui
from typing import TYPE_CHECKING
from shared.ui_state import StateUI
from shared.networking import encode_chat_message

if TYPE_CHECKING:
    from shared.game_state import GameState

class ServerStateUI(StateUI):

    def __init__(self, manager: pygame_gui.UIManager, game_state: "GameState"):
        super().__init__(manager, game_state)
        self.players_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0, 0, 320, 720),
            manager=manager,
            object_id="#players_panel",
        )
        self.players_title = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(12, 10, 296, 30),
            text="ACCEPTED PLAYERS",
            manager=manager,
            container=self.players_panel,
        )
        self.player_list = None
        self._player_rows = {}
        self._player_order = None
        self.refresh_player_list()

    def refresh_player_list(self) -> None:
        network_interface = self.game_state.network_interface
        players = (
            network_interface.accepted_players
            if network_interface is not None
            else ()
        )
        player_order = tuple((client_id, username) for client_id, username, _, _ in players)
        if player_order != self._player_order:
            for row in self._player_rows.values():
                for element in row:
                    element.kill()
            if self.player_list is not None:
                self.player_list.kill()
            self._player_rows = {}
            self.player_list = pygame_gui.elements.UIScrollingContainer(
                relative_rect=pygame.Rect(0, 46, 320, 674),
                manager=self.manager,
                container=self.players_panel,
                starting_height=max(674, len(players) * 82 + 16),
                allow_scroll_x=False,
                allow_scroll_y=True,
            )
            self._player_order = player_order
            if not players:
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(12, 10, 280, 28),
                    text="No accepted players",
                    manager=self.manager,
                    container=self.player_list,
                )
            for index, (client_id, username, _, _) in enumerate(players):
                row_y = 10 + index * 82
                username_label = pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(12, row_y, 280, 24),
                    text=username,
                    manager=self.manager,
                    container=self.player_list,
                )
                health_label = pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(12, row_y + 24, 280, 20),
                    text="",
                    manager=self.manager,
                    container=self.player_list,
                )
                health_bar = pygame_gui.elements.UIProgressBar(
                    relative_rect=pygame.Rect(12, row_y + 46, 280, 22),
                    manager=self.manager,
                    container=self.player_list,
                    object_id="#health_bar",
                )
                self._player_rows[client_id] = (
                    username_label,
                    health_label,
                    health_bar,
                )
        for client_id, _, current_health, max_health in players:
            _, health_label, health_bar = self._player_rows[client_id]
            health_label.set_text(f"{current_health} / {max_health} HP")
            health_bar.set_current_progress(current_health / max_health * 100)

    def handle_message_sent(self, message: str) -> None:
        formatted_message = f"Server: {message}"
        if self.game_state.network_interface is not None:
            self.game_state.network_interface.send_message(
                encode_chat_message(formatted_message)
            )
        self.add_chat_message(formatted_message)

    def process_events(self, event) -> bool:
        event_handled = super().process_events(event)
        return event_handled