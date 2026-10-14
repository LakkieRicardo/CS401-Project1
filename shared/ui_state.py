import html
from typing import TYPE_CHECKING

import pygame, pygame_gui

if TYPE_CHECKING:
    from shared.game_state import GameState

class StateUI():

    def __init__(self, manager: pygame_gui.UIManager, game_state: "GameState"):
        self.manager = manager
        self.game_state = game_state
        # Add reference to network interface
        self.chat_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(-400, 0, 400, 720),
            manager=self.manager,
            anchors={
                "left": "right",
                "right": "right",
                "top": "top",
                "bottom": "bottom",
            },
            object_id="#chat_panel",
        )
        self.chat_field = pygame_gui.elements.UITextEntryBox(
            relative_rect=pygame.Rect(0, -100, 400, 100),
            manager=self.manager,
            container=self.chat_panel,
            anchors={
                "left": "left",
                "right": "right",
                "top": "bottom",
                "bottom": "bottom",
            },
        )
        self.chat_history = pygame_gui.elements.UITextBox(
            html_text="",
            relative_rect=pygame.Rect(0, 0, 400, 620),
            manager=self.manager,
            container=self.chat_panel,
            object_id="#chat_history",
        )
        self.button_a = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((350, 175), (100, 50)), text='Button A', manager=manager)

    def add_chat_message(self, message: str) -> None:
        self.game_state.message_history.append(message)
        self.show_message_history(self.game_state.message_history)

    def show_user_message(self, message: str) -> None:
        self.game_state.message_history.append(message)
        self.show_message_history(self.game_state.message_history)

    def show_message_history(self, messages: list[str]) -> None:
        formatted_messages = "".join(
            f'<font color="#ffcccc">{html.escape(message)}</font><br>'
            for message in messages
        )
        self.chat_history.set_text(formatted_messages)
        if self.chat_history.scroll_bar is not None:
            self.chat_history.scroll_bar.set_scroll_from_start_percentage(1.0)

    def process_command(self, command: str) -> None:
        if command == "/hello":
            self.show_user_message("APP: HAIII :3")
        elif command == "/help":
            self.show_user_message("APP: Available commands: /help /hello /accept /reject")
        elif command in ("/accept", "/reject"):
            self.game_state.process_command(command)
        else:
            self.show_user_message("ERROR: Unrecognized command. Type /help for help.")

    def handle_message_sent(self, message: str):
        pass

    def process_events(self, event) -> bool:
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.button_a:
            print("button a clicked")
        if (
            event.type == pygame.KEYDOWN
            and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER)
            and self.chat_field.is_focused
        ):
            message = self.chat_field.get_text().strip()
            self.chat_field.set_text("")
            if message:
                if message.startswith("/"):
                    self.process_command(message)
                else:
                    self.handle_message_sent(message)
            return True
        return False