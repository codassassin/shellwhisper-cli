from textual.widgets import Static, Label, Button, LoadingIndicator
from textual.containers import Vertical
from textual.app import ComposeResult

class Sidebar(Static):
    def compose(self) -> ComposeResult:
        yield Label("ShellWhisper", id="sidebar-title")
        yield Static(classes='spacer')

        yield Button("🌐 ROOM ACTIONS", id="btn_room_mgmt")
        yield Button("✉️ PRIVATE WHISPER", id="btn_private")

        yield Static(classes='spacer')
        yield Label("MY ROOMS", id="section-label")

        with Vertical(id="rooms-list"):
            yield LoadingIndicator()

        yield Static(classes='spacer')
        yield Button("Logout", variant="error", id="logout_btn")

    # async def update_rooms(self, rooms: list):
    #     rooms_list = self.query_one("#rooms-list")
    #     await rooms_list.query("*").remove()

    #     if not rooms:
    #         await rooms_list.mount(Label("No rooms yet...", classes="empty-msg"))
    #     else:
    #         current_user = self.app.current_user

    #         for room in rooms:
    #             display_name = room['roomName']

    #             if room.get("type") == "PRIVATE":
    #                 clean_name = display_name.replace("private_", "")

    #                 parts = clean_name.split("_")

    #                 if len(parts) == 2:
    #                     display_name = parts[1] if parts[0] == current_user else parts[0]

    #                 btn_label = f"💬 {display_name}"
    #             else:
    #                 btn_label = f"#{display_name}"

    #             btn = Button(
    #                 # label=f"#{room['roomName']}",
    #                 label=btn_label,
    #                 id=f"room_{room['id']}",
    #                 classes="room-link"
    #             )
    #             await rooms_list.mount(btn)

    async def update_rooms(self, rooms: list):
        rooms_list = self.query_one("#rooms-list")
        await rooms_list.query("*").remove()

        if not rooms:
            await rooms_list.mount(Label("No rooms yet...", classes="empty-msg"))
        else:
            current_user = self.app.current_user

            for room in rooms:
                room_name = room['roomName']
                room_type = room.get("type", "GROUP")

                if room_type == "PRIVATE":
                    raw = room_name

                    if raw.startswith("private_"):
                        raw = raw[len("private_"):]

                    other = raw

                    if raw.startswith(current_user + "_"):
                        other = raw[len(current_user) + 1:]
                    elif raw.endswith("_" + current_user):
                        other = raw[: -(len(current_user) + 1)]

                    btn_label = f"💬 {other}"
                else:
                    btn_label = room_name

                btn = Button(
                    label=btn_label,
                    id=f"room_{room['id']}",
                    classes="room-link"
                )

                await rooms_list.mount(btn)
