import os
import pygame, pygame_gui
import sys
from shared.game_state import GameState
import threading
from client.client_connect import ClientConnect
from server.server_host import ServerHost

def print_usage():
    print("Usage: python game.py server <port>")
    print("Usage: python game.py connect <ip:port>")

if len(sys.argv) < 3:
    print_usage()
    sys.exit(1)

exec_mode = sys.argv[1]
if exec_mode not in ("server", "connect"):
    print_usage()
    sys.exit(1)

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption(exec_mode)
clock = pygame.time.Clock()
running = True
manager = pygame_gui.UIManager(screen.get_size(), os.path.join(os.path.dirname(__file__), "shared", "themes.json"))

network_interface = None
if exec_mode == "server":
    network_interface = ServerHost(int(sys.argv[2]))
    game_state = GameState(exec_mode, manager, network_interface)
    threading.Thread(target=network_interface.serve_forever, daemon=True).start()
    threading.Thread(target=network_interface.listen_for_messages, daemon=True).start()
else:
    host, port = sys.argv[2].rsplit(":", 1)
    client_connection_factory = lambda username: ClientConnect(
        host, int(port), username
    )
    game_state = GameState(
        exec_mode,
        manager,
        client_connection_factory=client_connection_factory,
    )

while running:
    time_delta = clock.tick(60) / 1000.0
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        event_handled = game_state.process_events(event)
        if not event_handled:
            manager.process_events(event)

    game_state.process_network_messages()
    manager.update(time_delta)
    # fill the screen with a color to wipe away anything from last frame
    screen.fill("black")
    manager.draw_ui(screen)
    pygame.display.flip()

if game_state.network_interface is not None:
    game_state.network_interface.close()
pygame.quit()