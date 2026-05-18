from textual.screen import ModalScreen
from textual.containers import Grid, Vertical
from textual.widgets import Label, Input, Button

class PrivateWhisperPromptScreen(ModalScreen):
    def compose(self):
        with Vertical(id="room-action-dialog"):
            yield Label("Start a Private Whisper", id="action-label")
            yield Input(placeholder="Enter target username...", id="room-input")

            with Grid(id="action-button-grid"):
                yield Button("Start Chat", variant="success", id="start_btn")
                yield Button("Cancel", variant="error", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.dismiss(None)
            return

        target_user = self.query_one("#room-input").value.strip()

        if not target_user:
            self.app.notify("Please enter a username.", severity="error")
            return

        self.dismiss(target_user)
