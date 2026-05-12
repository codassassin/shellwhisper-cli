from textual.app import App
from textual.message import Message

from src.events import NewWhisperReceived
from src.screens.chat_screen import ChatScreen
from src.screens.login import LoginScreen
from src.utils.api_client import APIClient

import stomp
import websocket
import json
import threading
class TerminalChatApp(App):
    SCREENS = {
        "login": LoginScreen,
        "chat": ChatScreen,
        # "signup": SignupScreen
    }
    BINDINGS = [
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]
    CSS_PATH = "styles/main.tcss"

    def __init__(self):
        super().__init__()
        self.api = APIClient(self)
        self.access_token = None
        self.current_user = None
        self.stomp_conn = None

    def on_mount(self) -> None:
        self.push_screen(LoginScreen())

    def action_logout(self) -> None:
        self.access_token = None
        self.current_user = None

        self.switch_screen(LoginScreen())
        self.notify("Logged out successfully", severity="information")

    def connect_websocket(self):
        try:
            ws_url = "ws://127.0.0.1:8080/chat/websocket"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }

            self.stomp_conn = websocket.create_connection(ws_url, header=headers)

            connect_frame = "CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\n\n\x00"
            self.stomp_conn.send(connect_frame)

            self.notify("Connected to ShellWhisper signal", severity="information")
        except Exception as e:
            self.notify(f"WebSocket connection failed: {str(e)}", severity="error")
            self.stomp_conn = None

        if self.stomp_conn:
            thread = threading.Thread(target=self.listen_for_messages, daemon=True)
            thread.start()

    def listen_for_messages(self):
        while self.stomp_conn and self.stomp_conn.sock:
            try:
                raw_data = self.stomp_conn.recv()

                # self.notify(f"DEBUG SOCKET RECEIVED: {raw_data}...", severity="debug")

                if "MESSAGE" in raw_data:
                    parts = raw_data.split('\n\n', 1)
                    if len(parts) > 1:
                        body_str = parts[1].rstrip('\x00')
                        message_data = json.loads(body_str)

                        self.screen.post_message(NewWhisperReceived(message_data))
            except Exception:
                break
