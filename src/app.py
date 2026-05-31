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
        self.logout_process()

    def logout_process(self) -> None:
        from src.screens.login import LoginScreen

        try:
            self.api.logout_backend()
        except Exception:
            pass

        self._disconnect_websocket()
        self.access_token = None
        self.refresh_token = None
        self.current_user = None
        self.current_room_id = None
        self.file_cache.clear()

        self.notify("Logged out successfully", severity="information")
        self.switch_screen(LoginScreen())


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

                personal_sync_frame = (
                    f"SUBSCRIBE\n"
                    f"id:sub-user-sync\n"
                    f"destination:/user/queue/rooms/refresh\n"
                    f"ack:auto\n"
                    f"Authorization:Bearer {self.access_token}\n\n\x00"
                )
                conn.send(personal_sync_frame)

                if getattr(self, 'current_room_id', None):
                    restore_frame = (
                        f"SUBSCRIBE\n"
                        f"id:sub-{self.current_room_id}\n"
                        f"destination:/topic/room/{self.current_room_id}\n"
                        f"ack:auto\n"
                        f"Authorization:Bearer {self.access_token}\n\n\x00"
                    )
                    conn.send(restore_frame)

                delay = 1
                attempts = 0
                self.call_from_thread(
                    self.notify, "Connected to ShellWhisper signal", severity="information"
                )

                loop_should_continue = self._listen_for_messages()
                if loop_should_continue is False:
                    raise Exception("Broker explicitly rejected the subscription session.")

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
                if not raw_data:
                    continue

                if isinstance(raw_data, bytes):
                    if "ExecutorSubscribableChannel" in raw_data:
                        self.call_from_thread(
                            self.notify,
                            "Authentication Interceptor Refused Room Subscription.",
                            severity="error"
                        )
                        return False

                if raw_data.startswith("ERROR"):
                    self.call_from_thread(self.notify, f"Broker Error: {raw_data[:200]}", severity="error")

                if "MESSAGE" in raw_data:
                    normalized_data = raw_data.replace('\r\n', '\n')
                    parts = normalized_data.split('\n\n', 1)

                    if len(parts) > 1:
                        body_str = parts[1].rstrip('\x00')

                        try:
                            if not body_str.strip():
                                continue

                            message_data = json.loads(body_str)

                            if message_data.get("content") == "ROOM_DELETED_SIGNAL":
                                sender_name = message_data.get("sender")
                                deleter = sender_name if sender_name != self.current_user else "You"

                                self.call_from_thread(
                                    self.notify,
                                    f"Active room has been deleted by {deleter}.",
                                    severity="warning"
                                )

                                if self.current_room_id == message_data.get("roomId"):
                                    self.current_room_id = None
                                    self.file_cache.clear()
                                    self.call_from_thread(self.screen._clear_to_empty_viewport)

                                self.call_from_thread(self.screen.refresh_rooms)
                                continue

                            self.call_from_thread(
                                self.screen.post_message, NewWhisperReceived(message_data)
                            )
                        except json.JSONDecodeError as json_err:
                            self.call_from_thread(self.notify, f"JSON Error: {json_err}", severity="error")
                        except Exception as inner_err:
                            self.call_from_thread(self.notify, f"Event Error: {inner_err}", severity="error")
                else:
                    self.call_from_thread(self.notify, f"Malformed Frame Received: {raw_data[:100]}", severity="error")
            except Exception as ws_err:
                self.call_from_thread(self.notify, f"WebSocket crashed: {ws_err}", severity="error")
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

