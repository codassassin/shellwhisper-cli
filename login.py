from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Button, Label
from textual.containers import Vertical, Center, Middle

from chat_screen import ChatScreen

import requests

class LoginScreen(Screen):
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Middle():
            with Center():
                with Vertical(id="login-form"):
                    yield Label("[bold cyan] Welcome to ShellWhisper[/]", id="title")
                    yield Input(placeholder="Username", id="username")
                    yield Input(placeholder="Password", password=True, id="password")
                    yield Button("Login", variant="success", id="login_btn")
                    yield Button("Need an account? Sign up", variant="default", id="to_signup")
        yield Footer()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login_btn":
            username = self.query_one("#username").value
            password = self.query_one("#password").value

            try:
                response = requests.post(
                    "http://localhost:8080/api/v1/auth/login",
                    json={"username": username, "password": password},
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    self.app.access_token = data.get("token")
                    self.app.notify(f"Welcome, {username}!", severity="success")
                    self.app.current_user = username
                    self.app.switch_screen(ChatScreen())
                elif response.status_code == 401:
                    self.app.notify("Invalid username or password", severity="error")
                else:
                    self.app.notify(f"Server Error: {response.status_code}", severity="error")
            
            except requests.exceptions.RequestException as e:
                self.app.notify("Could not connect to ShellWhisper server", severity="error")

        elif event.button.id == "to_signup":
            self.app.push_screen(SignupScreen())
    
class SignupScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back to Login")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="signup-form"):
                yield Label("[bold]Create Account[/]")
                yield Input(placeholder="Username", id="signup_user")
                yield Input(placeholder="Email", id="signup_email")
                yield Input(placeholder="Password", password=True, id="signup_pass")
                yield Button("Register", variant="primary", id="register_btn")
                yield Button("Back to Login", variant="default", id="back_btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_btn":
            self.dismiss()
        
        elif event.button.id == "register_btn":
            username = self.query_one("#signup_user").value
            email = self.query_one("#signup_email").value
            password = self.query_one("#signup_pass").value
            # self.app.notify(username + " " + email + " " + password)

            if not username or not password:
                self.app.notify("Username and Password required!", severity="error")
                return
            
            try:
                payload = {
                    "username": username,
                    "email": email,
                    "password": password
                }
                response = requests.post("http://localhost:8080/api/v1/auth/signup", json=payload)

                if response.status_code == 200:
                    self.app.notify("Account created! PLease login.", severity="information")
                    self.dismiss()
                else:
                    error_msg = response.text if response.text else "Signup failed"
                    self.app.notify(f"Error: {error_msg}", severity="error")

            except requests.exceptions.ConnectionError:
                self.app.notify("Backend server is not running!", severity="error")
