from textual.app import App

from src.screens.login import LoginScreen
from src.utils.api_client import APIClient

class TerminalChatApp(App):
    # SCREENS = {
    #     "login": LoginScreen,
    #     "chat": ChatScreen,
    #     "signup": SignupScreen
    # }
    BINDINGS = [
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]
    CSS_PATH = "styles/main.tcss"

    def __init__(self):
        super().__init__()
        self.api = APIClient(self)
        self.access_token = None
        self.current_user = None

    def on_mount(self) -> None:
        # self.api = APIClient(self)
        # self.push_screen(ChatScreen())
        self.push_screen(LoginScreen())

    def action_logout(self) -> None:
        self.access_token = None
        self.current_user = None

        self.switch_screen(LoginScreen())
        self.notify("Logged out successfully", severity="information")