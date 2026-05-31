from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label
from textual.containers import Vertical, Center, Middle

class ForgotPasswordScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back to Login")]

    def compose(self) -> ComposeResult:
        yield Header()

        with Middle():
            with Center():
                with Vertical(id="login-form"):
                    yield Label("[bold yellow]Reset Password[/]", id="title")
                    yield Label("Enter your registered email address:", classes="hint")
                    yield Input(placeholder="Email", id="reset_email")
                    yield Button("Send Reset Code", variant="primary", id="send_code_btn")
                    yield Button("Back to Login", variant="default", id="back_btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_btn":
            self.dismiss()
        elif event.button.id == "send_code_btn":
            email = self.query_one("#reset_email").value.strip()
            if not email:
                self.app.notify("Email is required", severity="error")
                return

            try:
                self.app.api.request_password_reset(email)
                self.app.notify("Reset code sent! Check you email.", severity="information")
                self.app.switch_screen(ConfirmResetScreen(email=email))
            except Exception:
                self.app.notify("Failed to contact server.", severity="error")

class ConfirmResetScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back to Login")]

    def __init__(self, email: str = ""):
        super().__init__()
        self.target_email = email

    def compose(self) -> ComposeResult:
        yield Header()

        with Middle():
            with Center():
                with Vertical(id="login-form"):
                    yield Label("[bold green]Confirm New Password[/]", id="title")
                    yield Label(f"Code sent to {self.target_email}", classes="hint")
                    yield Input(placeholder="8-Character Code", id="reset_code")
                    yield Input(placeholder="New Password", password=True, id="new_pass")
                    yield Button("Update Password", variant="success", id="update_btn")
                    yield Button("Cancel", variant="error", id="cancel_btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from src.screens.login import LoginScreen
        if event.button.id == "cancel_btn":
            self.app.switch_screen(LoginScreen())
        elif event.button.id == "update_btn":
            code = self.query_one("#reset_code").value.strip()
            new_pass = self.query_one("#new_pass").value.strip()

            if not code or not new_pass:
                self.app.notify("All fields are required", severity="error")
                return

            try:
                res = self.app.api.confirm_password_reset(self.target_email, code, new_pass)
                if res.status_code == 200:
                    self.app.notify("Password updated successfully! Please log in.", severity="success")
                    self.app.switch_screen(LoginScreen())
                else:
                    self.app.notify("Invalid or expired code.", severity="error")
            except Exception:
                self.app.notify("Failed to contact server", severity="error")
