import requests
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, LoadingIndicator, RichLog, Button, Label, Static
from textual.screen import Screen
from textual.containers import Vertical, Horizontal

from join_screen import JoinRoomScreen

class ChatScreen(Screen):
    TITLE = "ShellWhisper"
    BINDINGS = [
        ("ctrl+l", "logout", "Logout"),
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def _on_mount(self) -> None:
        username = getattr(self.app, "current_user", "Guest")
        self.sub_title = f"Logged in as {username}"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():

            with Vertical(id="sidebar"):
                yield Label("SHELLWHISPER", id="sidebar-title")
                yield Static(classes='spacer')

                yield Button(" + CREATE ROOM", variant="success", id="btn_create")
                yield Static(classes='spacer-room-btn')
                yield Button(" > JOIN ROOM", variant="primary", id="btn_join")

                yield Static(classes='spacer')
                yield Label("MY ROOMS", id="section-label")
                with Vertical(id="rooms-list"):
                    yield LoadingIndicator()

                yield Button("# public-chat", classes="room-link")

                yield Static(classes='spacer')
                yield Button("Logout", variant="error", id="logout_btn")

            with Vertical(id="chat-container"):
                yield RichLog(id="chat_log", highlight=True, markup=True)
                yield Input(placeholder="Type a whisper and press Enter...", id="chat_input")
        yield Footer()

    async def on_mount(self) -> None:
        rooms = self.fetch_user_rooms()
        rooms_list = self.query_one("#rooms-list")

        await rooms_list.query("*").remove()

        if not rooms:
            await rooms_list.mount(Label("No rooms yet...", classes="empty-msg"))
        else:
            for room in rooms:
                new_room_btn = Button(
                    label=f"#{room['name']}",
                    id=f"room_{room['id']}",
                    classes="room-link"
                )
                await rooms_list.mount(new_room_btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create":
            self.app.notify("Opening Create Room dialog...")
        elif event.button.id == "btn_join":
            self.app.notify("Enter Room ID to join")
            self.app.push_screen(JoinRoomScreen(), self.handle_join)
        elif event.button.id == "logout_btn":
            from login import LoginScreen
            self.app.switch_screen(LoginScreen())
        elif event.button.classes == "room-link":
            room_id = event.button.id.replace("room_", "")
            self.switch_to_room(room_id)

    def switch_to_room(self, room_id) -> None:
        self.app.notify(f"Switching to Room: {room_id}")
        self.query_one("#chat_log").clear()
        self.app.current_room_id = room_id

    def handle_join(self, room_id: str | None) -> None:
        if room_id:
            self.app.notify(f"Attempting to join: {room_id}")

    def on_button_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()

        if message:
            chat_log = self.query_one("#chat_log", RichLog)
            chat_log.write(f"[bold cyan]You:[/] {message}")
            self.query_one("#chat_input").value = ""

    def fetch_user_rooms(self):
        url="http://localhost:8080/api/v1/room/all"
        headers = {"Authorization": f"Bearer {self.app.access_token}"}

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.app.notify(f"Failed to load rooms with exception {e}", severity="error")

        return []


    def action_logout(self) -> None:
        self.logout_process()

    def logout_process(self):
        from login import LoginScreen

        self.app.access_token = None

        if hasattr(self.app, 'conn') and self.app.conn.is_connected():
            self.app.conn.disconnect()

        self.app.notify("Logged out successfully", severity="information")
        self.app.switch_screen(LoginScreen())
