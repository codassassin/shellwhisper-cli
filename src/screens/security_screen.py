from textual.screen import ModalScreen
from textual.containers import Grid
from textual.widgets import Label, Input, Button

class SecurityScreen(ModalScreen):
    def compose(self):
        with Grid(id="security-dialog"):
            yield Label("Enter Security String", id="security-label")
            yield Input(placeholder="Secret key...",password=True, id="security-input")
            yield Button("Authenticate", variant="primary", id="auth_btn")

    def on_button_pressed(self, event):
        if event.button.id == "auth_btn":
            val = self.query_one("#security-input").value
            self.dismiss(val)
