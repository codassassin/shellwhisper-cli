from textual.screen import ModalScreen
from textual.containers import Grid, Vertical
from textual.widgets import Label, Input, Button

class RoomActionScreen(ModalScreen):
    def compose(self):
        with Vertical(id="room-action-dialog"):
            yield Label("Room Actions", id="action-label")
            yield Input(placeholder="Enter room name...", id="room-input")

            with Grid(id="action-buttons-grid"):
                yield Button("Join Room", variant="primary", id="join_btn")
                yield Button("Create Room", variant="success", id="create_btn")

            yield Button("Cancel", variant="error", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.dismiss(None)
            return

        room_name = self.query_one("#room-input").value.strip()

        if not room_name:
            self.app.notify("Please enter a room name.", severity="error")
            return

        if not room_name.replace("-", "").replace("_", "").isalnum():
            self.app.notify(
                "Room name can only contain letters, numbers, hyphens and underscores.",
                severity="error",
            )
            return

        self.dismiss({"name": room_name, "action": event.button.id})