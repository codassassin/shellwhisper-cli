from textual.widgets import Static, Label, Button, LoadingIndicator
from textual.containers import Vertical
from textual.app import ComposeResult

class Sidebar(Static):
    def compose(self) -> ComposeResult:
        yield Label("ShellWhisper", id="sidebar-title")
        yield Static(classes='spacer')

        yield Button("🌐 ROOM ACTIONS", variant="primary", id="btn_room_mgmt")
        yield Button("✉️ PRIVATE WHISPER", variant="warning", id="btn_private")

        yield Static(classes='spacer')
        yield Label("MY ROOMS", id="section-label")

        with Vertical(id="rooms-list"):
            yield LoadingIndicator()

        yield Static(classes='spacer')
        yield Button("Logout", variant="error", id="logout_btn")

    async def update_rooms(self, rooms: list):
        rooms_list = self.query_one("#rooms-list")
        await rooms_list.query("*").remove()

        if not rooms:
            await rooms_list.mount(Label("No rooms yet...", classes="empty-msg"))
        else:
            for room in rooms:
                btn = Button(
                    Label=f"#{room['name']}",
                    id=f"room_{room['id']}",
                    classes="room-link"
                )
                await rooms_list.mount(btn)