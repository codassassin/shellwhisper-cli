from textual.widgets import Header, Footer, Input, Label, RichLog, Button
from textual.screen import Screen
from textual.containers import Vertical, Horizontal

from src.events import NewWhisperReceived
from src.components.sidebar import Sidebar
from src.screens.room_action_screen import RoomActionScreen
from src.screens.security_screen import SecurityScreen
from src.utils.api_client import APIClient

import json

from datetime import datetime

class ChatScreen(Screen):
    TITLE = "ShellWhisper"
    BINDINGS = [
        ("ctrl+l", "logout", "Logout"),
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def compose(self):
        yield Header()

        with Horizontal():
            yield Sidebar(id="sidebar")

            with Vertical(id="chat-view-container"):
                yield Label("Select a room to start whispering...", id="empty-view")

                with Vertical(id="chat-view"):
                    yield RichLog(id="chat_log", highlight=True, markup=True)
                    yield Input(placeholder="Type a whisper and press Enter...", id="chat_input")

        yield Footer()

    async def on_mount(self) -> None:
        self.sub_title = f"Logged in as {self.app.current_user}"
        
        self.app.connect_websocket()
        
        self.rooms = self.fetch_user_rooms()
        
        self.call_after_refresh(self.update_sidebar_data, self.rooms)

    def update_sidebar_data(self, rooms) -> None:
        sidebar = self.query_one("#sidebar")
        self.app.run_worker(sidebar.update_rooms(rooms))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_room_mgmt":
            self.app.push_screen(RoomActionScreen(), self.handle_room_action)
        elif event.button.id == "btn_private":
            self.app.notify("Private whisper feature coming soon!", severity="warning")
        elif "room-link" in event.button.classes:
            room_id = event.button.id.replace("room_", "")
            self.switch_to_room(room_id)

    def handle_room_action(self, data: dict | None) -> None:
        if data:
            self.pending_room_data = data
            self.app.push_screen(SecurityScreen(), self.handle_security_auth)

    def handle_security_auth(self, security_string: str | None) -> None:
        if security_string:
            room_name = self.pending_room_data["name"]
            action = self.pending_room_data["action"]

            if action == "create_btn":
                self.app.notify(f"Creating {room_name} with key: {security_string}")
            else:
                self.app.notify(f"Joining {room_name} with key: {security_string}")

    def switch_to_room(self, room_id: str) -> None:
        self.app.current_room_id = room_id
        room = next((r for r in self.rooms if r['id'] == room_id), None)

        if not room:
            self.app.notify("Room details not found", severity="error")
            return

        # room_name = room['roomName']

        if self.app.stomp_conn and self.app.stomp_conn.sock:
            subscribe_frame = (
                f"SUBSCRIBE\n"
                f"id:{room_id}\n"
                f"destination:/topic/room/{room_id}\n"
                f"ack:auto\n\n"
                f"\x00"
            )
            
            try:
                self.app.stomp_conn.send(subscribe_frame)
            except Exception as e:
                self.app.notify(f"Subscribe failed: {str(e)}", severity="error")

        self.query_one("#chat-view").styles.display = "block"
        self.query_one("#empty-view").styles.display = "none"
        self.query_one("#chat_log").clear()
        self.fetch_and_display_messages(room_id)

    def fetch_and_display_messages(self, room_id: str) -> None:
        try:
            self.app.notify(f"Loading messages for room {room_id}...")
            response = self.app.api.fetch_messages(room_id)
            if response.status_code == 200:
                messages = response.json()
                chat_log = self.query_one("#chat_log", RichLog)

                for msg in messages:
                    sender = msg.get("sender", "System")
                    content = msg.get("content", "")

                    if sender == self.app.current_user:
                        chat_log.write(f"[bold cyan]You:[/] {content}")
                    else:
                        chat_log.write(f"[bold green]{sender}:[/] {content}")

            else:
                self.app.notify("Failed to load message history", severity="error")
        except Exception as e:
            self.app.notify(f"Error fetching messages: {e}", severity="error")

    def handle_join(self, room_id: str | None) -> None:
        if room_id:
            self.app.notify(f"Attempting to join: {room_id}")

    def fetch_user_rooms(self):
        try:
            response = self.app.api.fetch_rooms()

            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.app.notify(f"Failed to load rooms with exception {e}", severity="error")

        return []

    def fetch_messages(self, room_id: str):
        try:
            response = self.app.api.fetch_messages(room_id)

            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.app.notify(f"Failed to load messages with exception {e}", severity="error")


    def action_logout(self) -> None:
        self.logout_process()

    def logout_process(self):
        from src.screens.login import LoginScreen

        self.app.access_token = None

        if hasattr(self.app, 'conn') and self.app.conn.is_connected():
            self.app.conn.disconnect()

        self.app.notify("Logged out successfully", severity="information")
        self.app.switch_screen(LoginScreen())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        message_text = event.value.strip()
        if message_text and self.app.current_room_id:

            payload = {
                "sender": self.app.current_user,
                "content": message_text,
                "roomId": self.app.current_room_id,
                "messageTime": datetime.now().isoformat()
            }

            body = json.dumps(payload)
            stomp_frame = f"SEND\ndestination:/app/sendMessage\ncontent-type:application/json\n\n{body}\x00"

            if self.app.stomp_conn and self.app.stomp_conn.sock:
                try:
                    self.app.stomp_conn.send(stomp_frame)
                    # self.query_one("#chat_log").write(f"[bold cyan]You:[/] {message_text}")
                    self.query_one("#chat_input").value = ""
                except Exception as e:
                    self.app.notify(f"Failed to send message: {str(e)}", severity="error")
    
    def on_new_whisper_received(self, event: NewWhisperReceived) -> None:
        data = event.data
        sender = data.get("sender", "Unknown")
        content = data.get("content", "")
        chat_log = self.query_one("#chat_log")
        
        if sender == self.app.current_user:
            chat_log.write(f"[bold cyan]You:[/] {content}")
        else:
            chat_log.write(f"[bold green]{sender}:[/] {content}")