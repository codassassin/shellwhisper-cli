from textual.app import App

from src.events import NewWhisperReceived
from src.screens.chat_screen import ChatScreen
from src.screens.login import LoginScreen
from src.utils.api_client import APIClient

import websocket
import json
import threading
import time
import os
import base64

class TerminalChatApp(App):
    SCREENS = {
        "login": LoginScreen,
        "chat": ChatScreen,
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
        self.current_room_id = None
        self.stomp_conn = None
        self.file_cache = {}
        self._ws_reconnect = True
        self._ws_max_retries = 5

    def on_mount(self) -> None:
        self.push_screen(LoginScreen())

    def action_logout(self) -> None:
        self._disconnect_websocket()
        self.access_token = None
        self.current_user = None
        self.current_room_id = None
        self.file_cache.clear()
        self.switch_screen(LoginScreen())
        self.notify("Logged out successfully", severity="information")

        ### WebSocket / STOMP ###

    ### WEBSOCKET / STOMP ###

    def connect_websocket(self):
        self._ws_reconnect = True
        thread = threading.Thread(target=self._ws_connect_loop, daemon=True)
        thread.start()

    def _ws_connect_loop(self):
        delay = 1
        attempts = 0

        while self._ws_reconnect and attempts < self._ws_max_retries:
            conn = None
            try:
                ws_url = "ws://127.0.0.1:8080/chat/websocket"
                headers = [f"Authorization: Bearer {self.access_token}"]

                conn = websocket.create_connection(ws_url, header=headers)
                self.stomp_conn = conn

                connect_frame = (
                    f"CONNECT\n"
                    f"accept-version:1.1,1.2\n"
                    f"heart-beat:0,0\n"
                    f"Authorization:Bearer {self.access_token}\n\n\x00"
                )
                conn.send(connect_frame)

                response = conn.recv()
                if "CONNECTED" not in response:
                    raise Exception(f"STOMP handshake failed: {response[:100]}")

                delay = 1
                attempts = 0
                self.call_from_thread(
                    self.notify, "Connected to ShellWhisper signal", severity="information"
                )

                self._listen_for_messages()

            except Exception as e:
                error_detail = f"{type(e).__name__}: {e}"
                self.stomp_conn = None
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                conn = None
                attempts += 1

                if self._ws_reconnect and attempts < self._ws_max_retries:
                    self.call_from_thread(
                        self.notify,
                        f"WS error ({attempts}/{self._ws_max_retries}): {error_detail}",
                        severity="warning"
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                else:
                    self.call_from_thread(
                        self.notify,
                        f"Could not connect: {error_detail}",
                        severity="error",
                    )

    def _listen_for_messages(self):
        while self.stomp_conn and self.stomp_conn.sock:
            try:
                raw_data = self.stomp_conn.recv()

                if "MESSAGE" in raw_data:
                    parts = raw_data.split('\n\n', 1)
                    if len(parts) > 1:
                        body_str = parts[1].rstrip('\x00')
                        message_data = json.loads(body_str)
                        self.call_from_thread(
                            self.screen.post_message, NewWhisperReceived(message_data)
                        )
            except Exception:
                break

    def _disconnect_websocket(self):
        self._ws_reconnect = False
        if self.stomp_conn:
            try:
                disconnect_frame = "DISCONNECT\n\n\x00"
                self.stomp_conn.send(disconnect_frame)
                self.stomp_conn.close()
            except Exception:
                pass
            finally:
                self.stomp_conn = None

    ### File Download ###

    def action_download_file(self, filename: str) -> None:
        if filename not in self.file_cache:
            self.notify(f"File '{filename}' not in cache.", severity="error")
            return
        try:
            save_path = os.path.join(os.getcwd(), "downloads")
            os.makedirs(save_path, exist_ok=True)

            full_path = os.path.join(save_path, filename)
            binary_data = base64.b64decode(self.file_cache[filename])

            with open(full_path, "wb") as f:
                f.write(binary_data)

            self.notify(f"Whisper saved to: {full_path}", severity="success")
        except Exception as e:
            self.notify(f"Download failed: {e}", severity="error")

