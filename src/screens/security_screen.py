from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Label, Input, Button

class SecurityScreen(ModalScreen):

    def __init__(self, action: str = "authenticate", room_name: str = "") -> None:
        super().__init__()
        self.action = action
        self.room_name = room_name

    def compose(self):
        if self.action == "create_btn":
            title = f"Set Security Key for '{self.room_name}'"
            hint = "Others will need key to join."
            btn_label = "Create Room"
            btn_variant = "success"
        elif self.action == "chat_command_delete":
            title = f"Confirm Deletion of '{self.room_name}'"
            hint = "Enter the room security key to permanently delete this room."
            btn_label = "Delete Room"
            btn_variant = "error"
        else:
            title = f"Enter Security Key for '{self.room_name}'"
            hint = "The key set by the room creator."
            btn_label = "Join Room"
            btn_variant = "primary"

        with Vertical(id="security-dialog"):
            yield Label(title, id="security-label")
            yield Label(f"[dim]{hint}[/]", id="security-hint")
            yield Input(placeholder="Secret key...", password=True, id="security-input")
            yield Button(btn_label, variant=btn_variant, id="auth_btn")
            yield Button("Cancel", variant="error", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.dismiss(None)
        elif event.button.id == "auth_btn":
            val = self.query_one("#security-input").value.strip()
            if not val:
                self.app.notify("Security key cannot be empty.", severity="error")
                return
            self.dismiss(val)

