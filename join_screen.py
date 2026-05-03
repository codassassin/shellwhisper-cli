from textual.screen import ModalScreen
from textual.containers import Grid
from textual.widgets import Input, Label, Button

class JoinRoomScreen(ModalScreen):

    def compose(self):
        with Grid(id="join-dialog"):
            yield Label("Enter Room ID to Join", id="join-label")
            yield Input(placeholder="Room ID", id="room-id-input")
            yield Button("Join Room", variant="primary", id="confirm-join")
            yield Button("Cancel", variant="error", id="cancel-join")

    def on_button_pressed(self, event):
        if event.button.id == "confirm-join":
            room_id = self.query_one("#room-id-input").value
            
            self.dismiss(room_id)
        else:
            self.dismiss(None)
