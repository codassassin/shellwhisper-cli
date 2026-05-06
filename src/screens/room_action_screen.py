from textual.screen import ModalScreen
from textual.containers import Grid, Vertical
from textual.widgets import Label, Input, Button

class RoomActionScreen(ModalScreen):
    def compose(self):
        with Vertical(id="room-action-dialog"):
            yield Label("Enter Room ID/Name", id="action-label")
            yield Input(placeholder="Room ID or Name", id="room-input")

            with Grid(id="action-buttons-grid"):
                yield Button("Join Room", variant="primary", id="join_btn")
                yield Button("Create Room", variant="success", id="create_btn")

            yield Button("Cancel", variant="error", id="cancel_btn")

    def on_button_pressed(self, event):
        room_name = self.query_one("#room-input").value.strip()

        if event.button.id == "cancel_btn":
            self.dismiss(None)
        elif not room_name and event.button.id != "cancel_btn":
            self.app.notify("Please enter a valid room name or ID.", severity="error")
        else:
            self.dismiss({"name": room_name, "action": event.button.id})