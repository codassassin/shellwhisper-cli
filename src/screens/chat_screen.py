import requests
from textual.app import ComposeResult
from textual.widgets import Header, Footer, Input, Label, RichLog, Button
from textual.screen import Screen
from textual.containers import Vertical, Horizontal

from src.components.sidebar import Sidebar
from src.screens.room_action_screen import RoomActionScreen
from src.screens.security_screen import SecurityScreen
from src.utils.api_client import APIClient

class ChatScreen(Screen):
    TITLE = "ShellWhisper"
    BINDINGS = [
        ("ctrl+l", "logout", "Logout"),
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]

    # def compose(self) -> ComposeResult:
    #     yield Header()
    #     with Horizontal():
    #         yield Sidebar(id="sidebar")
    #         with Vertical(id="chat-container"):
    #             yield RichLog(id="chat_log", highlight=True, markup=True)
    #             yield Input(placeholder="Type a whisper and press Enter...", id="chat_input")
    #     yield Footer()

    def compose(self):
        yield Sidebar(id="sidebar")
        with Horizontal():
            yield Label("Select a room to start whispering...", id="empty-view")

            with Vertical(id="chat-view"):
                yield RichLog(id="chat_log", highlight=True, markup=True)
                yield Input(placeholder="Type a whisper and press Enter...", id="chat_input")

        yield Footer()

    async def on_mount(self) -> None:
        self.sub_title = f"Logged in as {self.app.current_user}"
        rooms = self.fetch_user_rooms()
        self.call_after_refresh(self.update_sidebar_data, rooms)

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
        # self.app.notify(f"Switching to Room: {room_id}")

        self.app.current_room_id = room_id

        chat_view = self.query_one("#chat-view")
        chat_view.styles.display = "block"

        try:
            self.query_one("#empty-view").styles.display = "none"
        except:
            pass

        # self.app.notify(f"Switched to room {room_id}", severity="success")
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
                    sender = msg.get("senderUsername", "System")
                    content = msg.get("content", "")
                    chat_log.write(f"[bold cyan]{sender}:[/] {content}")
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
            # client = APIClient(self.app);
            # response = client.fetch_rooms()

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
        message = event.value.strip()
        if message:
            self.query_one("#chat_log").write(f"[bold cyan]You:[/] {message}")
            self.query_one("#chat_input").value = ""
